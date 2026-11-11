# Handoff Note — LRR manual verification checklist

- Date: 2026-11-11
- Topic: lrr-manual-checklist

## Summary

The LRR batch (`26a0c19..6963d0a`, CI run `42970567833` green on 3.11, 3.12
and 3.13) changed what colour text and row controls are drawn in on a
segment-coloured list row, and which items get a red critical chip. Every
criterion has an automated test. **Nothing was checked on screen**, by anyone,
in either theme — no session can do that here, so this is the part that is
still open.

This note exists because the batch's verification status is not plainly green:
the tests prove `row_fill` and the five screens' conditions, and prove nothing
about what a real row looks like.

## Before you start

1. **Quit the packaged app first** if `/Applications/daVIPA.app` is running. A
   source launch exits silently while it holds the database lock.
2. **The factor chips are hidden by default.** Items 5 and 6 need the
   **Expand** button on the screen's own toolbar (it becomes **Collapse**).
   Today, Upcoming and All Items can start expanded via Settings →
   Appearance → *Start list views expanded (Today, Upcoming, All Items)*;
   Completed always starts collapsed and has its own Expand button.
3. **Switch themes** at Settings → Appearance → *Appearance Mode* (`system`,
   `dark`, `light`). Several checks below differ by theme, and two of them are
   only visible in one of the two.
