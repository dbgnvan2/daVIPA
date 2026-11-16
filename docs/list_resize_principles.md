# How a listing of action items resizes

Read this before adding a listing of action items, or changing how one sizes
its columns. It is the contract seven listings already keep — Today, Upcoming,
All Items, Hierarchical, Completed, the Project Board's linked Action Items and
the Scheduler — and `tests/test_list_resize_principles.py` asserts it over all
seven, so a new listing that departs from it fails the suite rather than
quietly looking different.

The code is `screens/column_resize.py` (`ColumnResizer`: widths, weights,
floors, divider drags, persistence) and `screens/item_list_columns.py`
(`ItemListLayout`, the shared defaults, `ToolbarWrap`).

## The principles

1. **One default width per column kind**, in `COLUMN_DEFAULT_PX`. A listing
   names its columns and takes the width; it does not choose one. Title 260, a
   lineage column (Segment, SubSegment, Category) 150, Who 110, a date column
   110, Status 90, Time 60.

2. **A default is also a weight.** A listing shares the width it is given
   across its resizable columns in proportion to their weights, so each
   column's change is a fixed ratio of Title's change. That is what makes two
   listings at different widths feel like the same list.

3. **A drag writes a weight, not a width.** The shape the user set therefore
   survives a window of a different size, and it is the weights — not the
   drawn widths — that persist. A list held partly at its floor draws widths
   that are not its shape.

4. **One floor: six characters at the row font** (`list_floor_px()`), Title
   included. It follows the row-font setting, so a larger font widens every
   floor. A list too narrow for its floors keeps them and reports the
   shortfall in pixels; a floor that gives way under pressure is not a floor.

5. **One maximum per column kind**: 2000 px for Title, 800 for everything
   else. A column at its maximum stops taking its share, so these have to
   match across listings or two lists diverge on a wide window.

6. **Controls keep their size.** A checkbox, a Timer button, a priority cell
   or the factor chips are fixed width in the header and in every row, and are
   not in the defaults table. The priority cell is the one column kind
   deliberately sized per listing (60 px, 80 on All Items), which is why it is
   listed in `UNSHARED_KEYS`.

7. **Every listing refits on `<Configure>` of its list area**, debounced by
   `FIT_DELAY_MS` so a window drag refits once at the end rather than on every
   event, and never mid-drag of a divider.

8. **The toolbar wraps rather than clips.** Controls right of the spacer
   column move to a second row, left-justified, when one row does not fit.
   There is no window `minsize`; the budget is held by a test instead, because
   a wrapped row wider than the toolbar overflows an edge where nothing sees
   it.

## Adding a listing

- Build an `ItemListLayout` (or `ItemListLayout.custom` where the columns are
  not the shared four), passing `TextColumn(key, grid_col, heading)` with no
  width. A key absent from `COLUMN_DEFAULT_PX` raises, which is the intended
  outcome: add the kind to the table, or give the column a width and a reason.
- Call `layout.bind(<the list area>)` so it refits, and `layout.build_header`
  so it gets dividers.
- A legacy `<prefix>_title_col_width` scalar in `AppSettings` wins over a spec
  default, so it must equal the table's Title. The Scheduler opened at 220
  rather than 260 for exactly this reason until 2026-11-16.

Decisions and the measurements behind them:
`docs/unused-docs/implementation_plan_2026-11-16_list_resize_principles.md`.
