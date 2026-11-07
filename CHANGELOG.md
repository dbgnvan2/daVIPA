# Changelog

All notable changes to GetMoreDone are recorded here.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
conventions and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — the APE quarter/month consistency batch (2026-11-07)

- **APE Month and APE Quarter both open on the period you are actually in,
  and both say what Save did.** The Quarter picker on each screen opened on the
  literal "1" while the Month picker opened on today's month, so on 7 November
  APE Month offered Q1 + M11 and saved it — an APE filed in a quarter that does
  not contain its month, which APE Weekly then could not find, every November
  week, with nothing on screen to say why. Both pickers now agree, APE Month
  offers only the selected quarter's three months, and a mismatched pair is
  refused before anything is written. Records already stored that way are
  repaired when the app next opens, and the repair now says in the log which
  rows it changed. Both screens report a refused assignment instead of letting
  it look like a successful one, on the Save button and on the drop target
  alike.
- **What those screens tell you is read off the record, not off the save.**
  A save can fail halfway: the APE is filed in the month with no month tactic
  behind it. Counting what the save reported made that look like a save that
  did nothing, with the row visible in the panel beside the message. Both
  screens now read the sentence from the same list the panel is drawn from,
  and say which of four things happened to each APE — assigned, partly
  assigned, could not be assigned, or reported assigned but missing from the
  month. Remove says the same three things about itself: removed, still there,
  or gone but with the removal reporting a problem.

### Added — reported from the running screen (2026-11-07)

- **A "Clear Day" button**, the reverse of AutoLoad: it takes every scheduled
  item back off the day in one click, where undoing a plan meant one
  right-click per block. It asks first and the count is in the question, since
  the app has no undo. Breaks and buffers stay where they are — AutoLoad never
  wrote one, each was put there by hand — and the question says how many are
  staying. A day with no items scheduled says so and asks nothing, and
  clearing asks nothing about the weekday list: taking work off a day is not
  planning work onto it.
- **An item in the Plan list says whether it is scheduled.** A green check when
  the day already holds a block for it, a red question mark when it holds none.
  The column used to say something about a scheduled item and nothing at all
  about the rest, so an unscheduled item and an unmarked row looked the same.
  Both marks are theme tokens held to the 4.5:1 text contrast bar against every
  priority fill in both themes: the fills are pale tints in the light theme and
  deep in the dark one, where the ordinary dark-green success colour measures
  1.63:1 against the green fill and would have been a mark nobody could see.

### Fixed — reported from the running screen (2026-11-07)

- **The Plan screen's panes repaint when they are rebuilt.** Both panes are
  redrawn by taking the scroll frame out of the grid, destroying its children
  and putting it back, and Tk draws from an idle handler. Every one of those
  rebuilds runs inside an event callback, so the re-gridded pane could stay
  undrawn until the next mouse movement over the window. Moving a block to
  another half hour, resizing one and adding a break all wrote the day
  correctly and looked like a gesture that had done nothing.
- **A click on an item no longer leaves its title beside the pointer.** The
  floating drag label was built on the button *press*, so an ordinary click put
  one on screen; the release hid it again, but the hiding was not drawn either.
  The label now waits for the pointer to move — a press with no motion is not a
  drag — and hiding it repaints, so a drag released over nothing clears too.

- **A weekend no longer looks like a broken screen.** The Plan screen opens on
  today, Saturday and Sunday are off in the default week, and every write path
  checked that first: AutoLoad returned before reading an item, a dropped item
  before a block was written, and the only sign was a status line. Reported as
  "AutoLoad doesn't work" and "Drag and Drop doesn't move item" — one guard,
  not two defects. A day outside the weekday list now asks *"<date> is not a
  regular work day. Day Settings allows Mon, Tue, Wed, Thu, Fri. Schedule
  anyway?"*; Yes plans that date for as long as the screen is open and changes
  nothing in Day Settings, No writes nothing and still says which days the week
  allows. Asked once per date, not once per drop.
- **The divider between the panes is 15px of grip.** It was a 6px grip with a
  2px pad on each side: a 10px gap on screen of which only the middle 6px
  started a drag. The gap and the grip are now one thing.
- **A narrow window no longer short-changes the day pane by the grip.** The
  clamp that keeps both panes above their minimum widths compared them against
  the whole window, though the grip and the window's two edge pads are 35px of
  it and none of that is pane — so the day pane could be left under its own
  minimum, which is the clipping the minimums exist to prevent.
- **The depth bars are justified like the text beside them.** The three-bar
  stack is shorter than a line of text and was aligned to the top of the row,
  so it floated above the title on every row in the items pane. It now takes
  the title's own vertical justification — centred on the line — and the
  stack's trailing gap is gone, so the bars fill the stack with no slack at
  either end to put them a pixel out.
- **A test fixture was reporting other tests' dialogs.** `messageboxes` yielded
  the session-wide record and trimmed only the tail on teardown, so a test that
  did not ask for the fixture left its dialogs in it for every later test. One
  of the new tests above failed on a dialog raised two tests earlier and passed
  on its own. The record is emptied on the way in as well as out.

### Fixed — what the cold sweep found

- **Extending the day earlier no longer re-times every other date's work.**
  A block's box is stored as a count from Day Start, and Day Start is one
  setting for every date — so moving it back half an hour and renumbering only
  the date on screen left every other date's blocks drawn half an hour early,
  with their own rows still showing the old time and nothing marked wrong. A
  10:00 Monday meeting read 09:30 after an item was dropped on Tuesday. The
  renumber now covers every date, which is what "every existing block keeps its
  clock time" has to mean when there is one Day Start.
- **AutoLoad's counts cover the whole list.** It plans the first 60 items, the
  same cap the pane draws, but reported "blocked N of 60" — so on a day with
  more items than that, the ones past the cap appeared in none of the counts.
  The denominator is now every item on the day and the capped number is named,
  so the counts add up to the list. A failure that is not a refused box is now
  reported too: before, anything else left the screen unchanged and silent, so
  a press that failed looked like a press with nothing to do.
- **A narrow window no longer clips the block length off the day boxes.** The
  two panes each have a minimum width, but only the items pane was held to its
  own — so a window too narrow for both took the whole difference out of the
  day pane and laid the `30m` label past the right edge of every box. Narrowing
  the window now takes the width off the items pane first, down to its floor,
  and widening gives it back.
- **A click on the divider no longer changes the width you set.** Pressing the
  grip took the width from the settings file rather than the width on screen.
  The two differ whenever the window is too narrow for the setting, so a click
  that moved nothing saved the narrowed width over the one you had chosen, with
  nothing said — and widening the window afterwards no longer gave it back. A
  press now starts from the column as drawn, so a click that moves nothing
  writes nothing, and a drag moves the edge from its first pixel.
