# daVIPA User Guide

This guide explains what each screen, button, and workflow does, and why you might use it. It is aligned to the current UI and screen code in `src/getmoredone/screens`.

Last updated: 2026-06-06

---

## 1) What daVIPA is for

daVIPA is a desktop task manager focused on prioritization and execution.

- What: A single place to capture action items, assign priorities, and schedule work.
- Why: It helps you decide what to do next, track progress, and keep long-term planning connected to daily execution.

---

## 2) Core concepts

### List Views
- What: In this project, `List Views` refers specifically to the `Today`, `Upcoming`, `All Items`, and `Hierarchical` screens.
- Why: These four screens share list-style browsing, filtering, and row presentation patterns, so they are treated as one UI family in planning and implementation discussions.
- Layout note: The current List Views show `Title`, `SubSegment`, and `Category` as stable columns and keep `Immediate Step` readable as the window narrows; lower-priority columns compress first.

### Action Items (tasks)
- What: The central record you work with. Required fields: `Who` and `Title`.
- Why: A consistent structure makes filtering, scheduling, and prioritization reliable.

### Time Blocks (the spaces on the Day Plan)
- What: One half-hour space in the Plan screen's day. Empty, or holding up to
  four Action Items.
- Why: The two words are not interchangeable, and the screen's messages use them
  this way: **Action Items** are the work, **Time Blocks** are the spaces it
  goes into. A 90-minute Action Item takes three Time Blocks; a break, a buffer
  or a lunch takes one.

### Priority score
- What: Calculated as Importance x Urgency x Effort-Cost (Size) x Value.
- Why: A single number makes it easy to rank items and focus on the highest impact work.

### Dates
- What: Each item can have a Start Date and a Due Date.
- Why: Start dates help with scheduling; due dates help with deadlines.
- Rule: Due date is never earlier than start date.

### Planned minutes
- What: Your estimate for how long the item should take.
- Why: Powers time blocks, timer defaults, and planned vs actual stats.

### Status
- What: Items can be `open`, `completed`, or `canceled`.
- Why: Status controls what shows up on Today/Upcoming views and what counts toward stats.

### Contacts and Who
- What: Contacts are people/clients. The item `Who` field can link to a contact.
- Why: You can filter by Who and keep consistent naming across items.

### Links (Item Links)
- What: Attachments/URLs tied to an item (e.g., Obsidian notes, Google Calendar events).
- Why: Keeps the context for a task inside the task.

