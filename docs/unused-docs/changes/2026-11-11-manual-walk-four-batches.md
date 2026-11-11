# Handoff Note — the on-screen walk four batches are waiting on

- Date: 2026-11-11
- Topic: manual-walk-four-batches

## Summary

One pass through the app that covers everything four batches left
unverified on screen. It consolidates the two per-batch checklists that
already exist and adds the two batches that had none:

| Section | Batch | Range | Its own note |
|---|---|---|---|
| A | LRR — the five list screens' row rendering | `26a0c19..6963d0a` | `2026-11-11-lrr-manual-checklist.md` (10 items) |
| B | SCV — one authority for a segment colour | `c8dbbfc..124b73d` | `2026-11-11-scv-manual-checklist.md` (5 items) |
| C/D | CE + AWA — the calendar update and the week link | `89223d9..0864390` | none |
| E | PF — the Plan screen walk's follow-ups | `71da9e5..a4f40f5` | the plan's **The walk**, step 4 and step 5 |

Every criterion in all four has a passing test. **Nothing in any of them
was looked at on screen, by anyone, in either theme.** Sections A and B
restate their own notes in walk order rather than replacing them; those
notes carry the measured contrast figures and the reasoning, and stay the
reference for a failure.

This note exists because the ordering matters more than the four lists
do: one launch of the app, one database, four batches, and a few of the
checks below are destructive enough (a segment colour re-set, a lunch
moved) that doing them in the wrong order costs a relaunch.

## Before you start

1. **Quit `/Applications/daVIPA.app`** if it is running. A source launch
   exits silently while the packaged app holds the database lock, and
   that app also trips the "real database changed" warning.
2. Launch from source: `./start.sh`.
3. Themes switch at **Settings → Appearance → Appearance Mode**
   (`system`, `dark`, `light`). Section A differs by theme and two of its
   items are visible in one theme only.
4. The factor chips are hidden by default — **Expand** on each list
   screen's own toolbar. Today, Upcoming and All Items can start expanded
   via Settings → Appearance → *Start list views expanded*; Completed
   always starts collapsed.
5. You need one action item whose segment has a colour. Any item with a
   segment lineage qualifies: a segment with no stored `color_hex` still
   gets one from the deterministic 7-colour fallback in
   `vps_manager.resolve_segment_color`, so an untouched database already
   shows this.

## A · Today / Upcoming / All Items — segment-coloured rows (LRR)

Full detail, and the contrast figures to judge "looks fine" against, in
`2026-11-11-lrr-manual-checklist.md`.

1. **Dark theme, a segment-coloured row:** the title and every column on
   it in **black**, not near-white. This is the whole of `PLC-A1` —
   amber `#F59E0B` measured 1.67:1 before, which is near-invisible.
2. **The same row, light theme:** still black, still legible. The change
   is nearly imperceptible here, and that is the correct outcome.
3. **A slate `#64748B` row, light theme:** text flips to **white**. The
   only one of the eight fallback colours where the derived answer
   disagrees with the light theme's own `row_text` — 4.76:1 white against
   3.66:1 dark. Expected, not a bug, but it is a judgement about your own
   colours that no contrast figure settles.
4. **The complete checkbox's border and Today's drag grip (`⣿`) on a
   segment row**, drawn in the same colour as the row text rather than a
   pale grey. **Light theme especially** — this was the worst measurement
   in the batch, `gray65` against amber at 1.13:1 against a 3:1 bar for a
   non-text control. Repeat on Upcoming and All Items; Hierarchical and
   Completed build no row controls.
5. **The `P:` badge is unchanged on ordinary items** — exactly the rows
   that were red before are red now, in the same red (`danger`,
   `#B91C1C`). The condition changed; for every value the UI can produce
   the answer did not, so a visible difference here means something is
   wrong. The red deliberately still disagrees with the row tint; that is
   `PLC-A3`, filed as an open product decision.
6. **Expand the chips.** An Importance-**Critical** item: `I:20` red and
   the row's `P:` badge red, same row. One with Urgency Critical and
   Importance blank: `U:20` red, `I:` empty and not red. **`E:` and `V:`
   never red**, whatever their values — they are Size and Value, in the
   priority score and in no priority level. Four screens draw these;
   Hierarchical has no factor row.
7. **An Importance-Critical / Urgency-blank item still gets the red `P:`
   badge.** A missing factor has never disqualified an item.
