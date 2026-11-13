# PCC-A3 fixed — a filled Priority cell has an edge

- Date: 2026-11-12
- Fix: `src/getmoredone/screens/priority_cell.py::build_level_cell`, used by the
  Priority cell on five screens and the critical I/U chip on four.
- Guard: `tests/test_priority_level_colors.py::test_pcca3_a_filled_cell_has_an_edge_on_every_row_surface`

`CTkLabel` takes no border, so the entry's one-line fix was not available. A
filled cell is now a frame with a 1px border in the cell's text colour, holding
the label inset 2px. Colours unchanged. Applied to every filled cell, not only
completed rows: the pale fill was 1.1:1 on a white open row too.

## The entry as it was filed

### PCC-A3 — a completed row's Priority cell is invisible in light mode (medium)

Found by two independent cold passes on 2026-11-12, which reached it
separately. Measured here with the repo's own `color_contrast.contrast_ratio`:

| cell fill | vs completed row, light (`success_tint` `#E8F5EE`) | vs the same, dark (`#1F2B24`) |
|---|---|---|
| Any Critical `#DCFCE7` | **1.02:1** | 13.38:1 |
| Any High `#FEF3C7` | **1.01:1** | 13.19:1 |
| what it replaced, `palette["danger"]` `#B91C1C` | 5.77:1 | 2.27:1 |

Today, All Items and Hierarchical all pass `use_completed_tint=True`, so a
completed critical item is a pale-green row carrying a pale-green cell: the
indicator renders and cannot be seen. The same applies to its `I:`/`U:` chips
on Today and All Items. This repo holds a non-text indicator to 3:1
(`row_control_kwargs`, and `tests/test_priority_level_colors.py`'s own bar).

**Not a defect in the change as approved.** The user was told before approving
that a critical cell would be pale green rather than red, chose that, and on
2026-11-12 was shown the numbers above and chose to ship them and file this
rather than alter the colours or add a border. Recorded so the decision is
visible, not to reopen it.

Note the trade is not one-way: in dark mode these colours are far *better*
against a completed row than the red was (13.4:1 against 2.27:1). The
regression is light mode only.

Fix when touched, cheapest first: give the cell `border_width=1,
border_color=cell.text_color` — the derived text colour is black on both
defaults, so the patch gains an edge at about 19:1 against a completed row
with no colour change at all. Measure it on screen: a
CustomTkinter border draws beneath the widget's children, so it survives only
where `corner_radius` exceeds `border_width` and no child sits flush to the
edge — which is what sank the same fix on the day chips (PBG-A7). Then hold it to 3:1 with a test over every row
background a cell can sit on (each theme's `CTkFrame.fg_color` plus
`palette["success_tint"]`).

No assertion covers this composition: `tests/render_priority_cells.py` renders
open items for the three screens that tint completed rows, and CompletedScreen
passes `use_completed_tint=False`, so no rendered row in the suite has a fill
under a cell. It is the plan's §8 checklist item 4.
