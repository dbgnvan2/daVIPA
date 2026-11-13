# BACKLOG archive — 2026-11-13

Filed out of `BACKLOG.md` by the BSF batch, which worked the items whose entry
named the fix (`docs/unused-docs/implementation_plan_2026-11-13_backlog_small_fixes.md`).
Each item carries its closure under it. This is a filed record. No test reads it.

### ~~LMM-A1 — a block dragged onto an extended slot is refused (medium)~~ — fixed 2026-11-12

Fixed in the PBG sweep, together with a fifth call site the entry below had
claimed was fine. `move_block_to_slot` now passes `day_span=self._grid.span`
to `place_block_at`, and `set_block_length` takes a `day_span` of its own —
it had no such parameter at all, so a right-click resize of any block on a box
the drawn day added was refused `outside_grid` whatever length was asked for,
the one it already had included. Guards:
`tests/test_plan_screen.py::test_pbga8_an_ordinary_block_moves_onto_a_box_the_extended_day_drew`
and `tests/test_time_block_crud.py::test_pbga3_a_block_on_a_drawn_box_can_be_resized`.

**The completeness claim in the original entry was wrong**, and that is the
part worth keeping. It said the four other call sites got it right and "this
one is the omission". There were three more: `set_block_length` above,
`add_padding_block` (`plan.py:1316`) and AutoLoad (`plan.py:1946`). The last
two are deliberate — `template_span`'s docstring names the template as what
AutoLoad and the break button are allowed to fill — but the entry drew no line
between a deliberate omission and a defective one, which is what the next
reader would have acted on. The false docstring on
`_refuse_unless_it_fits` that made every omission look safe is corrected in
the same change.

**Closed:** Fixed 2026-11-12 (PBG sweep); the entry had been struck through and left in place.

### LMM-A2 — nothing refuses a second LUNCH block on one date (low)

`lunch_window` (`time_block_layout.py:572`) walks the date's blocks and
`return`s on the first `LUNCH` it finds. A second one is not an error, it is
simply unread: it keeps its slot, it draws, and it shades nothing. No write
path refuses it either, so a duplicate can only arrive from a bug elsewhere or
from a hand-edited database — which is why this is low rather than medium.

Fix when touched: either refuse the second write where lunch blocks are
created, or have `lunch_window` surface the duplicate rather than silently
taking the first (the "surface, never silently drop" rule, P2/P9). A silent
`return` on the first of several is the shape that hides the state.

**Closed:** Fixed 2026-11-13, BSF-M6: `add_block_at`, the only insert of a time block, refuses a second LUNCH block on a date (`SlotRefusal.LUNCH_EXISTS`).

### CGH-A1 — the `-topmost` silencer only inspects the first attribute (low)

`conftest.py`'s wrapper drops a `-topmost` write only when it is the FIRST
argument:

```python
if args and args[0] == "-topmost" and len(args) > 1:
    return None
```

`window.attributes("-alpha", 0.0, "-topmost", True)` is one call that sets
both, and it would go straight through to Tk — the hole the wrapper exists to
close, in the one shape it does not look at. An un-silenced `-topmost` during
a run forces window-server round-trips and has beachballed this machine.

Latent, not live: all six call sites under `src/` are single-attribute
(`grep -rn "attributes(" src/` → `"-topmost", True` or `'-topmost', True`),
so nothing produces the multi-attribute form today. `_RecordingTk` in
`tests/test_tk_offscreen.py` already recognises `-topmost` anywhere in the
call, so the test spy is stricter than the thing it tests.

Fix when touched: scan the argument pairs rather than `args[0]`, and drop the
`-topmost` pair while passing the rest through. Found by the third cold pass
of the CGH batch, which was reviewing the spy, not the wrapper.

**Closed:** Fixed 2026-11-13, BSF-M4: the silencer drops a `-topmost` pair anywhere in the call, and the Python 3.13 `topmost=` keyword.

### CE-A2 — `_say` prints to stdout from a GUI app (low)