### Hierarchy (parent/child tasks)
- What: Any item can have child items. An item gets a parent in one of two
  ways: you set one with **Set Parent**, or you file the item under a Weekly
  Tactic — a tactic is the parent of the items filed under it, and behaves like
  one everywhere a parent is shown (the Hierarchical tree, **Show Related**,
  the editor's `Parent:` line, and the delete guard).
- Why: Useful for breaking large work into smaller next actions, and it means
  a week's plan and the work under it are one tree rather than two lists.
- If an item has both — a parent you set *and* a Weekly Tactic — the parent you
  set wins, so the item appears in one place in the tree, not two. The tactic
  is still shown on the editor's Organise tab.

### VSP (Vision Strategy Plan)
- What: A planning hierarchy from long-term vision down to weekly actions, grouped by life segment.
- Why: Connects long-term goals to day-to-day tasks.

---

## 3) Screen-by-screen guide (What + Why)

### Today
- What: Shows items scheduled for today, split into open and completed today.
- Why: A focused daily view of what matters right now.
- **Column headers & resizable Title** — What: A pinned heading row (Title, SubSegment, Category, Who, Start, Due, Pri, Time) stays put while the list scrolls. Drag the vertical divider at the right edge of the **Title** header to widen or narrow the Title column, spreadsheet-style; titles re-clamp with `…` as you drag. Why: Make room for long titles without losing the other columns. The width is remembered between sessions.

Header controls:
- **Search** — What: Searches title, description, and next action within Today scope. Why: Quickly find an item.
- **Expand/Collapse** — What: Toggles extra columns and priority factor chips. Why: Show or hide detail to reduce noise.
- **Top 3** — What: Shows only the top 3 open items by priority. Why: Focus on the highest priority work.
- **+ New Item** — What: Opens the Item Editor for a new task. Why: Capture work quickly.
- **Refresh** — What: Reloads the list. Why: Pull in updates after edits.

Row controls (open items):
- **Drag to top (pin)** — What: Each open row has a small drag handle (`⣿`) at its left edge. Drag it upward to pin the item above every other Today row. Why: Force a task to the top regardless of its priority score. The pin sticks (it survives edits, priority changes, and reschedules) and is independent of the calculated priority — dragging another item to the top puts that one above. Pinning affects the Today list only.
- **Complete checkbox** — What: Marks item completed. Why: Clear finished work and log progress.
- **Timer** — What: Opens the focused timer window. Why: Work in a time block and log actual time.
- **Edit** — What: Opens the Item Editor. Why: Adjust details or add context.
- **Quick date edit** — What: Click a row's **Start** or **Due** cell to open the inline date editor. Alongside `Today`, `-1`, and `Clear`, a **From today** row offers `+1 +2 +3 +4 +5 +6 +7 +10 +14` buttons that set the date to that many days from today (weekend-aware). Why: Reschedule in one click without typing a date.
- **Push** — What: Moves start/due dates forward by 1 day using weekend settings. Why: Reschedule quickly.

Completion feedback:
- **Completion badge** — What: Completed rows can show a large green check mark or a user-uploaded badge image. Why: Make completion more visible and customizable.
- **Confetti threshold** — What: Optional celebration every N completions in the current session. Why: Add lightweight positive feedback without changing completion logic.

### Upcoming
- What: Shows open items due within the next N days, grouped by date.
- Why: Plan and look ahead without losing overdue items.

Header controls:
- **Search** — What: Searches title, description, next action. Why: Find items fast.
- **Next N days** — What: Sets the lookahead window. Why: Match planning horizon.
- **Who** — What: Filters by Who. Why: Focus on a client or context.
- **Expand/Collapse** — What: Toggles extra columns and priority factor chips. Why: Show or hide detail.
- **+ New Item** — What: Opens the Item Editor. Why: Capture a new upcoming task.

Row controls (open items):
- **Timer** — What: Starts the timer window. Why: Execute the task in a focused block.
- **Edit** — What: Opens the Item Editor. Why: Update scheduling or details.
- **Push** — What: Moves start/due forward by 1 day (weekend-aware). Why: Reschedule quickly.

### All Items
- What: A table view of all items, with filters.
- Why: Full visibility across open, completed, and canceled items.

Header controls:
- **Search** — What: Searches title, description, next action. Why: Locate items quickly.
- **Status** — What: Filters by open/completed/canceled/all. Why: Narrow the list to the state you need.
- **Who** — What: Filters by Who. Why: Focus on a person or client.
- **Expand/Collapse** — What: Toggles extra columns and priority factor chips. Why: Show or hide detail.
- **+ New Item** — What: Opens the Item Editor. Why: Add a new item.

Row controls:
- **Complete checkbox** — What: Marks an open item completed. Why: Clear finished work.
- **Timer** — What: Starts a timer for open items. Why: Track actual work time.
- **Edit** — What: Opens the Item Editor. Why: Modify item details.

### Hierarchical
- What: Tree view of parent/child relationships.
- Why: Visualize complex tasks and their sub-items.

Header controls:
- **Search** — What: Searches items. Why: Find a node quickly.
- **Status** — What: Filters by open/completed/all. Why: Reduce tree noise.
- **+ New Item** — What: Creates a new item. Why: Add tasks from the hierarchy view.

Behavior:
- Without search: shows roots and children indented. A Weekly Tactic is a root,
  with the items filed under it indented beneath it, and its row shows `(N sub)`
  counting them.
- With search: shows a flat list of matching items.

### Scheduler
- What: A drag-and-drop rescheduling view. Left side shows Action Items; right side shows Date Boxes and a Calendar tab.
- Why: Quickly drag tasks onto a specific date and reschedule in one move.

Header controls:
- **Next N days** — What: Sets how many date boxes to show. Why: Adjust your planning horizon.
- **Who** — What: Filters the left list by Who. Why: Focus on one client or context.
- **Segment / SubSegment** — What: Filters the Scheduler by APE lineage. Why: Focus scheduling on one planning area.
- **Refresh** — What: Reloads the full visible range using the current `Next N days` and `Who` filters and clears any clicked date filter. Why: Reset back to the full scheduling set.

Main area:
- **Action Items list (left)** — What: Open items with no dates plus upcoming items in the selected window. Why: A short list of items worth scheduling.
  - Columns: `(checkbox)`, `Title`, `Segment`, `SubSegment`, `Category`, `Start`
  - **Resizable columns** — What: Every data column (Title, Segment, SubSegment, Category, Start Date) has a draggable divider at its right edge; drag it to widen or narrow the column, spreadsheet-style. Cell text expands to fill the new width (so a wide Title shows the full title instead of "…"). Widths are remembered between sessions. Same reusable resizer as the Today view.
  - **Row checkbox** — What: A checkbox in the first column of each item row. Why: Select several items to move them together (see "Drag a group" below). Optional — leave them all unchecked to drag items one at a time.
- **Date Boxes (right)** — What: Drop targets for dates. Why: Reschedule by drag-and-drop.
  - Date box columns: `Day`, `Date`, `Items`, `Time`
  - Weekday names use the full day name.
  - Start-date color rule on the left list: overdue = red, today = green, future = yellow.
  - Date/future box height: controlled by setting (`Drag Schedule box height (px)`).
- **Next item rows (left)** — What: draggable source records. Why: schedule items quickly.
  - Row height: uses the same `Drag Schedule box height (px)` setting for visual alignment with right-side boxes.
- **Calendar tab** — What: Month-style calendar with clickable/drop-target day boxes. Why: Schedule by calendar instead of date list.
- **Projects tab** — What: A list of active project boxes. Why: Drag action items onto a project to link them.
  - Project box columns: Shows project title, planning lineage, and open item counts.
  - Row height: 50% larger than date boxes for prominence.
  - **No Project box** — What: A special box at the top of the project list. Why: See unlinked items or drag an item here to remove its project link.
- **Future options (bottom)** — What: `Next Month`, `Next Quarter`, `Near Term`, `Long Term` boxes. Why: Fast scheduling to common future anchors.

Drag behavior:
- **Drag onto Date** — What: Drag an item title onto a date box or calendar day. Why: Sets both Start Date and Due Date to the drop date.
- **Drag onto Project** — What: Drag an item title onto a project box. Why: Links the item to that project and synchronizes its planning lineage (APE).
- **Drag onto No Project** — What: Drag a linked item onto the "Unlinked" box. Why: Removes existing project links and clears planning lineage.
- **Drag a group (checkboxes)** — What: Check one or more item rows, then drag any *checked* row. Why: Every checked item moves together to the dropped date or project in one action. Dragging an *unchecked* row still moves just that one item, so single-item drag is unchanged. While dragging a group the drag label shows the count (e.g. "3 items").

Filtering behavior:
- **Click a date box or calendar day** — What: Filters the left list to that specific date. Why: Inspect what is already scheduled there.
- **Click a project box** — What: Filters the left list to show items linked to that project. Why: See the current project backlog.
- **Click the same date/project again** — What: Clears the filter. Why: Return to the full view quickly.
- **Project Sort** — What: Dropdown to sort projects by Title, Subsegment, or Category. Why: Find projects faster in long lists.
- **Refresh** — What: Reloads the full visible range and clears all active date/project filters. Why: Reset back to the full scheduling set.
- **Resize divider** — What: Drag the center divider between left and right panels. Why: Give more space to either the item list or the date/calendar/project panel.

### Projects
- What: A board of project notes, each linked to an Annual Plan Element (APE).
- Why: Gives you a visual project layer between planning and individual action items.

Board behavior:
- **Every project has an APE (required)** — What: A project must be linked to an Annual Plan Element; the editor defaults new projects to `Contribution - Projects - Projects` as a catch-all and refuses to save without an APE. Why: The APE supplies each project's Segment/SubSegment/Category lineage, which drives card color and the Scheduler's Segment/SubSegment filters.
- **Multiple projects may share one APE** — What: Several projects can point at the same APE (for example, many under the catch-all `Contribution - Projects - Projects`). Why: You are not limited to one project per planning element. APEs still auto-create a starter project note, but you can add more.
- **Color** — What: Note color comes from the APE category color. Why: Preserve planning lineage visually. If a card looks uncolored, its APE's category has no color set, or (on older data) the project had no APE — re-open the project, confirm the APE, and Save.
- **Top title** — What: Each note shows `SubSegment - Category`. Why: Keep the planning context visible at a glance.
- **Rank box** — What: A prominent number in the upper-left shows the board order position. Why: Make manual ordering obvious after dragging cards.
- **Body** — What: Shows the project title, full next step (bolded), and as many notes as will fit. Why: Keep strategic work visible on the board without manual setup.
- **Click a note** — What: Selects the note and loads its detail panel. Why: Prevent accidental opens while still supporting drag reordering.
- **Drag notes** — What: Reorders notes left-to-right, top-to-bottom. Why: Let you organize the board visually.
- **Board divider** — What: Drag the vertical divider between the board and detail panel. Why: Make the board wider or narrower.
- **Note Size slider** — What: Resizes all notes together. Why: Fit more notes on the board or make them easier to read.
- **Compact Height** — What: Reduces note height. Why: Fit more notes vertically.

Note actions:
- **Pencil** — What: Edit project (vertical yellow pencil with black tip and red eraser). Why: Update title, next step, notes, or status.
- **Plus** — What: Create and link a new action item. Why: Turn project planning into execution.
- **Page (📄)** — What: Opens a small chooser asking "Create New Obsidian Note" or "Link Existing Obsidian Note", which delegates to the same dialogs used for Action Item notes. Why: Make the natural reading of the icon ("add a note here") match its behavior.
- **Clock** — What: Set project note to Pending. Why: Hide it from the active board without deleting it.
- **Check mark** — What: Set project note to Completed. Why: Remove it from the active board when finished.
- **Trash can** — What: Delete the project note. Why: Remove obsolete project records when appropriate.

Filters:
- **Show Pending / Show Complete** — What: Toggles those note states onto the board. Why: Review inactive work without mixing it into the default active board.
- **Link Action Item button color** — What: In the detail panel, the button uses the Category color. Why: Keep the project-to-action workflow visually tied to planning lineage.

#### Project detail panel (right side)

The header above the two lists carries a **Time** line:

```
Time: 12 sessions | 8h 45m
```

That is every timer session logged against every action item filed under this
project — completed items and follow-ups included, since a follow-up inherits its
project link. It is counted from the session records themselves rather than kept
as a running total on the project, so it cannot drift out of step with them.

Not to be confused with the reward protocol's own counter, which counts
*completed deliverables* (Done presses) to decide how often you get a celebration
and carries no time at all. See "The reward protocol" below.

When you click a project on the board, the right side shows two stacked sections — Project Notes on top, Action Items below — with a shared filter above both.

- **Shared "Show Completed" checkbox** — What: A single toggle above both lists, default OFF. Why: First view shows only open Project Notes and open Action Items; flip it on to reveal completed work in both lists at once.

Project Notes section:
- **What it is** — Each row is an Obsidian note linked to this project. Project Notes have a Status (Open / Completed) but no priority and no dates.
- **Per-row buttons**:
  - **Open** — What: Opens the note in your Obsidian vault. Why: Read or edit the note.
  - **Complete** / **Reopen** — What: Flips the note's status. Why: Track whether a reference doc still needs attention.
  - **Unlink** — What: Removes the link from this project (does not delete the .md file). Why: Disassociate a note that no longer belongs.
- **Ordering** — Notes are shown most-recently-linked first.
- **Count label** — Reads "N note(s) shown" or "N shown • M completed hidden" when the shared filter hides completed notes.

Action Items section:
- **Select All checkbox** — What: Checks every visible action item row in one click. Why: Avoid clicking each row when planning a bulk change. Respects the shared Show Completed filter — only visible items are selected.
- **Per-item checkbox** — What: Selects a single action item. Why: Build an arbitrary selection for bulk edits.
- **Bulk Edit button** — What: Enabled when ≥1 item is selected; opens a small dialog. Why: Apply Start Date and/or Priority to several items at once.
  - **Start Date** — Future dates only (today or later). When set, Due Date is auto-set to Start Date + 1 day for every selected item.
  - **Priority** — Any importance value, or "(Skip)" to leave each item's existing priority untouched.
  - **Field preservation** — Leaving a field blank / on "(Skip)" preserves the existing value for every selected item; only the fields you fill in change.
- **Edit / Complete / Unlink** — Per-row controls work as before.

#### Toolbar buttons (right panel)
- **Create Action Item** — Add a new task to this project.
- **Link Action Item** — What: Opens the Link Action Items dialog to attach existing tasks to this project. Why: Pull already-created items onto a project so they pick up its planning lineage.
  - **Search** — Filter by title, description, next step, or who.
  - **Filter buttons (AND logic)** — `Completed`, `Not Completed`, `Linked`, `Not Linked`. What: Toggle any combination; active filters highlight and all selected filters must match (e.g. `Not Completed` + `Not Linked` shows only open tasks not yet on any project). Why: Narrow a long task list to exactly the items you want to link.
  - **Per-row checkbox + Link Selected** — What: Check several rows and click **Link Selected** to attach them all at once; the per-row **Link** button still links one item. Why: Bulk-link a batch without clicking each row.
  - Linking an item also stamps the project's APE onto it, so it becomes filterable by Segment/SubSegment in the Scheduler.
- **Bulk Edit** — See above; enabled when items are selected.
- **Edit Project** — Open the project editor dialog.
- **Create Note** / **Link Note** — Create a new Obsidian note (lands in your Project Notes Folder) or link an existing one.
- **Open Notes** — Browse the project's linked notes in a separate dialog (kept for explicit "show me the notes I have" use).

### Plan (Time Blocks)
- What: Build a day by dragging the items that start on that date onto a grid of
  half-hour boxes.
- Why: A planned day is a **grid**, not an order. Every half hour from Day Start
  to Day End is a box, drawn whether you have put anything in it or not, and you
  drop work on the box you want it in.

> **Before you start: the start dates must be right.**
> This screen lists the items whose Start Date is **exactly** the date you have
> selected — not "on or before", and not overdue items carried forward. An item
> with a missing or wrong start date will simply not appear here, and nothing
> will tell you it is missing. Fix the start dates first (the Scheduler and the
> item editor are the places to do it), then come back and plan the day.

Three things follow from the grid, and they are the whole model:

1. **Gaps are a legitimate day.** An empty 09:00 between two filled boxes is a
   day with a gap in it, not a mistake to be packed away. Nothing slides up to
   close it, ever.
2. **Lengths round up to whole boxes.** A 45-minute task takes two boxes. It
   keeps its own 45 minutes — it ends at 09:45 — and the second box says
   `15m spare`, because that quarter hour is spent even though the task does not
   use it. The next task starts at the following box.
3. **A box is worth 30 minutes however many tasks are in it.** Up to four tasks
   can share one half hour; the box grows to show them all, and still counts as
   one half hour of your day.

Header, in two rows. The first holds the date, **Clear Day** and **AutoLoad** —
the three controls that are about the day as a whole. The second holds
**+ Buffer**, **+ Break**, **⤴ Google Calendar** and **⚙ Day Settings**, the
four that add something to the day or open something else. Every button on both
rows takes an equal share of the width, so widening the window widens the
buttons together instead of leaving them at a fixed size beside panes that grew.

- **Date picker** — What: Chooses the day you are planning. Why: Changing it
  reloads both panes. It is a picker rather than a typed field, so a date that
  cannot be stored cannot be entered.
- **⚙ Day Settings** — What: Opens the Day Settings modal (below). Why: The
  hours of the day are what the grid is drawn from.
- **⤴ Google Calendar** — What: Writes this day's blocks to Google Calendar as
  timed events. Why: the day you planned is no use to the rest of your life
  while it only exists in daVIPA; a planned day on the calendar is a day other
  people can see you are busy.

  Every block **on the grid** that has a length goes out — items, buffers and
  breaks alike — titled the way the block is titled on screen, and timed from
  **the box it is drawn in**, not from any time stored with it. That matters
  because the grid moves: change *Day Start* and the whole day shifts on
  screen, and what goes on the calendar is the time you can see, every time.

  Blocks under *Outside the day* are skipped and counted — a block with no box
  has no time the app knows, and putting work on your calendar at an hour
  nobody chose is worse than leaving it off. *Outside the day* is exactly what
  the day shows there, so a block that fell out because you moved *Day End*
  earlier, or moved the lunch hour over it, is skipped too. Lunch is not a
  block, so nothing is written for it.

  **A second export of the same day does not duplicate it.** Each block
  remembers the event it owns: a block you moved or resized moves and resizes
  on the calendar, a block you deleted takes its event with it, and an event
  you deleted in Google Calendar by hand comes back. Events daVIPA did not
  create are never touched, so your real meetings are safe even in the same
  hour. A block whose export failed keeps the event it had — nothing is removed
  on the strength of a run that did not finish. A block you delete *while* an
  export is running is not left behind either: the event it was given is taken
  back off the calendar, and the status line counts it. Exporting a day you have
  **cleared** is worth doing for that reason: there is nothing to send, but the
  events that day had still come off the calendar — *"No blocks planned for
  2026-11-12 — 2 removed"*.

  The button disables itself while the export runs and the status line reports
  every number, the ones that did not happen included — *"3 of 5 block(s)
  exported to Google Calendar for 2026-11-12 — 2 new, 1 updated, 2 skipped
  (not on the grid)"*. One block failing is one block failing: the rest of the
  day still goes out and the run can be repeated. Without the Google
  libraries, without credentials, **before you have connected your account
  once**, or when the connection you had has stopped working — access revoked,
  password changed — the button says so and comes back rather than staying
  dead. Signing in has to happen where a browser can open, which is an item's
  *Add to Calendar* dialog; the export runs in the background and will never
  open one, so it stops and tells you instead of hanging.

  One export per day runs at a time. Starting a second one of the same day —
  from this window or another — is refused with *"2026-11-12 is already being
  exported"* rather than run alongside the first.

  Exported blocks carry **no reminder of their own** — they use whatever your
  calendar is set to do, so a planned day does not become a day of popups. A
  meeting made from an item's *Add to Calendar* dialog still gets its
  ten-minute popup.

  Setup is in `docs/google-calendar-setup.md`; the day goes to your primary
  calendar unless `plan_export_calendar_id` names another. **If you change
  that setting, the next export moves the events it had already made** — off
  the old calendar, onto the new one, reported as *"3 moved to this
  calendar"* — rather than leaving them stranded where nothing can find them
  again.

  The status line it writes to is the full-width line **under the day**, not in
  the header: with seven controls up there the header had no room left for it.
- **+ Break** / **+ Buffer** — What: Puts a 30-minute padding block in the first
  box that will hold it. Why: Real days are not back-to-back. These carry no
  item, so they are drawn in a neutral colour rather than a priority one — the
  same stripe colour and the same box surface as lunch, because the three are
  one kind of thing: time the day is not working. An empty box is not drawn
  that way; it is room, and it is drawn as room.
- **AutoLoad** — What: Blocks every item in the left-hand list that the day
  still has room for, one after another: from the top of the list down the
  day, each at the earliest half hour with nothing in it. A task longer than
  half an hour takes the boxes it needs, and the next item starts after them.
  Why: a day's worth of dragging in one click. It only ever adds — nothing
  already on the day moves, changes length or disappears — so a run you did not
  want can be undone by deleting the blocks it made. It will not lengthen the
  day to fit the list: an item with nowhere to go is reported rather than
  squeezed in, and *Day Start* / *Day End* stay where you set them.

  It skips an item that already has a block today rather than giving it a
  second one, and it leaves the half hours lunch covers alone.

  The status line to the right of the buttons says what happened, with all
  three numbers every time — `AutoLoad: blocked 4 of 7 — 2 did not fit, 1
  already blocked` — so "blocked 4" can never be mistaken for "blocked 4 and
  there were only 4". A day with no items on the left says *nothing to block*,
  which is not the same as no room. The whole run is one write: if the day
  refuses a block part-way, nothing at all is written and the message says how
  far it had got. On a day the week's Day Settings exclude, the button asks
  the same question a drop onto that day asks, and plans the day on a Yes.
- **Clear Day** — What: Takes every scheduled item back off the day — the
  reverse of AutoLoad. Why: A plan you want to redo takes one click to undo
  rather than one right-click per block. It asks first, with the count in the
  question (*"Remove 5 scheduled items from 2026-11-07?"*), because the app has
  no undo. **Breaks and buffers stay**: AutoLoad never wrote one, each was put
  there by hand, and the question says how many are staying. A lunch you moved
  stays too, for the same reason. Lunch is otherwise not a block at all — it
  comes from *Day Settings* — so it is untouched either way.
  A day with no items scheduled says *nothing to remove* and asks nothing. It
  does not ask about the weekday list: taking work off a day is not planning
  work onto it, so a Saturday you filled can be cleared without being asked
  about the week again.
- **Earlier** / **Later** — What: A box at each end of the day column, above
  the first half hour and below the last. They sit outside the scrolling grid,
  so both are on screen whatever the day is scrolled to — a day with more half
  hours than the pane can show used to put **Later** below the bottom of it,
  where no drag could reach it. Drop an item on one and the day
  lengthens to hold it: *Day Start* moves back, or *Day End* moves forward, by
  the item's own work-block length, and the item is blocked in the new half
  hours. Why: the day you planned is not always the day you get, and the
  alternative is opening Day Settings, working out the arithmetic and then
  coming back to drag the item. The boxes are there on an empty day too — that
  is the day with no first block to drop above.

  Everything already on the day keeps the time it had. The day cannot be
  extended across midnight: an item too long to fit before *Day Start* or after
  *Day End* is refused and says so, rather than being given a day too short for
  it. Dragging a block that already has a box onto one of these does nothing
  but say why — they exist to make room for work that is not planned yet.

  Lengthening the day does not count as confirming the day's hours, so if the
  app guessed them it still says so afterwards. If the settings file cannot be
  written, the day goes back to the hours it had and the reason appears on the
  status line.
- **Day summary** — What: `4 of 18 boxes · 2h 00m occupied · 1h 45m planned`.
  Why: Three separate numbers, because they are three separate facts. A
  45-minute task occupies a whole hour of your day and plans 45 minutes of it;
  one number would have to be wrong about one of them.

Items pane (left):
- **Column width** — What: The items column is a fixed width. Drag the thin
  vertical divider between the two panes to change it, or type a number into
  *Plan items column width (px)* in Settings ▸ Date Increment Settings, beside
  the Drag Schedule sizes; the two are one value, so a drag shows up in the
  field and a typed width shows up on screen. Why: it holds titles, and the day
  beside it is what the rest of the window is for. Widening the window widens
  the day, not the list.

  Neither the drag nor the field can shut either pane: the items column stops
  at the width one of its own rows needs, and the drag stops before the day
  pane goes below the width of one day row. The row's width comes from *Drag
  Schedule title column width (px)*, so a wider title column raises the
  narrowest the items pane can be.

  The drag writes the settings file when you let go, not while you move. If
  that write fails, the pane goes back to the width it had and the reason
  appears under the *Items* heading — the width you dragged to is not kept,
  because nothing on disk would hold it.
- **Items starting \<date\>** — What: Open items whose start date is that date,
  highest priority score first. Why: These are the only items the day is built
  from. Each row is one line, laid out exactly like a task inside a day box:
  colour stripe, title, a mark saying whether the item is scheduled, the depth
  bars, and the block length it would get (`30m`) at the right-hand end. The
  mark is a **green ✓** when the day already holds a block for this item and a
  **red ?** when it holds none, so the column says something about every row
  rather than only about the scheduled ones. It is a mark rather than the words
  it replaced because the words needed a second line, and a second line set a
  floor that made every row the same height — see *How tall a row is* below. A
  scheduled item is marked rather than hidden, because an item can genuinely
  need two blocks in a day. The priority
  score is not printed: the row is drawn in its priority band and striped in
  it, so the number said a third time what the colour already says twice.
- **How tall a row is** — What: The space the item's work block will take in an
  empty day — from the top edge of the first box it would fill to the bottom
  edge of the last. A half hour that already holds a task is taller than one
  box, so the row matches the day it would be dropped into, not every day. A 90-minute item is three boxes tall; a 45-minute
  item is two, for the reason it takes two in the day: a half-hour grid cannot
  hold a quarter hour. Why: the row is the shape of the space it is about to
  take, so you can see whether the day has room for it before dragging. The
  height comes from *Drag Schedule box height (px)*, the same setting the day's
  boxes use.
- **The shortest a row gets** — What: 33px, one line of text, whatever the box
  height is set to. Why: a row cannot be drawn shorter than the line it has to
  show. At every box height the setting allows this is below what the day gives
  a half hour, so the row and the day agree everywhere and the floor never
  changes a row's height in practice. It was 66px — two lines — until the
  `already blocked` words became a marker on the first line; at that floor a
  30-minute row and a 60-minute row were drawn within a few pixels of each
  other, which defeated the point of sizing rows at all.
- **Drag a row onto a box** — What: Creates a block for it in that half hour.
  Why: This is how blocks are made, and the box you drop on is the box you get.
  If the item needs more than one box, the status line says how many and what is
  left spare. A label with the item's name follows the pointer once you start
  to move it — not on the press, so an ordinary click on a row leaves nothing
  behind.

  **One block per item per day.** Dropping an item that is already on the day
  writes nothing and says where it is — *"Draft the proposal is already blocked
  at 09:00 — drag that block to move it"*. The row's *already blocked* marker
  was the passive version of the same fact; this is the version that answers a
  drag.

  **A follow-on lands with the work it follows.** When the item you drop is the
  child of a block already in that box — or the parent of one — it takes the
  place directly after that block rather than the end of the box. A
  **continuation** whose parent is in an earlier box goes to the *top* of the box
  you drop it on, so work that carries on from the box above reads in that order.
  A Weekly Tactic is a container, not a chain: its steps get no ordering rule.
  Everything else joins the end, which is what it always did.

- **The day scrolls itself while you drag** — What: Hold a dragged item or
  block near the top or bottom edge of the day pane and the day scrolls that
  way, until you move off the edge or let go. Why: A half hour you cannot see
  is a half hour you cannot drop on, and a hand holding a drag cannot work the
  scroll wheel. It keeps going while the pointer is held still, and the
  outline follows whichever box has moved under it.
- **Release in the day column but not on a box** — What: Nothing is created, and
  the status line says *Drop an item on a half-hour box*. Why: The app will not
  pick an hour for you. A release over the heading or the summary is not a
  choice of time, so it is reported rather than guessed at.
- Long lists are capped, and the cap says how many of how many are shown.

Day pane (right):
- **Every half hour, in order** — What: One box per half hour from Day Start to
  Day End, each labelled with its own start time. Why: An empty box is a place
  you can drop work; a pane that drew only the filled hours would give you
  nothing to aim at.
- **A task in a box** — What: Its title, its depth as a three-bar stack, and its
  length in minutes. Why: The box tells you the time; the chip tells you the
  task.
- **A task that runs through a box** — What: The later boxes of a longer task
  are shaded and striped like the box that starts it, and marked with `↳`. Each
  reads `same task`, except the final one, which reads how many minutes of
  itself the task leaves — `15m spare` for a 45-minute task in two boxes. Why:
  the colour says which task owns the half hour and the arrow says it is the
  same one, continued. They were drawn unshaded at first, so that a
  continuation would not read as a second task of equal weight; on screen a
  90-minute task became one coloured box followed by two empty ones, which
  reads as a task that stops after half an hour. Only the last box can have
  minutes left over, so only the last box claims any: a middle box is spent in
  full.
- **Colour** — What: The stripe down the left of a task is its item's priority
  band: critical, high, medium, low, or grey for unscored. Why: The shape of
  the day is readable before any of the text is.
- **Release a task in the day column but not on a box** — What: Nothing moves,
  and the status line says *Drop a block on a half-hour box*. Why: The same
  reason as for an item: a release over the heading, the summary or the
  *Outside the day* group is not a choice of time. A move that did nothing and
  said nothing would look exactly like a drag that missed.
- **Drag a task to another box** — What: Moves it there. Why: This is how you
  re-time one piece of work. Nothing else in the day moves. A drag that lands
  on no box is a cancelled drag and changes nothing.
- **A continuation cannot be dragged** — What: The `↳` chips in a long task's
  later boxes carry no drag and no menu. Why: The box a task **starts** in is
  the one that owns it, so a gesture aimed at an hour the task merely runs
  through cannot move it.
- **Right-click a task** — What: Sets its length to 15, 30, 45, 60 or 90
  minutes, or a custom number, or deletes it. Why: 30 minutes is the default for
  a dropped item unless the item has a Work Block value, which is used instead.
  A length is refused if it would not fit from where the task sits — the task is
  never slid somewhere it does fit, because that would answer a question you did
  not ask.
- **Block lengths stop at a day** — What: 1440 minutes is the longest block
  the app will store. A custom length above it is refused in the dialog. An
  item whose Work Block is above it is clamped to 1440, which needs 48 boxes,
  so unless your day is a full 24 hours the drop is then refused for not
  fitting — and the status line names that refusal, not the clamp. Why: past a
  day the app can no longer write an end time that is the start plus the
  length, so the block would be drawn claiming minutes it does not own.
- **What a task in a box shows** — What: A coloured bar in its priority band,
  the task's title, a three-bar depth stack, and its length in minutes. The task
  is also shaded in its priority band, so the day reads as a column of
  priorities without having to look at the bars. Padding — a Buffer or a Break —
  is left unshaded and keeps its neutral bar, because it has no priority to
  show. A continuation box (the second and later boxes of a longer task) carries
  the same shade and stripe as the box that starts the task, with its `↳` to
  say it is the same task rather than another one. Why: a box that showed only
  the bar was the state this screen shipped in; the title is what tells you
  which task the half hour is spent on.
- **Task height and title width** — What: Both come from Settings ▸ Date
  Increment Settings, which is where the Drag Schedule sizes live: a task is as
  tall as *Drag Schedule box height (px)* and its title column is as wide as
  the Drag Schedule title column. A value below 30 is raised to 30, which is
  one line of text — a shorter box clips the task in a half hour that holds
  two. Why: a task is the same size and the same shape on the two screens that
  draw one, and in the "Outside the day" group beneath the item list.
- **Lunch** — What: A box like any other, labelled `Lunch`, that takes no tasks.
  Why: It is part of the day's shape, so it is drawn in its place rather than as
  a gap you have to infer. A drop on it is refused with *That would run into
  lunch — try a later box*.

  **Lunch can be moved, on that date only.** Drag the `Lunch` box onto another
  half hour and the day keeps its own lunch there; every other date keeps the
  lunch Day Settings names. The first drag writes the lunch block the setting
  had been standing in for, its length is still *Day Settings → Lunch
  (minutes)* until you pick another from its own right-click menu, and
  **deleting** the box (right-click → *Delete block*) hands the
  date back to Day Settings. A date with its own lunch shows one Lunch box, not
  two: the moved one replaces the setting rather than sitting beside it.

  **Any half hour of the day takes it, in either direction** — including back
  onto the hour Day Settings names, which is where every lunch starts, and a
  box that already holds work. A lunch box shows `Lunch` and nothing else, so
  the tasks that were in that box move to **Outside the day**, and the status
  line says how many: *Lunch moved to 14:00 — 2 Time Blocks moved to Outside the
  day*. Choosing a longer lunch from its right-click menu says the same thing
  about the boxes the new length takes. Drag them back onto the day wherever
  you want them.
- **A refusal always says which** — What: One of *That is outside the day — Day
  Settings sets its hours*, *That would run into lunch — try a later box*, or
  *That half hour is full — try another box*. Choosing a length for a block that
  is not on a box yet says *That block is not on a box yet — drag it onto a half
  hour first*. Why: Nothing is written, nothing is moved, and you are told what
  stopped it, in the screen's own words rather than the database's.
- **Outside the day** — What: A group beneath the item list in the left
  column, headed *Outside the day (n) — drag onto a box to place*, holding any
  block the grid can no longer hold: one whose box is past a Day End you have
  moved earlier, one whose length now runs off the end, or one lunch has since
  moved onto. The group scrolls, and its rows are the size a task is in a box,
  so a day that fills it stays draggable to the last row. Why: planned work is
  never dropped silently. It stays on screen,
  and dragging it onto a box puts it back — the same move, from the same
  column, as an item above it.

Day Settings modal:
- **Day Start** — What: The time of the first box. Why: A block remembers
  **which box** it is in, not what time that was, so moving Day Start moves the
  whole day's times with it and writes nothing to your blocks.
- **Lunch Start** and **Lunch (minutes)** — What: When the gap is and how long.
  Why: The boxes it covers are marked and take no tasks; nothing is split across
  it. Set the minutes to 0 for no lunch.
- **Day End** — What: The time of the last box. Why: The grid stops here, so
  there is nowhere past it to drop work.
- **Days for Blocks** — What: Seven checkboxes, Monday to Sunday. Why: These are
  the weekdays a normal week plans work on. They describe a normal week; they
  are not a lock on the calendar, and what happens on an unchecked day depends
  on how you got there:
  - **Dragging an item** onto a half hour, or onto **Earlier** or **Later**,
    asks the same question first — *"<date> is not a regular work day. Day
    Settings allows Mon, Tue, Wed, Thu, Fri. Schedule anyway?"* — and blocks
    the item on a Yes. **Cancel** writes nothing and the status line says which
    days the week allows. If the question cannot be shown at all, the work is
    scheduled rather than lost and the status line says which day it was on:
    losing the gesture silently is the one outcome worse than either answer.
    Until 2026-11-10 this gesture wrote the block without asking, because the
    question used to be put to the screen at the moment the drag was released —
    a moment macOS refuses a dialog at. It is asked before that moment now.
  - **AutoLoad** and the **break/buffer** button ask the same question —
    because either one can fill a whole day at once. The question
    is asked once for that date, not once per item, and answering it plans that
    day only: it does not tick the box, and the next time the screen is opened
    on that date it asks again. **Cancel** writes nothing and says which days
    the week allows. If the question cannot be shown at all, the work is
    scheduled rather than lost and the status line says which day it was on —
    losing the gesture silently is the one outcome worse than either answer.

  At least one day must be checked.
- Times must be written as `HH:MM`, between `00:00` and `23:59`. A time the app
  cannot read — including an hour past 23, such as `24:00` — is rejected in the
  modal with the field named, never silently replaced. A settings file that
  already holds such a value from an older version loads as the default for
  that field rather than being taken as given.
- **Save** writes **nothing** to your blocks, on any day. Why: every block's box
  is stored relative to Day Start, so every day re-times itself the next time you
  open it. There is no day left showing times that no longer follow from your
  settings, and no day that can be "too full to re-time". If a block no longer
  fits the day you have just described, it appears under **Outside the day** and
  the status line says how many — drag it onto a box, or shorten it.

**Days planned in an older version** are mapped onto the grid the first time you
open them. A block with a readable start time goes on the box that time names,
or — if that box is past your Day End, before your Day Start, in lunch, or
already full — nowhere, and it appears under **Outside the day** for you to
place. It is never slid to the nearest free box, because that would move your
work to an hour you never picked.

The status line says how many blocks were placed **and which Day Start they were
placed against**, because that mapping cannot be undone: a box is stored
relative to Day Start, so the Day Start in force at that first open is the one
the day keeps. Set your day's shape before opening an upgraded day, or expect to
drag.

The mapping runs only against a day shape **you** have confirmed — which means
a day you have saved in Day Settings at least once. Until then the blocks stay
off the grid, appear under **Outside the day**, and the status line says the
day's shape has not been confirmed, rather than being placed permanently
against a Day Start the app guessed at. Three ordinary situations are that
guess: a settings file that cannot be read; a settings file written by a version
of daVIPA that had no Day Settings, which is every version before this one, so
this is the normal upgrade; and a day time the app had to replace because the
file held something it could not read as a time.

**To recover:** open **⚙ Day Settings**, check the four times and the weekday
boxes, and save. That writes a settings file the app can read, and the blocks
are mapped onto the grid the next time the day is drawn. **Day Settings is the
only place that restores it** — saving from Settings or any other screen writes
a readable file, but it does not tell the app that the day's four times are
yours, because it never showed them to you. That holds across a relaunch and
across an upgrade: the settings file itself records whether the day's shape was
confirmed, so neither quitting and reopening nor installing a new version turns
a guess into a setting. A settings file from a version that did not have this
field counts as unconfirmed, which is why you may be asked to confirm a day you
feel you have already set — it is one save, and the alternative is the app
rewriting your planned times against a day start it invented. Three things
happen on that save, all deliberate:

- The unreadable file is **kept aside** next to the new one, named
  `settings.json.unreadable-<date>-<time>`. Saving replaces every setting in
  the file, not just the day's shape, so the old file is the only copy of
  anything the app could not read out of it — an Obsidian path, a theme, a
  business year. The path it was kept at is written to the log.
- If that copy cannot be made, **nothing is overwritten.** The dialog says the
  file that would not load could not be set aside, and the unreadable file
  stays exactly as it is rather than being replaced with no copy of it
  anywhere. The way out of that one is to move or delete
  `settings.json` yourself — the app will not destroy it for you. While this is
  the case, **saving from other screens does nothing either** — every Save
  button on the Settings screen now says so instead of reporting a save, and
  the Appearance section does not apply a theme it could not write. Four
  places still fail silently rather than wrongly: a column drag on Today, the
  same drag on Drag Schedule, the timer window's position when it closes, and
  the Next Action dialog's. See `BACKLOG.md`.
- If the new file cannot be written — a permissions problem, a full disk — the
  dialog says so and stays open. It does not report the day settings as saved,
  and the day's shape goes back to what it was rather than being left changed
  in memory only.

### Completed
- What: Shows completed items over the last N days.
- Why: Review progress and time spent.

Header controls:
- **Last N days** — What: Sets the lookback window. Why: Focus on a recent period.
- **Who** — What: Filter by Who. Why: Review work for a client or context.
- **Expand/Collapse** — What: Toggles priority factor chips. Why: Show or hide detail.
- **Stats label** — What: Shows count and total planned minutes. Why: Quick summary.

Row controls:
- **Edit** — What: Opens the Item Editor. Why: Review or adjust completed items.
- **Reopen** — What: Changes status back to open. Why: Restore work that was completed by mistake.

### Contacts
- What: Manage your contacts (people/clients).
- Why: Cleaner Who values and faster filtering.

Header controls:
- **Search** — What: Searches name/email/phone. Why: Find contacts quickly.
- **+ New Contact** — What: Opens the contact editor. Why: Add a new contact.

Row behavior:
- **Click a contact** — What: Opens the contact editor. Why: Update details.

### Defaults
- What: Set default values for new items, system-wide or per Who.
- Why: Reduce repetitive data entry and standardize priority factors.

Controls:
- **Defaults For** — What: System Defaults or Who-specific defaults. Why: Apply defaults globally or per client.
- **Priority Factors** — What: Importance, Urgency, Effort-Cost, Value. Why: Auto-populate priority for new items.
- **Organization** — What: Default Group and Category. Why: Keep items organized.
- **Planned Minutes** — What: Default time estimate. Why: Set a typical duration.
- **Date Offsets section** — What: Start/Due offsets. Why: Centralize scheduling defaults.
- **Save Defaults** — What: Stores the defaults. Why: Make them apply to new items.
- **Clear Form** — What: Resets inputs. Why: Start over.

### Stats
- What: Planned vs actual time statistics for items that used the Timer.
- Why: Improve estimation accuracy and understand time usage.

Controls:
- **Refresh** — What: Reloads stats. Why: Update after new work logs.

### Settings
- What: Application configuration and data management.
- Why: Control behavior, integrations, and maintenance.

Tabs and controls:

Database Management:
- **Database Path** — What: Shows the current DB file. Why: Know where your data lives.
- **Backup Database** — What: Creates a timestamped backup. Why: Protect against loss.
- **Load Demo Data** — What: Adds sample items to the current DB. Why: See how the app works.
- **Business year starts (MM-DD)** — What: Sets the first day of the business year used by Scheduler/plan-oriented date logic. Why: Align quarter and annual planning to your real operating year.

Obsidian Integration:
- **Vault Path** — What: Path to your Obsidian vault. Why: Enable note linking.
- **Notes Subfolder** — What: Subfolder for notes created from Action Items (and other non-project entities). Default `daVIPA`. Why: Keep generic GMD notes organized.
- **Project Notes Folder** — What: Separate subfolder for notes created from a Project (via Create Note, Link Note, or the 📄 chooser on a project tile). Default `daVIPA/Projects`. Leave blank to fall back to the Notes Subfolder above. Why: Keep project reference material separate from per-task notes so the vault stays browsable.
- **Save Settings** — What: Stores vault settings. Why: Persist configuration.
- **Test Connection** — What: Validates vault path and subfolder. Why: Confirm setup is correct.

Date Increment Settings:
- **First day of week (VSP)** — What: Sets week start day for APE Period week generation. Why: Keep weekly planning aligned with your calendar.
- **Drag Schedule date text color** — What: Hex color for date-box text (default `#FFFFFF`). Why: Improve readability across box colors.
  - Includes **Pick Color** button for visual selection.
- **Drag Schedule box height (px)** — What: Controls the height of all Drag Schedule date/future boxes, and, since 2026-11-06, the height of each task in a Plan half-hour box. Why: Match readability and spacing preferences, and keep a task the same size on both screens. A larger value makes the Plan tasks easier to read but makes the day scroll; empty half hours keep their compact height whatever this is set to. A blank, zero or non-numeric value falls back to 30 for the Plan boxes rather than flattening them, and a value below 30 is raised to 30 — one line of text, below which a half hour holding two tasks clips the second. Saving it takes effect as soon as you leave Settings; before 2026-11-06 the value was written to the file and the screens kept the one they started with until the next launch.
- **Plan items column width (px)** — What: Width of the items column on the Plan screen (default 260). Why: Size it to the titles you actually have; the day column takes the rest of the window. A blank, zero or non-numeric value falls back to 260 rather than hiding the list. Either way the width is then raised, if it has to be, to what one item row needs — the stripe, *Drag Schedule title column width (px)*, the "already blocked" marker, the depth bars and the block length with its right-hand gap, plus the pane's own padding and scrollbar. At the default sizes that is 384px, so the shipped 260 is raised: a narrower column would clip the block length off the right-hand edge of every row with nothing on screen to say so. Dragging the divider between the panes writes this same setting. Narrowing the window takes width off this column first, down to that floor, so the day column keeps enough room to draw a block; widening it gives the width back.
- **Completion Badge** — What: Optional image shown on completed Today items. Why: Replace the default large green check mark with your preferred badge.
- **Confetti Every N Completions** — What: Controls how often confetti triggers on Today completions. Why: Tune or disable celebration feedback.

Priority Colours (added 2026-11-08; moved from the row to the Priority cell 2026-11-11):
- What: The background of the **Priority cell** for each of the three
  **priority levels**. A priority level is a rule on an item's own Importance
  and Urgency, and it colours the Priority cell in Today, Upcoming, All Items,
  Hierarchical and Completed, and in the Action Items panel of APE Week
  Assignment, which draws Today's rows.
- Why: The old behaviour had one tint, a pale red, for Critical items only, with
  no way to change it and no tier between Critical and nothing.
- **Changed on 2026-11-11.** Between 2026-11-08 and then these colours tinted
  the **whole row**, and the Priority cell carried a separate hard red that no
  setting could reach. The two have swapped: the level colour is the cell's
  background now, and a row with no VSP segment colour and no completion is
  drawn in the theme's own background, as it was before 2026-11-08. The red is
  gone. Nothing else about the three colours changed — the same values, set in
  the same place, shown somewhere smaller.
- The three levels, checked in this order:
  - **Any Critical** — Importance *or* Urgency is Critical. Default `#DCFCE7`,
    a green. One Critical factor outranks a High one.
  - **Any High, but no Critical** — either factor is High, and neither is
    Critical. Default `#FEF3C7`, an amber. This tier is new; before
    2026-11-08 a High item looked the same as a Low one.
  - **No high or critical** — neither factor is High or Critical. Default: no
    fill, so the cell is transparent and keeps the row's own text colour.
- A missing factor does not disqualify an item: Urgency Critical with
  Importance unset is still **Any Critical**.
- Controls per level: a `#RRGGBB` field, a **Pick Colour** button, and a swatch
  that repaints as you type, showing what is in the field. A field holding
  something that is not a colour shows no fill in its swatch until it is.
  - **Apply / Save** — Writes all three. Nothing is written if any of the three
    is not a colour; the status line names the level and the value it refused,
    rather than silently substituting one.
  - **Restore Defaults** — Puts the three shipped defaults back into the
    fields. It does not save them; press Apply / Save to keep them.
- **Clear a field** to give that level no colour. With Any Critical cleared, a
  critical item's Priority cell looks like any other — and so does its critical
  Importance or Urgency chip, which takes the same colour (see below).
- One colour per level, used in both light and dark mode. The cell's *text*
  colour is chosen automatically for contrast against whatever you pick, so a
  pale colour gets dark text in either mode.
- **A VSP segment colour no longer competes with these.** It fills the row;
  these colour one cell on it, so both can show at once. Where Today, Upcoming
  and All Items colour a row from its segment, that row picks its own text
  colour for contrast (since 2026-11-10), and an uncoloured Priority cell keeps
  that text colour rather than choosing its own.
  - Since 2026-11-11 a segment colour that is **not** a `#RRGGBB` value draws
    no fill at all, so those rows look as they would with no segment colour
    set, and `app.log` names the value once. The narrow accent stripe at the
    left edge of the row is dropped for the same value, so a row with an
    unreadable segment colour has neither. Before that the value was passed to
    the row as given and could blank the screen it was drawn on. A colour set
    in the segment editor is always a `#RRGGBB` value, so this applies only to
    one left behind by an earlier version.
- A saved colour shows the next time you open one of those screens; no relaunch
  is needed.
- These are **not** the Plan screen's priority bands. A band comes from the
  priority *score* — the product of all four factors — and has its own five
  colours. An item can sit in the top band while being in no critical level:
  Medium Importance and Urgency with XL Size and Value scores 6400, which is
  the critical band, and is "No high or critical" as a level.
- **The I and U factor chips** (shown when the columns are expanded) take the
  **Any Critical** colour when that one factor is itself Critical. Size (`E`)
  and Value (`V`) never do: they are in the priority score and in no level.
  Before 2026-11-11 those chips were the same hard red as the Priority cell.

### Vision Planning (Unified Hub)
- What: A single workspace with top navigation for all vision-planning flows.
- Why: Removes redundant screens and keeps workflows in one place.

Top buttons:
- **Vision Elements** — Create and maintain Segment|SubSegment|Category keys. Three lists shown one at a time; the view-switcher buttons and `Refresh` are at the top, and the `+ New Segment` / `+ New SubSegment` / `+ New Category` button sits under the list (one button, labelled for the view you are in) as of 2026-11-11. This tab has no left-to-right tick filter: it is one list at a time, so there is no right panel for a tick to narrow.
- **Annual Plan Elements** — Promote Vision Elements into annual records for a selected year.
- **APE Assignment** — Assign Annual Plan Elements into a selected quarter. Opens on the current calendar quarter.
- **APE Period View** — Assign quarter-selected APEs into a selected month. Opens on the current quarter and the current month, and the Month picker only ever offers the three months the selected Quarter contains.
- **APE Week Assignment** — Assign month-assigned APEs into a selected week, and work the weekly tactics for that week. Called **APE Weekly** before 2026-11-07.
- **APE Week Actions** — Pick a Weekly Tactic from the selected week on the left; the right panel lists that tactic's Action Items and works the way the Today tab does.

Deletion protection (child records):
- **Delete a Vision Element** — What: Blocked when child records still exist (annual plan records, attached projects, or linked action items). A dialog lists what is attached and tells you to delete or reassign those child items first. Why: Prevent a single delete from silently cascading away annual records and projects.
- **Delete an Annual Plan record (APE)** — What: Blocked when projects are attached to that APE — either more than its starter project note, or any project that has linked action items. The dialog lists the attached projects. Why: Now that multiple projects can share one APE, deletion must not destroy projects you parked there; delete or reassign them first.

APE assignment behavior:
- **The tick on the left filters the right** — What: Since 2026-11-11, ticking rows in the left panel narrows the right panel to the records those rows own, and the right panel's heading says so (`N of M, filtered by tick`). No tick means no filter, so the right panel shows everything. The filter applies the moment you tick — there is no button to press — and a tick stops filtering if the lineage dropdowns hide its row, because a filter you cannot see is one you cannot clear. Why: This is what the ticks were for. Until this change a tick did nothing at all until `Save` was pressed, and what it then did was create records.
- **Add New, at the bottom** — What: Each tab has one button under its right panel: `Add New Annual Plan Element`, `Assign APE to Quarter`, `Assign APE to Month`, `Add Weekly Tactic`. It opens a small dialog that asks which parent record to use, pre-filled when exactly one row is ticked, and offers only the records that are not already there and not hidden by the lineage dropdowns above the left panel. The outcome, including a refusal, is written to the status line beside the button, and a refusal names its reason: the year or quarter holds no records yet, the dropdowns are hiding them all, or every one the left panel shows is already in the period. On APE Week Assignment the one wording it used to give sent you to the APE Month Assignment tab even when the records were there and a Category filter was hiding them. Why: Every tab needed one way to add a right-panel record, and the tick now means something else.
- **The header `Save` is gone** — What: Removed from Annual Plan Elements, APE Assignment, APE Period View and APE Week Assignment on 2026-11-11. Why: It read the ticks, and a tick is a filter now.
- **Drag and drop** — What: The APE screens also support dragging left-side records onto the right-side assignment panel. Why: Speed up planning when working item by item.
- **Quarter and Month always agree** — What: Since 2026-11-07 the Quarter picker on both APE assignment screens opens on the current calendar quarter, and the Month picker on APE Period View offers only that quarter's three months (Q4 offers 10, 11 and 12). Changing the Quarter moves the Month into it: a month already inside the new quarter is kept, one outside it moves to that quarter's first month. Why: Before this the Quarter picker always opened on Q1 while the Month picker opened on the current month, so for eight months of the year the screen offered a pair that cannot both be true — Q1 with M11, for instance — and Save wrote it. An APE filed in a quarter that does not contain its month was then invisible in APE Week Assignment (named APE Weekly at the time).
- **Dragging says what it did too** — What: Dropping a Vision Element on the Annual Plan Elements panel reports on that tab's status line, the way the other three assignment tabs' drops always have, and says so when the write failed instead of leaving the panel unchanged with no message. Why: Until 2026-11-11 that one drop reported nothing either way, so a failed write and a successful one looked identical.
- **The count under APE Week Assignment follows the tick** — What: The status line says how many month items are on the left and how many weekly tactics on the right, and it is now rewritten when a tick narrows the panel, not only when you press Load Week. Why: Until 2026-11-11 the panel and its heading narrowed and that line went on naming the pre-filter total.
- **Adding says what it did** — What: APE Period View reports how many APEs were assigned, and names any that were not. Both `Add New` and the drop target report, and the sentence is computed from the rows the panel was redrawn from rather than from what the write returned — so a record that was written and then refused reads as *partly assigned*, not as a success. Why: A refused assignment used to look exactly like a successful one.
- **Existing mismatched records are repaired** — What: On first launch after this change, any APE with a month flag set but not the quarter flag that month implies has the quarter flag added. Nothing is ever removed, so an APE assigned to a quarter but not yet to a month keeps that state. Why: Make records created before the fix visible again without re-entering them.

APE Week Assignment behavior:
- Left list shows Annual Plan Elements already assigned to the selected month. Since 2026-11-07 that list is matched on the month assignment alone; it previously also required the APE to carry the flag for the quarter containing that month, which hid any record whose quarter and month disagreed.
- Right list shows weekly tactics for the selected Week Start.
- **Week Start selector** — What: Always includes the current week plus up to 3 future week starts, even when no weekly tactics exist there yet. Why: Lets you create a weekly tactic for the current or near-future week without being limited to existing records.
- **Create weekly assignments** — What: `Add Weekly Tactic` under the right panel asks which month-assigned APE the tactic is for, or drag a left-side row onto the right panel. Both paths report what happened on the status line, including a week that already had a tactic for that APE. Why: Mirrors the same assignment pattern used by the Year → Quarter and Quarter → Month screens.
- **Weekly tactic actions** — What: Each right-hand row carries its own `Edit` and `Delete`, and a double-click on the row opens the editor. The three bottom buttons this tab used to have are gone (2026-11-11): `Edit Weekly Tactic` opened the same editor as the double-click, `Delete Weekly` called the same delete as the row's own, and `Add Action Item` created an Action Item this panel cannot display — that button belongs to APE Week Actions, which has it. Why: One route to each action, on the row it acts on.
- New daily item title format: `Weekly Title Prefix - Action Item Title`.
- Prefix shortening rule: first two pipe-delimited parts become initials.
  - Example: `Purposeful Work|Living Systems|Blog` → `PW|LS|Blog`.
- Week token normalization: `Week 8` is normalized to `W8` in generated/normalized titles.

APE Week Actions behavior:
- **What the tab is for** — What: A second view of the same week, turned the other way round: APE Week Assignment answers "which APEs get a tactic this week", and this tab answers "what am I actually doing for this week's tactics". Why: The Action Items under a weekly tactic previously had no screen that listed them together — they were reachable only one at a time, from the tactic that made them.
- **Week Start picker** — What: Opens on the current week, and offers the same week starts APE Week Assignment offers: the current week, any week that already has tactics, and up to 3 future weeks. `This Week` jumps back to today's week. Why: One rule for what a week is, shared by both tabs.
- **Left panel** — What: Lists the selected week's Weekly Tactics, with the count in the panel heading and in the status line. Why: An empty list and a list you cannot see the end of look the same without a count.
- **Every tactic in the week is listed** — What: Including a tactic whose Annual Plan Element has since been detached. Why: Hiding it would leave its Action Items unreachable from this tab with nothing on screen to say they exist.
- **Right panel** — What: The Action Items linked to the tactic you clicked, in the same rows the Today tab uses — same checkbox, same inline Title, Who and Date editing, same timer, same push buttons, same drag-to-reorder grip, same column widths you can drag. Why: It is the Today screen, filtered by tactic instead of by date, rather than a second screen that looks like it.
- **Column widths are its own** — What: Dragging a column divider here does not change the Today tab's columns, and the width is remembered between launches. Why: The panel is half a window wide; Today is a whole one.
- **A row's date is not filtered** — What: A completed Action Item stays listed whatever day it was completed on. Why: Once the list is filtered by tactic, "completed today" has no meaning.
- **Add Action Item** — What: Asks for a title, creates the item linked to the selected tactic and dated to the week start, then opens it in the editor. An empty title creates nothing. Since 2026-11-11 the button sits at the bottom of the right panel rather than above the list, with the other tabs' Add buttons; it is the same button with the same behaviour. Why: Most of what a new item needs is in the editor, not in a one-field dialog.
- **Known gap** — What: Dragging a row to the top of this panel also floats it to the top of the Today tab, because the pin it writes is the one Today orders by. Why: Recorded in `BACKLOG.md` as AWA-A4; both fixes are behaviour changes beyond what the tab was asked to do.

Appearance:
- **Theme** — What: Dark/light/system. Why: Choose a comfortable look.

Date Increment Settings:
- **Include Saturday** — What: Weekend-aware push and +/- logic. Why: Control scheduling on weekends.
- **Include Sunday** — What: Same as above. Why: Adjust weekend behavior.
- **Start list views expanded** — What: Default expanded/collapsed state for Today/Upcoming/All Items. Why: Match your preference.
- **Future Date Options** — What: Mid Term and Long Term day offsets for Drag Schedule. Why: Customize long-range targets without manual date picking.
- **Save Settings** — What: Saves date increment preferences. Why: Apply behavior consistently.

Timer & Audio:
- **Music Folder** — What: Folder of audio files used during the timer. Why: Automatically play focus music.
- **Browse** — What: Opens a folder picker. Why: Choose the music folder.
- **Music Volume** — What: Slider for playback volume. Why: Adjust sound level.
- **Save Settings** — What: Saves audio settings. Why: Keep them persistent.

Organizational Factors:
- **Groups tab** — What: Manage Group values used on items. Why: Keep grouping consistent.
- **Categories tab** — What: Manage Category values used on items. Why: Keep categorization consistent.
- **Rename** — What: Renames a value across items (optional). Why: Fix naming without manual edits.
- **Delete** — What: Removes a value, with optional replacement. Why: Clean up unused values.
- **Refresh List** — What: Reloads values. Why: See recent changes.

Email Import (Gmail):
- **Enable Gmail import** — What: Turns the importer on or off. Why: Pause imports without changing config.
- **Trigger Label** — What: Gmail label to scan for new items. Why: Control which emails become tasks.
- **Processed Label** — What: Label applied after import. Why: Prevent duplicate imports.
- **Poll Interval** — What: Seconds between import checks. Why: Control frequency.
- **Save Email Import Settings** — What: Stores config. Why: Persist your choices.
- **Run Import Now** — What: Runs the importer immediately. Why: Pull in emails on demand.
- **Open Logs** — What: Opens importer logs. Why: Debug or confirm imports.
- **Gmail account** — What: Uses the Gmail account authorized on this machine. Why: Keeps imports tied to the correct inbox.

VSP Life Segments:
- **+ New Segment** — What: Creates a new life segment. Why: Organize VSP plans by life area.
- **Segment colour** — What: The `#RRGGBB` field in the segment editor, with a
  **Pick Color** button beside it. Why: Colour a segment's rows on Today,
  Upcoming and All Items. Since 2026-11-11 the short form `#abc` is accepted
  and saved as `#AABBCC`, and the field refuses anything that is not six hex
  digits — `#0X1234`, `#1_2345`, `#+12345`, `# 12345` and `#-12345` were all
  accepted before that and could not be drawn. The same refusal now applies
  wherever a segment colour is saved, including VSP → Vision Elements' segment
  admin, which had no check of its own. The editor also **opens** on a colour
  left behind by an earlier version: the field shows the stored value so you
  can see what to correct, and the swatch beside it shows a neutral slate
  instead. Before 2026-11-11 the dialog failed to open at all on such a value,
  which made it the one screen that could not repair what only it could
  repair. The same is true of the subsegment and category colour dialogs on
  VSP → Vision Elements, and of the **Pick Color** button inside them, which
  opens on the neutral slate rather than on the value being corrected. Both
  screens that list segments — this one and VSP → Vision Elements — also now
  *render* on such a value; before 2026-11-11 the list stopped at the first
  bad row, so the Edit button never appeared and the colour could not be
  corrected from the app at all.
- **Refresh** — What: Reloads the list. Why: See recent changes.
- **Edit** — What: Modify segment details. Why: Keep segments accurate.
- **Delete** — What: Deletes a segment if no linked VSP records exist. Why: Clean up unused segments.
- **Deletion protection** — What: If linked VSP records exist, deletion is blocked and you are guided to remove child records first. Why: Prevent accidental data loss.

Future Date Options:
- **Near Term / Long Term** — What: Offsets from today. Why: Quick scheduling targets for Drag Schedule.
- **1st Next Month / 1st Next Quarter** — What: Offsets from the 1st of next month/quarter. Why: Align with month/quarter starts.

### VSP Planning
- What: The Vision Strategy Plan hierarchy.
- Why: Turn long-term vision into concrete actions.

Common controls:
- **Expand All / Collapse** — What: Opens or collapses all nodes. Why: Fast navigation.
- **Segment filter** — What: Filter by VSP segment. Why: Focus on a life area.
- **Add buttons** — What: Create new TL Vision, Annual Vision, Annual Plan, Quarter Initiative, Month Tactic, Week Action. Why: Build the planning tree.
- **Edit** — What: Modify a plan node. Why: Keep planning current.
- **Delete** — What: Remove a node (with safety checks). Why: Clean up or reorganize.

---

## 4) Item Editor (What + Why)

The Item Editor is where you create and edit Action Items. It appears from **+ New Item** and **Edit** buttons.

Main fields:
- **Who** — What: Person, client or context the item belongs to. Start typing and
  matching Contacts drop down; picking one links the item to that contact. On a *new*
  item, changing Who also re-applies that person's Defaults to any field you have left
  empty (priority factors, group, category, planned minutes, date offsets) — it never
  overwrites something you have already set, and it does nothing on an existing item.
  Why: Filter and group items by owner, and get sensible defaults per client.
- **Title** — What: The task name, in full. Why: The primary label everywhere in the app.
  (The separate **Context** box in front of Title has been removed — it was never a field
  of its own, only the front half of this same title. Titles are unchanged; the whole
  title now lives in, and saves from, this one box.)
- **Description** — What: Longer notes. Why: Store context or details.
- **Next Action** — What: Short, action-focused notes, often one per line. Why: Break a task into next steps.
- **Deliverable** — What: The crisp "done = ..." for this item, in one line. A checkable
  artifact, not a time-box: *"Draft section 2's opening paragraph"*, never *"work on the
  report for 25 min"*. Why: It is what the Timer's reward protocol is contingent on. If
  you leave it blank here, the Timer asks for one when you start a session on an item
  that belongs to a Project — so it is only ever optional, never skipped where it counts.
- **Planned Minutes** — What: Time estimate. Why: Better scheduling and stats.
- **Parent** — What: Shown only when the item has one: `Parent: <title>`, with a
  **View Parent** button that opens that item in its own editor. The parent is the item
  you set with **Set Parent**, or — if you have not set one — the Weekly Tactic this item
  is filed under. Why: Know what this task belongs to, and step up to it in one click.

Action Plan (top left):
- **Project** — What: The Project Board this item is filed under. Why: See at a glance where
  the item sits in your plan, without opening a tab. Set it with **Set Project**.
- **Wk Tactic** — What: The Weekly Tactic the item is filed under. Why: Same, for the week.
  Set it with **Set Wk Tactic**.
- **Orig. Week** — What: The week the item was originally meant to start. Why: A task pushed
  out repeatedly still shows where it began.
- **Depth** — What: How much focus this task needs — Deep, Medium, or Shallow. Why: Set
  on the Priority tab; echoed here so the whole scheduling picture is visible at once.
- **Work Block** — What: The time-box to schedule on the calendar (90, 60, or 30 minutes).
  Why: A ready duration for the calendar button.

Tabs:

Dates:
- **Start Date** — What: When work should start. Why: Schedule intentionally.
- **Due Date** — What: Deadline. Why: Keep commitments visible.
- **Today / -1 / +1 / Clear** — What: Quick date controls. Why: Fast scheduling.
- **Is Meeting** — What: Meeting flag. Why: Track meeting tasks and calendar links.
- **Meeting Time** — What: Auto-filled from Calendar events. Why: Keep meeting time visible.

Priority:
- **Importance, Urgency, Effort-Cost, Value** — What: Priority factors. Why: Compute priority score and compare items.
- **Depth** — What: How much focus this task needs (Deep, Medium, Shallow). Why: Match the task to your energy.
- **Work Block** — What: The time-box to schedule (90, 60, or 30 minutes). Why: A ready duration for scheduling.
- **Schedule on Calendar** — What: Opens the calendar event dialog for this item, with its Duration pre-filled from Work Block. Why: Put the work block on your calendar from the same tab.

Organization:
- **Group, Category** — What: Organizational labels. Why: Filter and report by area.
- **Status / Completed Date** — What: Item state. Why: Control workflow and visibility.

  (The Weekly Tactic and Orig. Week fields moved from this tab to the Action Plan block in
  the top left, alongside the Project.)

Notes:
- **+ Create Note** — What: Creates an Obsidian note for the item. Why: Keep longer notes linked.
- **+ Link Note** — What: Links an existing Obsidian note. Why: Connect existing context.
- **Open** — What: Opens a linked note. Why: Jump to details quickly.
- **Remove (X)** — What: Unlinks the note. Why: Clean up attachments.

Buttons (top row):
- **Save & Close** — What: Saves and closes. Why: Finish editing quickly.
- **Save** — What: Saves changes, keeps editor open. Why: Iterate without reopening.

Buttons (paired below):
- **Timer** — What: Opens the focus timer for this item. Why: Work in tracked sessions.
- **Cancel** — What: Closes without saving. Why: Discard changes.
- **Add Follow-up** — What: Saves your edits, then creates a follow-up item seeded from this
  one — inheriting its Project and Weekly Tactic. Why: Continue work without losing history.
  (This replaces the old separate **Duplicate** button; a follow-up is a copy that also keeps
  the link back to the original.)
- **Add Subtasks** — What: Creates one child item per line in Next Action. Why: Quickly split work.
- **Set Parent** — What: Assigns a parent item. Why: Organize tasks into a tree.
- **Show Related** — What: Shows parent and children — for an item filed under a
  Weekly Tactic, the tactic is the parent, and opening it on a tactic lists that
  week's items as its children. Why: Navigate the hierarchy.
- **Set Wk Tactic** — What: Files the item under a Weekly Tactic. Why: Tie daily work to the week's plan.
- **Set Project** — What: Files the item under a Project Board — and can create a new Project on
  the spot with **+ New Project**. Why: Create a task and the project it belongs to without
  leaving the editor. **Clear Project** unfiles it. Not available on a Weekly Tactic record.
- **Complete** — What: Marks the item completed. On a Weekly Tactic with items
  still open it asks first, naming how many; completing the tactic does not
  complete them. The same question is asked wherever a Weekly Tactic is
  completed — the Today checkbox, All Items, Upcoming, a Project Board, and
  the timer's **Done** button — not only here. (The Hierarchical screen is
  read-only in this respect: its rows have no Complete control, so there is
  nothing to ask about there.) Why: Track progress without silently closing a
  week that is not finished.