- **A failed AutoLoad says what failed.** A failure carrying no message of its
  own ended the sentence at the dash; it now names the fault, and the fault is
  written to the log as well, since the status line is replaced by the next
  thing that happens.

### Changed — the two panes, read side by side

Six corrections from looking at the built screen.

- **An item row is now the height of the space it will take, at every box
  height.** It was meant to be since PB-M6, but the row had a second line for
  the `already blocked` words, and the floor that line imposed was 66px — two
  boxes' worth at any box height anyone sets. So a 30-minute row and a
  60-minute row came out within a few pixels of each other, and the pane
  stopped showing the one thing its row heights are for. A 90-minute item is
  three boxes tall because the day will give it three boxes.
- **`already blocked` is a `>` marker**, in a column of its own left of the
  depth bars, on both panes' layout so nothing shifts out of line when it
  appears. Not the green check: that already means *this task is finished* on
  a day box, and one glyph cannot carry both.
- **Every block ends 8px short of its right edge**, in both panes. The length
  was gridded hard against the edge. The inset is counted into the length's own
  column, so the width the items pane can be dragged to accounts for it.
- **`30m` is the size of the text beside it.** It was 11pt against the title's
  13, which made the one number on the row the smallest thing on it.
- **A break or a buffer is now drawn on the same surface as lunch.** The
  previous change gave the three one stripe colour and stopped there, so the
  stripes matched while the boxes did not — and the boxes are what you compare.
  An empty box still looks like an empty box: it is room, not padding.
- **The word "Lunch" is body text at body size.** At the theme's muted text on
  the surface a lunch box is drawn on it was within a few values of its own
  background — measured off the screenshot at (239, 234, 252) on (240, 231, 255).

### Added — an item dropped above or below the day lengthens it

- There is now a box at each end of the day, above the first half hour and
  below the last, labelled **Earlier** and **Later**. Drop an item on one and
  the day grows to hold it: *Day Start* moves back, or *Day End* moves forward,
  by exactly the item's own length, and the item is blocked in the half hours
  that appear. A 90-minute task takes the day back an hour and a half, not half
  an hour.
- The boxes are drawn every redraw, on an empty day too, which is the day that
  most needs them: there is no first block to drop above.
- **The day's existing work keeps its clock times.** A block is stored by which
  half hour of the day it sits in, not by the time, so moving *Day Start* back
  would otherwise have slid every block on the day earlier with nothing on
  screen to say so. Extending earlier now renumbers the day by the same number
  of boxes it gained.
- Midnight is the floor and the ceiling. An item too long to fit before *Day
  Start* or after *Day End* without crossing it is refused and says why, rather
  than being given a shorter day than it needs — a day is one date.
- Dragging a **block** onto one of these boxes is refused: the day lengthens to
  make room for work that is not planned yet, not to rehouse work that already
  has a box.
- Lengthening the day is not confirming it. A day whose four times the app
  guessed still says so afterwards, so the warning and the guards that depend
  on it stay where they were.
- If the settings file refuses the write, the day, the grid and the app's own
  settings are put back as they were and the reason appears on screen (P41).
  Nothing is left claiming a longer day than disk holds.

### Added — an AutoLoad button fills the day from the item list

- **AutoLoad**, in the Plan header beside *+ Break* and *+ Buffer*, blocks
  every item in the list that the day still has room for: one after another,
  from the top of the list down the day, each at the earliest half hour with
  nothing in it. A task longer than half an hour takes the boxes it needs and
  the next item starts after them.
- It only adds. It never moves, resizes or deletes a block that is already
  there, and it does not lengthen the working day — an item that will not fit
  is reported, not accommodated.
- It says what it did, all three numbers every time: how many it blocked, how
  many did not fit, and how many were skipped because they already had a block
  today. A day with no items says that instead, which is a different fact from
  a day with no room.
- The whole run is one write. If the day refuses a block part-way, nothing at
  all is written and the message says how far it had got, rather than leaving
  half a planned day behind.
- Not offered on a day the week's Day Settings exclude: it refuses with the
  same reason a drop onto that day gives.

### Changed — an item is drawn as the task it is about to become

- A row in **Items starting** now uses a day box's own first line: the same
  four columns in the same order at the same widths — colour stripe, title,
  depth bars, block length. The length is beside the bars at the right-hand
  end, where a box writes it, not under them. The two panes read as one list of
  tasks either side of the divider, which is what the width settings were for.
- The depth word has come off the second line. The row is already drawn in its
  depth's shade, striped in it, and carries the bar stack that exists to show
  it, so the word was a fourth telling in the one place a reader looks for
  something the colours cannot say. `already blocked` is what that line
  carries, and only when it is true.
- The title column takes its width from **Drag Schedule title column width
  (px)** on both panes. It had been a constant on the left, so the columns
  lined up at the default and nowhere else.
- **Fixed in the same change:** at the shipped settings the four columns asked
  for 306px inside a 256px pane and the length label was laid out past the
  right edge — invisible in every item row. **Plan items column width (px)** is
  now raised, when it has to be, to what one row needs: the stripe, the title
  column, the bars, the length, and the pane's padding and scrollbar. At the
  default sizes that is 360px, so the shipped 260 is raised. A blank, zero or
  non-numeric value is raised too; it was not, which was the one path around
  the guard.

### Added — the divider between the Plan panes drags

- The thin vertical line between **Items starting** and **Day Plan** is now a
  grip: drag it to make the item list wider or narrower, and the day takes the
  rest. It writes **Plan items column width (px)**, the same setting the field
  in Settings holds, so a drag shows up in the field and a typed width shows up
  on screen.
- Written once, when you let go, not on every pixel of the drag. If the write
  is refused the pane goes back to the width it had and the reason appears
  under the *Items* heading: the app never draws a width the file does not
  hold.
- Neither pane can be dragged shut. The item list stops at the width one of its
  own rows needs; the day stops at the width one day row needs.

### Changed — break, buffer and lunch are one colour

- The three kinds of time that are not work now share a single colour, so the
  day reads as work and not-work rather than as four kinds of thing. Lunch had
  no colour of its own to share — it was drawn as a bare surface with no stripe
  at all — so it gains the stripe the other two have.

### Added — a finished box shows a green check

- A half hour whose every task is complete carries a check mark to the left of
  its time, in the theme's success colour. A box with any work left in it does
  not, including one holding a finished task beside an open one. Padding in the
  box neither claims the check on its own nor withholds it from a finished task
  beside it. The later boxes of a long finished task show it too — the box is
  spent either way.
- Day Plan only: the item list on the left shows open items, so a completed one
  is never in it.

### Fixed — a box height saved in Settings did nothing until the next launch

