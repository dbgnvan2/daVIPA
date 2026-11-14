# Implementation plan — resizable list layouts (LSR)

Request (2026-11-13): "For the layouts for Today, Upcoming, All items,
Hierarchical - make them so all items resize as the user changes the height or
width of the whole screen or any resizable panels."

Status: **plan, awaiting approval.** No code written. Tier: Full (`src/`), one
cold pass at least (CLAUDE.md *Review sweeps*).

## What is there now (review)

The app shell already resizes: `app.py:97-107` gives the content frame the
weight, and every screen is gridded `nsew` (`app.py:318-343`). Height already
works on all four: the list is a `CTkScrollableFrame` in a weighted row
(`today.py:109,119`, `upcoming.py:62,68`, `all_items.py:60,66`,
`hierarchical.py:55,61`). The gaps are all **width, inside the screens**:

| # | Where | What does not resize |
|---|---|---|
| R1 | all four | Nothing binds `<Configure>`. Widths are computed once, when rows are built. |
| R2 | `title_format.py:74-82` | `responsive_column_chars(available_width)` ignores its argument and returns constants. Every caller (`today.py:212,501`, `upcoming.py:306`, `all_items.py:258`, `hierarchical.py:242`) passes a width that is thrown away. |
| R3 | all four | SubSegment / Category / Who are fixed `max(56, chars*8)` px; Start, Due 60; Pri `SCORE_CELL_WIDTH_PX`/`ALL_ITEMS_SCORE_CELL_WIDTH_PX`; Time 50; factor chips 120/40; Status 80; Timer 70 (e.g. `today.py:599-734`). |
| R4 | `today.py:498-500` | Title is a fixed pixel width (draggable via `ColumnResizer`, `weight=0`); slack goes to spacer column 99. Widening the window widens nothing. |
| R5 | `upcoming.py:305`, `all_items.py:257`, `hierarchical.py:241` | Title column has `weight=1`, so it stretches, but the label holds the full title with no clamp; narrowed, it is clipped mid-word with no ellipsis. |
| R6 | `all_items.py:218-233` | The column header is a separate grid whose labels have no width, over rows whose cells have fixed widths, so header and row columns do not line up. With columns expanded, rows put factor chips at column 9 and Status at 10 (`all_items.py:435-436`) while the header puts "Status" at 9. Breaks the CLAUDE.md aligned-columns rule. |
| R7 | Upcoming, Hierarchical | No column header, so no divider to drag. |
| R8 | `hierarchical.py:205-206` and `:248,273-274` | Indent is applied twice: frame `padx=indent*30+5` and title `padx=indent*30`. 60px per level, and each level's title column is a different width. |
| R9 | toolbars `today.py:138-205`, `upcoming.py:79-159`, `all_items.py:77-152`, `hierarchical.py:72-123` | One grid row of fixed-width controls; on a narrow window the right-hand buttons (New, Refresh) clip off. |
| R10 | `app.py:53` | No `minsize`; the window can be made narrower than any layout. |

**Shared code:** none between the four screens. Each builds its own rows
(`today.py:471`, `upcoming.py:280`, inline loop `all_items.py:236-452`,
`hierarchical.py:216`) with the same column set and formulas. What can be
reused already exists:

- `ColumnResizer` (`column_resize.py`): per-column `ColumnSpec`, drag
  dividers, persistence to `<prefix>_col_widths`, live text re-clamp
  (`register_row`), and `fit_to_width(available)` — proportional share across
  resizable columns, fixed columns reserved first, five-character floor,
  overflow returned as a count, drag shape kept across resizes (UPD-F4).
  Today uses it for Title only; the VSP screens use it through `ChipTable`.
- Plan's divider (`plan.py:822-925`): `<Configure>` → `on_resize`, ignored
  while `_divider_from_x` is set (a drag is in progress); `apply_items_width`
  reconfigures only on a change so a `<Configure>` cannot feed itself.
  `SplitPanel` is the two-panel version of the same. None of the four screens
  has two panels, so the pattern to reuse is the resize guard, not the splitter.

## Decisions — those marked *(your call)* are defaults, change any

