# Implementation plan — the suite's honesty about its own environment (CGH)

**Status:** draft — approved by nobody, no implementation code written.
**Written:** 2026-11-11, measured at `474e7b7`.
**Closes:** `CIG-A1`, `CIG-A2`, `CIG-A3`, `CIG-A4` (all medium), filed 2026-11-09
and 2026-11-11.
**Scope:** `conftest.py`, `tests/test_display_capabilities.py`,
`tests/test_timer_session_endings.py`, `tests/test_tk_offscreen.py`,
`tests/test_ci_contract.py`, `tests/test_settings_isolation.py`. No `src/`.

## 1. Why these four together

All four are the same defect in different places: **the suite tells the reader
something about its environment that is not true.** A guard blames a test for
what the packaged app did; two tests skip where they could assert; two more
skip because they ask a window manager for something a spy could answer; and
the guard that is supposed to catch the whole class is a hand-written list of
the eight tests that already comply.

They also interact, which is why they are one batch and not four. `CIG-A2` and
`CIG-A3` each remove two entries from
`test_display_capabilities.EXPECTED_CALLERS`, and `CIG-A1` replaces that
registry. Built separately, the registry would be rewritten three times.

Measured from the last green CI run (`43146675855`, python 3.11,
**2827 passed, 10 skipped**):

| skip | count | where |
|---|---|---|
| `-topmost` read-back | 6 | `tests/display_capabilities.py:90` |
| `-alpha` read-back | 2 | `tests/display_capabilities.py:90` |
| display does not honour `-topmost` | 1 | `tests/test_display_capabilities.py:169` |
| no music folder | 1 | `tests/test_audio.py:65` |

`CIG-A1` says "CI reports 10 skips for display reasons". It is **9**; the
tenth is the audio one. The criterion below asserts the display count, so an
unrelated skip elsewhere cannot redden it. The 6 + 2 matches
`len(EXPECTED_CALLERS) == 8` exactly, so the registry is accurate today — it is
its *form* that is the defect.

## 2. Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| CGH-M1.1 | The guard's decision is a pure function of `(before, after, app_state)` returning a verdict per key — `app_running`, `content_changed`, `timestamp_only`, `app_unknown` — and the warning text is built from the verdict. Tests assert the verdict, never the sentence | `tests/test_settings_isolation.py::test_cghm11_the_guard_verdict_is_a_function_of_the_fingerprints` — parametrised over the four cases |
| CGH-M1.2 | With the app detected as running, a timestamp-only change carries no "a test bypassed the isolation" line and does not fail the run | same test's `app_running` case, plus `::test_cghm12_a_running_app_does_not_fail_the_run` through the existing nested-pytest harness |
| CGH-M1.3 | With no app running, a content change still fails the run and still says a test may have bypassed the isolation | the two existing guard tests stay green, unmodified |
| CGH-M1.4 | Detection never raises and never hangs: an absent or slow `pgrep` yields `app_unknown`, not `content_changed` (P1 — unknown is not terminal), with a timeout on the subprocess (P5) | `::test_cghm14_app_detection_cannot_hang_or_raise` — monkeypatch the call to raise, to time out, and to return nonsense |
| CGH-M2.1 | T5.6 asserts the nesting bug against a spy window that returns the last `-topmost` written, with no `require` and no window manager | `tests/test_timer_session_endings.py::test_t56_a_second_modal_does_not_hand_the_flag_back_early` — converted, not added |
| CGH-M2.2 | T5.7 asserts the unbalanced-resume bug the same way | `::test_t57_an_unbalanced_resume_does_not_break_the_next_modal` — converted |
| CGH-M3.1 | The two `-alpha` read-backs take `mapped_windows`, drop `require`, and leave `EXPECTED_CALLERS` | `tests/test_tk_offscreen.py::test_alpha_still_passes_through_the_attributes_wrapper`, `::test_raw_tkinter_windows_are_hidden_and_registered_too` |
| CGH-M3.2 | `CLAUDE.md` and `conftest.py` each state the mapped-window count once, and it is 25 | `tests/test_ci_contract.py::test_the_documented_mapped_window_count_is_the_real_one` — exists, must stay green |
| CGH-M4.1 | A detector replaces the registry: an AST walk finds every test that reads a window attribute back on a **real** Tk window — a name bound from `ctk.CTk()`, `tk.Tk()`, `CTkToplevel()` or `Toplevel()` in that function, read directly or through a same-file helper that performs the read — and asserts the set that neither calls `require` nor takes `mapped_windows` is exactly empty | `tests/test_display_capabilities.py::test_cghm41_every_real_read_back_asks_or_maps` |
| CGH-M4.2 | The detector catches a *new* offender, which the registry cannot: a synthetic module source (parsed from a string, not a file) that reads `-topmost` back without asking is reported | `::test_cghm42_a_new_offender_is_detected` — adversarial (P7) |
| CGH-M4.3 | The number of display-dependent tests is asserted exactly, in one place, and is 4 after this batch | `::test_cghm43_the_display_dependent_count_is_exact` — an exact count, no floor |

