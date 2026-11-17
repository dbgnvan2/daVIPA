# Handoff Note

- Date: 2026-11-16
- Topic: MOD-A2 — the mapped-window guard asks for the pair, not the token

## Summary

`tests/test_tk_offscreen.py::test_every_test_that_needs_a_mapped_window_asks_for_one`
was red on `main`. It is now a per-test AST check instead of a file-level
substring search.

The guard's own docstring names the hazard precisely: `event_generate`
**followed by** `update()` deadlocks on a withdrawn window. The implementation
did not. It read each test file as text and failed any file containing
`event_generate` with no `mapped_windows` anywhere in it. That is wrong in both
directions at once, and the measurement below says so rather than inferring it.

**The false positive it was red for.** `tests/test_scheduler_column_resize.py`
has one `event_generate("<Configure>")` and no `update()`. Tk delivers a
generated event straight to the binding, so the test runs fine withdrawn — it
has been passing since `e35fc1d`. Only the guard was red.

**The false negatives it was clearing.** `tests/test_screen_resize_spc.py` does
the identical thing twice (`test_spcm4_*`, `test_spcm12_*`) and passed only
because an unrelated test in the same file, `test_spcm15_*`, happens to take
the fixture. `tests/test_unified_panel_design.py` passed on a worse accident:
its only occurrences of `mapped_windows` are inside *another guard's own
source* — a docstring and a list comprehension that scan for the word. So the
check cleared a file on a substring in code written to look for that substring.

Both of the backlog's first two options were therefore wrong. Requesting the
fixture in `test_scrm4_configure_refits` would put a real window on the screen
for a test that cannot hang, and add one to the set the documented local
workflow skips. Calling the handler directly would delete the only proof the
`<Configure>` binding exists. The third option — the guard's shape — was the
defect.

### What the new detector counts

`tests/display_capabilities.py` gains `needs_a_mapped_window(func, lookup)`,
beside `fixture_names` and for the same reason: two guards asking one question
in two places is how they come to disagree. A test needs a mapped window when,
over its own body plus every same-module helper it calls and every fixture it
requests:

- `event_generate` **and** a bare `update()` both appear, or
- any call passes `withdraw=False`, which is a test asking for a real window
  outright.

Three narrowings, each of which a mutation proves is load-bearing:

- `update_idletasks` is a different attribute and is not the pump. It runs idle
  tasks without waiting on the event queue, which is exactly why the
  `<Configure>` tests that use it are safe.
- `update` counts only when called with no arguments at all. `d.update({...})`
  on a plain dict is the same attribute name; the no-argument form is what a
  window pump looks like and what a dict update essentially never is.
- Resolution follows helpers (`_click`, `_press_target`), `self.helper(...)` on
  the class-based tests, and requested fixtures, including those defined in
  `conftest.py`. Without it, `_click`-style indirection reads as no event at
  all.

### Measurement

A probe over all of `tests/` before changing anything, so the new shape was
chosen against the tree rather than against an argument:

| | count |
|---|---|
| tests the new detector says need a mapped window | 5 |
| of those, already requesting `mapped_windows` | 5 |
| tests requesting `mapped_windows` | 29 |
| of those, needing it for the event hazard | 5 |

The five are the four real-event tests in `tests/test_plan_screen.py` and
`test_real_grip_events_pin_on_upward_drag` in `tests/test_today_pin_drag.py`.
The other 24 hold the fixture for the geometry reason — `winfo_width()` returns
1 on a withdrawn window — which the guard has never demanded and still does
not. **No test gained or lost the fixture, so the documented count stays 29**
and `CLAUDE.md`, `conftest.py` and `tests/test_ci_contract.py` are untouched.

## Files changed

- `tests/display_capabilities.py` — `needs_a_mapped_window`, `_markers`,
  `_reachable`, `bare_calls`, `module_functions`, `test_functions`
- `tests/test_tk_offscreen.py` — the guard rewritten; a new guard on the
  detector; the module docstring now states the fixture's second purpose
- `tests/test_ci_contract.py` — `_mapped_window_test_count` and the
  both-guards test brought onto the widened reader
- `tests/test_display_capabilities.py` — the third reader of the fixture
  request, brought onto the same call
- `BACKLOG.md` — MOD-A2 removed, MOD-A7 filed
- `docs/spec_coverage.md`, `docs/DOCUMENTATION_INDEX.md` — the row and the
  entry for this note

## The first cold pass, and what it changed

A `learning-qa` pass over the two commits above, run cold — a fresh reviewer
with none of the context that wrote them. Four findings, one of them
demonstrated rather than argued, and all four fixed here. The pass is the
reason this note has a second half: the first version of the detector shipped
with a hole of exactly the kind it was written to close.