- **Drag Schedule box height (px)** and **Plan items column width (px)** were
  written to the settings file and ignored by the running app. The Settings
  screen loads its own settings object, and the Plan screen reads the app's;
  the appearance section hands its object over after a successful save, and the
  section holding these two did not. Changing the box height now changes the
  Day Plan and the item rows as soon as you leave Settings, with no relaunch.
  What the app is handed is re-read from the file, not the Settings screen's
  own object: handing that object over would have made the two the same
  object, and from the next Save on a *refused* write would have reached the
  running app anyway -- red "could not write the settings file" and the new
  sizes at once. The app never shows sizes the file does not hold.
- Found by running the app after three review passes and a green suite, none of
  which could see it: every test builds a screen from a settings object it was
  handed, which is exactly the step the Save button was missing.

### Fixed — a planned task in the Plan grid showed nothing but its colour bar

- A task placed on a half hour drew as a bare 6px stripe: no title, no
  duration, no depth bars. `ctk.CTkFrame` requests 200x200 when neither
  dimension is given, and the accent stripe set only `width`, so its height
  request was a constant nobody chose. The chip passed that request up and the
  box clipped it, leaving the title laid out around y=100 inside a box 34px
  tall — drawn, but below everything the box shows. The stripe now asks for a
  height.
- The same missing `height=` made every row in the **Items starting** list
  about 200px tall. Those rows are now as tall as their two lines of text.
- The *no items start on this date* note was clipped at **both** ends, because
  `CTkLabel` centres its text and the note was wider than the column. It is
  now anchored left and wraps to the column's width.
- `tests/test_plan_screen.py` carried a comment stating this sliver bug did
  not reproduce. It did. TG-M8.1 and TG-M8.2 passed throughout, because a
  label clipped by its parent is still full-width and still `winfo_ismapped()`
  — the new PB-M2.1 measures where the title sits inside the box instead.

### Changed — an item row is the size of the space it will take

- A row in **Items starting** is now as tall as the space its work block will
  take in an empty day: a 90-minute item is three boxes, a 45-minute item is
  two, measured the way a user would — from the top edge of the first box to the
  bottom edge of the last, gaps included. A half hour that already holds another
  task is taller than one box, so the match is with the day the item would be
  dropped into. The row is the shape of the space it
  is about to take, so the day's room for it is visible before the drag.
- A row never goes below its own two lines of text, whatever the box height
  says. The 30px floor on the box height was set for a chip holding one line,
  and an item row holds two; matched to a 34px box the row showed its title and
  silently cut the second line. So the row and the day agree exactly from a box
  height of 62 up, and below that the row is the taller of the two. (66px and
  62 since the length label moved onto the first line — see *an item is drawn
  as the task it is about to become* below. It was 67px and 63 as shipped
  here.)
- The priority score has come off the row. The row is drawn in its priority
  band and striped in it, so the number was a third way of saying one thing in
  the one place a reader looks for what the colour cannot tell them.
- The work-block length (`30m`) moved out of the detail line to sit under the
  depth bars, which puts it in the same place on an item row as on a task in a
  box. *Superseded below*: a box does not put it under the bars, it puts it
  beside them at the right-hand end of the task's line, and that is where it is
  now.

### Fixed — a long task's later boxes read as empty half hours

- The second and later boxes of a task were drawn transparent, so a 90-minute
  task was one coloured box followed by two blank ones — a task that appears to
  stop after half an hour. A continuation now carries the task's shade and its
  stripe, and keeps the `↳` that says it is the same task continued. Buffers
  and breaks stay transparent. The `same task` / `15m spare` line takes the
  text colour the new fill calls for instead of the pane's muted grey.

### Changed — a task in the Plan grid is shaded by its priority

- A task now carries its priority band as the shade it is drawn on, as well as
  the bar at its edge, on both the Day Plan and the items list. Padding
  (Buffer, Break) is left unshaded: it has no priority to show. A continuation
  box carries the task's shade and stripe (see below). Title colour is chosen
  for the shade behind it.
- The band stripes are brighter. A second table, `priority_stripe_colors()`,
  held to the 3:1 WCAG bar for a non-text object; `priority_band_colors()` is
  unchanged and stays at 4.5:1 for anywhere a band colour sits behind text.
- A task in a Plan box is now as tall as **Drag Schedule box height (px)** and
  its title column as wide as the Drag Schedule title column, so a task is the
  same size on both screens. Empty half hours keep their compact height. An
  unusable setting falls back rather than flattening the day.
- A box height below 30 is raised to 30, which is one line of text. A box does
  not grow to its contents while a task inside it does, so a shorter box made a
  half hour holding two tasks the same height as one holding one, with the
  second task laid out past the box's clip edge.
- The **Outside the day** group's rows are the size a task is in a box, and the
  group scrolls. It had moved into the items column on a plain frame, so a day
  with more than a few blocks outside it clipped the lower rows out of reach
  while the header still counted them.
- The *no items start on this date* note wraps at a minimum width. Tk reads a
  wraplength of zero or less as "do not wrap", so an items column of 56px or
  narrower got back the single clipped line.
- *Plan items column width (px)*, the two *Drag Schedule* sizes and the
  date-increment rules are all in Settings ▸ **Date Increment Settings**. The
  docs said Appearance for the first two.

### Fixed — settings saves that could not happen were reported as done

- Every **Save** button on the Settings screen now reports a write that was
  refused, instead of printing *"✓ Saved"* over it. `AppSettings.save` declines
  to write when a settings file is present, will not parse, and cannot be
  copied aside — refusing is deliberate, because that file is the only copy of
  whatever could not be read out of it — and seven buttons said they had saved
  anyway. Two of them did more than say it: **Appearance** applied the new theme
  app-wide, so the user saw a theme that was gone on the next launch, and
  **Email Import** reloaded launchd from a file that had not changed, handing
  the importer the old interval while reporting the new one.
- The Plan screen's warning about an unconfirmed day no longer names a cause it
  cannot know. It blamed an unreadable settings file for all three of the states
  that reach it, and the common one — a settings file from a version that had no
  Day Settings — reads perfectly well.

### Added

- **The Plan screen builds a day on a grid of half-hour boxes.** Every half
  hour from Day Start to Day End is a box, drawn whether it holds anything or
  not. Drag an item from the left pane onto the box you want it in; drag a task
  to another box to move it; right-click it to set its length to 15/30/45/60/90
  minutes, a custom number, or delete it. `+ Break` and `+ Buffer` put a
  padding block in the first box that will hold it. Three consequences, all
  deliberate: **gaps are a legitimate day** and nothing ever slides up to close
  one; **lengths round up to whole boxes**, so a 45-minute task takes two,
  keeps its own 45 and shows `15m spare` on the second; and **a box is worth 30
  minutes however many tasks share it** — up to four, and the box grows to show
  them. A block stores *which box* it is in (`slot_index`), relative to Day
  Start, so the clock times follow from the box on read.
- **Day Settings saves without writing to a single block.** Moving Day Start
  re-times every planned day, on every date, because each block's box is stored
  relative to it. There is no re-packing, no day left on the old shape, and no
  day that can be "too full to re-time".
