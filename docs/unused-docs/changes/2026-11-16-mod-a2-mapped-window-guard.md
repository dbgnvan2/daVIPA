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
- Not run: the full suite. Not run: the two `<Configure>` tests in
  `tests/test_screen_resize_spc.py` and `tests/test_unified_panel_design.py`,
  which the old guard cleared by accident and the new one clears on purpose;
  neither file was changed.

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

## Next agent actions

- None blocking. `main` is green on this guard again.
- `BACKLOG.md` MOD-A3 still proposes a mapped-window check for the VPS notice
  rows. It would be the first test to *gain* the fixture since this change, so
  it moves the documented count off 29 and touches `CLAUDE.md`,
  `conftest.py` and `tests/test_ci_contract.py`. The new detector does not
  change that arithmetic.
