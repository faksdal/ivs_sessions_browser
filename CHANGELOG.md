# File: CHANGELOG.md
# Changelog
All notable changes to this project will be documented in this file.

## Unreleased
- Added in-app `?` help popup and updated help bar
- Expanded README with features, keymap, and filter syntax
- Introduced docs: USER_GUIDE, FILTER_SYNTAX, KEY_BINDINGS, ROADMAP
- Case-sensitive, AND/OR-capable stations filtering; active/removed/all modes
- Whole-row status coloring; removed stations highlighted

## [0.2.0] - 2025-08-18
### Added
- Support for intensive schedules (`ivscc.gsfc.nasa.gov/sessions/intensive/`)
- `[I]` tag appended to `Type` for intensive sessions
- Sessions are automatically sorted chronologically by `Start`
- `F` hotkey to clear filters in TUI

### Fixed
- Column width for `Code` expanded to 8 to fit intensive session IDs

## [0.1.0] - 2025-08-15
### Added
- Initial version of IVS Sessions TUI browser
- Fetch and display master schedule
- Navigation with arrow keys, PgUp/PgDn, Home/End
- `/` filter input bar
- Color coding for status and removed stations