**1 (high, P2) — the walk started from a name, not from a node.** `_reachable`
seeded itself with `todo = [func.name]` and then looked that name up in the
lookup. `module_functions` keys by bare name, so two classes in one module that
give a method the same name make the lookup hold only one of them — and the
walk then answered the question about the *other* body. Reproduced before
fixing: two classes, one method name, the hazardous one generating an event and
pumping, and `needs_a_mapped_window` returned `False` for both. Renaming one
method returned `True`. A silent pass, which is the single direction this guard
must not fail in.

Worse than the bug: the docstring on `module_functions` asserted that a
collision "can only widen what the caller sees ... never a silent pass". True
of a *callee*, false of the subject of the question, where the lookup replaces
it. So the code had a hole and the comment told the next reader not to look for
it. Both are fixed — `_reachable` now takes its markers from the node it was
handed, and the docstring says what was wrong with it and when.

Latent today: 0 name collisions across the suite's test functions. But 149 test
classes hold 186 methods, so two classes in one file sharing a method name is
an ordinary thing to write, and nothing failed when someone did.

**2 (medium, P3/P5) — a `usefixtures` mark on a class was invisible.** pytest
applies a class's mark to every method on it; `fixture_names` read only the
function's own parameters and own decorators. Both directions broke, and one
silently: a class marked with a window-mapping fixture read as needing nothing,
while a hazardous method in a class marked `usefixtures("mapped_windows")` read
as an offender and would have sent the author to add a parameter the mark
already supplies.

`fixture_names` now takes the enclosing classes, `test_functions` returns them
with each test, and `usefixtures_names` is split out because a `ClassDef`
carries the same mark and has no parameters to read.

**This one reached a sibling.** `_mapped_window_test_count` in
`tests/test_ci_contract.py` reads the same `fixture_names`, so fixing only the
guard would have left the count of 29 unable to see a request the guard can —
the exact divergence `tests/display_capabilities.py` exists to prevent, and
that `test_the_fixture_request_is_read_the_same_way_by_both_guards` was written
to catch. The counter and that test's synthetic source were changed in the same
commit. The count is still 29: no class in the suite uses the mark.

**3 (medium, P3/P6) — the shared-fixture arm read one hard-coded file.** The
guard parsed `conftest.py` beside `tests/` and nothing else, while pytest
resolves a conftest chain. The arm also contributes nothing to the live tree —
no function in the root `conftest.py` carries a marker, and all five tripped
tests trip on their own bodies — so it could have broken without a single test
noticing. It now looks for both conftests pytest would apply and asserts it
found at least one.

**4 (medium, P2/P9) — the guard reported offenders and nothing else.** A
detector that stops detecting produces zero offenders and a green run. The
first round's mutation proved the guard can still see an offender among tests it
*already* detects; nothing proved it would notice if it stopped detecting them.
`DRIVES_REAL_EVENTS` now names the five, exact and not a floor, the way the
count of 29 is named — and mutation F4 below is that scenario made to happen.

### Adjacent issues found, not fixed

- `tests/test_unified_panel_design.py:2782`
  `test_updm71_no_test_here_needs_a_mapped_window` reads
  `[arg.arg for arg in node.args.args]` directly rather than through
  `fixture_names`, so it misses the keyword-only and both mark spellings. It is
  a file-local assertion of zero, pre-existing, and untouched by this change.
  With the third reader found by the second pass below, it is the fourth place
  this one question is asked and the only one that does not go through the
  shared helper at all. Filed as `BACKLOG.md` MOD-A7 rather than swept in.

## The second cold pass, and what it changed

The four fixes above are themselves the least-reviewed code in this change, so
they got their own cold pass. Three more findings, **every one of them a silent
pass** -- the direction a hung suite fails in, naming nothing. Each was
reproduced before being accepted and each is fixed here.

**1 (medium) -- the amended docstring was still wrong, and the hazard it denied
was real.** The fix for the first pass's finding 1 left `module_functions`
claiming that a collision on a *callee* "can only widen what the caller sees".
It is the opposite: the lookup kept one node per name, so the body that lost
the collision was discarded, markers and all. Reproduced -- a harmless
module-level `_click` shadowing a hazardous `TestA._click` gave `False` for a
test that calls it. `module_functions` now returns a **tuple of every body** of
that name and `_reachable` unions over them, so a collision widens instead of
narrowing; `merge_functions` does the same when the conftest lookup and the
module lookup are combined, where `{**a, **b}` had been dropping `a`'s bodies.

This is the second round in which a comment in this module asserted a hazard
away that took ten lines to reproduce. Both claims are recorded in the
docstring with their dates, because the comment is what stops the next reader
looking.