## 3. Order, and why

1. **CGH-M1** — `conftest.py`, independent of the other three, and the one
   actively costing attention now.
2. **CGH-M2** — the spy. Locally verifiable in full, and it is the
   highest-impact fix of the three test items (two assertions regained on CI),
   so its test is the first one written (fix→test map, P10).
3. **CGH-M3** — mapping the two `-alpha` tests. Third because it is the one
   that cannot be verified here (§5).
4. **CGH-M4** — the detector, last, because M2 and M3 decide the shape it must
   assert on. First action when it is written: run it against the tree and
   report what it finds, rather than assuming the answer is "the four".

Then, in the same change (global rule 13): the `EXPECTED_CALLERS` comment block
in `tests/test_display_capabilities.py` says "A registry, not a detector … and
`CIG-A1` records that gap" — false once M4 lands, so rewrite or delete it with
the registry. `CLAUDE.md` and `conftest.py`: the count, 23 → 25. Check
`docs/spec_coverage.md` rather than assuming it needs an entry, and say in the
status report what it held. `BACKLOG.md`: delete `CIG-A1` to `CIG-A4` **last,
after the merge** — it is the chronic conflict surface.

## 4. Three decisions the plan takes, rather than leaving implicit

**T5.1 and T5.2 stay on real Tk.** They are about the attribute reaching Tk,
which a spy cannot measure; only the depth-counter pair converts. So
`EXPECTED_CALLERS` keeps two timer entries and loses two.

**App detection is `pgrep`, not the lock file.** Probing
`~/Library/Application Support/GetMoreDone/app.lock` would be cheaper and need
no subprocess, but `app.py:507` takes `flock(LOCK_EX | LOCK_NB)` and the loser
exits silently with status 0 — so a probe that holds the lock for an instant
can make a launch the user attempts in that instant vanish with no message.
A read-only guard must not be able to do that. `pgrep` with a timeout, and
`app_unknown` where it is unavailable (Windows, or a stripped container).

**A content change still fails the run even when the app is running.** For the
database key the fingerprint carries no digest (`conftest.py:77` computes
sha256 for `settings` only), so "content changed" there means the **size**
moved, which the app saving the same values does not do. Narrowing that to a
warning would weaken the guard against the thing it exists for. Only the
accusing line and the timestamp-only branch change.

> **Amended 2026-11-11, after the cold pass this plan costed in §6 — the
> decision above is withdrawn.** Its premise is false: a size comparison does
> not establish that nothing was rewritten. Measured on a throwaway SQLite
> file in `journal_mode=delete` (which is what this app runs — no
> `journal_mode` or WAL appears anywhere under `src/`), 400 in-place `UPDATE`s
> with same-length payloads moved `mtime_ns` and changed the size by **0
> bytes**. So a test escaping to the user's real database landed in the
> timestamp-only branch, where the new wording called it harmless and the run
> stayed green — the guard's own blind spot, stated as a conclusion.
>
> Replaced by two changes. **Both files are hashed**, so "its bytes are
> unchanged" is now evidence rather than an assumption (measured cost: sha256 over
> this machine's real 3.03 MB database, best of five, 1.4 ms -- twice per
> session). And because the packaged
> app *does* rewrite that database as it sits idle — the 2026-11-09
> measurement behind `CIG-A4` — hashing it would otherwise redden every local
> run with the app open, so a content change splits three ways: no app process
> found → fails the run (the escape); a packaged app process found → reported,
> green, with "re-run with the app closed to be sure"; undetermined → fails,
> because unknown is not an alibi (P1). CI has no app running, so CI still
> fails hard on any content change.
>
> `GUARD_FAILING_VERDICTS` holds the failing set and
> `::test_cghm12_a_verdict_blames_a_test_exactly_when_it_fails_the_run`
> asserts that a verdict accuses exactly when it fails, so the accusation
> cannot drift out of its branch again in either direction.
>
> The same pass found the app probe's pattern too wide:
> `daVIPA\.app/Contents/MacOS|run\.py` matched the suite's own
> `<repo>/run.py --selftest` subprocesses (`tests/test_first_run.py:174`,
> `tests/test_selftest_cli.py:34`), which resolve the user's real
> `settings.json` because they redirect `GETMOREDONE_DB` only — a leaked one
> would have handed the guard an alibi for its own writes. The pattern is now
> the packaged executable alone, and a source launch deliberately reads as "no
> app process". `GETMOREDONE_TEST_GUARD_APP` forces the state in tests, so no
> test's outcome depends on whether the app happens to be open.