- **Work the grid can no longer hold is shown, never dropped.** A block whose
  box is past a Day End you have moved earlier, whose length now runs off the
  end of the day, or that lunch has since moved onto, appears in an **Outside
  the day** group beneath the item list, in the left column; dragging it onto
  a box puts it back. Days
  planned in an older version are mapped onto the grid the first time they are
  opened: a readable start time goes on the box that time names **or nowhere**,
  never slid to the nearest free box. That mapping cannot be undone, so it
  reports how many blocks it placed **and the Day Start it placed them
  against** — and it runs only against a day shape you have confirmed in Day
  Settings: otherwise the blocks wait under *Outside the day* rather than being
  written permanently against a day shape the app guessed at. An unreadable
  settings file is one such guess; so is a settings file from any version
  before this one, which had no Day Settings, and so is a day time the app had
  to substitute because the file held something it could not read. The settings
  file itself records whether the four times were confirmed, so the guarantee
  holds across a relaunch and across an upgrade in either direction. Saving **Day Settings** is the way back, and
  the only way: it is the one screen that shows you the day's four times, so it
  is the one whose save tells the app they are yours. It keeps the unreadable
  file aside as
  `settings.json.unreadable-<date>-<time>` first, because saving replaces every
  setting in the file and not just the day's shape; if that copy cannot be
  made, nothing is overwritten; and if the new file cannot be written, the
  dialog says so, stays open, and puts the day's shape back instead of
  reporting a save that did not happen.
- **Every refusal says which refusal it is**: outside the day, running into
  lunch, that half hour already full, or — choosing a length for a block that
  is not on a box yet — *that block is not on a box yet*. Nothing is written
  and nothing moves. A release in the day column but on no box creates nothing
  and says so, for a task being moved as well as an item being added — the app
  does not pick an hour for you, and a gesture that did nothing silently would
  look exactly like one that missed.
- **Day Settings for the Plan screen** (⚙ in the Plan header): day start, lunch
  start and length, day end, and seven checkboxes for the weekdays that accept
  blocks. A drop onto a day that is not checked is refused with the reason. A
  time the app cannot read is rejected in the modal with the field named.
- **Blocks are readable before they are read.** The stripe down a task's left
  is its item's priority band, and depth is drawn as a three-bar stack (deep 3,
  medium 2, shallow 1, unset 1). The later boxes of a longer task are greyed,
  marked `↳`, and carry no drag and no menu — the box a task starts in is the
  one that owns it. Each continuation reads `same task`, except the last, which
  reads what the task leaves of it (`15m spare`): only the final box can have
  minutes to spare, and a middle box is spent in full. A dropped item's
  block takes the item's Work Block value as its length when it has one,
  otherwise 30 minutes.
- **The day summary reports three numbers, not one**: boxes used, time
  occupied, time planned. A 45-minute task occupies an hour of the day and
  plans 45 minutes of it, and one number would have to be wrong about one of
  them.
- **A demo instance that runs beside your real one.** `./start-demo.sh` starts
  a second, fully isolated copy of the app — its own database, settings,
  single-instance lock and logs under
  `~/Library/Application Support/GetMoreDone-Demo/` — seeded with sample items
  on its first launch. The new `GETMOREDONE_DATA_DIR` environment variable
  redirects the whole data directory, where `GETMOREDONE_DB` redirected only
  the database. Documented in `docs/DEMO_INSTALL.md`.

### Fixed

- **The Plan screen's time blocking did not work.** There was no way to change
  a block once created — `DatabaseManager` had no `update_time_block` at all —
  so a block's length could not be edited and the day could not be reordered.
  The date was a free-text field that silently wrote unusable dates, and the
  item list was not filtered by the selected date.
- **Dropping an item or reordering a block could hang the app.** The release
  handler destroyed the row widget whose own event it was still dispatching.
  Found by driving real Tk button events at the real row widgets; every test
  that called the handlers directly passed.
- **Dragging a block down moved it one place too far.** *(Superseded before
  release: there is no order to drag within. A drop names a box, and the drop
  either lands in one or is a cancelled drag.)* The drop position was counted
  against the rows as drawn, dragged block included, and passed to a function
  that counts against the list with that block already removed. A drop in a
  block's own lower gap moved it past the next block instead of doing nothing.
- **A block could be longer than a day, and then lie about its own end time.**
  The length ceiling was checked only in the dialog that asks you for a number.
  An item's Work Block value, which the item editor accepts as any integer, went
  straight through — so a Work Block of 5000 made a 5000-minute block whose
  stored end time was not its start plus its length. Both ways in now stop at
  1440 minutes, and a capped Work Block is reported rather than quietly applied.
- **Day Settings accepted an hour past 23.** A Day End of `24:00` or `25:00` was
  stored, which put the end of the day past every block the planner can make and
  retired the "past day end" warning permanently; `170:0` was stored as `99:59`,
  a value nobody typed. Times outside `00:00`–`23:59` are now rejected in the
  modal with the field named.
- **A settings file already holding one of those values was still read as
  given.** Rejecting them in the modal healed new input and left an existing
  file wrong forever — a Day End of `25:00` written by an earlier version kept
  the overrun warning switched off with nothing anywhere to say so. All three
  day-bound values are now read through a parser that refuses an hour of 24 or
  more and falls back to that field's default.
- **A day too full to write was written clamped rather than refused.**
  *(Superseded before release: the grid stops at Day End, so a day cannot run
  past what `HH:MM` can express and this ceiling is unreachable. The refusals
  that remain are the three the grid can actually give.)* The length ceiling
  bounds one block; running past the last time the app can express is a
  property of the whole day. Four blocks of exactly a day each are individually
  legal and together pass that point, where the fourth row would have been
  stored claiming 1440 minutes between two times 899 minutes apart.
- **Saving Day Settings re-timed only the day on screen.** *(Superseded before
  release: a block's box is stored relative to Day Start, so a save re-times
  every day by writing nothing at all.)* Day start, lunch and day end shape
  every planned day, so every other day was left holding times derived from
  settings that no longer existed.
- **Each block write and its derived times were two separate commits.**
  Between them, a newly dropped block had no times at all, and a resized one
  read as a 30-minute block claiming 90. A block's box, its order within that
  box and its clock times are now settled and written as one unit, and a
  refusal is raised before anything is written rather than rolled back.
- `tools/create_demo_data.py` could not run at all. It added `tools/src` to the
  import path instead of the repository's `src/`, so the script that both
  README.md and CLAUDE.md tell you to run failed with `ModuleNotFoundError`.
- The demo launcher's refusal to run against your real data directory compared
  the two paths only as strings, so three spellings of that directory got past
  it: a case variant (stock macOS volumes are case-insensitive), a firmlink
  path such as `/System/Volumes/Data/Users/...`, and `/` itself. It now
  compares case-folded names and directory identity, refuses the filesystem
  root, and refuses a `getmoredone.db` symlinked out of the demo directory.
