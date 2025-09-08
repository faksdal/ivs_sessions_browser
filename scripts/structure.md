
# File: structure.md
# IVS Sessions TUI Browser Program Structure

This document describes the structure, and execution of the script.

## Structure of existing script, ivs_session_browser.py
- main() called on start
  - ArgumentParser() called from main()
  - 'args' and 'cli_stations' are set in main()
  - SessionBrowser(year, scope, session_filter, antenna_filter).run() is called from main with arguments:
    - year = args.year (for instance 2025)
    - scope = args.scope (both, intensive, master)
    - session_filter = args.session (for instance: IVS-R1|IVS-R4)
    - antenna_filter = cli_stations (for instance: Ns|Nn)
    - self.load_data() is called:
      - self.rows are populated by calling self.fetch_all()
      - self.rows are sorted in sort_by_start(self.rows)
      - self.rows are of type class 'list'
      - self.view_rows are populated
      - idx is set to today
      - self.selected = idx
      - self.offset = idx
- curser.wrapper is called with argument self.curses_main