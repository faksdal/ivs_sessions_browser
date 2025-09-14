# File: docs/FILTER_SYNTAX.md
# Filter Syntax:
- stations: case sensitive
- other:    case in-sensitive

## Clauses
- Multiple clauses separated by `;` are AND across clauses.
- A clause is either plain text (searches all columns) or `field: value`.

## Fields
- `type`, `code`, `start`, `doy`, `dur`, `stations`, `db code`/`db`, `ops center`/`ops`, `correlator`, `status`, `analysis`.

## Non‑Stations Fields (OR)
- Split `value` on **space/comma/plus/pipe** → OR within the field.
- Example: `code: R1 R4` == `code: R1|R4` == `code: R1,R4` == `code: R1+R4`

## Stations Fields
- Active-only: `stations: …`
- Removed-only: `stations_removed: …`
- Any (active or removed): `stations_all: …`

### Operators
- `&` or `&&` → AND inside stations.
- `|` or `||` → OR inside stations.
- If no operator, default AND over space/comma/plus.

### Examples
- `stations: Nn&Ns`
- `stations: Nn|Ns`
- `stations_removed: Ft|Ur`
- `code: R1|R4; stations: Nn&Ns`