`src/getmoredone/google_calendar.py::_say` writes status lines to stdout.
Same family as the fixed defect where a status `print` inside a credential
`try` discarded a valid token when the stdout write failed: a packaged app's
stdout is not guaranteed writable, and a print in a `try` makes the failure
look like the thing being tried. The export path calls it through the shared
helpers.

**Priority:** Low
**Effort:** Small

**Closed:** Closed 2026-11-13 without code: the console is the manual sign-in's interface (it ends in `input()`), and `_say` already cannot abort its caller.

### SCV-A1 — `interpolate_hex_color` slices into `int(…, 16)` with no guard (low)

`screens/drag_schedule_support.py:109-110` reads both endpoints of its gradient
as `int(s[0:2], 16)` with nothing checking them first, which is the third copy
of the parse `SCV-M1` removed from the other two. Not on the stored-colour
path — its only caller is the gradient in its own module, over theme colours —
so it is not what `LRR-A1` named, and fixing it in the SCV batch would have
been a sweep of a module nobody asked about. It will behave exactly as
`_derive_subsegment_color` did the day something hands it a stored colour.
`tests/test_segment_colour_validation.py::test_scvm11_no_hand_rolled_hex_validator_survives`
counts it, so it cannot multiply unnoticed.

**Priority:** Low
**Effort:** Low

**Closed:** Fixed 2026-11-13, BSF-M5: `interpolate_hex_color` parses through `color_contrast`.

### SCV-A3 — `_text_color_for_background` misreads the `int(…, 16)` family (low)

`color_contrast.py`'s private `_text_color_for_background` slices and parses
its argument without going through `_HEX_COLOR_RE`, so it is the third member
of the family `SCV-M1` removed from the other two. The SCV plan's §5 recorded
it as "correct already", which is wrong: it reads `#+12345` as `#0B368D` by the
same misread slice `_derive_subsegment_color` did, and answers for the wrong
background.

Left as low because the consequence is cosmetic and bounded — one text colour
on one widget, no raise and no stored value — and because every caller now
reaches it through a normalised colour, so the misread needs a new caller to
become visible. Fixing it inside the SCV batch would have meant touching the
authority module's maths for a case no live path produces.

**Priority:** Low
**Effort:** Low

**Closed:** Fixed 2026-11-13, BSF-M5: the weekly tactic dialog's text colour parses through `color_contrast`.

### CI-A1 — the apt step has no retry, so a mirror outage is a red build (medium)

`.github/workflows/tests.yml:47-48` runs `sudo apt-get update` then
`sudo apt-get install -y xvfb python3-tk` with nothing around them. On
2026-11-11 all three matrix jobs (3.11, 3.12, 3.13) died there with
`Temporary failure resolving 'security.ubuntu.com'` and
`E: Failed to fetch .../python3-tk_3.14.3-0ubuntu2_amd64v3.deb`, exit code
100, before pytest ran at all. A re-run four minutes later failed identically.
Twelve minutes of red that said nothing about the commit.

This is P1 and global rule 5 in the workflow rather than in `src/`: a
retryable network failure given a terminal result, on an external call with no
timeout, retry or backoff. The fix is retry options on the apt call
(`-o Acquire::Retries=3`, or a retry action around the step), possibly with
the two packages cached.

Not done in the SCV batch that found it: it is a change to the CI contract,
which `tests/test_ci_contract.py` asserts on, and that wants a batch of its
own rather than a workflow edit tacked onto the end of one. Found by two
sessions independently on 2026-11-11.

**Priority:** Medium
**Effort:** Low

**Closed:** Fixed 2026-11-13, BSF-M7: the apt calls retry in a loop inside a 15-minute step limit.

### 2026-11-07 - Type: Technical Debt

