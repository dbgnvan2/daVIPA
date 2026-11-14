# Implementation plan — CIP batch 3, the week view (CIP-M6)

Spec: `docs/spec_2026-11-08_calendar_into_the_plan.md` §8 (CIP-M6.1, M6.2, M7.1).
Status: **approved and built 2026-11-13** with the defaults below. Not walked
on screen: `docs/unused-docs/changes/2026-11-13-cip-week.md`.

**Built differently from W1:** the toggle is in the day pane's heading row,
not the Plan header, whose button groups are pinned by the pf_header tests.
**W7 as built:** unread boxes are a flat border-grey, not hatched (no new
colour), and a failed read in any of the seven is shown before the unread
count and the oldest read time.

## Decisions (W1–W8) — the four marked *(your call)* are defaults, change any

| # | Decision |
|---|---|
| W1 *(your call)* | **Placement:** a `Day` / `Week` toggle in the Plan header. Week replaces the day grid in the same screen; clicking a day column opens that date's day grid. No new sidebar entry. |
| W2 *(your call)* | **Free means** a box in the drawn day that holds no meeting, no lunch and no Time Block. Committed means held by a meeting. Lunch and blocks are neither, and are counted separately ("planned"). |
| W3 *(your call)* | **Days:** the selected date and the six after it ("the next seven days", M6.1). `‹` / `›` step a week. |
| W4 *(your call)* | **Form:** seven narrow columns of the same half-hour boxes, each box shaded free / meeting / planned / lunch from theme tokens (no new colours), with "Meetings 3h · Free 2½h" under each column. Read-only (spec §9): no drag, no menu. |
| W5 | **One code path (M6.2):** each column is `build_day_grid(get_time_blocks(d), bounds, committed=committed_slots(get_commitments(d) minus dismissed, bounds))` — the same call the day grid makes. No second parse and no second occupancy rule. Box counting is a pure function, `week_summary(grid) -> DaySummary`, in a new module `plan_week.py` (logic) next to a new screen mixin `screens/plan_week_view.py`; `plan.py` (3,337 lines) gets only the toggle and the swap. |
| W6 | **One fetch (M6.1):** Refresh in week mode calls `refresh_commitments(first, last, …)` once for the seven dates, under the existing claim (`claim_refresh`), so it is refused while a day refresh or an edit runs and vice versa. Auto-refresh (M5.5) fires once if any of the seven dates is stale. |
| W7 | **Age stays on screen (M5.4) per column:** a date never read draws its boxes hatched with "not read", never as free — an unread day must not look like an empty one. The header shows the oldest read time of the seven. |
| W8 | **Days that are not block days** (Day Settings weekdays) draw their meetings, and show "no blocks" instead of a free count, since nothing can be planned there. |

## Criteria → tests

`TW` = `tests/test_plan_week.py` (logic, no Tk); `TV` = `tests/test_plan_screen_week.py` (unmapped Plan screen, fake client).

| ID | Criterion | Test |
|---|---|---|
| CIP-M6.1a | A week shows the selected date and the six after it | `TV::test_cipm61_the_week_is_seven_days_from_the_selected_date` |
| CIP-M6.1b | Each day's meeting and free minutes are counted from its grid (W2) | `TW::test_cipm61_free_excludes_meetings_lunch_and_blocks`, `TW::test_cipm61_a_box_with_a_meeting_and_a_block_counts_once` |
| CIP-M6.1c | Refresh in week mode makes **one** fetch over the seven dates | `TV::test_cipm61_refresh_fetches_the_range_once` |
| CIP-M6.1d | The week refresh shares the claim: refused while a write or day refresh runs | `TV::test_cipm61_week_refresh_is_refused_while_an_edit_runs` |
| CIP-M6.1e | A date never read is drawn "not read", not free (W7) | `TW::test_cipm61_an_unread_day_has_no_free_count`, `TV::test_cipm61_an_unread_day_says_so` |
| CIP-M6.1f | A non-block day shows "no blocks" (W8) | `TW::test_cipm61_a_non_block_day_has_no_free_count` |
| CIP-M6.1g | Clicking a column opens that date's day grid; the toggle goes back | `TV::test_cipm61_a_click_on_a_day_opens_it`, `TV::test_cipm61_the_toggle_returns_to_the_same_day` |
| CIP-M6.1h | Opening the week makes no network call when every date is fresh | `TV::test_cipm61_opening_the_week_makes_no_call` |
| CIP-M6.2 | The week column and the day grid agree box for box on the same date | `TV::test_cipm62_the_week_column_matches_the_day_grid` (compares `week_summary` of the column's grid with the day screen's own `DayGrid`) |
| CIP-M7.1 | Docs: `USER_GUIDE.md`, `google-calendar-setup.md`, `CHANGELOG.md`, `NOTES.md`, `BACKLOG.md`, `DOCUMENTATION_INDEX.md`, `spec_coverage.md`, spec status line | `check_docs_sync.py` |

Each test mutation-checked against the verbatim line it names, as in batches 1 and 2.
Screen tests use `update_idletasks()`, never a full `update()` (the macOS
hang found in `test_cipm51` during batch 2).

## Order

1. `plan_week.py`: `week_dates`, `DaySummary`, `week_summary` + `TW` (no dependencies).
2. `screens/plan_week_view.py` mixin: draw the seven columns from W5, the toggle in the header, click-to-open + `TV` display tests.
3. Week refresh (W6) and auto-refresh + `TV` refresh/claim tests.
4. Docs (M7.1), then `/csdp`: cold `learning-qa` and a cold correctness pass, mutation run, push.

## Not code-testable (spec §11)

- That the week answers "where is my room" in one look — open it on a real week and find the free afternoon.
- That the shading reads in both themes — look at it in light and dark.
Both go in the handoff note's walk checklist.

## Risks

- **Width:** seven columns of boxes in a Plan pane that is half a window wide on a small screen. A column narrower than ~60 px drops its time labels (only the first column keeps them); measured on the running screen at the walk, not assumed.
- **Seven grids on open:** seven `get_time_blocks` + seven `get_commitments` reads on the Tk thread. Small SQLite reads; measured in a test with 7×20 blocks before any caching is added.