- **Delete** — What: Deletes the item. Refused if the item has child items,
  naming how many — including, for a Weekly Tactic, the items filed under it.
  Why: Remove obsolete tasks without losing the work underneath them.
  (Deleting a Weekly Tactic from the VSP screen's weekly list is a different
  path: it *does* delete the items under it, after a confirmation.)
- **Save + New** (new items only) — What: Saves and opens a new item. Why: Rapid entry of multiple tasks.

Note: filing an item under a Project also stamps that project's Annual Plan Element onto the
item, and clearing the project clears it — the same rule as dragging an item onto a project in
the Scheduler.

---

## 5) Timer window (What + Why)

The Timer supports focused work sessions and time tracking.

The window has three areas: the **timer**, the **music**, and the **session actions**.

Timer area:
- **Deliverable** — What: What this session is for, shown at the top with an **Edit**
  button. Why: It is what the reward is contingent on, so it is on screen the whole time
  rather than typed once into a dialog and never seen again. If the item has no
  deliverable, starting the timer asks for one; if it already has one, you are not asked
  again — you can see it, and edit it if it changes.
- **Time Block** — What: Total minutes for the session. Why: Set a time boundary.
- **Time To Finish** — What: Countdown of work time. Why: Keep pace.
- **Wrap/Break** — What: Break duration. Why: Account for wrap-up time.
- **▶ Start / ⏸ Pause / ⏹ Stop** — What: The transport, laid out like a recorder and
  sitting inside the timer area. Why: They belong to the clock they drive.
