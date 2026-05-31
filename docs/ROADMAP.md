# IVS Sessions Browser - Roadmap

## Current Version (v4.x)

### ✅ Implemented Features

- **Core TUI Interface**
  - Curses-based terminal interface
  - Smooth keyboard navigation (arrow keys, PgUp/PgDn, Home/End)
  - Jump to today's session (`T` key)
  - Responsive screen updates

- **Data Fetching**
  - Fetch from IVS Central Bureau (primary and mirrors)
  - Automatic selection of most recent data when using `--mirrors`
  - Support for master and intensive session schedules
  - HTML parsing with BeautifulSoup

- **Filtering System**
  - Powerful filter syntax with field:value pairs
  - AND logic across multiple clauses (`;` separator)
  - OR logic within fields (`|` separator and alternatives)
  - Special station filters with explicit AND/OR operators
  - Support for active, removed, and all-stations filtering
  - Case-sensitive station names, case-insensitive other fields
  - Real-time filter application

- **Operator Management**
  - Assign operators to sessions (keys 0-5)
  - Configurable operator bindings (`operators.json`)
  - Custom color coding per operator
  - Persistent assignments (`operator_assignments.json`)
  - Filter by assigned operator

- **Visual Features**
  - Color-coded session status (Released/Processing/Cancelled)
  - Operator-based row coloring
  - Highlighted removed stations (in brackets)
  - Removed/active/all station filtering via filter expressions
  - Status bar with filter indication and position info
  - Inline help screen (`?` key)

- **Browser Integration**
  - Open selected session in web browser (Enter key)
  - Direct links to IVS session pages

- **CLI Options**
  - Year selection (`--year`)
  - Scope selection (master/intensive/both)
  - Initial filter expression (`--filters`)
  - Mirror checking (`--mirrors`)
  - Text output to file/stdout (`--output`)
  - Column selection for textual output (`--pretty-print`)
  - Quiet-by-default export with optional progress override (`--verbose-fetch`)
  - Append mode (`--append`)
  - Output format selector (`--format text|pdf|xlsx`)
  - Config initialization (`--init-config`)
  - Startup defaults from `startup_defaults.json`
  - Bundled manual page (`--man`)
  - Version display (`--version`)

- **Exports and Reports**
  - Colored PDF output from CLI and TUI
  - XLSX workbook output from CLI and TUI
  - Statistics popup (`S`) with session, hour, network, reliability, and station contribution summaries
  - Station contribution plot (`G`) with session share, hours, and weighted-hours metrics

## Near-Term Roadmap (Next 6 months)

### High Priority

- **Enhanced Output Formats** 🔨
  - Full JSON export with nested structure
  - CSV export with all fields
  - Additional report templates for operator and station summaries

- **Improved Sorting** 🔨
  - Press `s` to cycle through sort modes
  - Sort by: Code, Start Date, DOY, Duration, Status
  - Ascending/descending toggle
  - Visual indicator for active sort

- **Advanced Filter Grammar** 🔨
  - Parentheses for grouping: `(code: R1|R4) AND (status: released)`
  - NOT operator: `NOT status: cancelled`
  - Range queries: `doy: 100-200`, `dur: >12`
  - Regex support for text fields

- **Multi-Year View** 🔨
  - Browse multiple years simultaneously
  - Quick year switcher (e.g., `Y` key + number)
  - Year boundary indicators in session list
  - Cross-year filtering

### Medium Priority

- **Persistent Configuration** 📋
  - Save last filter between sessions
  - Remember window size and layout preferences
  - Configurable default scope (master/intensive/both)
  - Additional per-user preferences under `~/.config/ivs-sessions-browser/`

- **Enhanced Navigation** 📋
  - Bookmarks for frequently viewed sessions
  - Search within filtered results (`/` for filter, `Ctrl+F` for search)
  - Jump to specific DOY or date
  - Navigation history (back/forward)