| # | Decision |
|---|---|
| D1 *(your call)* | **Which columns stretch:** Title, SubSegment, Category, Who share the width in proportion to their current widths. Fixed: checkbox/grip, Start, Due, Pri, Time, factor chips, Status, Timer. |
| D2 *(your call)* | **Minimums:** Title 120 px (today's floor); the other stretching columns 5 characters (`MIN_COLUMN_CHARS`). The window gets a `minsize` = sidebar + the widest of the four at its floors, so nothing clips. |
| D3 *(your call)* | **Text:** one line, truncated with "..." to the column (`ColumnResizer.cell_text`), re-truncated on every resize; the full text is kept and returns when widened. Not wrapped (rows stay one height). |
| D4 *(your call)* | **Font sizes do not scale** with the window. |
| D5 *(your call)* | **Upcoming and Hierarchical get Today's pinned column header with drag dividers.** This is new visible UI. Without it they stretch with the window but have no divider to drag. |
| D6 *(your call)* | **Column shape saved per screen** (`upcoming_`, `all_items_`, `hierarchical_col_widths`; Today keeps `today_col_widths`), not one shape shared by all four. |
| D7 *(your call)* | **Toolbar:** the search entry gives up width first (down to 120 px); buttons keep their size; the window `minsize` (D2) also covers the widest toolbar. No second toolbar row. |
| D8 | **One shared module, rows stay per screen.** New `screens/item_list_columns.py`: the column specs, the header builder, and the `<Configure>` binder (debounced to one fit per idle, ignored during a drag, reconfigures only on change). Merging the four row builders is a larger diff and is listed below, not done. |
| D9 | All Items header moves out of the scroll frame to a pinned row, as Today's is, with its own header texts kept ("Immediate Step", "Status", "Actions"). |

## Criteria → tests

`TR` = `tests/test_list_screen_resize.py`: unmapped screens on a module root
(as `test_plan_screen.py` does), `winfo_width` patched, every
`DatabaseManager` on `tmp_path`. Tests marked **(m)** take `mapped_windows`.

| ID | Criterion | Test |
|---|---|---|
| LSR-M1 | Header and every row of each screen give each managed column the same `minsize` (aligned), in both column modes | `TR::test_lsrm1_header_and_rows_agree_per_column[screen-expanded]` |
| LSR-M2a | A wider list area widens only the stretching columns, in proportion; fixed columns keep their widths | `TR::test_lsrm2_wider_list_widens_only_stretch_columns[screen]` |
| LSR-M2b | The real `<Configure>` binding drives the fit (deleting the bind turns it red) | `TR::test_lsrm2_resize_event_refits[screen]` **(m)** |
| LSR-M3 | Below the floors, columns hold their floors and the shortfall is logged as a count, once per crossing | `TR::test_lsrm3_floor_holds_and_shortfall_is_counted` |
| LSR-M4 | Cell text is re-truncated after a refit and the full text returns when widened | `TR::test_lsrm4_text_follows_width_and_comes_back` |
| LSR-M5 | A divider drag persists per screen (D6) and its shape survives a resize; a resize during a drag is ignored | `TR::test_lsrm5_drag_shape_survives_resize`, `TR::test_lsrm5_resize_ignored_mid_drag` |
| LSR-M6 | 20 `<Configure>` events in one idle make one fit; a fit that changes nothing reconfigures nothing (500-item All Items fixture, P9) | `TR::test_lsrm6_events_coalesce_and_no_op_fit_is_silent` |
| LSR-M7 | Upcoming and Hierarchical have a pinned header with dividers (D5) | `TR::test_lsrm7_upcoming_and_hierarchical_have_headers` |
| LSR-M8 | Hierarchical indents inside the title cell only, once per level; columns right of Title align at every depth | `TR::test_lsrm8_indent_once_and_columns_align_across_levels` |
| LSR-M9 | All Items header is pinned and its expanded-mode columns sit over the row columns (factors, Status, Actions) | `TR::test_lsrm9_all_items_header_matches_rows_expanded` |
| LSR-M10 | At the window `minsize`, every toolbar control and the last column lie inside the screen | `TR::test_lsrm10_nothing_clips_at_min_window[screen]` **(m)** |
| LSR-M11 | Contract: every existing toolbar and row control is still present on each screen | `TR::test_lsrm11_controls_preserved[screen]` |
| LSR-M12 | `responsive_column_chars` is removed; every width comes from the resizer | covered by M1/M2 (deleting the function is the change; no source-grep guard) |

The four new mapped tests change the count in CLAUDE.md's Commands block and
`conftest.py`, which `tests/test_ci_contract.py` asserts; both are updated in
the same commit.

Not code-testable: how it looks. A walk checklist goes in the handoff note:
drag the window narrow and wide on each screen, drag each divider, collapse and
expand columns, check a 3-level tree in Hierarchical.

## Order

1. `item_list_columns.py` + the three settings fields, tests first (M1, M3, M6 logic).
2. Today: all columns as `ColumnSpec`s, binder attached (M1, M2, M4, M5).
3. All Items (M9), Upcoming, Hierarchical (M7, M8), one commit each.
4. Toolbar weights and window `minsize` (M10), contract tests (M11).
5. Docs: `docs/USER_GUIDE.md` (resizing the lists), CLAUDE.md mapped count.
   Colour inventory only if a colour literal changes (none expected).

## Adjacent issues found, not fixed

- Four copies of the row builder with the same columns and widths (see *Shared code*).
- `column_resize.py:280` default divider colour `("gray70", "gray30")` is a literal; Today passes the theme border, the default is still there.
- `hierarchical.py:268-269` child titles use a hard-coded `size=14, family="Courier"` font instead of `list_row_font()`.
- `CHAR_PX = 8` (`column_resize.py:19`) approximates the font; a different `LIST_ROW_FONT_SIZE` makes every character budget wrong. `CTkFont.measure` would be exact.
- `all_items.py:225` has 13 weights for 11 headers (harmless, goes with D9).