> **Second amendment, 2026-11-11.** The first cold pass returned a
> high-severity finding, which this repo answers with a further cold pass in a
> different failure family (`CLAUDE.md`, *Review sweeps*). That pass was test
> quality over the batch's test diff, and returned one high and four medium —
> all fixed in-loop, each mutation-proved.
>
> 1. **The detector had the registry's blind spot in a new shape.** A
>    same-file helper only counted when it read the attribute back on one of
>    its own *parameters*, so `_independently` — a helper that builds its own
>    window, the natural way to write one — was invisible, and with it every
>    test calling it. `test_cigm11_cigm12_the_probe_agrees_with_the_display`
>    was therefore unguarded and unseen: on Xvfb both sides of its
>    `is` comparison are `False`, so it passed while measuring nothing. The
>    rule is now "any same-file function that reads an attribute back", which
>    takes the tree from 8 read-backs to 9, and that one test — which must
>    *not* ask the precondition, since it exists to check the precondition
>    against a real window — is named in `EXEMPT_FROM_THE_PRECONDITION` with
>    its reason, asserted to be exactly one entry and asserted still to be a
>    read-back, so neither a quiet addition nor a stale exemption survives.
>    `test_cghm42` gained the refactored shape as a fourth adversarial case.
> 2. **Dropped, with the reason recorded in the code** (below medium by the
>    reviewer's own grading): also counting `caps.require(...)` as asking. The
>    two tests *of* `require` call it that way while monkeypatching the probe,
>    so they are not display-dependent, and counting them took `test_cghm43`'s
>    exact count from 4 to 6. A guarded test written that way is reported as
>    unguarded — loudly, by name.
> 3. **The silencing tests asserted the wrapper's return value**, not that
>    `-topmost` never reached Tk, so they stayed green against a wrapper that
>    called through and then returned `None`. They now record what reached the
>    interpreter. Writing that spy found a second thing: `Wm.wm_attributes`
>    hands `tk.call` the whole command packed into one tuple, so the first
>    version recorded the call and recognised nothing — it passed against the
>    very mutation it was written to catch, and only the mutation proof showed
>    it. The spy flattens, and refuses to forward a `-topmost` write even when
>    one arrives, because an un-silenced `-topmost` during a run beachballs
>    this machine.
> 4. **Three smaller ones.** The verdict table never took the
>    `old is None` / `new is None` routes — the escape on a machine where the
>    app has never run is a test *creating* the file — so it has two more rows.
>    `::test_cghm14_app_detection_cannot_hang_or_raise` read the forcing seam
>    it was not testing, so exporting `GETMOREDONE_TEST_GUARD_APP` in a shell
>    inverted it; it clears it first. And the accusation is now a named
>    constant, `GUARD_ACCUSATION`, instead of a phrase the test found by
>    grepping the dict's prose — this repo asserts on code, not on English.
>
> Also deleted: `_requirers()`, left without a caller by `bf8b6c6`.

## 5. What this batch cannot verify here, and how it is proved

`CGH-M3.1` makes two tests take `mapped_windows`, the fixture the local
throttle skips, so **on this machine they will skip, not pass** — the change is
written blind and its CI behaviour is proved only by the next CI run. What *is*
provable locally is the coupling: `test_ci_contract.py` counts the fixture by
AST and compares it with `CLAUDE.md` and `conftest.py`, so a wrong count fails
before the push.

Acceptance for M3.1 is therefore two-part, and the status report says so: the
count test green locally, and the next CI run's skip list showing the two
`-alpha` skips gone (9 display skips → 5: 4 `-topmost` read-backs + the
`-topmost`-honouring one). If they are still there, M3 is `partial`, not
`done`.

## 6. Budget (`effort-budget.md`, stated before the work, not after)

**Tier: Light.** `conftest.py`, `tests/`, and two count statements in prose.
No `src/`, no data path, no scoring. This repo's rule is that tests or config
alone earn no sweep.

**One exception, costed:** one cold `learning-qa` pass over the `conftest.py`
diff alone (M1), because that diff decides a run's exit status, and the
plausible finding is a real escape that now reports as `app_running` and
returns green. Nothing else gets a pass; M2 to M4 get their targeted run and
one read of the diff.

**This is a fix batch, so it is counted by findings, not lines:** four findings,
so at most four or five new guards. M1 contributes a parametrised verdict test
plus the hang/raise case, M2 and M3 convert existing tests and add none, M4
contributes the detector, its adversarial fixture and the count. Over that,
cut rather than justify.

## 7. Verification

```
GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest \
  tests/test_settings_isolation.py tests/test_display_capabilities.py \
  tests/test_timer_session_endings.py tests/test_tk_offscreen.py \
  tests/test_ci_contract.py -q
```

`tests/test_settings_isolation.py` holds the guard's own nested-pytest harness;
`tests/test_ci_contract.py` holds the mapped-window count. Every converted test
is mutation-proved with its **verbatim** original (delete the clamp, ignore the
depth), and `./venv/bin/python tools/agents/check_docs_sync.py` is run by hand
before the push. Commit test changes separately from `conftest.py`.
