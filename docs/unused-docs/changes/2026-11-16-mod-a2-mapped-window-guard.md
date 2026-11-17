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
- `BACKLOG.md` — MOD-A2 removed

## The cold pass, and what it changed

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
  a file-local assertion of zero, pre-existing, and untouched by this change —
  the third place this one question is asked. Filed as `BACKLOG.md` MOD-A7
  rather than swept in.

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
  5. `_PUMP_CALL` changed to match nothing → `offenders` stays empty and the
     `DRIVES_REAL_EVENTS` set is what turns it red. Finding 4's scenario,
     made to happen.
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