- **Done — deliverable complete** — What: Marks the deliverable finished and closes out the
  session. Available the whole time a session is running, not only when the clock stops.
  Why: Finishing the thing is what ends the work; the clock running out is not.

At the end of a break the timer no longer stops on its own. It asks:
- **Pause (rest)** — What: Stops the clock and waits. Resume starts a fresh focus block.
- **Continue focus** — What: Straight into another block, no interruption.

Neither of these completes anything. That is the point: the reward has to fire on
finishing a deliverable, never on the timer ringing, or what gets reinforced is sitting
there until the bell goes.

Two things follow from that. **Music keeps playing through the end of a break** — it
used to stop, because the break ending used to stop the whole timer. It now behaves the
way it does when you Pause: yours to control, from the music buttons. And the **session
actions are one click further away at the ring** — press Stop to reach them, or press
Done if the deliverable is actually finished.

Music area:
- **▶ Play** — What: Starts music from your configured folder. Why: Focus support.
  **Music never starts on its own.** Starting the timer used to start the music too,
  which decided for you that this was a session with music in it.
- **⏸ Pause** — What: Pauses music. Why: Quiet when needed.
- The track name and any reason music could not start appear here, in the music area —
  not on the timer's own status line.

Session actions (after **Stop**):

A timer session is a *record of work on* an action item, not the item's ending. These
three say what they do:

- **Save Related - Close Timer** — What: Prompts for a session note, saves the session
  as a related record against the action item along with the time spent, and returns you
  to the action item, which stays **open**. Why: The ordinary ending — you did some work,
  it is written down, the task is not finished.

**Session Notes.** All three endings that record a session — *Done*, *Save Related* and
*Complete & Create Follow Up* — ask for a note in a window called **Session Notes**. What
you type is appended to the **description** of the action item you were working on,
prefixed with the date:

```
what this task is for

08-25: got the opening paragraph down
08-26: sent the draft to Legal
```

Notes accumulate rather than replacing each other, and Skip adds nothing. The note is also
stored on the session record itself, but nothing in the app displays those yet — the
description is where you read them back. On *Complete & Create Follow Up* the note goes on
the **original** item, not the follow-up, because it describes the session that just
happened.
- **Cancel Timer** — What: Closes the timer and returns you to the action item with
  **nothing recorded**. No session, no time, no note, and no change to the item — not
  even notes you typed into this window. Why: Cancel means nothing happened. If you want
  the time kept, use *Save Related - Close Timer* instead.
- **Complete & Create Follow Up** — What: Completes the *timer session* — saves it as a
  related record against the action item — then creates a follow-up item and opens it for
  you to fill in. The action item itself stays **open**. The follow-up is titled
  *"<original title> - Follow up MM-DD"* — the day it was made, which is what tells two
  follow-ups of one item apart. It starts with *"Add your next steps and set the dates and
  priority"* in its description, and inherits the original item's start and due dates, its
  project, its weekly tactic and its links — so an item that was already late produces a
  follow-up that is already late. Change the dates in the editor it opens. Why: Ending today's block on work that continues, with the
  next step already written down beside it.