- `./start.sh` could print an isolated data directory and then open the real
  production database: a value of one non-breaking space was non-empty to the
  shell and empty to `paths.py`. Both launchers now apply every path rule in
  Python, so the launcher and the app cannot disagree about where a launch
  goes.
- Reading the demo's item count spliced the path into a SQLite URI, so a `?` in
  it created a file during `--print-env` — the one command documented to create
  nothing — and a `%` made every launch reseed and double the demo's items.
- Both launchers hardcoded the macOS data directory, so on Linux the demo guard
  protected a directory the app never opens and `./start.sh` exported a
  database `python run.py` would not have chosen.
- `./start-demo.sh --printenv`, or any other typo, performed a full launch
  instead of reporting what it would do; it now exits 2. `./start.sh` forwards
  its arguments to `run.py`, so `--selftest` is no longer an ordinary GUI
  launch.

## [0.3.2] - 2026-10-02

### Added

- **Depth and Work Block on action items.** Two new scheduling hints set on the
  editor's **Priority** tab — **Depth** (Deep, Medium, Shallow) and **Work Block**
  (90, 60, or 30 minutes). Both echo in the **Action Plan** block beside Project,
  Wk Tactic, and Orig. Week. A **Schedule on Calendar** button on the same tab
  opens the calendar dialog with its Duration pre-filled from the Work Block.

## [0.3.1] - 2026-08-28

### Added

- **The timer now rewards finishing a thing, not running out of time.** Give an
  action a **Deliverable** — the crisp "done = ..." for it, a checkable artifact
  rather than a time-box. "Draft section 2's opening paragraph", not "work on
  the report for 25 minutes". The field is on the item editor, and the timer
  asks for one when you start a session on an action that belongs to a Project.

- **A "Done — deliverable complete" button on the timer**, available the whole
  time a session is running rather than only when the clock stops. Pressing it
  is what completes the work, so the reward attaches to what you made instead
  of to how long you sat there.

- **A savor step after a completed deliverable.** It shows you what you set out
  to do, says it is done, and asks you to look at it for five seconds. Early on
  in a project it appears every time; after fifteen completed deliverables it
  drops to roughly two in five, because a signal that arrives every single time
  stops carrying information. There is no "good job" in it anywhere — the words
  point at the artifact and at the effort, which is the whole idea.

- **An occasional celebration** — confetti, balloons or a chime — on about one
  completion in five, at random, in every phase. It is never guaranteed and
  never replaces the savor step; the moment a surprise becomes predictable it
  is just a cue.

### Changed

