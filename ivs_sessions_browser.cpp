// File: src/ivs_sessions_browser.cpp
// Build: g++ -std=c++17 -O2 src/ivs_sessions_browser.cpp -lncurses -lcurl -o ivs_sessions_browser
// Runtime deps: ncurses, libcurl; Linux with xdg-open for launching URLs
// Purpose: C++ OOP TUI port of Python ivs_sessions_browser.py
// Notes (why): We avoid heavy HTML parsers and use targeted regex for IVSCC table structure
//              to keep dependencies minimal while matching the original behavior.

#include <algorithm>
#include <array>
#include <chrono>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <curses.h>
#include <curl/curl.h>
#include <getopt.h>
#include <iomanip>
#include <iostream>
#include <locale>
#include <map>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

using std::array;
using std::pair;
using std::size_t;
using std::string;
using std::string_view;
using std::unordered_map;
using std::vector;

namespace util {

static inline string ltrim(string s) {
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), [](unsigned char ch) { return !std::isspace(ch); }));
    return s;
}
static inline string rtrim(string s) {
    s.erase(std::find_if(s.rbegin(), s.rend(), [](unsigned char ch) { return !std::isspace(ch); }).base(), s.end());
    return s;
}
static inline string trim(string s) { return rtrim(ltrim(std::move(s))); }

static inline string tolower_copy(string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return std::tolower(c); });
    return s;
}

// Left-justify, truncate to width, pad with spaces
static inline string ljust(string_view sv, int width) {
    string s(sv);
    if ((int)s.size() > width) return s.substr(0, static_cast<size_t>(width));
    if ((int)s.size() < width) s.append(static_cast<size_t>(width - (int)s.size()), ' ');
    return s;
}

static inline vector<string> split_regex(const string& s, const std::regex& re) {
    std::sregex_token_iterator it(s.begin(), s.end(), re, -1);
    std::sregex_token_iterator end;
    vector<string> out;
    for (; it != end; ++it) {
        string tok = util::trim(it->str());
        if (!tok.empty()) out.push_back(tok);
    }
    return out;
}

static inline bool starts_with(const string& s, const string& pref) {
    return s.size() >= pref.size() && std::equal(pref.begin(), pref.end(), s.begin());
}

// strptime helper for "%Y-%m-%d %H:%M"
static inline bool parse_start_time(const string& s, std::tm& out) {
    std::istringstream iss(s);
    iss >> std::get_time(&out, "%Y-%m-%d %H:%M");
    return !iss.fail();
}

} // namespace util

// ---------------------------- HTTP (libcurl) ----------------------------
namespace http {

static size_t write_cb(char* ptr, size_t size, size_t nmemb, void* userdata) {
    auto* buf = static_cast<string*>(userdata);
    buf->append(ptr, size * nmemb);
    return size * nmemb;
}

static string get(const string& url, long timeout_sec = 20) {
    CURL* curl = curl_easy_init();
    if (!curl) throw std::runtime_error("curl_easy_init failed");
    string buf;
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &buf);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "ivs_sessions_browser/1.0");
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_sec);
    CURLcode rc = curl_easy_perform(curl);
    long http_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
    curl_easy_cleanup(curl);
    if (rc != CURLE_OK || http_code >= 400) {
        std::ostringstream oss;
        oss << "HTTP GET failed (" << url << ") rc=" << rc << " http=" << http_code;
        throw std::runtime_error(oss.str());
    }
    return buf;
}

} // namespace http

// ---------------------------- Data model ----------------------------
struct Meta {
    string active;
    string removed;
};

struct Row {
    std::array<string, 11> cols; // Type, Code, Start, DOY, Dur, Stations, DB Code, Ops Center, Correlator, Status, Analysis
    string url;                   // may be empty
    Meta meta;
};

// Column layout (titles & widths)
struct Column { const char* title; int width; };
static const array<Column, 11> HEADERS = {Column{"Type",14}, {"Code",8}, {"Start",18}, {"DOY",3}, {"Dur",5},
                                          {"Stations",44}, {"DB Code",14}, {"Ops Center",10}, {"Correlator",10}, {"Status",20}, {"Analysis",10}};