**Only one of these five buttons closes a task.** "Complete" in *Complete & Create Follow
Up* means the timer session is complete, not the work:

| Button | Task closed? | Counts towards the reward phase? |
|---|---|---|
| **Done — deliverable complete** | yes | **yes** |
| **Complete & Create Follow Up** | no — it opens the follow-up beside it | no |
| **Save Related - Close Timer** | no | no |
| **Cancel Timer** | no — nothing is recorded at all | no |
| **Stop** | no — it just stops the clock | no |

So **"Done" is the only button that closes a task or counts a completed deliverable**
towards a project's phase. *Complete & Create Follow Up* leaves today's item open: it
records the session and gives you the next step to work on, and you close the item with
*Done* when the work is actually finished.

One exception, by design: if you press **Done** and saving fails (a locked database, say),
your completion is remembered so it is not lost — press *Done* again to record it.
*Complete & Create Follow Up*, *Save
Related* and *Cancel Timer* deliberately do not — they say the task is still open, so they
discard the pending completion rather than banking it for a task they are leaving
unfinished.

The old buttons were called *Finished* and *Continue*, and both quietly completed the
item and closed the window, which looked from the outside like pressing them did nothing
at all.

Notes:
- **Pop Out** — What: Opens the notes in a separate window. Why: More space to write.
- **Save Notes** — What: Saves edits to the item description. Why: Keep notes synced.