8. **The inherited surfaces:** Vision Planning → **APE Week Actions**
   (pick a weekly tactic, read the right panel) and the Action Items
   panel of **APE Week Assignment**. Items 1, 4 and 6 must hold there
   too. `WeekTacticActionsPanel` subclasses `TodayScreen` and overrides
   neither `create_item_row` nor `refresh`; that inheritance is the only
   reason the panel is covered, and what it draws has not been seen.
9. **Nothing else moved.** Scroll all three screens: column alignment,
   row heights and the completed-row tint unchanged. The completed tint
   deliberately still takes the theme's text colour.

## B · The segment colour editors (SCV)

Full detail in `2026-11-11-scv-manual-checklist.md`. Items 10 and 11 are
the only check that `save_segment`'s normalisation is wired to the entry
the user types in rather than to a value a test supplied.

10. **VSP → Settings → VSP Life Segments → Edit a segment.** Type
    `#0X1234` and Save. Expect: **refused**, the error naming the
    `#RRGGBB` form, and the dialog open with the typing intact. Before
    2026-11-11 this saved.
11. **Same dialog, type `#abc` and Save.** Expect: accepted, the dialog
    closes, and re-opening the editor on that segment shows `#AABBCC`.
    Before 2026-11-11 `#abc` was refused.
12. **VSP → Vision Elements → edit a subsegment, then a category.** Both
    dialogs open, each showing a swatch and the stored text, and **Pick
    Color** opens. On a malformed stored colour the swatch is neutral
    slate `#334155` and the text is the stored value. Before 2026-11-11
    the dialog raised on opening.
13. **Both screens that *list* a segment render** — VSP Life Segments and
    VSP → Vision Elements. Before 2026-11-11 the list stopped at the
    first bad row, so the Edit button was never created and the colour
    could not be corrected from the app at all.
14. **Only if `app.log` names a malformed colour (item 29).** Its rows on
    Today, Upcoming and All Items draw with **no fill and no left accent
    stripe** — as they would with no segment colour set — and the screen
    does not blank. Subsegment and category colours *are* repaired on
    read (reopen the screen; they stay repaired). The **segment's own**
    colour is never repaired: there is no repair pass for
    `segment_descriptions`, so it reads back malformed in the editor and
    `app.log` names it on each fresh launch until you re-set it there.

## C · The weekly-tactic link (AWA)

No note of its own. From `89223d9..0864390`: `AWA-A1` now writes
`weekly_tactic_id` only, the launch migration clears `parent_id` on a row
that already names a tactic, and four readers that still read `parent_id`
were moved onto the same link — Plan Day's private copy of
`lineage_for_item`, the segment stamp, its repair pass and the colour
step.

15. **APE Week Assignment → Add an action item against a weekly tactic
    that has no Annual Plan Element of its own.** Expect that item to
    carry its segment chips and its accent on Today, Upcoming and All
    Items, and to appear under Plan Day's **Segment** filter. Before this
    batch it lost all three, and Plan Day disagreed with four other
    screens about the same row.
16. **Relaunch, then look at that item again.** Chips, accent and filter
    unchanged. The launch migration rewrites the row's link columns, so
    this is the check that the migration and the readers agree.
17. **Weekly Items — create an item.** It re-files into the right week
    and the status line reports what the cascade did, as its sibling
    button already did.

## D · The Google Calendar export (CE) — only if you use it

**Read this before performing it.** `CE-A1`'s visible half is narrower
than its commit message suggests: `update_event` gained writable
`location` and `attendees`, and **no caller passes either** — the Plan
day export must not touch them and `calendar_dialog.py` only ever
creates. That half is API symmetry ahead of the first code that edits a
meeting, and there is nothing on screen to check for it. What is
reachable is below.

18. **Export a day (⤴ Google Calendar). In Google Calendar, give one of
    those events a location and a guest. Move the block in daVIPA and
    export the same day again.** Expect: the event moves and resizes, and
    the location and the guest list — with any reply — are still there.
    The preservation itself is `CE-M3.3` and predates this batch; the
    check is a regression check, because this batch edited that function.
19. **The guests get no mail for that re-export.** `sendUpdates='none'`
    is now stated on the update call rather than inherited from the API
    default, which is the same answer `create_event` already gave.

## E · The Plan screen (PF)

No note of its own; the plan is
`docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md`.
Item 20 is `PF-M1.6`, the one criterion in that batch no test can reach.

