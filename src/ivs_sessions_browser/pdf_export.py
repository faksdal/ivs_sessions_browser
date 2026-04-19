# flake8: noqa
# isort: skip_file
"""
Defined in pdf_export.py

Filename:       pdf_export.py
Author:         jole
Created:        15.09.2025

Description:    Holds class definitions for PDF export along with attributes
                and methods.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Import section
# ──────────────────────────────────────────────────────────────────────────────
import io
import re

from datetime                   import datetime
from reportlab.lib              import colors
from reportlab.lib.pagesizes    import A4, landscape
from reportlab.pdfbase          import pdfmetrics
from reportlab.pdfgen           import canvas
# ─── END OF Import section ────────────────────────────────────────────────────



# ──────────────────────────────────────────────────────────────────────────────
# Constants and helper functions
# ──────────────────────────────────────────────────────────────────────────────
#
#   I find reg.ex a bit complicated, so I like to have an explanation of what
#   each pattern is doing right here in the code, as a comment.

#
#   re.compile(r"\x1b\[([0-9;]*)m")
#       r""         : means no escape by Python, everything goes straight to the regex engine.
#       \x1b        : is the ASCII escape character, which starts an ANSI code
#       \[          : matches the literal '[' character
#       ([0-9;]*)   : captures a sequence of digits and semicolons (the ANSI codes).
#                     matches digits 0-9 and semicolons ';', * means zero or more times.
#       m           : matches the literal 'm' character, which ends the ANSI code
#
#   This means that a line like:
#       '\x1b[1m\x1b[96mOp | Start            | Code     | Stations                                        | Corr  \x1b[0m'#   
#   would be parsed into:
#       'Op | Start            | Code     | Stations                                        | Corr'
ANSI_PATTERN = re.compile(r"\x1b\[([0-9;]*)m")

DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})")

ANSI_RESET  = "\033[0m"
ANSI_BOLD   = "\033[1m"
ANSI_WHITE  = "\033[97m"
ANSI_CYAN   = "\033[96m"

WEEK_HEADING    = "Week"
WEEK_WIDTH      = len(WEEK_HEADING) + 2

TRANSFER_DONE_HEADING   = "Tx done"
TRANSFER_DONE_WIDTH     = len(TRANSFER_DONE_HEADING) + 2

ANSI_COLOR_MAP = {
    30: colors.black,
    91: colors.HexColor("#ff6b6b"),
    92: colors.HexColor("#69db7c"),
    93: colors.HexColor("#b58900"),
    94: colors.HexColor("#4dabf7"),
    95: colors.HexColor("#da77f2"),
    96: colors.HexColor("#66d9e8"),
    97: colors.white,
}

DEFAULT_TEXT_COLOR      = colors.black
DEFAULT_FONT_NAME       = "Courier"
DEFAULT_BOLD_FONT_NAME  = "Courier-Bold"
DEFAULT_FONT_SIZE       = 10.5
MIN_FONT_SIZE           = 7.5
MAX_FONT_SIZE           = 13.0
#DEFAULT_MARGIN = 36.0
DEFAULT_MARGIN          = 18.0
#FRAME_PADDING = 8.0
FRAME_PADDING           = 4.0
FRAME_COLOR             = colors.HexColor("#c7c7c7")
ROW_SEPARATOR_COLOR     = colors.HexColor("#dfdfdf")
FRAME_LINE_WIDTH        = 0.8
ROW_SEPARATOR_WIDTH     = 0.5
CELL_PADDING            = 4.0            # horizontal padding (pt) on each side of text within a column

SEP                     = f"{ANSI_WHITE} | {ANSI_RESET}"  # canonical ANSI column separator used for splitting

HIGHLIGHTED_STATIONS    = frozenset({"Nn", "Ns"})
STATION_TOKEN_RE        = re.compile(r"[A-Z][a-z0-9]")  # matches one 2-char IVS station code
# ─── END OF Constants and helper functions ────────────────────────────────────



def _strip_ansi(text: str) -> str:
    """
    Defined in pdf_export.py

    Remove ANSI escape sequences from the given text, using the ANSI_PATTERN
    regex defined above.
    """

    return ANSI_PATTERN.sub("", text)
# ─── END OF _strip_ansi() ─────────────────────────────────────────────────────



def _parse_ansi_segments(line: str) -> list[tuple[str, colors.Color, bool, bool]]:
    """
    Defined in pdf_export.py

    Parse *line* into (text, color, is_bold, is_reversed) segments.
    This is used to create the PDF in ansi_lines_to_pdf_bytes() with the correct
    formatting for each part of the text.
    """
    
    segments: list[tuple[str, colors.Color, bool, bool]] = []
    current_color = DEFAULT_TEXT_COLOR
    is_bold = False
    is_reversed = False
    position = 0

    for match in ANSI_PATTERN.finditer(line):
        if match.start() > position:
            segments.append((line[position:match.start()], current_color, is_bold, is_reversed))

        codes_text = match.group(1)
        codes = [int(code) for code in codes_text.split(";") if code] if codes_text else [0]
        if not codes:
            codes = [0]

        for code in codes:
            if code == 0:
                current_color = DEFAULT_TEXT_COLOR
                is_bold = False
                is_reversed = False
            elif code == 1:
                is_bold = True
            elif code == 7:
                is_reversed = True
            elif code in ANSI_COLOR_MAP:
                current_color = ANSI_COLOR_MAP[code]

        position = match.end()

    if position < len(line):
        segments.append((line[position:], current_color, is_bold, is_reversed))

    return [segment for segment in segments if segment[0]]
# ─── END OF _parse_ansi_segments() ────────────────────────────────────────────



def _measure_line_width(line: str, font_size: float) -> float:
    """
    Defined in pdf_export.py

    Measure the rendered width of a line, accounting for ANSI formatting.
    This is used to compute the necessary column widths and font size to fit
    the content.
    """

    width = 0.0
    for text, _color, is_bold, _rev in _parse_ansi_segments(line):
        font_name = DEFAULT_BOLD_FONT_NAME if is_bold else DEFAULT_FONT_NAME
        width += pdfmetrics.stringWidth(text, font_name, font_size)
    return width
# ─── END OF _measure_line_width() ─────────────────────────────────────────────



def _is_separator_line(line: str) -> bool:
    """
    Defined in pdf_export.py

    Check if a line is a separator line, consisting entirely of the '─'
    character. This is the line just below the header.
    """

    visible = _strip_ansi(line).strip()
    return bool(visible) and set(visible) == {"─"}
# ─── END OF _is_separator_line() ──────────────────────────────────────────────



def _extract_week_number(line: str) -> str:
    """
    Defined in pdf_export.py

    Extract the ISO week number from a line containing a date.

    The date is expected to be in the format "YYYY-MM-DD HH:MM".
    """

    match = DATE_PATTERN.search(_strip_ansi(line))
    if match:
        try:
            dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M")
            return f"W{dt.isocalendar()[1]}"
        except ValueError:
            pass
    return ""
# ─── END OF _extract_week_number() ────────────────────────────────────────────



def _leading_color_code(line: str) -> str:
    """
    Defined in pdf_export.py

    Return the row-leading ANSI color escape, or empty string.

    We only consider a color code at the start of the row. This avoids
    accidentally picking the white ANSI separator color from uncolored rows.
    """

    match = ANSI_PATTERN.match(line)
    if match:
        return match.group(0)
    return ""
# ─── END OF _leading_color_code() ─────────────────────────────────────────────



def _prepend_week_column(line: str, is_header: bool) -> str:
    """
    Defined in pdf_export.py

    Prepend a "Week" column to the line, extracting the week number from the
    date if possible.
    """

    separator = f"{ANSI_WHITE} | {ANSI_RESET}"
    if is_header:
        heading = f"{ANSI_BOLD}{ANSI_CYAN}{WEEK_HEADING:<{WEEK_WIDTH}}{ANSI_RESET}"
        return f"{heading}{separator}{line}"

    week_str    = _extract_week_number(line)
    color       = _leading_color_code(line)

    # Never draw week text in white on a white PDF background.
    if color and color != ANSI_WHITE:
        colored_week = f"{color}{week_str:<{WEEK_WIDTH}}{ANSI_RESET}"        
    else:
        colored_week = f"{week_str:<{WEEK_WIDTH}}"
    
    return f"{colored_week}{separator}{line}"
# ─── END OF _prepend_week_column() ────────────────────────────────────────────



def _recolor_header_cells(line: str) -> str:
    """
    Defined in pdf_export.py

    Re-apply bold+cyan to every cell of the (already augmented) header line.

    The source header is a single colour span over the whole row. After cell
    boundaries are added and normalised the inner cells lose their colour because
    each SEP contains a hard reset. Re-wrapping each cell individually fixes that.
    """

    norm = _normalize_separators(line)
    cells = _split_into_cells(norm)
    recolored = [
        f"{ANSI_BOLD}{ANSI_CYAN}{_strip_ansi(cell)}{ANSI_RESET}" for cell in cells
    ]
    return SEP.join(recolored)
# ─── END OF _recolor_header_cells() ───────────────────────────────────────────



def _highlight_stations_cell(cell: str, row_color_code: str) -> str:
    """
    Defined in pdf_export.py

    Wrap each highlighted station name with reverse-video markers.
    This makes them stand out in the PDF, and also ensures that
    the row color (if any) is still visible as the background of the highlighted
    station name.

    Intended to help the user identify the stations they are interested in more
    quickly when scanning the PDF.
    """

    def replacer(m: re.Match) -> str:
        token = m.group(0)
        if token in HIGHLIGHTED_STATIONS:
            # Ensure row color is active before reverse-video so bg uses row color.
            return f"{ANSI_RESET}{row_color_code}\033[7m{token}{ANSI_RESET}{row_color_code}"
        
        return token
    return STATION_TOKEN_RE.sub(replacer, cell)
# ─── END OF _highlight_stations_cell() ────────────────────────────────────────



def _find_stations_col_index(header_line: str) -> int | None:
    """
    Defined in pdf_export.py

    Return the 0-based column index whose header is 'STATIONS', or None.
    
    By default it's index is 3, but the user may change the column order, so we
    need to find it by header name.
    """

    cells = _split_into_cells(_normalize_separators(header_line))
    for i, cell in enumerate(cells):
        if _strip_ansi(cell).strip().upper() in ("STATIONS", "STATION"):
            return i
    return None
# ─── END OF _find_stations_col_index() ────────────────────────────────────────



def _prepare_pdf_lines(lines: list[str]) -> list[str]:
    """
    Defined in pdf_export.py

    Prepare the input lines for PDF export by:
    - Filtering out separator lines
    - Highlighting stations in the "STATIONS" column
    - Prepending a "Week" column
    - Appending a "Tx done" column
    - Recoloring header cells
    """

    filtered_lines = [line for line in lines if not _is_separator_line(line)]
    if not filtered_lines:
        return filtered_lines

    stations_col = _find_stations_col_index(filtered_lines[0])

    result = []
    for index, line in enumerate(filtered_lines):
        is_header = (index == 0)
        if not is_header and stations_col is not None:
            cells = _split_into_cells(_normalize_separators(line))
            if stations_col < len(cells):
                row_color = _leading_color_code(line)
                cells[stations_col] = _highlight_stations_cell(cells[stations_col], row_color)
                line = SEP.join(cells)
        line = _prepend_week_column(line, is_header)
        line = _append_transfer_done_column(line, is_header)
        if is_header:
            line = _recolor_header_cells(line)
        result.append(line)
    return result
# ─── END OF _prepare_pdf_lines() ──────────────────────────────────────────────



def _append_transfer_done_column(line: str, is_header: bool) -> str:
    """
    Defined in pdf_export.py

    Append a "Tx done" column to the line. For data rows this is left blank, but
    for the header it adds the column title.
    """

    separator = f"{ANSI_WHITE} | {ANSI_RESET}"
    if is_header:
        heading = f"{ANSI_BOLD}{ANSI_CYAN}{TRANSFER_DONE_HEADING:<{TRANSFER_DONE_WIDTH}}{ANSI_RESET}"
        return f"{line}{separator}{heading}"

    return f"{line}{separator}{'':<{TRANSFER_DONE_WIDTH}}"
# ─── END OF _append_transfer_done_column() ────────────────────────────────────



def _normalize_separators(line: str) -> str:
    """
    Defined in pdf_export.py

    Replace all bare ' | ' with the ANSI-coloured separator so every cell boundary is consistent.
    """
    
    return line.replace(" | ", SEP)
# ─── END OF _normalize_separators() ───────────────────────────────────────────



def _split_into_cells(line: str) -> list[str]:
    """
    Defined in pdf_export.py

    Split a line into cells using the canonical ANSI separator defined in SEP.
    This is used after normalising the separators to ensure we split at the
    correct points, even if the original line had inconsistent spacing or ANSI
    codes around the separators.
    """

    return line.split(SEP)
# ─── END OF _split_into_cells() ───────────────────────────────────────────────



def _best_font_size_for_columns(cell_rows: list[list[str]], usable_width: float) -> float:
    """
    Defined in pdf_export.py

    Compute font size so the total column content fits within *usable_width*.
    """

    if not cell_rows:
        return DEFAULT_FONT_SIZE
    n_cols = max((len(row) for row in cell_rows), default=0)
    if n_cols == 0:
        return DEFAULT_FONT_SIZE

    col_text_widths = []
    for c in range(n_cols):
        max_w = 0.0
        for row in cell_rows:
            if c < len(row):
                text = _strip_ansi(row[c]).rstrip()
                max_w = max(max_w, pdfmetrics.stringWidth(text, DEFAULT_FONT_NAME, DEFAULT_FONT_SIZE))
        col_text_widths.append(max_w)

    total_text_width = sum(col_text_widths)
    if total_text_width <= 0:
        return DEFAULT_FONT_SIZE

    available = usable_width - n_cols * 2 * CELL_PADDING
    if available <= 0:
        return MIN_FONT_SIZE

    scale = available / total_text_width
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, DEFAULT_FONT_SIZE * scale))
# ─── END OF _best_font_size_for_columns() ─────────────────────────────────────



def _compute_column_widths(cell_rows: list[list[str]], font_size: float) -> list[float]:
    """
    Defined in pdf_export.py

    Return the rendered width (including padding) of each column.
    """

    if not cell_rows:
        return []
    n_cols = max((len(row) for row in cell_rows), default=0)
    col_widths = []
    for c in range(n_cols):
        max_w = 0.0
        for row in cell_rows:
            if c < len(row):
                text = _strip_ansi(row[c]).rstrip()
                max_w = max(max_w, pdfmetrics.stringWidth(text, DEFAULT_FONT_NAME, font_size))
        col_widths.append(max_w + 2 * CELL_PADDING)
    return col_widths
# ─── END OF _compute_column_widths() ──────────────────────────────────────────



def _draw_page_frame(
    pdf: canvas.Canvas,
    left: float,
    top: float,
    width: float,
    height: float,
) -> None:
    """
    Defined in pdf_export.py

    Draw a rectangular frame around the page content.
    """

    if width <= 0 or height <= 0:
        return

    pdf.saveState()
    pdf.setStrokeColor(FRAME_COLOR)
    pdf.setLineWidth(FRAME_LINE_WIDTH)
    pdf.rect(left, top - height, width, height, stroke=1, fill=0)
    pdf.restoreState()
# ─── END OF _draw_page_frame() ────────────────────────────────────────────────



def _draw_row_separator(
    pdf: canvas.Canvas,
    left: float,
    right: float,
    y: float,
) -> None:
    """
    Defined in pdf_export.py

    Draw a horizontal separator line between rows.
    """

    if right <= left:
        return

    pdf.saveState()
    pdf.setStrokeColor(ROW_SEPARATOR_COLOR)
    pdf.setLineWidth(ROW_SEPARATOR_WIDTH)
    pdf.line(left, y, right, y)
    pdf.restoreState()
# ─── END OF _draw_row_separator() ─────────────────────────────────────────────



def _draw_column_separators(
    pdf: canvas.Canvas,
    sep_x_positions: list[float],
    top_y: float,
    bottom_y: float,
) -> None:
    """
    Defined in pdf_export.py

    Draw vertical separator lines between columns, from top_y to bottom_y.
    """

    if not sep_x_positions or top_y <= bottom_y:
        return
    pdf.saveState()
    pdf.setStrokeColor(FRAME_COLOR)
    pdf.setLineWidth(FRAME_LINE_WIDTH)
    for x in sep_x_positions:
        pdf.line(x, top_y, x, bottom_y)
    pdf.restoreState()
# ─── END OF _draw_column_separators() ─────────────────────────────────────────



def _contrasting_text_color(bg: colors.Color) -> colors.Color:
    """
    Defined in pdf_export.py

    Pick white or black text based on background luminance.
    """

    luminance = (0.2126 * bg.red) + (0.7152 * bg.green) + (0.0722 * bg.blue)
    return colors.black if luminance >= 0.55 else colors.white
# ─── END OF _contrasting_text_color() ─────────────────────────────────────────



def ansi_lines_to_pdf_bytes(lines: list[str]) -> bytes:
    """
    Defined in pdf_export.py

    Convert a list of ANSI-formatted text lines into a PDF file represented as
    bytes.
    Applying the following transformations to the input lines:
    - Filtering out separator lines
    - Highlighting stations in the "STATIONS" column
    - Prepending a "Week" column
    - Appending a "Tx done" column
    - Recoloring header cells
        The PDF is formatted with a frame around the content, column separators,
        and uses the ANSI color codes to determine text colors and bold
        formatting. The font size is automatically adjusted to fit the content
        within the page width.
    """

    # Examples:
    #   lines             = ['\x1b[1m\x1b[96mOp | Start            | Code     | Stations                                        | Corr  \x1b[0m', '───────────────────────────────────────────────────────────────────────────────────────────', '  \x1b[97m | \x1b[0m2026-04-08 00:00\x1b[97m | \x1b[0mVO6098  \x1b[97m | \x1b[0mGsHvIsK2KeNnOeOwWfWnWsYgYj [HbMgSa]            \x1b[97m | \x1b[0mWASH  ', '  \x1b[97m | \x1b[0m2026-04-09 18:30\x1b[97m | \x1b[0mR41254  \x1b[97m | \x1b[0mHbHtKeKkKvNnSvWwWzYgZc [Ft]                    \x1b[97m | \x1b[0mWASH  ', '  \x1b[97m | \x1b[0m2026-04-13 17:00\x1b[97m | \x1b[0mR11255  \x1b[97m | \x1b[0mHbHtIsKeKkKvNnOnWwWzYg [Nt]                    \x1b[97m | \x1b[0mBONN  ', '  \x1b[97m | \x1b[0m2026-04-15 00:00\x1b[97m | \x1b[0mR30002  \x1b[97m | \x1b[0mGsHvIsK2NnOeSaWfWsYg                           \x1b[97m | \x1b[0mBONN  ', '  \x1b[97m | \x1b[0m2026-04-16 18:30\x1b[97m | \x1b[0mR41255  \x1b[97m | \x1b[0mBdHbHtKeKkNnUrWwWzYgZc                         \x1b[97m | \x1b[0mWASH  ', '  \x1b[97m | \x1b[0m2026-04-20 17:00\x1b[97m | \x1b[0mR11256  \x1b[97m | \x1b[0mHbHtIsKeKkKvMaNnWwWzYg [Nt]                    \x1b[97m | \x1b[0mBONN  ', '  \x1b[97m | \x1b[0m2026-04-22 00:00\x1b[97m | \x1b[0mVO6112  \x1b[97m | \x1b[0mGsHvIsK2KeMgNnOeOwSaWfWnWsYgYj [Hb]            \x1b[97m | \x1b[0mSHAO  ', '  \x1b[97m | \x1b[0m2026-04-23 18:30\x1b[97m | \x1b[0mR41256  \x1b[97m | \x1b[0mBdFtHbKeKkKvMaNnWzYgZc [Sv]                    \x1b[97m | \x1b[0mWASH  ', '  \x1b[97m | \x1b[0m2026-04-29 00:00\x1b[97m | \x1b[0mVO6119  \x1b[97m | \x1b[0mGsHvIsK2KeMgNnOeOwSaWfWnWsYgYj [Hb]            \x1b[97m | \x1b[0mWETZ  ']
    #   prepared_lines   = ['\x1b[1m\x1b[96mWeek  \x1b[0m\x1b[97m | \x1b[0m\x1b[1m\x1b[96mOp\x1b[0m\x1b[97m | \x1b[0m\x1b[1m\x1b[96mStart           \x1b[0m\x1b[97m | \x1b[0m\x1b[1m\x1b[96mCode    \x1b[0m\x1b[97m | \x1b[0m\x1b[1m\x1b[96mStations                                       \x1b[0m\x1b[97m | \x1b[0m\x1b[1m\x1b[96mCorr  \x1b[0m\x1b[97m | \x1b[0m\x1b[1m\x1b[96mTx done  \x1b[0m', 'W15   \x1b[97m | \x1b[0m  \x1b[97m\x1b[97m | \x1b[0m\x1b[0m2026-04-08 00:00\x1b[97m\x1b[97m | \x1b[0m\x1b[0mVO6098  \x1b[97m\x1b[97m | \x1b[0m\x1b[0mGsHvIsK2Ke\x1b[0m\x1b[7mNn\x1b[0mOeOwWfWnWsYgYj [HbMgSa]            \x1b[97m\x1b[97m | \x1b[0m\x1b[0mWASH  \x1b[97m | \x1b[0m         ', 'W15   \x1b[97m | \x1b[0m  \x1b[97m\x1b[97m | \x1b[0m\x1b[0m2026-04-09 18:30\x1b[97m\x1b[97m | \x1b[0m\x1b[0mR41254  \x1b[97m\x1b[97m | \x1b[0m\x1b[0mHbHtKeKkKv\x1b[0m\x1b[7mNn\x1b[0mSvWwWzYgZc [Ft]                    \x1b[97m\x1b[97m | \x1b[0m\x1b[0mWASH  \x1b[97m | \x1b[0m         ', 'W16   \x1b[97m | \x1b[0m  \x1b[97m\x1b[97m | \x1b[0m\x1b[0m2026-04-13 17:00\x1b[97m\x1b[97m | \x1b[0m\x1b[0mR11255  \x1b[97m\x1b[97m | \x1b[0m\x1b[0mHbHtIsKeKkKv\x1b[0m\x1b[7mNn\x1b[0mOnWwWzYg [Nt]                    \x1b[97m\x1b[97m | \x1b[0m\x1b[0mBONN  \x1b[97m | \x1b[0m         ', 'W16   \x1b[97m | \x1b[0m  \x1b[97m\x1b[97m | \x1b[0m\x1b[0m2026-04-15 00:00\x1b[97m\x1b[97m | \x1b[0m\x1b[0mR30002  \x1b[97m\x1b[97m | \x1b[0m\x1b[0mGsHvIsK2\x1b[0m\x1b[7mNn\x1b[0mOeSaWfWsYg                           \x1b[97m\x1b[97m | \x1b[0m\x1b[0mBONN  \x1b[97m | \x1b[0m         ', 'W16   \x1b[97m | \x1b[0m  \x1b[97m\x1b[97m | \x1b[0m\x1b[0m2026-04-16 18:30\x1b[97m\x1b[97m | \x1b[0m\x1b[0mR41255  \x1b[97m\x1b[97m | \x1b[0m\x1b[0mBdHbHtKeKk\x1b[0m\x1b[7mNn\x1b[0mUrWwWzYgZc                         \x1b[97m\x1b[97m | \x1b[0m\x1b[0mWASH  \x1b[97m | \x1b[0m         ', 'W17   \x1b[97m | \x1b[0m  \x1b[97m\x1b[97m | \x1b[0m\x1b[0m2026-04-20 17:00\x1b[97m\x1b[97m | \x1b[0m\x1b[0mR11256  \x1b[97m\x1b[97m | \x1b[0m\x1b[0mHbHtIsKeKkKvMa\x1b[0m\x1b[7mNn\x1b[0mWwWzYg [Nt]                    \x1b[97m\x1b[97m | \x1b[0m\x1b[0mBONN  \x1b[97m | \x1b[0m         ', 'W17   \x1b[97m | \x1b[0m  \x1b[97m\x1b[97m | \x1b[0m\x1b[0m2026-04-22 00:00\x1b[97m\x1b[97m | \x1b[0m\x1b[0mVO6112  \x1b[97m\x1b[97m | \x1b[0m\x1b[0mGsHvIsK2KeMg\x1b[0m\x1b[7mNn\x1b[0mOeOwSaWfWnWsYgYj [Hb]            \x1b[97m\x1b[97m | \x1b[0m\x1b[0mSHAO  \x1b[97m | \x1b[0m         ', 'W17   \x1b[97m | \x1b[0m  \x1b[97m\x1b[97m | \x1b[0m\x1b[0m2026-04-23 18:30\x1b[97m\x1b[97m | \x1b[0m\x1b[0mR41256  \x1b[97m\x1b[97m | \x1b[0m\x1b[0mBdFtHbKeKkKvMa\x1b[0m\x1b[7mNn\x1b[0mWzYgZc [Sv]                    \x1b[97m\x1b[97m | \x1b[0m\x1b[0mWASH  \x1b[97m | \x1b[0m         ', 'W18   \x1b[97m | \x1b[0m  \x1b[97m\x1b[97m | \x1b[0m\x1b[0m2026-04-29 00:00\x1b[97m\x1b[97m | \x1b[0m\x1b[0mVO6119  \x1b[97m\x1b[97m | \x1b[0m\x1b[0mGsHvIsK2KeMg\x1b[0m\x1b[7mNn\x1b[0mOeOwSaWfWnWsYgYj [Hb]            \x1b[97m\x1b[97m | \x1b[0m\x1b[0mWETZ  \x1b[97m | \x1b[0m         ']

    prepared_lines = _prepare_pdf_lines(lines)
    if not prepared_lines:
        return b""

    # Normalise all ' | ' to the ANSI form so every cell boundary is a reliable
    # split point
    normalised  = [_normalize_separators(line) for line in prepared_lines]
    cell_rows   = [_split_into_cells(line) for line in normalised]

    buffer                  = io.BytesIO()
    page_width, page_height = landscape(A4)
    usable_width            = page_width - 2 * DEFAULT_MARGIN - 2 * FRAME_PADDING

    font_size = _best_font_size_for_columns(cell_rows, usable_width)
    line_height = max(font_size * 1.35, font_size + 2.0)

    col_widths = _compute_column_widths(cell_rows, font_size)
    total_content_width = sum(col_widths)
    frame_left = DEFAULT_MARGIN
    frame_width = min(page_width - 2 * DEFAULT_MARGIN, total_content_width + 2 * FRAME_PADDING)

    # Text x start for each column (inside left CELL_PADDING)
    col_x_starts: list[float] = []
    cx = frame_left + FRAME_PADDING
    for w in col_widths:
        col_x_starts.append(cx + CELL_PADDING)
        cx += w

    # X positions of vertical column separator lines (between every pair of adjacent columns)
    sep_x: list[float] = []
    cx = frame_left + FRAME_PADDING
    for w in col_widths[:-1]:
        cx += w
        sep_x.append(cx)

    pdf = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    usable_height = page_height - 2 * DEFAULT_MARGIN - 2 * FRAME_PADDING
    lines_per_page = max(1, int(usable_height // line_height))
    frame_top = page_height - DEFAULT_MARGIN
    y = frame_top - FRAME_PADDING - font_size

    def finish_page(n_lines: int) -> None:
        fh = n_lines * line_height + 2 * FRAME_PADDING
        _draw_page_frame(pdf, frame_left, frame_top, frame_width, fh)
        _draw_column_separators(pdf, sep_x, frame_top, frame_top - fh)

    for index, cells in enumerate(cell_rows):
        page_line_index = index % lines_per_page

        if index > 0 and page_line_index == 0:
            finish_page(lines_per_page)
            pdf.showPage()
            frame_top = page_height - DEFAULT_MARGIN
            y = frame_top - FRAME_PADDING - font_size

        for ci, cell in enumerate(cells):
            if ci >= len(col_x_starts):
                break
            draw_x = col_x_starts[ci]
            for text, color, is_bold, is_reversed in _parse_ansi_segments(cell):
                font_name = DEFAULT_BOLD_FONT_NAME if is_bold else DEFAULT_FONT_NAME
                text_w = pdfmetrics.stringWidth(text, font_name, font_size)
                if is_reversed:
                    box_pad = 1.0
                    pdf.saveState()
                    pdf.setFillColor(color)
                    pdf.rect(
                        draw_x - box_pad,
                        y - font_size * 0.15,
                        text_w + 2 * box_pad,
                        font_size * 1.15,
                        stroke=0,
                        fill=1,
                    )
                    pdf.setFillColor(_contrasting_text_color(color))
                    pdf.setFont(font_name, font_size)
                    pdf.drawString(draw_x, y, text)
                    pdf.restoreState()
                else:
                    pdf.setFillColor(color)
                    pdf.setFont(font_name, font_size)
                    pdf.drawString(draw_x, y, text)
                draw_x += text_w

        if page_line_index < lines_per_page - 1 and index < len(cell_rows) - 1:
            separator_y = y - (line_height - font_size) / 2.0
            _draw_row_separator(
                pdf,
                frame_left + FRAME_PADDING,
                frame_left + frame_width - FRAME_PADDING,
                separator_y,
            )

        y -= line_height

    final_page_lines = len(prepared_lines) % lines_per_page or lines_per_page
    finish_page(final_page_lines)

    pdf.save()
    return buffer.getvalue()
# ─── END OF ansi_lines_to_pdf_bytes() ─────────────────────────────────────────



def write_ansi_lines_pdf(lines: list[str], output_stream: io.BufferedIOBase) -> None:
    """
    Defined in pdf_export.py

    Write the given ANSI-formatted lines as a PDF to the provided output stream.
    """

    output_stream.write(ansi_lines_to_pdf_bytes(lines))
# ─── END OF write_ansi_lines_pdf() ────────────────────────────────────────────



def visible_line_length(line: str) -> int:
    """
    Defined in pdf_export.py

    Return the length of the line as it would appear when rendered, ignoring
    ANSI escape sequences.
    """

    return len(_strip_ansi(line))
# ─── END OF visible_line_length() ─────────────────────────────────────────────