static const array<int, 11> WIDTHS = {14,8,18,3,5,44,14,10,10,20,10};

static const unordered_map<string, int> FIELD_INDEX = {
    {"type",0}, {"code",1}, {"start",2}, {"doy",3}, {"dur",4}, {"stations",5}, {"db code",6}, {"db",6},
    {"ops center",7}, {"ops",7}, {"correlator",8}, {"status",9}, {"analysis",10}
};

// ---------------------------- HTML parsing (targeted) ----------------------------
namespace html {

static string strip_tags(const string& in) {
    string out; out.reserve(in.size());
    bool in_tag = false;
    for (char c : in) {
        if (c == '<') in_tag = true;
        else if (c == '>') in_tag = false;
        else if (!in_tag) out.push_back(c);
    }
    return util::trim(out);
}

static vector<string> find_tr_blocks(const string& html) {
    auto to_lower = [](string s){ std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c){ return std::tolower(c); }); return s; };
    string low = to_lower(html);
    size_t t0 = low.find("<table"); if (t0 == string::npos) return {};
    size_t t0_end = low.find('>', t0); if (t0_end == string::npos) return {};
    size_t t1 = low.find("</table>", t0_end); if (t1 == string::npos) return {};
    string table = html.substr(t0_end + 1, t1 - (t0_end + 1));
    string table_low = low.substr(t0_end + 1, t1 - (t0_end + 1));

    vector<string> trs;
    size_t pos = 0;
    while (true) {
        size_t a = table_low.find("<tr", pos); if (a == string::npos) break;
        size_t a_end = table_low.find('>', a); if (a_end == string::npos) break;
        size_t b = table_low.find("</tr>", a_end); if (b == string::npos) break;
        trs.emplace_back(table.substr(a, b + 5 - a));
        pos = b + 5;
    }
    return trs;
}

static vector<string> extract_tds(const string& tr_html) {
    string low = tr_html; std::transform(low.begin(), low.end(), low.begin(), [](unsigned char c){ return std::tolower(c); });
    if (low.find("<th") != string::npos) return {};
    vector<string> tds;
    size_t pos = 0;
    while (true) {
        size_t a = low.find("<td", pos); if (a == string::npos) break;
        size_t a_end = low.find('>', a); if (a_end == string::npos) break;
        size_t b = low.find("</td>", a_end); if (b == string::npos) break;
        tds.emplace_back(tr_html.substr(a, b + 5 - a));
        pos = b + 5;
    }
    return tds;
}

static string find_anchor_href(const string& td_html) {
    string low = td_html; std::transform(low.begin(), low.end(), low.begin(), [](unsigned char c){ return std::tolower(c); });
    size_t a = low.find("<a"); if (a == string::npos) return {};
    size_t href = low.find("href=\"", a); if (href == string::npos) return {};
    size_t start = href + 6; // at the opening quote
    start += 1; // move past quote
    size_t end = td_html.find('"', start);
    if (end == string::npos) return {};
    return td_html.substr(start, end - start);
}

static pair<string,string> parse_stations(const string& td_html) {
    string low = td_html; std::transform(low.begin(), low.end(), low.begin(), [](unsigned char c){ return std::tolower(c); });
    vector<string> active, removed;
    size_t pos = 0;
    while (true) {
        size_t li = low.find("<li", pos); if (li == string::npos) break;
        size_t li_end = low.find('>', li); if (li_end == string::npos) break;
        size_t close = low.find("</li>", li_end); if (close == string::npos) break;
        string li_open = low.substr(li, li_end - li + 1);
        string content = td_html.substr(li_end + 1, close - (li_end + 1));
        string classes;
        size_t cls = li_open.find("class=\"");
        if (cls != string::npos) {
            size_t cls_start = cls + 7; size_t cls_end = li_open.find('"', cls_start);
            if (cls_end != string::npos) classes = li_open.substr(cls_start, cls_end - cls_start);
        }
        string text = strip_tags(content);
        text = util::trim(text);
        string code; for (char c : text) if (std::isalnum((unsigned char)c)) code.push_back(c);
        if (!code.empty()) {
            string cls_low = util::tolower_copy(classes);
            if (cls_low.find("removed") != string::npos) removed.push_back(code);
            else active.push_back(code);
        }
        pos = close + 5;
    }
    auto join = [](const vector<string>& v){ string out; for (const auto& s : v) out += s; return out; };
    return {join(active), join(removed)};
}