**Title:** UPD-A7 - two dead members in annual_vision_segments.py, by index, left by the drag that moved to rows
**Description:** `self.drag_index: Optional[int] = None`
(`src/getmoredone/screens/annual_vision_segments.py:33`) has no reader anywhere
in `src/` or `tests/` - grep returns the assignment and nothing else - and
`_create_from_index(idx)` (`:272`) has no caller: it looks the row up in
`self.left_items` by position and then calls `_create_from_row`, which is what
the drag and the button both use directly. Both are leftovers from an earlier
drag that carried a list index instead of the row. UPD-M4 did not remove them,
under the standing rule: a feature change does not silently sweep adjacent
code. They are harmless but they describe a drag the screen no longer has, and
an index-based lookup is the kind of thing a later edit reaches for. Removing
both is a two-line deletion with no test to change.
**Priority:** Low
**Effort:** Low

**Closed:** Fixed 2026-11-13, BSF-M1: both deleted.

### 2026-11-07 - Type: Technical Debt

**Title:** UPD-A8 - weekly_items.py imports tkinter and never uses it
**Description:** `import tkinter as tk`
(`src/getmoredone/screens/weekly_items.py:10`) has no `tk.` reference left in
the file - grep returns the import and nothing else. It was already unused
before UPD-M5: the screen's own splitter and drag used `winfo_*` calls on
CustomTkinter widgets, not the `tkinter` namespace. UPD-M5 did not remove it,
under the standing rule that a feature change does not silently sweep adjacent
code. A one-line deletion with no test to change; the only reason to keep it is
that a later edit in this file may want it, which is not a reason.
**Priority:** Low
**Effort:** Low

**Closed:** Fixed 2026-11-13, BSF-M2: the import deleted.

### SAG-A5 — `run()` puts a literal backslash-n in its error message (low)

`tools/agents/check_docs_sync.py::run` raises
`RuntimeError(f"Command failed: {' '.join(cmd)}\\n{result.stderr}")` — an
escaped backslash in a plain (non-raw) string, so the message carries the two
characters `\n` instead of a newline and the git error runs on from the command
line. It is the class `CLAUDE.md`'s "backslash sequences in embedded code
strings" rule covers, arriving the other way round. The message is now read by
`SAG-M2.3`'s skip line, so it is user-facing.

**Priority:** Low
**Effort:** Small

**Closed:** Fixed 2026-11-13, BSF-M3.

### SAG-A6 — a dead `docs/unused-docs/changes/` clause in the docs check (low)

`verdict` computes `docs_changed` as `path.startswith(DOC_PREFIXES) or path in
DOC_FILES or path.startswith("docs/unused-docs/changes/")`. `DOC_PREFIXES` is `("docs/",)`,
so the third clause can never be the one that matters: every
`docs/unused-docs/changes/…` path already satisfies the first. A handoff note alone
**does** satisfy the docs requirement, and `tests/test_docs_sync_rule.py`'s
fixture `(("src/getmoredone/db_manager.py", "docs/unused-docs/changes/…md"), "pass")`
asserts exactly that — so the clause is dead, and the behaviour it looks like it
adds is the behaviour the rule already has. Whether that is the right rule is a
separate question from whether the clause is reachable; this item is only about
the clause.

Filed 2026-11-09 by the first cold pass over the SAG batch, which said the
fixtures prove a note alone does *not* satisfy the requirement; they prove the
opposite, corrected by the second pass. Deleting the clause is a
behaviour-preserving edit; it is filed rather than done because the batch's rule
is that below-medium findings are not fixed in-loop.

**Priority:** Low
**Effort:** Small

**Closed:** Moot 2026-11-13: the clause was already replaced by `FILED_PREFIX`, which excludes filed records.

### SAG-A11 — `run()` has no timeout on its subprocess (low, P5)

`tools/agents/check_docs_sync.py::run` calls `subprocess.run` with no
`timeout`, so a hung `git diff` hangs the check. `~/.claude/standards/learnings.md`
P5 is the rule — timeout, retry, backoff on every external call — and the
global rules say to fix a class rather than an instance, so the sibling calls in
`tools/agents/` should be done in the same change.

Adjacent, found 2026-11-09 by the third cold pass over the SAG batch and not
changed by it (global rule 10). `SAG-A5` is the other defect in the same
function.

**Priority:** Low
**Effort:** Small

**Closed:** Fixed 2026-11-13, BSF-M3: a 60-second timeout, reported as skipped. The only subprocess call in `tools/agents/`.
