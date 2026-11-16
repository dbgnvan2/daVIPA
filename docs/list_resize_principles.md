# How a listing of action items resizes

Read this before adding a listing of action items, or changing how one sizes
its columns. It is the contract eight listings already keep — Today, Upcoming,
All Items, Hierarchical, Completed, the Project Board's linked Action Items,
the Scheduler and the APE Week Actions panel (a `TodayScreen` subclass, so it
takes Today's layout and these defaults with it) — and
`tests/test_list_resize_principles.py` asserts it over all eight, so a new
listing that departs from it fails the suite rather than quietly looking
different. The Week Actions panel builds no toolbar of its own, so the filter
rules below do not reach it; `TOOLBARS` in that file is the other seven, and a
guard holds the exclusion rather than assuming it.

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

8. **A value filter resizes; a control does not.** Who, Status, Segment,
   SubSegment and Project take a share of the toolbar's slack in proportion
   to their own default widths — the same rule as the columns — down to
   `FILTER_MIN_PX` (90) and up to twice the default. A filter that hits
   either limit pins there and the rest of the room is shared again among
   the others, as `ColumnResizer._share` does it, so the drawn total never
   exceeds the room: clamping each share where it stood drew 190 px into 180
   on All Items. The numeric selectors (`Next 7 days`, `Last 30 days`) keep
   their width: they hold one to three characters. A toolbar names its
   filters when it builds its `ToolbarWrap`; a combo it does not name
   resizes like a label, which is to say not at all.

9. **The toolbar wraps rather than clips, and it wraps last.** Controls right
   of the spacer column move to a second row, left-justified, when one row
   does not fit — and "does not fit" means `min_one_row_px()`, one row with
   every filter at its minimum. So the search entry gives up width first
   (down to `SEARCH_MIN_PX`), then the filters, then the row wraps. There is
   no window `minsize`, so `fit` returns the pixels a wrapped row overruns
   the toolbar by and logs the crossing once, the way `ItemListLayout.fit`
   reports a list narrower than its column floors. The budget is held by a
   test as well, because that overflow is past the right edge, off screen.

   `one_row_px()` counts the filters at their **default** widths, never at
   the widths they are drawn at. A threshold measured from the drawn widths
   moves every time a fit resizes them, which makes the next fit's answer
   depend on the last one: All Items read 997 px, then 916, then 922 for one
   toolbar on 2026-11-16, and once it had wrapped it never unwrapped.

## Adding a listing

- Build an `ItemListLayout` (or `ItemListLayout.custom` where the columns are
  not the shared four), passing `TextColumn(key, grid_col, heading)` with no
  width. A key absent from `COLUMN_DEFAULT_PX` raises, which is the intended
  outcome: add the kind to the table, or give the column a width and a reason.
- Call `layout.bind(<the list area>)` so it refits, and `layout.build_header`
  so it gets dividers.
- Pass the screen's value filters to `ToolbarWrap(..., filters=(...))`. The
  conformance test discovers every combo box on the toolbar's control row and
  requires each one to be wired, bar the two named in `NON_FILTER_COMBOS`, so
  an unwired filter fails whether or not anyone remembers to update
  `FILTER_COUNT` and `LISTINGS` in `tests/test_list_resize_principles.py` —
  which you should update anyway, since those are what name your listing at
  all.
- A legacy `<prefix>_title_col_width` scalar in `AppSettings` wins over a spec
  default where someone stored one — it is the only record of a Title width
  dragged before `<prefix>_col_widths` existed. The settings class's own
  default for it does not win, because it is not a width anyone chose: taking
  it was how the Scheduler went on opening at 220 while every other listing's
  Title was 260. Do not raise that default to match the table instead; the
  Plan screen reads the same scalar live for its own title column (PB-M5), so
  that moves a different screen.

Decisions and the measurements behind them:
`docs/unused-docs/implementation_plan_2026-11-16_list_resize_principles.md`.