static string inner_text(const string& td_html) { return util::trim(strip_tags(td_html)); }

} // namespace html

// ---------------------------- Filtering helpers ----------------------------
namespace filters {

static vector<string> split_tokens(const string& val) {
    static const std::regex re("[ ,+|]+");
    return util::split_regex(val, re);
}

static bool match_stations(const string& hay, const string& expr) {
    string text = util::trim(expr);
    if (text.empty()) return true;
    bool has_or = text.find('|') != string::npos;
    bool has_and = text.find('&') != string::npos;
    if (has_or || has_and) {
        // Split OR parts by one or more '|'
        vector<string> or_parts = util::split_regex(text, std::regex("\\s*\
?\\|{1,2}\\s*"));
        for (const auto& part : or_parts) {
            vector<string> and_chunks = util::split_regex(part, std::regex("\\s*&{1,2}\\s*"));
            vector<string> and_tokens;
            for (const auto& chunk : and_chunks) {
                auto toks = util::split_regex(chunk, std::regex("[ ,+]+"));
                and_tokens.insert(and_tokens.end(), toks.begin(), toks.end());
            }
            if (!and_tokens.empty()) {
                bool all_in = true;
                for (const auto& tok : and_tokens) if (hay.find(tok) == string::npos) { all_in = false; break; }
                if (all_in) return true;
            } else if (!part.empty() && hay.find(part) != string::npos) {
                return true;
            }
        }
        return false;
    }
    auto toks = util::split_regex(text, std::regex("[ ,+]+"));
    for (const auto& tok : toks) if (hay.find(tok) == string::npos) return false;
    return true;
}

} // namespace filters

// ---------------------------- SessionBrowser ----------------------------
class SessionBrowser {
  public:
    enum class Scope { Master, Intensive, Both };

    SessionBrowser(int year, Scope scope, string session_filter, string antenna_filter)
        : year_(year), scope_(scope), session_filter_(std::move(session_filter)), antenna_filter_(std::move(antenna_filter)) {}

    void run();

  private:
    int year_;
    Scope scope_;
    string session_filter_;
    string antenna_filter_;

    vector<Row> rows_;
    vector<Row> view_rows_;
    string current_filter_;
    int selected_ = 0;
    int offset_ = 0;
    bool has_colors_ = false;
    bool show_removed_ = true;

    // ---------- Data ----------
    vector<string> urls_for_scope() const {
        string base = "https://ivscc.gsfc.nasa.gov/sessions";
        string y = std::to_string(year_);
        if (scope_ == Scope::Master) return {base + "/" + y + "/"};
        if (scope_ == Scope::Intensive) return {base + "/intensive/" + y + "/"};
        return {base + "/" + y + "/", base + "/intensive/" + y + "/"};
    }