4. **You need at least one action item whose segment has a colour.** Any item
   with a Segment lineage qualifies: a segment with no stored `color_hex`
   still gets a colour from a deterministic 7-colour fallback in
   `vps_manager.resolve_segment_color`, so an untouched database already shows
   this. Segment colours are set at Vision Planning → Vision Elements (the
   editor's **Color \*** field and **🎨 Pick Color** button).
5. **Only three screens fill the row from the segment colour** — Today,
   Upcoming, All Items. Hierarchical and Completed apply it as an accent
   stripe only and pass `segment_color=None`, so items 1–4 do not apply to
   them. That difference is `PLC-A2`, filed and untouched.

## What the numbers should be

Measured against the eight fallback segment colours, so you can tell "looks
fine" from "is right". Text was the theme's `row_text`; it is now derived.

| Segment colour | New text | Ratio | Was, dark (`#DCE4EE`) | Was, light (`gray10`) |
|---|---|---|---|---|
| `#0EA5E9` blue | black | 7.58 | 2.16 | 6.28 |
| `#10B981` green | black | 8.28 | 1.98 | 6.86 |
| `#F59E0B` amber | black | 9.78 | **1.67** | 8.10 |
| `#EF4444` red | black | 5.58 | 2.93 | 4.62 |
| `#8B5CF6` violet | black | 4.96 | 3.30 | 4.11 |
| `#14B8A6` teal | black | 8.44 | 1.94 | 6.99 |
| `#F97316` orange | black | 7.49 | 2.19 | 6.21 |
| `#64748B` slate | **white** | 4.76 | 3.71 | 3.66 |

4.5:1 is the WCAG AA bar for normal text. Every "was, dark" figure fails it;
every new figure clears it. Both themes improve, so nothing here should look
worse than before in either.

## The checklist

### 1 · A segment-coloured row is legible in the dark theme

Dark theme, Today. Find a row with a segment colour. **Expect:** the title and
every column on that row in **black**, not near-white.

This is the whole of `PLC-A1`. The dark theme is where it was broken —
`#F59E0B` was 1.67:1, which is near-invisible. If the row text still looks
pale, the fix is not reaching the screen.

### 2 · The same row in the light theme

Switch to light. **Expect:** the text still black and still legible.

The change is nearly imperceptible here — the light theme's `row_text` is
`gray10`, already dark — and that is the correct outcome, not a failure. The
one exception is next.

### 3 · A slate `#64748B` row flips to white text in the light theme

**Expect:** white text, and that it reads better than dark text would.

This is the only colour of the eight where the derived answer disagrees with
the light theme's own `row_text`, so it is the only visibly changed row in
light mode. 4.76:1 white against 3.66:1 dark. **Expected, not a bug** — but if
it looks wrong to you, say so, because it is a judgement about your own
colours that no contrast figure settles.

### 4 · The checkbox and drag grip on a segment row — light theme especially

Light theme, Today, a segment-coloured row. **Expect:** the complete checkbox's
border and the drag grip (`⣿`, left edge) drawn in the same colour as the row
text, not in a pale grey.

This is the cold pass's second finding and the item most likely to still look
wrong, because it was the worst measurement in the batch and in the theme I
would not have thought to check: the light theme's checkbox border was
`gray65` against the fill — **1.13:1** on amber, 1.95:1 on slate, against a
3:1 bar for a non-text control. Dark was better but still failing (2.19:1 on
violet). Today's grip had already moved on its own, so before this fix the row
disagreed with itself.

Check **Upcoming** and **All Items** too — same three screens, same change.
Hierarchical and Completed build no row controls at all.

### 5 · The `P:` badge is unchanged for ordinary items

Any of the five screens. **Expect:** exactly the rows that were red before are
red now, in the same red (`danger`, `#B91C1C`).

The condition changed; for every value the UI can produce the answer did not.
A visible difference here on ordinary items means something is wrong. The red
is deliberately unchanged — that is `PLC-A3`, still filed as an open product
decision, so the row tint and its chip still disagree on what critical looks
like.

### 6 · The I and U factor chips agree with the badge

Expand the columns. Find an item with Importance **Critical**. **Expect:** the
`I:20` chip red, and the row's `P:` badge red, on the same row. Then one with
Urgency Critical and Importance blank: `U:20` red, `I:` empty and not red.
**Expect `E:` and `V:` never red**, whatever their values — they are Size and
Value, which are in the priority score and in no priority level.

Four screens draw these: Today, Upcoming, All Items, Completed. Hierarchical
has no factor row.

### 7 · A Critical/blank item still gets the chip

An item with Importance Critical and Urgency blank. **Expect:** the `P:` badge
red. A missing factor has never disqualified an item and must still not.

### 8 · The APE surfaces, which inherit Today's rows

Vision Planning → **APE Week Actions** (pick a weekly tactic; the right panel
lists its action items), and the Action Items panel of **APE Week Assignment**.
**Expect:** items 1, 4 and 6 to hold there too.

`WeekTacticActionsPanel` subclasses `TodayScreen` and overrides neither
`create_item_row` nor `refresh`, so it inherits all of this. That inheritance
is the only reason the panel is covered, and it is asserted by
`test_plc_cold_the_week_panel_inherits_todays_rows_and_reload` — but what it
*draws* has not been looked at.

### 9 · A glance at `app.log`

Search for `is not a #RRGGBB value`. **Expect:** nothing.

If it appears, one of your segments holds a colour the normaliser cannot read,
that row kept the theme's text colour, and you have an instance of `LRR-A1`
(below) in your own data. The message names the value and says where to fix
it, and is logged once per colour rather than once per row.

### 10 · Nothing else moved

Scroll Today, Upcoming and All Items. **Expect:** column alignment, row
heights and the completed-row tint unchanged. The completed tint deliberately
still takes the theme's text colour, so a completed row should look exactly as
it did.

## Risks / Known gaps

- **Items 1–10 are all unverified.** Everything above is a prediction from the
  theme tables and the contrast functions, not an observation.
- `LRR-A1` (medium, new in `BACKLOG.md`): `vps_segment_editor.validate_color`
  accepts `#0X1234`, `#1_2345` and `#+12345`, because `int(x, 16)` takes an
  `0x` prefix and underscores. Such a value reaches Tk and raises `TclError`
  part-way through a row build, taking the list screen down. Pre-existing, not
  a regression — `row_fill` passes the raw value through as the fill exactly as
  before. Item 9 is how you would notice it in your own data.
  **Planned since, by another session:**
  `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md`
  (SCV, draft, approved by nobody at the time of writing). It adds something
  this filing missed — `VPSManager._is_valid_hex_color` is a *second* copy of
  the same three checks, and it gates the colour-repair pass inside
  `get_vision_subsegments` and `get_vision_categories`, so the pass that
  exists to replace a bad colour is blind to this class of bad colour. Its
  SCV-M4 would also stop `row_fill` returning a raw value at all, which would
  supersede the paragraph in `row_fill`'s docstring explaining why it does.
  **Built and closed 2026-11-11** (SCV, 7 of 7 criteria `done`): `LRR-A1` is
  gone from `BACKLOG.md`, `row_fill` returns the normalised value or no fill,
  and that docstring paragraph is replaced. Item 9 below is superseded — a
  malformed segment colour now draws no fill rather than reaching Tk.
- A 3-digit segment colour (`#ABC`) derives its text from the CSS expansion
  (`#AABBCC`) while Tk draws the X11 one (`#A0B0C0`). Same black/white answer
  either way, so the consequence is a wrong contrast figure rather than a
  wrong colour. Below-medium, dropped, reachable only from a hand-edited
  database. **Closed 2026-11-11** as a side effect of SCV-M4.1: the fill is
  now the normalised `#AABBCC`, so Tk draws what the text colour was derived
  from. Asserted by
  `tests/test_priority_level_colors.py::test_scvm41_a_malformed_segment_colour_does_not_become_a_fill`.
- Sixteen other screen modules still call `pick_text_color` on a raw colour,
  so black-on-unparseable remains the house rule everywhere except `row_fill`.
  Nothing records which of the two is now intended. Below-medium, dropped.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_priority_level_colors.py -q`
- Result: PASS (65 tests)
- Command: `./venv/bin/python tools/agents/check_docs_sync.py`
- Result: PASS
- Command: `gh run list` → run `42970567833`
- Result: PASS (3.11, 3.12, 3.13)
- On-screen verification: **NOT RUN** — this note is that gap.

## Next agent actions

- Nothing, unless an item above fails. A failure in item 4 is a code defect in
  `priority_levels.row_control_kwargs` or in the three screens' use of it; a
  failure in items 1–3 is in `row_fill`; a failure in 5–7 is in
  `is_critical_factor` or a call site.
- If item 3 looks wrong to you on your own colours, that is a product
  decision, not a defect, and it belongs with `PLC-A3`.