20. **Drag a single action item onto a Saturday.** Expect the question —
    *"<date> is not a regular work day. Day Settings allows Mon, Tue,
    Wed, Thu, Fri. Schedule anyway?"* Declining writes nothing, schedules
    nothing and leaves the refusal on the status line; a second drop on
    the same date must not ask again, and neither should AutoLoad
    afterwards. **This is the third attempt at a dialog on this path** —
    the first two were each written against a correct diagnosis and each
    failed on screen, one raising `TclError` from the idle callback and
    one hanging the app. A dialog that cannot be shown must still
    schedule the work and name the day it went on.
21. **Drop an item that is already on the day.** Refused, naming the half
    hour: *"… is already blocked at 09:00 — drag that block to move
    it"*. Breaks and buffers stay repeatable. A drop the grid would
    refuse anyway must ask nothing, so the day's one answer is not spent
    on a gesture that writes nothing.
22. **Drop a child on the box holding its parent** → it sits directly
    behind the parent. A continuation whose parent is in another box goes
    to the **top** of the box you drop on. A Weekly Tactic's siblings get
    no ordering rule.
23. **A task spanning half hours:** the greyed `↳` chip is drawn at the
    **top** of each box it runs through, with the tasks that start in the
    box stacked below it. It used to be drawn last, so every new task
    pushed it down.
24. **Drag the `Lunch` box onto another half hour.** This date keeps its
    own lunch there; the length is still Day Settings → Lunch (minutes);
    every other date keeps the lunch the setting names; deleting the box
    hands this date back to the setting.
25. **Drag a block that is already in a Time Block onto Earlier or
    Later.** It moves into the new Time Block and the day grows to hold
    it. The old refusal *"A block cannot make a new half hour"* should be
    gone, and the outline the drag leaves on the last Time Block it
    crossed must not stay behind after the drop.
26. **Drop an item on a box the day grew into** (a half hour outside Day
    Settings' hours). It must take the drop; it was refused as "outside
    the day" while the box was on screen.
27. **The header is two rows** — date, Clear Day, AutoLoad above; +
    Buffer, + Break, ⤴ Google Calendar, ⚙ Day Settings below — and every
    button on both rows takes an equal share as the window widens. The
    screen's messages should say **Time Block** for the half-hour spaces
    and **Action Item** for the work in them.
28. **Never walked, and not part of this batch:** drag an item onto a
    project on the **Scheduler** screen and see whether it files without
    a dialog. Step 5 of the 2026-11-10 walk was not run; its `BACKLOG.md`
    entry says two remedies there were both wrong on screen, so it is
    worth a walk before anything else is written for it.

## F · Finally

29. **Search `app.log` for `is not a #RRGGBB value`.** Expect nothing. If
    it appears, one of your own segment colours is malformed: the message
    names the value and says where to fix it, logged once per colour
    rather than once per row. There is no repair pass for segment
    colours, so that line is the only signal a user gets. It is also the
    precondition for item 14.

## Verification

- On-screen verification: **NOT RUN.** This note is the instrument for
  it, not a record of it.
- The four batches' own test and CI status is in their notes and in
  `docs/spec_coverage.md`; nothing here re-measures any of it.
- `CE-A1`'s unreachable half (item 18's preamble) was read from
  `src/getmoredone/google_calendar.py` and its one caller,
  `calendar_exporter.py:545`, on 2026-11-11.

## Risks / Known gaps

- **Items 1–27 and 29 are predictions**, from the theme tables, the
  contrast functions and the tests — not observations.
- Section A's figures assume the eight fallback segment colours. A
  segment colour you set yourself gets the same treatment and a different
  number.
- Item 20 is the only item here whose failure has a history on screen
  rather than a measurement behind it.
- Sections C, D and E had no checklist before this note, so unlike A and
  B they were not written by the session that built the code. Each item
  cites what it came from; a disagreement between an item and its batch's
  commit message should be resolved by reading the code, as item 18's
  preamble was.

## Next agent actions

- Nothing, unless an item fails. Routing: items 1–3 are `row_fill`; item
  4 is `priority_levels.row_control_kwargs` or the three screens' use of
  it; 5–7 are `is_critical_factor` or a call site; 10–14 are the segment
  colour gates in `vps_manager`, `vps_manager_taxonomy`,
  `vps_segment_editor`, `vision_segments`, `settings_vsp_segments`,
  `theme.apply_segment_accent` and `segment_color_utils`; 15–17 are the
  four readers in `db_manager`, `drag_schedule`, `item_lineage`,
  `segment_color_utils` and `vps_manager`; 18–19 are
  `google_calendar.update_event`; 20–27 are `screens/plan.py`.
- Item 3 looking wrong on your own colours is a product decision and
  belongs with `PLC-A3`, not a defect.