    static vector<Row> fetch_one(const string& url, const string& session_filter, const string& antenna_filter) {
        vector<Row> parsed;
        string body;
        try {
            body = http::get(url);
        } catch (const std::exception& e) {
            std::cerr << "Error fetching " << url << ": " << e.what() << "\n";
            return parsed;
        }
        bool is_intensive = url.find("/intensive/") != string::npos;
        auto trs = html::find_tr_blocks(body);
        for (const auto& tr : trs) {
            auto tds = html::extract_tds(tr);
            if (tds.size() < 11) continue;

            auto [active_ids, removed_ids] = html::parse_stations(tds[5]);
            string stations_str;
            if (!active_ids.empty() && !removed_ids.empty()) stations_str = active_ids + " [" + removed_ids + "]";
            else if (!removed_ids.empty()) stations_str = "[" + removed_ids + "]";
            else stations_str = active_ids;

            array<string, 11> values{};
            values[0] = html::inner_text(tds[0]);
            values[1] = html::inner_text(tds[1]);
            values[2] = html::inner_text(tds[2]);
            values[3] = html::inner_text(tds[3]);
            values[4] = html::inner_text(tds[4]);
            values[5] = util::ljust(stations_str, WIDTHS[5]);
            values[6] = html::inner_text(tds[6]);
            values[7] = html::inner_text(tds[7]);
            values[8] = html::inner_text(tds[8]);
            values[9] = html::inner_text(tds[9]);
            values[10] = html::inner_text(tds[10]);

            // Tag intensives right-aligned within Type field with "[I]"
            const int TYPE_W = WIDTHS[0];
            if (is_intensive) {
                int base = std::max(0, TYPE_W - 3);
                std::ostringstream os; os << std::left << std::setw(base) << values[0] << "[I]";
                values[0] = os.str();
            } else {
                values[0] = util::ljust(values[0], TYPE_W);
            }

            string session_url;
            if (auto href = html::find_anchor_href(tds[1]); !href.empty()) {
                if (util::starts_with(href, "/")) session_url = "https://ivscc.gsfc.nasa.gov" + href;
                else session_url = href;
            }

            // Initial CLI-like filters (case-sensitive)
            if (!session_filter.empty() && values[1].find(session_filter) == string::npos) continue;
            if (!antenna_filter.empty() && active_ids.find(antenna_filter) == string::npos) continue;

            Row row{values, session_url, Meta{active_ids, removed_ids}};
            parsed.emplace_back(std::move(row));
        }
        return parsed;
    }

    vector<Row> fetch_all() const {
        vector<Row> all;
        for (const auto& url : urls_for_scope()) {
            auto part = fetch_one(url, session_filter_, antenna_filter_);
            all.insert(all.end(), part.begin(), part.end());
        }
        return all;
    }

    // ---------- Filtering ----------
    static vector<Row> apply_filter_impl(const vector<Row>& rows, const string& query) {
        if (query.empty()) return rows;
        vector<string> clauses = util::split_regex(query, std::regex(";"));
        if (clauses.empty()) return rows;

        auto clause_match = [](const Row& row, const string& clause) -> bool {
            string cl = util::trim(clause);
            if (cl.empty()) return true;
            auto pos = cl.find(':');
            if (pos != string::npos) {
                string field = util::tolower_copy(util::trim(cl.substr(0, pos)));
                string value = util::trim(cl.substr(pos + 1));
                auto it = FIELD_INDEX.find(field);

                if (field == "stations" || field == "stations_active" || field == "stations-active") {
                    return filters::match_stations(row.meta.active, value);
                }
                if (field == "stations_removed" || field == "stations-removed") {
                    return filters::match_stations(row.meta.removed, value);
                }
                if (field == "stations_all" || field == "stations-all") {
                    string both = row.meta.active + " " + row.meta.removed;
                    return filters::match_stations(both, value);
                }
                if (it == FIELD_INDEX.end()) return false;
                const string& hay = row.cols[it->second];
                auto tokens = filters::split_tokens(value);
                for (const auto& tok : tokens) if (hay.find(tok) != string::npos) return true;
                return false;
            }
            for (const auto& col : row.cols) if (col.find(cl) != string::npos) return true;
            return false;
        };

        vector<Row> out;
        out.reserve(rows.size());
        for (const auto& r : rows) {
            bool ok = true;
            for (const auto& c : clauses) if (!clause_match(r, c)) { ok = false; break; }
            if (ok) out.push_back(r);
        }
        return out;
    }

    // ---------- Sorting & index helpers ----------
    static void sort_by_start(vector<Row>& rows) {
        std::sort(rows.begin(), rows.end(), [](const Row& a, const Row& b) {
            std::tm ta{}; std::tm tb{};
            bool pa = util::parse_start_time(a.cols[2], ta);
            bool pb = util::parse_start_time(b.cols[2], tb);
            if (!pa && !pb) return false;
            if (!pa) return false;
            if (!pb) return true;
            std::time_t ea = timegm(&ta);
            std::time_t eb = timegm(&tb);
            return ea < eb;
        });
    }

