# Filter Syntax Reference

## Overview
The IVS Sessions Browser supports a powerful filtering system that allows you to quickly narrow down sessions based on multiple criteria. Filters use a simple field:value syntax with support for logical operators.

## Case Sensitivity
- **Station names**: Case-sensitive (e.g., `Nn` ≠ `nn`)
- **All other fields**: Case-insensitive (e.g., `released` = `RELEASED` = `Released`)

## Basic Syntax

### Single Field Filter
```
field: value
```

### Multiple Clauses (AND logic)
Multiple clauses separated by `;` are combined with **AND**:
```
code: R1; status: released
```
This matches sessions with code R1 **AND** status released.

## Available Fields

The following fields can be used in filters (match column headers):

| Field | Description | Example Values |
|-------|-------------|----------------|
| `type` | Session type | `VLBA`, `IVS`, `IDS` |
| `code` | Session code | `R1`, `R4`, `CRF`, `T2` |
| `start` | Start date | `2025-02-06`, `2025-02`, `jun`, `june` |
| `doy` | Day of year | `037`, `100` |
| `dur` | Duration | `24`, `1` |
| `stations` | Active stations | `Nn`, `Ns`, `Ft` |
| `db` / `db code` | Database code | `SI`, `BD`, `MK` |
| `ops` / `ops center` | Operations center | `USNO`, `WASH` |
| `correlator` / `corr` | Correlator | `BONN`, `WASH`, `SHAO` |
| `status` | Session status | `Released`, `Processing`, `Waiting`, `Cancelled` |
| `analysis` / `analys` | Analysis center | `NASA`, `BKG`, `SHA` |  
| `op` | Operator assignment | Operator labels from `~/.config/ivs-sessions-browser/operators.json` |

## Non-Stations Fields (OR Logic)

For fields **other than stations**, values can be split by multiple delimiters, and they are treated as **OR** logic:

**Supported delimiters**: space, comma (`,`), plus (`+`), pipe (`|`)

### Examples
All of these are equivalent:
```
code: R1 R4
code: R1|R4
code: R1,R4
code: R1+R4
```
Each matches sessions with code R1 **OR** R4.

### More Examples
```
status: released processing waiting
type: VLBA IVS
correlator: BONN|WASH|HAYSTACK
```

## Stations Field (Special Syntax)

Stations fields support three variants with different AND/OR logic:

### Field Variants
1. `stations:` - Active stations only (default)
2. `stations_active:` - Explicit active stations  
3. `stations_removed:` - Removed stations only
4. `stations_all:` - Any stations (active or removed)

### Operators for Stations
- `&` or `&&` → **AND** (all specified stations must be present)
- `|` or `||` → **OR** (any of the specified stations must be present)
- **Default** (space/comma/plus without operator) → **AND**

### Station Filter Examples

#### AND Logic (all must be present)
```
stations: Nn&Ns
stations: Nn&&Ns
stations: Nn Ns
stations: Nn,Ns
```
All match sessions that include **both** Nn **AND** Ns.

#### OR Logic (any can be present)
```
stations: Nn|Ns
stations: Nn||Ns
```
Matches sessions that include **either** Nn **OR** Ns (or both).

#### Removed Stations
```
stations_removed: Ft|Ur
```
Matches sessions where Ft **OR** Ur appears in removed stations.

#### Active Stations
```
stations_active: Kk&Ny
```
Matches sessions where **both** Kk **AND** Ny are active.

#### All Stations (active or removed)
```
stations_all: Ke|Oe
```
Matches sessions where Ke **OR** Oe appears anywhere (active or removed).

## Complex Filter Examples

### Combining Multiple Criteria
```
code: R1|R4; stations: Nn&Ns; status: released
```
Matches sessions where:
- Code is R1 **OR** R4, **AND**
- Both Nn **AND** Ns are active stations, **AND**
- Status is released

```
type: IVS; stations_removed: Ag|Kk; correlator: BONN|WASH
```
Matches sessions where:
- Type is IVS, **AND**
- Removed stations include Ag **OR** Kk, **AND**
- Correlator is BONN **OR** WASH

### Date Filtering
```
start: 2025-02
```
Matches all sessions starting in February 2025.

```
start: 2025-02-06; status: released
```
Matches released sessions starting on February 6, 2025.

```
start: jun
start: june
```
Matches sessions starting in June, regardless of year. All month names and
3-letter abbreviations are accepted. Numeric month-only filters such as
`start: 06` are intentionally not special-cased; use `start: 2025-06` when you
want a year/month date prefix.

### Operator Filtering
```
op: Alice
```
Matches sessions assigned to operator "Alice" (as defined in `~/.config/ivs-sessions-browser/operators.json`).

```
op: Alice|Bob; status: processing
```
Matches processing sessions assigned to Alice **OR** Bob.

## Tips & Best Practices

1. **Station names are case-sensitive**: Use `Nn`, not `nn`
2. **Partial matching**: Text fields support substring matching (e.g., `start: 2025-02` matches all dates in Feb 2025)
3. **Combine filters**: Use `;` to stack multiple conditions
4. **Default operators**: For stations, if you don't specify `&` or `|`, the default is **AND**
5. **Spaces**: In the TUI, filters must be entered carefully; use quotes in CLI: `--filters "code: R1; stations: Nn|Ns"`
6. **Filter indicator**: Active filters are shown in cyan in the status bar at the bottom of the TUI

## Filter Syntax Summary

```
┌─────────────────────────────────────────────────────┐
│ Filter Structure                                    │
├─────────────────────────────────────────────────────┤
│ clause1; clause2; clause3                           │
│    │       │       │                                │
│    │       │       └─ clause3 (field:value)        │
│    │       └──────── clause2 (field:value)         │
│    └──────────────── clause1 (field:value)         │
│                                                     │
│ Clauses are combined with AND                      │
│                                                     │
├─────────────────────────────────────────────────────┤
│ Non-Stations Fields (OR logic)                     │
├─────────────────────────────────────────────────────┤
│ code: R1|R4|CRF    → R1 OR R4 OR CRF              │
│ status: released processing → released OR processing│
│                                                     │
├─────────────────────────────────────────────────────┤
│ Stations Fields (Explicit logic)                   │
├─────────────────────────────────────────────────────┤
│ stations: Nn&Ns    → Nn AND Ns (both present)     │
│ stations: Nn|Ns    → Nn OR Ns (either present)    │
│ stations_removed: Ft|Ur → Ft OR Ur in removed     │
│ stations_all: Ke   → Ke in active or removed      │
└─────────────────────────────────────────────────────┘
```

## Interactive Usage

### In the TUI
1. Press `/` to enter filter mode
2. Type your filter expression (e.g., `code: R1|R4; stations: Nn&Ns`)
3. Press Enter to apply
4. Press `F1`-`F12` to toggle `start: jan` through `start: dec`
5. Press `C` to clear filters
6. Current filter is displayed in the status bar at the bottom

### CLI Mode
Use the `--filters` flag:
```bash
./run_browser --year 2025 --filters "code: R1; status: released"
```

**Note**: Use quotes around the filter expression in the shell to prevent interpretation of special characters.