### The reward protocol (items filed under a Project)

Starting a timer on an item that belongs to a Project asks you to confirm its
**Deliverable** first, prefilled from the item. Cancelling does not start the timer —
a tracked session with no deliverable has nothing to be contingent on. Items **not**
filed under a Project run the timer exactly as they always have, with none of this.

When you press **Done**:

1. **Savor.** A short prompt naming what you set out to do, confirming it is done, and
   asking you to look at it for five seconds and notice the effort. Early in a project
   this appears on *every* completed deliverable — that is how the association gets
   built. After fifteen completed deliverables on that Project it drops to roughly two
   in five, because something that happens every single time stops telling you anything.
2. **Celebration.** About one completion in five, at random, in either phase: confetti,
   balloons, or a short chime. Never guaranteed, and never *instead of* the savor step.
3. The Project's completed-deliverable count goes up — every time, whether or not the
   savor prompt appeared — and the session is written to your work log along with which
   deliverable it was for and what the protocol did.

Nothing here says "well done". The words point at the thing you made and at the effort
of making it, which is what the whole design is for.

---

## 6) Calendar dialog (What + Why)

The Calendar dialog schedules a Google Calendar event and links it to an item.

Fields:
- **Event Title** — What: Calendar event title. Why: Clear meeting name.
- **Date** — What: Meeting date with Today and +1 buttons. Why: Quick scheduling.
- **Start Time** — What: Hour/minute/AM-PM. Why: Exact start time.
- **Duration** — What: Minutes. Why: Accurate calendar blocks.
- **Description** — What: Event details. Why: Add context.
- **Location** — What: Meeting location. Why: Keep logistics visible.
- **Attendees** — What: Comma-separated emails. Why: Invite participants.