    static int index_on_or_after_today(const vector<Row>& rows) {
        if (rows.empty()) return 0;
        std::time_t now = std::time(nullptr);
        std::tm* lt = std::gmtime(&now);
        int y = lt->tm_year, m = lt->tm_mon, d = lt->tm_mday;
        std::tm today_tm{}; today_tm.tm_year = y; today_tm.tm_mon = m; today_tm.tm_mday = d;
        std::time_t today = timegm(&today_tm);
        for (int i = 0; i < (int)rows.size(); ++i) {
            std::tm t{}; if (!util::parse_start_time(rows[i].cols[2], t)) continue;
            std::tm day{}; day.tm_year = t.tm_year; day.tm_mon = t.tm_mon; day.tm_mday = t.tm_mday;
            if (timegm(&day) >= today) return i;
        }
        return (int)rows.size() - 1;
    }

    // ---------- Curses helpers ----------
    static void addstr_clip(WINDOW* win, int y, int x, const string& text, int attr = 0) {
        int max_y, max_x; getmaxyx(win, max_y, max_x);
        if (y >= max_y || x >= max_x) return;
        int n = std::max(0, max_x - x - 1);
        if (n <= 0) return;
        if (attr) wattron(win, attr);
        mvwaddnstr(win, y, x, text.c_str(), n);
        if (attr) wattroff(win, attr);
    }

    static string get_input(WINDOW* win, const string& prompt) {
        curs_set(1);
        int max_y, max_x; getmaxyx(win, max_y, max_x);
        string buf;
        while (true) {
            string line = prompt + buf;
            if ((int)line.size() > max_x - 1) line = line.substr(0, (size_t)max_x - 1);
            addstr_clip(win, max_y - 1, 0, string(max_x - 1, ' '));
            addstr_clip(win, max_y - 1, 0, line, A_REVERSE);
            wmove(win, max_y - 1, std::min((int)line.size(), max_x - 2));
            int ch = wgetch(win);
            if (ch == '\n' || ch == KEY_ENTER) break;
            if (ch == 27) { buf.clear(); break; }
            if (ch == KEY_BACKSPACE || ch == 127 || ch == 8) { if (!buf.empty()) buf.pop_back(); continue; }
            if (ch >= 32 && ch <= 126) buf.push_back((char)ch);
        }
        curs_set(0);
        return util::trim(buf);
    }

    static int status_color(bool has_colors, const string& status_text) {
        if (!has_colors) return 0;
        string st = util::tolower_copy(util::trim(status_text));
        if (st.find("released") != string::npos) return COLOR_PAIR(4);
        if (st.find("waiting on media") != string::npos || st.find("ready for processing") != string::npos ||
            st.find("cleaning up") != string::npos || st.find("processing session") != string::npos) return COLOR_PAIR(5);
        if (st.find("cancelled") != string::npos || st.find("canceled") != string::npos) return COLOR_PAIR(6);
        if (st.empty()) return COLOR_PAIR(7);
        return 0;
    }

    void draw_header(WINDOW* win) {
        std::ostringstream hdr;
        for (size_t i = 0; i < HEADERS.size(); ++i) {
            if (i) hdr << " | ";
            hdr << std::left << std::setw(HEADERS[i].width) << HEADERS[i].title;
        }
        string header_line = hdr.str();
        int attr = A_BOLD | (has_colors_ ? COLOR_PAIR(2) : 0);
        addstr_clip(win, 0, 0, header_line, attr);
        addstr_clip(win, 1, 0, string((int)header_line.size(), '-'));
    }

    void draw_rows(WINDOW* win) {
        int max_y, max_x; getmaxyx(win, max_y, max_x);
        int view_h = std::max(1, max_y - 3);
        if (selected_ < offset_) offset_ = selected_;
        else if (selected_ >= offset_ + view_h) offset_ = selected_ - view_h + 1;

        if (view_rows_.empty()) { addstr_clip(win, 2, 0, "No sessions found."); return; }

        for (int i = offset_; i < std::min((int)view_rows_.size(), offset_ + view_h); ++i) {
            const auto& row = view_rows_[i];
            array<string, 11> vals = row.cols; // copy for optional override
            if (!show_removed_) vals[5] = util::ljust(row.meta.active, WIDTHS[5]);

            std::ostringstream line;
            for (size_t c = 0; c < vals.size(); ++c) {
                if (c) line << " | ";
                line << util::ljust(vals[c], WIDTHS[c]);
            }
            string full = line.str();
            int y = i - offset_ + 2;
            int row_attr = (i == selected_) ? A_REVERSE : 0;
            int row_color = status_color(has_colors_, vals[9]);
            addstr_clip(win, y, 0, full, row_attr | row_color);

            if (has_colors_ && show_removed_ && !vals[5].empty()) {
                auto lpos = full.find('[');
                if (lpos != string::npos) {
                    auto rpos = full.find(']', lpos + 1);
                    if (rpos != string::npos && rpos > lpos) {
                        // Repaint the bracketed portion in yellow to highlight removed stations
                        string segment = full.substr(lpos, rpos - lpos + 1);
                        addstr_clip(win, y, (int)lpos, segment, row_attr | COLOR_PAIR(1));
                    }
                }
            }
        }
    }