- **The timer window is now three clear areas.** The **timer** (deliverable, clock,
  and ▶ Start / ⏸ Pause / ⏹ Stop laid out like a recorder), the **music** (play, pause,
  and the track name — which used to be appended to the timer's own status line), and
  the **session actions**.

- **The deliverable is on the timer window.** It was typed into a dialog at the start and
  then never shown again — the one thing the reward depends on was the one thing you
  could not see. It now sits at the top with an **Edit** button. If an item has no
  deliverable, starting the timer asks for one; if it has one already, you are not asked
  to retype it.

- **Music no longer starts by itself.** Starting the timer used to start the music,
  which decided for you that this was a session with music in it. Only the Play button
  starts it now.

- **Finished and Continue are gone, and what replaced them says what it does.** Both of
  them quietly completed the action item and closed the window, which looked from the
  outside like nothing had happened — the window vanished and the task left Today. A
  session is now a record of work *on* a task, and it ends one of three ways:
  **Save Related - Close Timer** (saves the session and the time as a related record,
  task stays open), **Cancel Timer** (nothing is recorded at all — no session, no time,
  no note, no change to the item), and **Complete & Open Follow Up** (saves the record,
  completes the item, and opens the follow-up). Two of them close a task — Done, and
  Complete & Open Follow Up — but **only "Done — deliverable complete" counts one
  towards a project's reward phase.**

- **Fixed: the session buttons appeared to do nothing.** Pressing Stop and then any of
  them left the window sitting there. They were working — the dialog they opened was
  landing *behind* the always-on-top timer while holding the input grab, so it was
  invisible and swallowed every click. Every dialog the timer opens now raises itself
  properly.

- **The end of a break no longer ends the session.** It used to stop the timer
  and offer Finished/Continue, which quietly made the timer ringing the thing
  that decided your work was over. Now it asks: **Pause (rest)** or **Continue
  focus**, and neither completes anything. Stop still works exactly as before,
  and Finished/Continue still appear after you press it.

  Two consequences worth knowing. **Music now keeps playing through the end of a
  break** — it used to stop, because the break ending stopped the whole timer.
  That matches how Pause has always behaved (music is yours to control from the
  music buttons). And Finished/Continue are one click further away at the ring:
  press Stop first, or use **Done** if the deliverable is finished.

## [0.3.0] - 2026-08-21

### Changed

- **The app is now called daVIPA.** Same app, same data, new name — with the tagline
  *Vision · Planning · Action*. The window title, the sidebar and the app icon all
  follow it, and the downloads are now `daVIPA-mac.zip` and `daVIPA-win64.zip`.

  **Your existing items and settings are untouched and stay exactly where they are.**
  The folder they live in still reads `GetMoreDone` — on purpose and permanently.
  Renaming it would leave the app looking for your database in a place it had never
  written one, and everything would appear to be gone. The name on the outside
  changed; where your data lives did not.

### Added

- **A daVIPA colour theme**, selectable in Settings alongside the existing nine. It is
  built from the palette measured off the new app icon: a deep indigo ground, indigo
  and violet for surfaces and buttons, and crimson kept for things that are a signal
  rather than a surface — a ticked checkbox, a switch that is on. Every text-and-background
  pairing in it was checked for legibility; the weakest is comfortably past the accessibility
  standard and most are far past it.
- **The Windows app finally has its own icon.** Every Windows build until now shipped the
  generic one that PyInstaller supplies by default.

### Fixed

- **Choosing a theme now gives you that theme.** Selecting one that had been added
  recently silently reverted to Apple Grey on the next start, because the list of valid
  themes existed in two places and only one of them had been updated. There is now one
  list.
- **The main window's background now matches the theme you chose.** It had been painted
  in the theme from the *previous* launch — the window is created before the theme is
  applied, so it was always one behind. This affected every theme, and showed as a window
  background that did not match its own sidebar.

### Added

- **File an Action Item under a Project from the item editor.** A new **Set Project**
  button beside Set Wk Tactic opens a project picker that also creates a Project inline
  (**+ New Project**), so a new task and the project it belongs to can be created from one
  screen. **Clear Project** unfiles the item. Filing stamps the project's Annual Plan Element
  onto the item — the same rule as dragging onto a project in the Scheduler — and the link is
  only written when the selection actually changes, so an ordinary Save can never clear it.
- **An Action Plan block in the top left of the item editor**, showing the item's Project and
  Weekly Tactic together. The Weekly Tactic and Orig. Week fields moved here from the
  Organization tab, which now holds Group and Category only.
- **A follow-up inherits the original's Project**, the way it already inherited the weekly
  lineage. Previously a follow-up of a project task landed unfiled. It inherits exactly one
  project, since an Action Item belongs to exactly one — a follow-up of one of the older
  multi-filed rows lands on the first of them, and the drop is logged.

- **A Weekly Tactic link of its own.** `action_items.weekly_tactic_id` replaces the
  overloaded use of `parent_id`, which previously served both ordinary subtask nesting
  and the week bucket at the same time — so attaching a tactic silently destroyed a
  hierarchy, and setting a parent silently destroyed the tactic link. An item can now be
  both a subtask and week-filed. The migration moves existing week links across and
  leaves daily nesting untouched, reporting both counts.
- **One owner of week identity and week numbering** (`week_calendar.py`). Week numbers
  now carry their year: 2026-12-28 and 2027-01-01 are both ISO week 53, and a bare `53`
  cannot say which. A new **First week of year** rule (`iso`, `jan1`, `first_full`)
  defaults to `iso`, which is how every existing database was numbered.
- **Project start and end dates** on Project Boards. Informational only — never
  validated and never derived from the items on the board, because a project may span
  any timeframe.
- **`weekly_tactic_start_date`** on Action Items, recording the week an item was
  originally meant to start. Existing items are left blank; nothing is backfilled.
- **Changing an Action Item's start date re-files it into the right Weekly Tactic**,
  creating any missing Quarter, Month and Week records along the way — including across
  a year boundary. The item's dates move by whole weeks so a Thursday task stays on a
  Thursday, and an item never spans two weeks.
- **Completing an item re-files it to the week you completed it in**, while
  `weekly_tactic_start_date` goes on holding the week it was originally meant to start,
  so a push-out stays visible. Re-opening does not undo that.
- **A new year is built from your existing plan structure, not invented.** The vision
  element, segment and key field carry across; the editorial text — vision statement, key
  priorities, theme, objective — is left blank for you to write, and those rows are
  flagged so the app can tell a stub from something you wrote. When a save creates them,
  it says so.
- **A first-week-of-year setting** under Settings, and project start/end dates on Project
  Boards.

### Changed

- **The release workflow publishes once, after both builds succeed.** `build-windows`
  and `build-macos` each called `softprops/action-gh-release`, so a tagged run made two
  release calls. Whichever finished first created the public Release; if the other then
  failed, that Release stayed up carrying one platform's assets, because a failed job does
  not un-publish a Release another job already created. A single `publish` job now runs
  `needs: [build-windows, build-macos]`, downloads both artifacts and makes one release
  call, so a half-succeeded run publishes nothing. The release notes are generated once
  rather than once per platform.
- **Test-only dependencies moved to `requirements-dev.txt`.** `requirements.txt` is now the
  runtime set — the list that ships inside the binary. `requirements-dev.txt` includes it and
  adds pytest, so one install still gives a contributor everything. Two places had been
  carrying a hand-maintained copy of which packages were test-only: a `TEST_ONLY_PACKAGES`
  set in `tests/test_release_licensing.py` and a `grep -v '^pytest'` in `start.sh`. Both are
  gone; a third test-only package would have slipped past both and been treated as a shipped
  dependency.
- **`GoogleCalendarManager` reads its arguments before touching the filesystem.** Constructing
  it with explicit `credentials_file` and `token_file` created `~/.getmoredone` anyway and then
  never used it. The default location is now resolved by `paths.google_auth_dir()`, shared by
  the constructor and the two static checks that previously each hardcoded the path — changing
  only the constructor would have left `has_credentials()` looking somewhere else. The location is
  unchanged — always `~/.getmoredone`, which the Gmail importer, the launchd import job and the
  diagnostic scripts all share. The directory is created where the token is written, which also
  fixes an explicit `token_file` in a non-existent directory failing behind a warning and
  re-authenticating every run. `tools/diagnose_google_auth.py` now shares the same resolver instead
  of hardcoding the path, and the calendar dialog's "credentials not found" message names the path
  it actually checked rather than a hardcoded one.

- **An Action Item belongs to exactly one Project, on every screen.** The Projects
  screen's "Link Action Items" dialog used to *add* a project to an item while the
  Scheduler and the item editor *moved* it, so the same item could accumulate boards
  depending on which screen you used. Linking now moves the item everywhere. Because
  that means links get deleted, all three screens ask the same question before
  unfiling anything — naming the project you are filing under, how many links go, and
  what happens to the item's Annual Plan Element — and nothing is removed without an
  answer. Filing under a project replaces that plan element with the project's (or
  clears it, if the project has none); clearing the project clears it. All three were
  silent before.
- **Removing an item from a project removes only the project link.** Its Annual
  Plan Element stays, because you may be on the way to filing it under a different
  project and losing your place in the plan in between helps nobody. The Projects
  screen's **Unlink** button always behaved this way; **Clear Project** and dragging
  onto **No Project** used to clear the plan element as well, so the same intention
  had two outcomes depending on which control you reached for. Filing an item under
  a project still stamps that project's plan element onto it.
- **An Annual Plan Element can only be deleted when nothing is on it.** Deleting one
  used to detach every Action Item pointing at it — silently for an ordinary item,
  and leaving a Weekly Tactic in a state the app refuses to save. It now says which
  items are in the way, and deletes nothing until you have moved them.
- **A project decides its items' Annual Plan Element, including when it has none.**
  Moving an item to a project with no plan element used to leave the *previous*
  project's on the item, so it went on claiming a place in the plan belonging to a
  project it was no longer on — visible as the wrong Segment and Category in every
  list view.
- **Items already filed under several projects are reported, not quietly cleaned up.**
  The Projects screen names them above the board list, with how many projects each
  sits on, and the count appears at start-up. Nothing is deleted for you: each one is
  resolved the next time you choose a project for it.
- **Creating an Action Item from a Weekly Tactic uses the title you typed.** It used
  to prepend the tactic's context (`PW|LS|Blog - W34 - your title`) for tactics with
  an older-style title. The item's place in the plan comes from its Annual Plan
  Element and its parent tactic, not from the title text.
- **The Scheduler's "Unlinked (No Project)" box no longer loads every unlinked item
  in the database to show a count**, and says "showing N of M" if there are more than
  it fetched.

### Removed

- **Push to Next Day (the Reschedule dialog) and complete-and-create.** Neither had
  been reachable from anywhere in the app; both were kept alive only by their own
  tests. Rescheduling is unchanged — drag an item in the Scheduler, or edit its dates.

### Fixed

