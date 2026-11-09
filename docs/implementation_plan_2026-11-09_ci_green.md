# Implementation plan — a green CI run (CIG, 2026-11-09)

**Status: approved under the standing instruction and built the same day.** The
user's instruction on 2026-11-09 was "proceed on your own recommendations as I'm
going to be away. Push so that local and github main are in sync. you can then
start on open items." That is the approval the global planning rule requires;
it is recorded here rather than assumed, and no part of this plan was built
before it was written.

## 0. Why this is one batch, and why it is first

`main` is red. Run 42586742228 at `1eb6ef4`: **9 failed, 2646 passed, 2
skipped** on each of Python 3.11, 3.12 and 3.13. The same nine failed at
`a2c3124` before the SST batch (run 42574953009, 9 failed, 2635 passed), so
nothing in that batch caused them and nothing in it fixed them.

`~/.claude/CLAUDE.md` is explicit about what this costs: "A red build you have
learned to ignore is worse than no CI. Fix a flaky workflow or delete it; never
leave one failing as background noise." Nine failures that have survived
several batches are exactly that. It goes ahead of `SST-A3`, which is a high
but is about a guard being narrower than its subject, not about the suite being
unreadable.

The nine are one batch because seven of them share a single cause, and the
remaining two are each one edit. `WTP-A11` in `BACKLOG.md` filed the shared
cause; this plan closes it.

## 1. Measurements taken before planning

All nine, with the file and line CI reports, from run 42586742228's 3.11 job:

| test | file:line | reported |
|---|---|---|
| `test_t51_a_modal_drops_the_timers_always_on_top` | `tests/test_timer_session_endings.py:218` | the precondition did not take |
| `test_t52_the_timer_is_topmost_again_afterwards` | `tests/test_timer_session_endings.py:253` | the timer never got its always-on-top back |
| `test_t56_a_second_modal_does_not_hand_the_flag_back_early` | `tests/test_timer_session_endings.py:438` | precondition |
| `test_t57_an_unbalanced_resume_does_not_break_the_next_modal` | `tests/test_timer_session_endings.py:478` | precondition: back to where we started |
| `test_wt_m6b6_a_notice_lowers_an_always_on_top_parent` | `tests/test_weekly_tactic_surfaces.py:703` | precondition: the parent is always-on-top |
| `test_alpha_still_passes_through_the_attributes_wrapper` | `tests/test_tk_offscreen.py:359` | the attributes wrapper swallowed -alpha |
| `test_raw_tkinter_windows_are_hidden_and_registered_too` | `tests/test_tk_offscreen.py:484` | `assert 1.0 == 0.0` |
| `test_updm14_zero_width_body_is_a_noop` | `tests/test_unified_panel_design.py:1090` | `assert 1208 <= 8` |
| `test_pbm61_a_tall_row_keeps_its_two_lines_together` | `tests/test_plan_screen.py:3712` | the row lost a label |

### 1.1 Seven of the nine measure a display capability, not the code

`.github/workflows/tests.yml` runs the suite under `xvfb-run -a`. Xvfb is an X
server with **no window manager**, so `wm attributes -topmost` is a request
nothing fulfils there: set it and the read-back returns the default.

**Corrected 2026-11-09 by the cold pass over this batch.** The first version of
this section said the same of `-alpha`, and that is false. Two `-alpha`
read-backs in `tests/test_tk_offscreen.py` — at `:236` and `:281`, inside
`test_a_remapped_window_is_made_transparent_again` and
`test_a_mapped_window_is_invisible_but_still_measurable` — run on CI and pass
there, and `conftest.py:859-880` records that they were made green *by CI
measurement*. What distinguishes them from the two that fail is that they take
the `mapped_windows` fixture and so map and settle their window first. So Xvfb
does report `-alpha`; what it does not report it for is a window that was never
mapped. The probe asks that narrower question, and `CIG-A2` files the better
fix for the two failing tests: map their windows and keep asserting on CI.

Five of the seven fail on a **precondition** line — the test sets
always-on-top itself and asserts it took, before exercising any application
code. Two fail on `-alpha`, which `conftest` uses to keep test windows
invisible.

This repo already has the pattern for it, written for exactly this reason:
`tests/test_weekly_tactic_completion_widgets.py:398-428` defines
`_TOPMOST_ON` and skips with "this display does not honour -topmost (no window
manager), so the restore this test measures cannot be observed on it". That
skip is why the suite reports 2 skipped rather than 10 failed. The pattern was
never applied to the other seven.

**Measured, not assumed:** all seven pass on this machine, where macOS honours
both attributes. None of the seven takes the `mapped_windows` fixture, so none
is affected by `GETMOREDONE_NO_MAPPED_WINDOWS=1` — they run here and they run
in CI, and the only difference is the display.

### 1.2 `test_updm14_zero_width_body_is_a_noop` relies on a resize propagating