    void draw_helpbar(WINDOW* win) {
        int max_y, max_x; getmaxyx(win, max_y, max_x);
        string help = "\342\206\222\342\206\222 Move  PgUp/PgDn  Home/End  Enter Open  '/' Filter  T Today  F ClearFilter R Show/hide removed  ? Help  q Quit  stations: AND(&) OR(|)  ";
        std::ostringstream right; right << "row " << std::min(selected_ + 1, (int)view_rows_.size()) << "/" << view_rows_.size();
        string bar = help + (current_filter_.empty() ? string("") : ("filter: " + current_filter_)) + "  " + right.str();
        if ((int)bar.size() > max_x - 1) bar = bar.substr(0, (size_t)max_x - 1);
        int attr = has_colors_ ? COLOR_PAIR(3) : A_REVERSE;
        addstr_clip(win, max_y - 1, 0, bar, attr);
    }

    void show_help_popup(WINDOW* win) {
        vector<string> lines = {
            "IVS Session Browser Help",
            "",
            "Navigation:",
            "  \342\206\222/\342\206\220 : Move selection",
            "  PgUp/PgDn : Page up/down",
            "  Home/End : Jump to first/last",
            "  T : Jump to today's session",
            "  Enter : Open session in browser",
            "",
            "Filtering:",
            "  / : Enter filter (field:value, supports AND/OR)",
            "  F : Clear filters",
            "  R : Toggle show/hide removed stations",
            "",
            "Other:",
            "  q or ESC : Quit",
            "  ? : Show this help",
            "",
            "Color legend:",
            "  Green   = Released",
            "  Yellow  = Processing / Waiting",
            "  Magenta = Cancelled",
            "  Blue    = No status",
        };
        int h, w; getmaxyx(win, h, w);
        int width = std::min(84, w - 4);
        int height = std::min((int)lines.size() + 4, h - 4);
        int y = (h - height) / 2, x = (w - width) / 2;
        WINDOW* popup = newwin(height, width, y, x);
        box(popup, 0, 0);
        for (int i = 0; i < (int)lines.size(); ++i) {
            int attr = (i == 0) ? A_BOLD : 0;
            wattron(popup, attr);
            mvwaddnstr(popup, i + 1, 2, lines[i].c_str(), width - 4);
            wattroff(popup, attr);
        }
        wrefresh(popup);
        wgetch(popup);
        delwin(popup);
    }