- **The test suite no longer flashes a window onto the screen on Linux.** Test
  windows are made fully transparent so they can be laid out and measured without
  being seen, but on Linux the transparency was lost whenever a window was
  re-shown — so a window appeared and took focus. It is now re-applied at that
  moment. This affected continuous integration, not the released app, and it is
  why the build had been failing since 20 August.

- **Renaming a life segment to a name another one already has, differing only in
  capitalisation, is now refused.** Creating one that way was already refused;
  renaming was not, so the same state could be reached through the segment editor.
  It matters because the two cannot be told apart afterwards: every link that
  resolves a segment by name gives up on both of them, permanently, and the startup
  check reports them as needing attention at every launch. The editor now explains
  the refusal and keeps the dialog open with what you typed, rather than saving or
  failing silently. A segment can still keep its own name, change its capitalisation,
  or take any name not already taken — and if your database already contains such a
  pair from before this check existed, both segments remain fully editable: you can
  still change their colour, description, order, retire one, or rename one of them to
  something free — which is the way out of the situation. What is refused is any save
  that would pull a *further* segment into the same trap.
- **A failed segment rename no longer leaves half of itself behind.** The name and the
  linked Vision Segment were written separately, so if the second write failed the
  first had already happened and the next unrelated save committed it — leaving one
  segment recorded under two different names. Both now succeed together or neither
  does, and a name clash the check could not foresee is explained in words rather than
  as a database error.

- **A plan element's Annual Initiative is found by its id and nothing else.** The
  lookup resolved by id — correct — and then also required the initiative's annual
  plan to carry the same year as the plan element. A plan element id identifies one
  plan element and a plan element carries one year, so that extra condition could
  never find a *different* initiative; it could only hide the right one. The year is
  stored separately on the plan, the plan element and the initiative, so any path
  that updates one without the others makes them disagree — and when they disagreed
  the initiative went invisible and the next assignment built a duplicate, which is
  the very bug this lookup was rewritten to prevent.

  Where the initiative is matched by its **title** instead — the one-time repair and
  the upgrade step, both used only for rows that have no id yet — the plan's year is
  now a tie-break rather than a requirement. An initiative whose plan agrees about the
  year is preferred; the wider set is only consulted when none does. Dropping the
  requirement outright would have let a same-titled initiative on a stale plan take
  the link, or made the repair see two candidates, decline to choose, and leave the
  caller to create a third.
- **A database upgraded from the oldest Vision Segment layout keeps the life segment
  each row was already attached to.** The upgrade knew the segment's id — the old row
  carried it — but wrote only the name and let a later step look the id up again from
  that name. If two life segments' names differed only in capitalisation, the lookup
  could not choose between them, so the row was left unlinked and reported as needing
  a human decision that the data had already made. The upgrade now keeps the id it
  was given, and still leaves a row unlinked when it genuinely points at a segment
  that no longer exists — or when two old rows collapse into one and disagree about
  which life segment they meant, which is reported for a person to settle rather than
  decided in favour of whichever row happened to sort first.

- **Renaming anything no longer breaks a link.** A segment, sub-segment, category,
  vision element key field, Project or Weekly Tactic can be renamed and every link
  survives. Renaming a segment used to make an ordinary date change on a filed Action
  Item **raise** — the item silently did not move — because the re-filing cascade
  resolved the segment by name, and `rename_vision_segment` updated only one of the
  two tables holding that name. Renaming a key field made the next assignment build a
  **second** Annual Initiative and Quarter Initiative for the same plan element,
  which accumulated silently.

  Four nullable id columns now hold those links (`annual_plan_elements` and
  `annual_vision_elements` gain `segment_description_id`, `vision_segments` gains one
  too, and `annual_initiatives` gains `annual_plan_element_id`). A migration backfills
  them from the current name once, at first launch. **It never guesses**: a row whose
  name matches nothing — or matches two segments differing only by case — is left
  unlinked and named in the report, because a wrong link is invisible where a missing
  one is not.

  Names are still shown, and a rename now refreshes every stored copy, including the
  Annual Initiative's derived title — unless you have edited that title yourself, in
  which case it is left alone.

  A user who has already renamed gets a report at startup naming every plan element
  with no resolvable segment, every orphaned initiative and every duplicate pair.
  Nothing ambiguous is repaired automatically: which of two duplicates holds work
  worth keeping is not a decision the app should make.

- **The test suite no longer has to steal keyboard focus.** Three tests build a real
  on-screen window to read geometry. `GETMOREDONE_NO_MAPPED_WINDOWS=1` now skips them, with a
  skip reason naming the variable so a suppressed run cannot be mistaken for a passing one.
  It is opt-in and `tests/test_ci_contract.py` asserts no workflow ever sets it.

- **A Weekly Tactic can no longer be filed under a Project**, which was never
  intended — the item editor already refused, the Projects screen's "Link Action
  Items" dialog did not. Filing one under a project with no Annual Plan Element
  stripped the tactic's own, leaving a row the app then refused to save.
- **The item editor no longer says "Saved" when it saved nothing.** If the item was
  deleted elsewhere while its editor was open — from a list, or a second editor
  window — Save reported success, closed the window and discarded every edit. It now
  says the item no longer exists and stays open.
- **A search in "Link Action Items" no longer leaves items selected that you cannot
  see.** Typing in the search box rebuilt the list with every checkbox cleared while
  the selection was kept behind the scenes, so "Link Selected" could re-file items
  that had scrolled out of the list entirely.
- **The item editor's Save and its Create Note both build a new item the same way.**
  They assembled the fields separately and had already disagreed twice about what a
  new item gets, so which button you pressed could change what was stored — most
  visibly the Annual Plan Element when a project and a weekly tactic were chosen
  together.
- **A Weekly Tactic left mid-week is now repaired instead of surviving forever.**
  When a tactic could not be moved onto its week start — because a duplicate
  already held that date — it was left where it was and never merged, because
  the dedupe grouped tactics by their raw start date. It now groups by the week
  a tactic belongs to, merges the duplicate, and moves the survivor onto the
  week start. The migration log says how many were moved.
- **Startup can no longer be blocked by an unreadable date.** A week item whose
  start date is not a date used to be able to make the unique-index step raise
  out of schema initialisation, and since nothing commits before that point,
  every later launch met the same state. Such rows are now reported and left
  alone rather than merged, and the index step declines with a reason instead of
  crashing.
- **The test suite no longer touches your real data.** One test opened the live
  database and ran migrations against it; several rewrote your real
  `settings.json`. Both are isolated now, with a session-level guard that fails
  the run if the real settings file is written. No data was lost.

- **The Who field works again.** Typing in Who did nothing — no contact dropdown, no
  error — because the autocomplete read three attributes (`suggestions_hide_job`,
  `contact_suggestions_frame`, `selected_contact_id`) that nothing ever initialised, so
  the first keystroke raised inside a Tk callback, where the traceback goes to stderr and
  the app carries on. The same hole could make saving a brand-new item fail with only a
  generic error message. The state now lives on the mixin that reads it.