Buttons:
- **Create Calendar Event** — What: Creates the event and links it to the item. Why: Keep tasks and calendar connected.
- **Cancel** — What: Closes dialog without changes. Why: Back out safely.

---

## 7) Common workflows (Why you would use them)

- **Daily focus**: Today screen + Top 3 to focus on the highest priority items.
- **Weekly planning**: Upcoming and Scheduler to place tasks on dates.
- **Time blocking**: Plan screen to translate tasks into a daily schedule.
- **Meetings**: Item Editor + Calendar dialog to schedule and link meetings.
- **Hierarchy**: Next Action + Create Tasks to break down large projects.
- **Review**: Completed and Stats to review progress and time accuracy.

---

## 8) Data location and backups

Default locations:
- macOS: `~/Library/Application Support/GetMoreDone/getmoredone.db`
- Windows: `%APPDATA%\GetMoreDone\getmoredone.db`

These paths keep the app's previous name, `GetMoreDone`, on purpose — changing
them would leave the app looking for your data somewhere it was never written.

Development mode:
- Set `GETMOREDONE_DB=/path/to/your/dev/getmoredone.db`
- `start.sh` defaults to `./data/getmoredone.db`

Backups:
- Use **Settings → Database Management → Backup Database** to create a timestamped backup next to your current DB file.

---

## Appendix: Glossary

- **Who**: Person/client/context the item is for.
- **Planned minutes**: Your estimated duration for the task.
- **Work log**: A record created by the Timer when you finish or continue.
- **Item link**: A stored URL/reference tied to an item (Obsidian note, Google Calendar event, etc.).
- **VSP Segment**: A life area bucket for VSP planning.