    void curses_main() {
        initscr();
        cbreak();
        noecho();
        keypad(stdscr, TRUE);
        curs_set(0);

        has_colors_ = has_colors();
        if (has_colors_) {
            start_color();
            use_default_colors();
            init_pair(1, COLOR_YELLOW, -1); // removed stations
            init_pair(2, COLOR_CYAN, -1);   // header
            init_pair(3, COLOR_BLACK, COLOR_WHITE); // help bar
            init_pair(4, COLOR_GREEN, -1);  // released
            init_pair(5, COLOR_YELLOW, -1); // processing
            init_pair(6, COLOR_MAGENTA, -1);// cancelled
            init_pair(7, COLOR_BLUE, -1);   // none
        }

        while (true) {
            clear();
            draw_header(stdscr);
            draw_rows(stdscr);
            draw_helpbar(stdscr);
            int ch = getch();
            if (ch == KEY_UP && selected_ > 0) selected_--;
            else if (ch == KEY_DOWN && selected_ < (int)view_rows_.size() - 1) selected_++;
            else if (ch == KEY_NPAGE) {
                int max_y, max_x; getmaxyx(stdscr, max_y, max_x);
                int page = std::max(1, max_y - 3);
                selected_ = std::min(selected_ + page, (int)view_rows_.size() - 1);
            } else if (ch == KEY_PPAGE) {
                int max_y, max_x; getmaxyx(stdscr, max_y, max_x);
                int page = std::max(1, max_y - 3);
                selected_ = std::max(selected_ - page, 0);
            } else if (ch == KEY_HOME) {
                selected_ = 0;
            } else if (ch == KEY_END) {
                selected_ = std::max(0, (int)view_rows_.size() - 1);
            } else if (ch == 't' || ch == 'T') {
                int idx = index_on_or_after_today(view_rows_);
                selected_ = idx; offset_ = idx;
            } else if (ch == '\n' || ch == KEY_ENTER) {
                if (!view_rows_.empty()) {
                    const string& url = view_rows_[selected_].url;
                    if (!url.empty()) {
                        string cmd = "xdg-open '" + url + "' >/dev/null 2>&1 &";
                        std::system(cmd.c_str());
                    }
                }
            } else if (ch == '/') {
                string q = get_input(stdscr, "/ ");
                current_filter_ = q;
                view_rows_ = apply_filter_impl(rows_, q);
                int idx = index_on_or_after_today(view_rows_);
                selected_ = idx; offset_ = idx;
            } else if (ch == 'F') {
                current_filter_.clear();
                view_rows_ = rows_;
                int idx = index_on_or_after_today(view_rows_);
                selected_ = idx; offset_ = idx;
            } else if (ch == 'r' || ch == 'R') {
                show_removed_ = !show_removed_;
            } else if (ch == '?') {
                show_help_popup(stdscr);
            } else if (ch == 'q' || ch == 27) {
                break;
            }
        }

        endwin();
    }

  public:
    void load_data() {
        rows_ = fetch_all();
        sort_by_start(rows_);
        view_rows_ = rows_;
        int idx = index_on_or_after_today(view_rows_);
        selected_ = idx; offset_ = idx;
    }
};

// Out-of-class definition to avoid duplicate in-class declarations
void SessionBrowser::run() {
    load_data();
    curses_main();
}

// ---------------------------- CLI ----------------------------
static void usage(const char* prog) {
    std::cerr << "Usage: " << prog << " [--year N] [--scope master|intensive|both] [--session CODE] [--antenna ID]\n";
}

int main(int argc, char** argv) {
    curl_global_init(CURL_GLOBAL_DEFAULT);

    int year = [](){
        std::time_t now = std::time(nullptr); std::tm* lt = std::gmtime(&now);
        return 1900 + lt->tm_year;
    }();
    string scope_str = "both";
    string session_filter;
    string antenna_filter;

    const option long_opts[] = {
        {"year", required_argument, nullptr, 'y'},
        {"scope", required_argument, nullptr, 's'},
        {"session", required_argument, nullptr, 'c'},
        {"antenna", required_argument, nullptr, 'a'},
        {"help", no_argument, nullptr, 'h'},
        {nullptr, 0, nullptr, 0}
    };

    int opt, idx;
    while ((opt = getopt_long(argc, argv, "", long_opts, &idx)) != -1) {
        switch (opt) {
            case 'y': year = std::atoi(optarg); break;
            case 's': scope_str = optarg; break;
            case 'c': session_filter = optarg; break;
            case 'a': antenna_filter = optarg; break;
            case 'h': usage(argv[0]); curl_global_cleanup(); return 0;
            default: usage(argv[0]); curl_global_cleanup(); return 1;
        }
    }

    SessionBrowser::Scope scope = SessionBrowser::Scope::Both;
    if (scope_str == "master") scope = SessionBrowser::Scope::Master;
    else if (scope_str == "intensive") scope = SessionBrowser::Scope::Intensive;

    try {
        SessionBrowser app(year, scope, session_filter, antenna_filter);
        app.run();
    } catch (const std::exception& e) {
        endwin();
        std::cerr << "Fatal: " << e.what() << "\n";
        curl_global_cleanup();
        return 1;
    }

    curl_global_cleanup();
    return 0;
}
