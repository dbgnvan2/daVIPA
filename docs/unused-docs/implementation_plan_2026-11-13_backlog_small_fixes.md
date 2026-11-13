# Implementation plan — backlog small fixes (BSF, 2026-11-13)

The backlog items whose entry already names the fix. Items that are open
design decisions are left in `BACKLOG.md`.

| ID | Backlog item | Change | Test |
|---|---|---|---|
| BSF-M1 | UPD-A7 | delete `drag_index` and `_create_from_index` in `annual_vision_segments.py` | none: deletion of unreachable code |
| BSF-M2 | UPD-A8 | delete the unused `tkinter` import in `weekly_items.py` | none: deletion |
| BSF-M3 | SAG-A5, SAG-A11 | `check_docs_sync.run`: a real newline in the error, and a timeout that raises `RuntimeError` | `tests/test_docs_sync_rule.py::test_bsfm3_*` |
| BSF-M4 | CGH-A1 | conftest's `-topmost` silencer drops the pair wherever it is in the call and passes the rest through | `tests/test_tk_offscreen.py::test_bsfm4_*` |
| BSF-M5 | SCV-A1, SCV-A3 | `interpolate_hex_color` and the weekly tactic dialog's text colour parse through `color_contrast` | `tests/test_segment_colour_validation.py` |
| BSF-M6 | LMM-A2 | `add_block_at` refuses a second LUNCH block on one date | `tests/test_time_block_crud.py::test_bsfm6_*` |
| BSF-M7 | CI-A1 | apt calls in `tests.yml` retry, and the step has a time limit | `tests/test_ci_contract.py::test_bsfm7_*` |

Closed without code: SAG-A6 (the clause was already replaced by
`FILED_PREFIX`), CE-A2 (the console is the manual sign-in's UI: it ends in
`input()`, and `_say` already cannot abort its caller).