The test builds a body 1208px wide, lays it out, then shrinks it with
`body.configure(width=body_width)` and asserts `body.winfo_width() <=
SPLITTER_WIDTH`. CI reports `assert 1208 <= 8`: the allocated width did not
change. The body is gridded directly into the root with `grid_propagate(False)`
and the root is withdrawn, so what the body is *allocated* follows the root's
own geometry, and a withdrawn root's geometry does not shrink to a child's new
request on X11 the way it does here.

This is a test-side defect, not an application one: `split_panel` reads
`winfo_width()` and the test never got the narrow width it meant to feed it. On
this machine the test passes while proving what it claims; on CI it fails
without reaching the code under test.

### 1.3 `test_pbm61_a_tall_row_keeps_its_two_lines_together` outlived its premise

It looks for a label whose text is exactly `"already blocked"`. There is no
such label: `PD_BLOCKED_TEXT` is `"✓"` since PD-M9, which put the marker
in **a column of row 0** rather than on a second line, with the reason recorded
at `src/getmoredone/screens/plan_blocks.py:404-409` ("A glyph rather than the
words it replaced, which cost the row a second line"). The test's own docstring
still describes the second line as the blocked marker.

So the row has one line of text, and the inter-line gap the test measures does
not exist. Under this repo's test rules both (b) *the behaviour changed
intentionally* and (c) *the test was over-specified* apply, and the criterion
itself is unaffected: the PB-M6.1 bullet in the 2026-11-06 walk section of
`docs/spec_coverage.md` stated it as two lines of text at the top with the
slack at the bottom (`grep -n 'slack at the bottom' docs/spec_coverage.md`),
and the surviving, measurable half of that is **the text at the top**. That
bullet is corrected by this batch too, because the bullet three above it
already records PD-M1 moving the length onto the task's one line, so one
document was holding both readings.

This is the one of the nine that `GETMOREDONE_NO_MAPPED_WINDOWS=1` hides on
this machine: it takes `mapped_windows`, so it is one of the 22 skipped here and
has only ever run in CI.

### 1.4 What is not in scope

The two `-alpha` tests are about `conftest`'s own window-hiding wrapper, not
about application code.

**Also corrected by the cold pass:** the first version added "so skipping them
there costs no coverage of the application", and that was wrong twice over.
`test_raw_tkinter_windows_are_hidden_and_registered_too` is the only test in
the suite that drives a raw `tk.Tk` and `tk.Toplevel` through the guard — WL-5's
entire subject, the bug where the patch covered only the CustomTkinter classes
— and its registration and withdraw assertions hold on any display. The
precondition was placed above them, which took all of it off CI. They are now
asserted first and only the `-alpha` read-back is behind the precondition. And
per §1.1, the read-back itself is assertable on CI with a mapped window, which
is `CIG-A2`.

## 2. Acceptance criteria → tests

Spec IDs are this plan's own, `CIG-M*`, and every test name carries the ID it
verifies.

| ID | criterion | test |
|---|---|---|
| CIG-M1.1 | One shared probe reports whether a window this display never maps still reports `-topmost` back, computed once per session against a real window and cached | `tests/test_display_capabilities.py::test_cigm11_cigm12_the_probe_agrees_with_the_display` (parametrised; one test covers M1.1 and M1.2, which is why the name carries both IDs) |
| CIG-M1.2 | The same for `-alpha` | same test, the `-alpha` parameter |
| CIG-M1.3 | The probe is a precondition, not a silent pass: a test that needs the capability and does not have it is **skipped with a reason naming the attribute**, never reported green | `tests/test_display_capabilities.py::test_cigm13_the_precondition_skips_rather_than_passing` |
| CIG-M1.4 | The five always-on-top tests and the two `-alpha` tests use the shared precondition, and the one place that already had its own copy uses it too | `tests/test_display_capabilities.py::test_cigm14_every_display_dependent_test_uses_the_shared_precondition` |
| CIG-M1.5 | On a display that does honour the attributes, every one of those tests still runs and still asserts what it asserted before — the precondition must not become a way to skip on this machine | `tests/test_display_capabilities.py::test_cigm15_the_precondition_does_not_skip_where_the_attribute_works` |
| CIG-M2.1 | `test_updm14_zero_width_body_is_a_noop` forces the one number the code reads — `body.winfo_width()` — rather than resizing a real widget and hoping every display agrees | `tests/test_unified_panel_design.py::test_updm14_zero_width_body_is_a_noop` |
| CIG-M2.2 | That test still fails loudly if the narrow reading does not take, rather than dropping the precondition | same test — the precondition assertion stays, against the stub |
| CIG-M3.1 | PB-M6.1's row test measures the surviving design: the row's text sits at the top and the slack is below it | `tests/test_plan_screen.py::test_pbm61_a_tall_row_keeps_its_slack_below_its_text` |
| CIG-M3.2 | The rewritten test fails on the defect PB-M6.1 was written for — a title centred in the row's slack | proved by mutation, recorded in `docs/spec_coverage.md` |
| CIG-M4.1 | `conftest`'s documented count of tests that build real windows stays true after the rename in CIG-M3.1 | `tests/test_ci_contract.py::test_the_documented_mapped_window_count_is_the_real_one` (existing) |
| CIG-N1 | **Not code-testable here:** that CI is green. No test can assert the state of a GitHub run from inside the suite. Verified by run id, recorded in the handoff note. | human-verified |

## 3. Implementation order

1. **CIG-M1** — `tests/display_capabilities.py` (the probe) and
   `tests/test_display_capabilities.py` (its own tests), then the seven call
   sites. The probe first, because the call sites import it.
2. **CIG-M2** — one test, no dependency on step 1.
3. **CIG-M3** — one test, renamed; run `tests/test_ci_contract.py` after it
   because the mapped-window count reads test names.
4. Sweep: at most 2 warm passes, at least 1 cold, per `CLAUDE.md`.
5. Push, then read the CI run and record its id. CIG-N1 is only closed by a
   green run, not by the plan.

## 4. Risks, and one rejected option

- **A skip is less coverage than a pass.** On CI these seven assertions will no
  longer run at all. That is honest rather than new: they do not currently
  measure the code there either, they measure Xvfb. The alternative considered
  was to replace each read-back with a spy on `wm attributes` so the call is
  asserted without a window manager. Rejected for the five always-on-top tests
  because the comment at `tests/test_timer_session_endings.py:205-207` says the
  read-back is deliberately "past the patch in both directions, so the
  measurement is of the code and not of conftest" — a spy is the measurement
  that comment rejects. Rejected for the two `-alpha` tests because what they
  guard is `conftest`'s wrapper keeping windows invisible on a developer's
  screen, which a headless runner does not have.   **Both rejections leave the
  mechanism proved on a desktop only, and that is recorded in
  `docs/spec_coverage.md` against CIG-M1, not left implicit.**

  The cold pass pointed out that this is a preference stated as a constraint:
  `tests/test_reward_protocol_timer.py:2040-2065` already spies on
  `wm attributes` with a stub window, and `_suspend_topmost` /
  `_resume_topmost` are a depth counter whose only display dependence is one
  read. T5.6 and T5.7 guard a reported bug and now have no CI coverage at all.
  That is `CIG-A3`, filed rather than built here, because it is a second design
  for tests this batch is already rewriting and the budget's reason for a cap
  applies to it.
- **The probe could itself be wrong on a third platform.** It is computed from
  a real window rather than from `sys.platform`, and CIG-M1.1/M1.2 assert the
  probe agrees with what the display reports, so a wrong probe is a red test,
  not a silent skip.
- **CIG-M2's fix was twice built on a cause nobody had measured.** A
  fixed-width holder was withdrawn when the body turned out to report 1px
  whatever the holder did, and cancelling the root's `wm geometry` was
  withdrawn when the cold pass pointed out that `_root()` sets the root to
  1400x900 and 1208 is the body's *own* request, so the root's geometry is not
  what the body follows. The X11 cause is still undiagnosed and is filed as
  `CIG-A8`. The test now forces the reading instead, which needs no diagnosis:
  mutation AE removes the stub and the precondition fails.
- **Renaming a test changes two documented counts.** `CLAUDE.md` and
  `conftest` both state the mapped-window count; CIG-M4.1 is the existing
  guard that holds them together.

## 5. Adjacent issues found, not fixed

Flagged per rule 10 rather than swept in:

1. **`tests/test_weekly_tactic_completion_widgets.py` keeps its own
   `_TOPMOST_ON`.** CIG-M1.4 moves it onto the shared probe, so this is fixed,
   not filed — recorded here because it is a file this batch would otherwise
   not touch.
2. **The suite reports 2 skipped on CI for display reasons already.** After
   this batch it will be 10 — the seven, the one that already skipped, and
   `test_cigm15_the_precondition_does_not_skip_where_the_attribute_works`,
   which skips wherever the capability is missing. The first draft said 9 and
   forgot the last of those. Nothing asserts that number, and a count that
   nobody checks is how the test figures in `CLAUDE.md` drifted. Filed as
   `CIG-A1` rather than fixed, because the right form — a test asserting *why*
   each skip happened — is a judgement about how much the suite should know
   about its own environment.
3. **No sibling to file.** I expected a family of tests in the same file
   shrinking a widget the same way, and there is none:
   `grep -c 'configure(width=' tests/test_unified_panel_design.py` prints
   **1**, the line CIG-M2 fixes. Recorded because the expectation was in this
   plan's first draft and measuring it is what removed it.