- **Extended Visualization** 📋
  - Year-by-year station participation trends
  - Timeline view mode showing session distribution
  - Operator workload summary
  - Session density heatmap by month

- **Session Details Pane** 📋
  - Split-screen mode showing session details
  - View full station list without opening browser
  - Display correlation and analysis status
  - Quick copy of session info to clipboard

### Lower Priority

- **Theme Customization** 💡
  - User-configurable color themes
  - Save/load theme presets
  - High-contrast mode for accessibility
  - Color-blind friendly palettes

- **Mouse Support** 💡
  - Click to select sessions
  - Scroll wheel support
  - Double-click to open in browser
  - Click column headers to sort

- **Notifications** 💡
  - Alert when specified sessions become available
  - Monitor status changes for filtered sessions
  - Email/webhook notifications
  - Desktop notifications on Linux/macOS

- **Offline Mode** 💡
  - Cache fetched data locally
  - Browse cached sessions when offline
  - Cache expiration and refresh control
  - Import/export cache files

## Long-Term Vision (12+ months)

### Advanced Features

- **Session Comparison** 🌟
  - Side-by-side comparison of multiple sessions
  - Difference highlighting (station changes, schedule shifts)
  - Compare across years
  - Export comparison reports

- **Statistical Analysis** 🌟
  - Generate reports on session patterns
  - Station participation trends over time
  - Correlator utilization statistics
  - Operator performance metrics

- **Integration Features** 🌟
  - Direct download of session data files
  - Integration with VLBI data processing pipelines
  - API mode for programmatic access
  - Web service with REST API

- **Collaboration Features** 🌟
  - Shared operator assignments (team mode)
  - Comments/notes on sessions
  - Session tagging system
  - Export/import of operator assignments

### Technical Improvements

- **Testing & Quality** 🔧
  - Comprehensive unit test suite
  - Integration tests for TUI workflows
  - Mock data sources for offline testing
  - CI/CD pipeline with automated tests
  - Type checking with mypy
  - Code coverage targets (>80%)

- **Performance Optimization** 🔧
  - Lazy loading for large datasets
  - Incremental filtering and rendering
  - Background fetch with progress indicator
  - Caching layer for repeated queries
  - Optimize memory usage for multi-year views

- **Documentation** 🔧
  - Video tutorials for new users
  - Interactive demo mode
  - Detailed API documentation
  - Contributing guidelines
  - Example workflows and use cases

- **Packaging & Distribution** 🔧
  - Conda package
  - Snap/Flatpak for Linux
  - Homebrew formula for macOS
  - Docker container
  - Pre-built binaries for Windows

## Community & Contribution

### Areas for Contribution

We welcome contributions in these areas:

1. **Code**
   - Feature implementation from roadmap
   - Bug fixes and performance improvements
   - Test coverage expansion

2. **Documentation**
   - Tutorial creation
   - Translation to other languages
   - Use case examples

3. **Design**
   - UI/UX improvements
   - Theme development
   - ASCII art and branding

4. **Testing**
   - Bug reports with reproduction steps
   - Feature testing on different platforms
   - Accessibility testing

### Versioning Strategy

- **Major versions** (v4.x → v5.x): Breaking API changes, major restructuring
- **Minor versions** (v4.1 → v4.2): New features, substantial improvements
- **Patch versions** (v4.1.0 → v4.1.1): Bug fixes, minor tweaks

## Feedback & Feature Requests

If you have ideas for features not listed here, please:
1. Check existing issues in the repository
2. Create a new issue with the `enhancement` label
3. Describe the use case and expected behavior
4. Include mockups or examples if applicable

## Legend

- ✅ Implemented and available now
- 🔨 High priority - planned for next release
- 📋 Medium priority - planned within 6 months
- 💡 Lower priority - nice to have
- 🌟 Long-term vision - 12+ months
- 🔧 Technical/infrastructure improvements

---

**Last Updated**: May 2026  
**Current Version**: v4.x (development)  
**Next Release Target**: Q2 2026