**2 (medium, P5) -- there was a *third* reader of the fixture request, not
two.** `tests/test_display_capabilities.py:184` calls `fixture_names(node)` on
its own, and the first pass's widening left it on the narrow call. It would
have reported a test guarded by a class mark as unguarded -- precisely the
divergence `tests/display_capabilities.py` exists to prevent, one function
below the docstring that said there were two. It now passes the enclosing
chain, like the other two.

Three written claims rested on "two", and all three were corrected in the same
change: the `fixture_names` docstring, the `docs/spec_coverage.md` row, and
`BACKLOG.md` MOD-A7's "the third spelling".

**3 (medium) -- a module-level `pytestmark` was invisible.** `usefixtures_names`
read `decorator_list`, which a `Module` node does not have, so
`pytestmark = pytest.mark.usefixtures(...)` contributed nothing. **Ten test files
here already mark a whole file that way**, so this is the house spelling, not a
corner. Reproduced: a module given a window-mapping fixture by a module mark
read as needing no window. `usefixtures_names` now reads the assignment, a
list or tuple of marks included, and `test_functions` puts the module at the
head of the enclosing chain.

**4 (low) -- a claim in this note was overstated**, and is corrected below:
mutation 5's redness is not isolated to `DRIVES_REAL_EVENTS`.

**5 (medium, P24) -- found by the gate, not by a reviewer.** Two of the three
fixes above had no assertion anywhere, and a third was pinned only by accident
of `ast.walk` order. The mutation gate is what surfaced that, which is the
argument for running it on a fix batch rather than treating it as ceremony;
the first attempt's verdicts and what was wrong with each are under
Verification.