- **Duplicate Weekly Tactics are merged**, one per Annual Plan Element per week, and a
  unique index keeps it that way. The surviving tactic keeps whichever row held more
  children, every reference is moved onto it before the other is deleted, and its title
  is re-derived — the real duplicate in the wild was titled `W8` for a week that is
  ISO week 9, so keeping the older row alone would have kept a wrong number.
- **A Weekly Tactic that cannot move now says so.** Only one tactic can occupy a week
  for a plan element, and a move onto an occupied week used to be reported as a clean
  save while nothing happened. The Today, Upcoming, All Items and Reschedule surfaces
  now tell you, and the reschedule history records where the item actually landed
  rather than where it was asked to go.
- **The weekly-items drag path reports what happened.** Dragging a plan element onto a
  week that already had a tactic produced no refresh, no message and no sign of
  rejection; the same drag with no week selected did nothing at all.



- **Two release-workflow steps could have succeeded while publishing nothing.**
  `actions/upload-artifact` defaults `if-no-files-found` to `warn`, and
  `softprops/action-gh-release` defaults `fail_on_unmatched_files` to `false` — so a
  glob matching nothing would have produced a green run with a missing artifact, or a
  public Release with correct notes and zero downloadable assets. Both now fail. The
  two are not equally strict — `if-no-files-found` fires only when a step's whole path
  set matches nothing, while `fail_on_unmatched_files` is per-pattern.

### Added

- **The release workflow can now sign and notarise the macOS build**, which removes the
  Gatekeeper prompt entirely. It is off until six Apple credentials are configured as
  repository secrets, and skips itself cleanly when they are absent — see
  `docs/CODE_SIGNING.md`. With credentials present, any signing failure fails the build
  rather than quietly publishing an unsigned one.

### Changed

- **Changing the project on an item that sits on several boards now asks first.**
  Filing is exclusive, so it removes the others; that used to be visible only as
  the "(+N more)" marker quietly disappearing. The project picker also says that
  filing an item files it under the project's Annual Plan Element.
- **The Context box is gone from the Item Editor, and the Context column from Today,
  Upcoming, All Items, Completed and Hierarchical.** Context was never a field of its
  own — only the front half of the Title string, rejoined on save — and it only read
  back out of titles whose prefix ended in a week marker (`W8`), so most items showed
  it empty while their title still carried the prefix. Title now holds and saves the
  whole title verbatim; no stored title changes. The Scheduler still colours rows by
  segment and subsegment, which is derived from the same title prefix.

- **The item editor's Duplicate button is gone; Add Follow-up is the one copy path.** A
  follow-up is a copy that also keeps the link back to the original, and it now saves the
  edits on screen before copying — a guard the Duplicate path had and the follow-up path
  did not, so a follow-up used to be built from the stored row while on-screen edits were
  left behind.
- **Item editor buttons re-paired**: Cancel sits beside Timer, Add Follow-up beside Add
  Subtasks (renamed from "Add Sub-tasks"), Set Parent beside Show Related, and Set Wk Tactic
  beside Set Project.
- Gatekeeper instructions now lead with the macOS 15 (Sequoia) System Settings route.
  Apple removed the Control-click override in macOS 15, so the old advice was wrong for
  every current Mac.
- All GitHub Actions moved off the deprecated Node 20 runtime: `actions/checkout` v7,
  `actions/setup-python` v7, `actions/upload-artifact` v7,
  `softprops/action-gh-release` v3.

## [0.2.0] - 2026-08-18

The first release whose binaries actually run.

Versions v0.1.0, v0.1.2 and v0.1.05 (February 2026) shipped binaries that
crashed on launch before showing a window — see "Fixed" below. This release
skips to 0.2.0 rather than reusing a version number that already has a
published release.

### Added

- **Downloadable builds for macOS and Windows**, published on the Releases page
  with a SHA-256 checksum beside each archive.
- **`LICENSE`** — proprietary and source-available: free to use, copyright
  retained, redistribution and commercial use reserved.
- **`THIRD_PARTY_NOTICES.md`** — every runtime dependency with its licence, plus
  the pygame LGPL notice and relink statement. A verbatim copy of the LGPL ships
  with the application.
- **`INSTALL.md`** — download, the macOS Gatekeeper step, run-from-source,
  checksum verification, optional Google and music setup, where data is stored,
  and how to uninstall.
- **`run.py --selftest`** — a headless startup check (resources, themes, theme
  application, database) that exits non-zero when a build is broken. CI runs it
  against the packaged binary on both platforms, so a bundle that cannot start
  never becomes a release.
- **Test CI** (`.github/workflows/tests.yml`) — the full suite on Python 3.11,
  3.12 and 3.13, headless under xvfb so the GUI tests genuinely run.

### Fixed

- **Every previously built binary crashed on launch.** `GetMoreDone.spec`
  bundled only `assets/`, while the app loads its colour theme from
  `themes/`, so packaged builds died with `FileNotFoundError` before showing a
  window. Themes are now bundled, and a broken bundle degrades to the built-in
  theme instead of crashing.
- **Windows builds were never verified.** The release workflow now runs the
  packaged executable's selftest on a real Windows runner before publishing.
- Two test files passed only when collected after another file that happened to
  set up `sys.path` first; run alone they errored.
- `build_mac.sh` fell back to the system Python when no virtualenv was present,
  then invoked `./venv/bin/pyinstaller` regardless — the fallback could never
  have worked.
- An unknown or corrupt theme name in `settings.json` could raise during
  startup, before any window existed to report it.

### Changed

- **The download is 68 MB instead of 160 MB.** PyInstaller was bundling a
  Google API discovery document for every Google API in existence — 569 files,
  around 93 MB — while the app uses exactly two of them.
- **The date picker no longer uses `tkcalendar`**, which is GPLv3 and cannot
  ship inside a binary under this licence. It is reimplemented on Python's
  standard `calendar` module, keeps the same interface, honours the
  first-day-of-week setting, and now follows the active theme instead of
  hard-coded colours.
- The Google auth diagnostic moved from `test_auth.py` at the repository root to
  `tools/diagnose_google_auth.py`. It was never a test.
- Root-level test files moved under `tests/`.

### Known limitations

- **Builds are unsigned.** macOS requires a one-time quarantine step, documented
  in `INSTALL.md`; Windows may show a SmartScreen warning.
- No Linux binary. Linux runs from source.
- No auto-update. New versions are downloaded manually.
- No bundled music. Point Settings at a folder of your own.

[Unreleased]: https://github.com/dbgnvan2/daVIPA/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/dbgnvan2/daVIPA/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/dbgnvan2/daVIPA/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/dbgnvan2/daVIPA/releases/tag/v0.2.0
