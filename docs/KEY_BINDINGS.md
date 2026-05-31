# Key Bindings Reference

## Navigation

| Key       | Action            | Description                               |
|-----------|-------------------|-------------------------------------------|
| `↑`       | Move up           | Move selection up one row                 |
| `↓`       | Move down         | Move selection down one row               |
| `PgUp`    | Page up           | Scroll up one page                        |
| `PgDn`    | Page down         | Scroll down one page                      |
| `Home`    | Jump to top       | Jump to first session                     |
| `End`     | Jump to bottom    | Jump to last session                      |
| `T`       | Jump to today     | Jump to session on or after today's date  |

## Actions

| Key | Action | Description |
|-----|--------|-------------|
| `Enter` | Open in browser | Open selected session page in default web browser |
| `P` | Export PDF | Save visible rows to a timestamped PDF and open it |
| `X` | Export XLSX | Save visible rows to a timestamped XLSX workbook and open it |
| `S` | Show statistics | Open operational statistics (trend, network, reliability metrics) |
| `G` | Plot station contribution | Save/open station contribution chart (cycles metric each press) |
| `?` | Show help | Display help popup with key bindings and color legend |

## Filtering

| Key | Action | Description |
|-----|--------|-------------|
| `/` | Enter filter | Enter filter mode to type a filter expression |
| `C` | Clear filters | Clear all active filters and show all sessions |

## Operator Assignment

| Key | Action | Description |
|-----|--------|-------------|
| `0` | Assign operator 0 | Assign operator bound to key "0" to selected session |
| `1` | Assign operator 1 | Assign operator bound to key "1" to selected session |
| `2` | Assign operator 2 | Assign operator bound to key "2" to selected session |
| `3` | Assign operator 3 | Assign operator bound to key "3" to selected session |
| `4` | Assign operator 4 | Assign operator bound to key "4" to selected session |
| `5` | Assign operator 5 | Assign operator bound to key "5" to selected session |

**Note**: Operator bindings and colors are configured in `~/.config/ivs-sessions-browser/operators.json`, which is created from packaged defaults when missing. Key `0` clears an assignment; keys `1`-`5` default to `U1`-`U5` and should be edited to local operator labels. Each operator can have a custom color for visual identification in the TUI.

## Application Control

| Key | Action | Description |
|-----|--------|-------------|
| `q` | Quit | Exit the application |
| `Q` | Quit | Exit the application (same as lowercase q) |

## Filter Syntax Quick Reference

When you press `/` to enter a filter:
- **Field:value syntax**: `code: R1|R4`
- **Multiple clauses (AND)**: `code: R1; status: released`
- **OR within field**: Use `|`, space, `,`, or `+` (non-stations fields)
- **Station AND**: `stations: Nn&Ns`
- **Station OR**: `stations: Nn|Ns`
- **Station variants**:
  - `stations:` - active stations (default)
  - `stations_active:` - active stations (explicit)
  - `stations_removed:` - removed stations only
  - `stations_all:` - any stations (active or removed)

See [FILTER_SYNTAX.md](FILTER_SYNTAX.md) for comprehensive filter documentation.

## Color Legend

| Color                 | Meaning                                                        |
|-----------------------|----------------------------------------------------------------|
| **Green**             | Released - session data has been released                      |
| **Yellow**            | Processing / Waiting - session is being processed or waiting   |
| **Magenta**           | Cancelled - session was cancelled                              |
| **White**             | No status - status not specified                               |
| **Cyan**              | Filter indicator - shown in status bar when filters are active |
| **Operator colors**   | Custom colors for each operator (configurable)                 |

## Status Bar

The bottom status bar shows:
- Current row position and total rows
- Active filter expression (if any) in cyan
- Number of visible rows vs. total rows when filters are active

## Tips

1. **Combine keys**: Use `T` to jump to today, then filter with `/` to narrow down current sessions
2. **Quick operator assignment**: After filtering for your relevant sessions, use `0-5` keys to quickly assign operators
3. **Browser integration**: Press `Enter` on any session to view full details on the IVS website
4. **Help always available**: Press `?` anytime to see the help screen with all key bindings
5. **Clear and retry**: Use `C` to clear filters if you want to start fresh
6. **Removed stations view**: Use filters like `stations_removed:Ft|Ur` or `stations_all:Ft|Ur` to inspect removed stations
7. **Stats popup navigation**: In statistics view, use `↑/↓`, `j/k`, or `PgUp/PgDn` to scroll, `q`, `Enter`, or `Esc` to close
8. **Quick exports**: Use `P` or `X` after filtering to export exactly the visible rows