No third review pass. This repo's rule is that a further pass is earned only by
a high-severity finding, and this one produced mediums; the fixes get the
mutation gate instead.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_tk_offscreen.py tests/test_ci_contract.py tests/test_display_capabilities.py tests/test_scheduler_column_resize.py -q --timeout=300`
- Result: PASS — 144 passed, 6 skipped. The red is gone and the documented
  count still reconciles.
- Mutation gate, all three RED, each file restored byte-identical (SHA-256
  checked, not assumed):
  1. drop `mapped_windows` from `test_real_grip_events_pin_on_upward_drag`'s
     signature → the guard fails. It can still see a real offender.
  2. `needs_a_mapped_window` back to the token alone → the detector's guard
     fails. The pair is what is being asked for.
  3. `_reachable` stops extending through `bare_calls` and `fixture_names` →
     the detector's guard fails. Helper resolution is not decoration.
- After the cold pass's fixes — PASS: `tests/test_tk_offscreen.py`,
  `tests/test_display_capabilities.py`, `tests/test_ci_contract.py`, 133 passed
  and 6 skipped, so the count of 29 still reconciles with the widened reader.
- Second mutation gate, all five RED, each file restored byte-identical:
  1. `_reachable` seeded by name again → the detector's guard fails on the
     collision arm.
  2. `fixture_names` ignoring the enclosing classes → the detector's guard
     fails on the class-mark arms.
  3. the same mutation against
     `test_the_fixture_request_is_read_the_same_way_by_both_guards` → fails, so
     the counter's reader is covered too.
  4. the conftest candidates pointed at a file that does not exist → the new
     assertion fires, rather than the arm reading nothing in silence.
  5. `_PUMP_CALL` changed to match nothing → red. Finding 4's scenario, made
     to happen, with one claim corrected: `offenders` does stay empty, but the
     detector's own guard reddens on the same mutation, so the
     `DRIVES_REAL_EVENTS` set is *a* thing that catches it and not the only
     one. What the set uniquely covers is a narrowing the synthetic module has
     no arm for.
- Third mutation gate, on the second pass's fixes. **Its first attempt is the
  reason this batch grew three arms**: it came back three GREEN and one RED,
  and all four verdicts were wrong in a way worth writing down, because a
  mutation gate that reports a fix as covered when it is not is the same
  failure as the guard it is gating.
  - `M1` kept the LAST body of a colliding name. `ast.walk` happens to yield a
    class's method after a module-level function of the same name, so the
    hazardous body survived the mutation and nothing failed. The verbatim
    original is "one body per name, **module level winning**"; written that
    way it is red.
  - `M2` and `M4` were GREEN because nothing asserted on the fixes at all.
    `merge_functions` had no arm, and the one existing mark arm in the
    read-back detector's cases spells the mark as a decorator **on the
    function**, which `decorator_list` carries either way — so putting that
    reader back on the narrow call could not fail. Three arms added, named
    below.
  - `M3` was RED on `AttributeError: 'Module' object has no attribute
    'decorator_list'`. The mutation made the module branch unreachable and the
    `else` then ran against a `Module`. A crash is not the guard detecting
    anything, and counting it as RED is a false pass for the gate itself; the
    gate now requires the failure to name an assertion, and the mutation
    leaves the branch running with a name nothing assigns.
- Third mutation gate, second attempt — baseline green first (13 passed), then
  **all four RED**, each on a named assertion, each file restored
  byte-identical:
  1. `module_functions` back to one body per name with module level winning →
     the detector's guard fails, having lost
     `TestCollidingNameHazardous.test_through_a_shadowed_helper`.
  2. `merge_functions` dropping the earlier lookup's bodies → the new
     collision assertions fail, in both orders.
  3. the module mark's name changed to one nothing assigns → the module-mark
     arm fails. Behavioural, not a crash.
  4. the third reader back on the narrow call → the two new read-back arms
     fail.
- Arms and assertions added for the three unguarded fixes, one per finding:
  a class-mark and a module-mark read-back case in
  `tests/test_display_capabilities.py`, and assertions on `merge_functions`
  and `module_functions` themselves in `tests/test_tk_offscreen.py` — on the
  functions that resolve a collision, rather than on an arm that happens to
  exercise one, because which body wins an `ast.walk` collision is incidental.
- Two failures in the guard run of the three files are **the concurrent
  session, demonstrated not inferred**:
  `tests/test_display_capabilities.py::test_cghm43_the_display_dependent_count_is_exact`
  scans every `tests/test_*.py` from disk at test time, and two of the four
  files it counts were being rewritten mid-run; computed again on the settled
  tree it gives `len(asks) == 4` with `asks <= reads`, which is what it
  asserts. `test_meta_marker_covers_exactly_the_repo_assertion_files` timed out
  at 300s in a whole-suite collect subprocess, the same contention that timed
  out three of them earlier the same day, with both runs' pids observed
  overlapping.
- Measured, not reasoned: the two withdrawn `<Configure>` tests in
  `tests/test_screen_resize_spc.py` complete in 3.79s rather than hanging,
  which is the premise the whole fix rests on.
- Not run: the full suite. Not run: `tests/test_unified_panel_design.py`, whose
  `_click` the new guard clears on purpose; the file was not changed.

## Risks / Known gaps

- **A helper imported from another test module is not resolved.** `lookup` is
  built from the test's own module and `conftest.py`, which is where this
  repo's shared fixtures live. A hang reached through an import would be found
  by waiting for a timeout, as before. No such helper exists today; nothing
  stops one being written.
- **A guard that over-reaches now fails loudly, naming the test.** That is the
  direction the narrowings err in deliberately: a false demand is visible, a
  false clearance is a hung suite with no name attached.
- The detector reads source. It cannot see a test that hangs for a reason other
  than these two.
- **A helper reached as `harness.click(...)` or `Cls.helper(...)` is not
  followed.** `bare_calls` follows plain names and `self.x(...)`. Checked by
  widening the walk to follow any `obj.attr(...)` whose attr is a module
  function and re-running over all of `tests/`: 0 additional tests trip, so
  this is latent.
- **`update()` is the only blocking call modelled.** `wait_visibility`,
  `wait_window` and `mainloop` also block on a window that is never mapped.
  Not live — `wait_window` appears in `tests/` only as a name being
  monkeypatched out.
- **`_ON_PURPOSE` reads as a knob and is not one.** `_markers` tests the
  hardcoded `keyword.arg == "withdraw"` against the constant `False`, so
  editing the string changes nothing, and `withdraw=0` or `withdraw=flag` do
  not match.
- **An arm that depends on which body wins a collision is not a guard.** The
  shadowed-helper arm reddens only while `ast.walk` yields the hazardous body
  last. The assertions on `merge_functions` and `module_functions` do not
  depend on the order; the arm is kept because it is the shape a real test
  takes, not because it pins the fix.
- **`usefixtures(*NAMES)` contributes no names.** The argument is a `Starred`
  node whose value cannot be resolved from the syntax, so a request written
  that way is unread — a silent pass. Surfaced rather than handled: nothing in
  this repo writes it, and resolving it means evaluating the module.
- **The synthetic module has no arm for a fixture that requests another
  fixture.** The chain is followed by `_reachable`; the depth-2 case is not
  asserted.

## Next agent actions

- None blocking. `main` is green on this guard again.
- `BACKLOG.md` MOD-A3 still proposes a mapped-window check for the VPS notice
  rows. It would be the first test to *gain* the fixture since this change, so
  it moves the documented count off 29 and touches `CLAUDE.md`,
  `conftest.py` and `tests/test_ci_contract.py`. The new detector does not
  change that arithmetic.
