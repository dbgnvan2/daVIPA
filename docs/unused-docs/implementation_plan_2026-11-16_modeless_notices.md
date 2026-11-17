# Implementation plan — modeless notices (MOD-M1 to M7)

**Status: approved 2026-11-16. Phase 1 (MOD-M1 to M4) built; phase 2 (MOD-M5,
MOD-M6) not started; MOD-M7's walk owed.** From `BACKLOG.md` MOD-A1. The
phase 1 record, including the three pieces of scope this plan did not have,
the nine findings of the pre-push review round, and the walk checklist, is
`docs/unused-docs/changes/2026-11-16-modeless-notices-phase1.md`. Two things
this plan got wrong are corrected there: MOD-M3's auto-clear was not safe to
apply blanket to the 21 `set_status` calls `plan.py` and `drag_schedule.py`
already had, and the colour inventory did need regenerating.
Reference for the idea only: `git show archive/no-focus-stealing-dialogs`
(`f1675f5`, 2026-08-25).

## The measurement this rests on

Counted on `main` at `f513b98`, 2026-11-16:

| | Count | Files |
|---|---|---|
| `messagebox.show*` — telling | **89** (64 `showerror`, 13 `showinfo`, 12 `showwarning`) | 25 |
| `messagebox.ask*` — asking | **24** (21 `askyesno`, 2 `askokcancel`, 1 `askyesnocancel`) | 15 |
| `grab_set()` | **49** | 24 |

So the backlog's "24 files and 26" understated it: 113 `messagebox` calls, not
26. 11 of the 25 telling files have no status surface at all; 14 have one.

## The decision that changes the shape of this work

**`main` has already answered "what replaces a modal", and it is not a toast.**
DRP-M3 / PD-M7 / PD-M13 established a per-screen status line —
`set_status(text, kind)` writing through `theme.status_text_color(kind)` — and
shipped it on `plan.py` (`:1518`) and `drag_schedule.py` (`:150`). Its
docstring at `plan.py:2446` records *why*, from two faults reported three hours
apart on 2026-11-07: on macOS the platform dialog raises bare `TclError` from
the idle callback a drag release schedules, and a hand-rolled grabbed toplevel
in its place **hung the application outright**, because its window could not
become visible while its own grab was up.

The archived commit's `widgets/toast.py` is a floating `CTkToplevel` with
`overrideredirect`, `-topmost`, four hard-coded hex colours and a module-level
`_active_toasts` list. Every one of those is a problem here: the hex colours
break `AGENTS.md`'s semantic colour rules and would redden
`test_color_inventory_sync.py`; a toplevel maps a window, which
`test_ci_contract.py` counts; the module global is shared state across tests
(P8); and `except Exception: return` silently drops the notice (P2).

**So this adopts `main`'s status line and discards the toast.** The archived
commit contributes the census and the intent, nothing else.

## Two further decisions, both narrowing the work

**The 24 asking sites keep `tkinter.messagebox`.** They are almost entirely
destructive confirmations — "Delete Segment?", "Remove APE from Quarter Q3?" —
which *should* block and *should* take focus. Replacing them with a bespoke
grabbed toplevel is the exact thing PD-M13 found hanging the app, and
`ui-regression.md` rule 2 forbids redesigning a working dialog without the
user asking. They get hardening (MOD-M5), not replacement.

**`grab_set` is not removed wholesale.** The archived commit removed all 27
indiscriminately. A confirm dialog needs its grab; an editor, picker or
settings window does not. That is a per-window judgement (MOD-M6), and it is
the only genuinely user-visible half of this work.

## Acceptance criteria

Spec IDs are used verbatim in code docstrings, and every test name carries its
ID.

### MOD-M1 — one notice contract, adopted rather than invented

A new `src/getmoredone/screens/status_notice.py` holds the contract `plan.py`
and `drag_schedule.py` already ship: `set_status(text, kind="muted")`, writing
`text` and `status_text_color(kind)` to a real label. Those two screens adopt
it with **no behaviour change**; the 14 screens with an ad-hoc status label
adopt it too; the 11 with none gain one.

- Test: `tests/test_modeless_notices.py::test_modm1_every_reporting_screen_sets_text_and_semantic_colour`
  — parametrized over the adopting screens, builds each for real, calls
  `set_status("x", "error")`, asserts the label's text and that its
  `text_color` equals `status_text_color("error")`.
- Test: `::test_modm1_the_two_existing_screens_keep_their_signature` — the
  adopted `set_status` accepts `(text)` and `(text, kind)` positionally, as
  the ~40 existing call sites pass it.

### MOD-M2 — telling goes to the notice line

All 89 `messagebox.show*` calls become `set_status(...)` at kind
`error` / `warning` / `info`. **Two sites are exempt and stay as they are:**

- `app.py:560` — the "already running" warning. No application window exists
  at that point; there is nothing to put a status line on.
- `app.py:440` — Settings failed to open, so the screen that would carry the
  notice is the one that did not build.

- Test: `::test_modm2_no_screen_tells_the_user_through_the_platform` — walks
  every `src/**/*.py` by AST, collects `messagebox.show*` calls, and asserts
  the set of `(file, line)` equals **exactly** the two exempt sites. An
  allowlist with a stated reason per entry, an exact count, not a floor.

### MOD-M3 — an error notice persists; info and success clear themselves

The objection to a status line is that it is easier to miss than a modal.
Answer: an `error` or `warning` notice stays until the next user action on that
screen, and is **not** cleared by a refresh. `info` and `success` clear
themselves after a timeout read from config, not a literal (P4).

- Test: `::test_modm3_an_error_survives_a_refresh` — set error, call the
  screen's refresh, assert the text is still there.
- Test: `::test_modm3_an_info_notice_clears_itself` — set info, drive the
  scheduled callback, assert empty.
- Test: `::test_modm3_the_dismiss_delay_is_configurable` — the timeout comes
  from `AppSettings`, and the test reads the shipped default from the class
  rather than restating the number, so changing it cannot leave the test
  asserting a value the app no longer has.

### MOD-M4 — the notice line survives what killed the dialog

PD-M13's failure path, generalized: a notice raised from a drag release or an
idle callback must appear and must not raise.

- Test: `::test_modm4_a_notice_from_an_idle_callback_does_not_raise` — schedule
  `set_status` through `after_idle`, pump the loop, assert text present and no
  exception. This is the test that would have caught PD-M12.

### MOD-M5 — no question takes the gesture with it

The 24 asking sites keep `messagebox`, wrapped so a platform `TclError` cannot
propagate into the caller's gesture. On a raise, the wrapper returns the
**safe** answer (the one that does not destroy data) and writes an error
notice.

- Test: `::test_modm5_a_raising_question_returns_the_safe_answer` —
  parametrized over all 24 sites' call paths, monkeypatch `messagebox.ask*` to
  raise `TclError`, assert the caller returns/declines rather than propagating,
  and that nothing was deleted.

### MOD-M6 — `grab_set` only on a true modal

Each of the 49 calls is classified in a table in this plan's follow-up, one
line per window: **keep** (a confirmation, or a dialog whose answer the next
line of code needs) or **drop** (an editor, picker or settings window the user
may legitimately leave open while working elsewhere). Dropping a grab is a
user-visible change, so each one is named in the status report per
`ui-regression.md` rule 6.

- Test: `::test_modm6_only_true_modals_take_a_grab` — AST walk over `src/`,
  asserting the set of files containing `grab_set` equals the **keep** list
  exactly, with a stated reason per entry.
- Test: `::test_modm6_a_dropped_grab_leaves_the_window_usable` — for the
  windows that lose their grab, build each and assert it still accepts input
  and still closes on its own close path (ui-regression rule 4: outcome, not
  presence).

### MOD-M7 — the on-screen walk

The program is never launched from a session here, so this criterion is **not
code-testable** and is flagged as such. It ships as a numbered walk checklist
in the handoff note, for the user to run: one screen per telling kind, one
destructive confirm, one window that lost its grab, and the drag-release path
on the Plan screen.

- Human review. No test.

## Order, and the phase boundary

**Phase 1 — MOD-M1 to M4** (the notice surface and the 89 telling sites).
Additive: nothing modal changes, so nothing the user relies on moves. Ends
pushed and walked.

**Phase 2 — MOD-M5 and M6** (the asking sites and the 49 grabs). This is where
focus behaviour actually changes, and it needs phase 1's notice line to exist
first, because a wrapped question reports its failure through it.

They are **sequential, not parallel** — `CLAUDE.md`'s one-build-batch rule, and
phase 2 depends on phase 1's module. Phase 2 does not start until phase 1 is
pushed.

Inside phase 1: the module and its tests first, then `plan.py` and
`drag_schedule.py` adopt it (proving the contract against the two screens that
already satisfy it), then the remaining 23 files in dependency order, then the
exact-count guard last — it cannot pass until the sweep is complete, so it is
the phase's own completion check.

## Budget, stated before the work

- **Tier: full.** `src/`, 26 files, user-visible behaviour.
- **Review:** the full sweep budget — at most 2 warm passes, at least 1 cold
  pass, `learning-qa` plus `/code-review`. `/security-review` is **not**
  triggered: no credentials, auth, HTTP, subprocess, SQL or deserialisation.
- **Ceilings:** prose ≤ 0.3x changed code, tests ≤ 2x. Phase 1 is a mechanical
  sweep of 89 call sites, so the test ceiling binds on the ~8 guards above, not
  on 89 per-site tests. **One guard per criterion, not one per call site.**
- **No new colour literals** — every notice colour comes from
  `status_text_color`, so `tools/color_audit.py` needs no regeneration and
  `test_color_inventory_sync.py` stays green.
- **Mapped windows:** phase 1 adds none, so `test_ci_contract.py`'s count is
  unchanged. If a phase 2 test needs a real grabbed window, that count changes
  and the change is declared in the commit.

## Documents this change must update (global rule 13)

`docs/USER_GUIDE.md` (errors now appear in the screen's status line, not an OS
dialog), `CHANGELOG.md`, `docs/DOCUMENTATION_INDEX.md` (this plan),
`docs/spec_coverage.md` (MOD-M1 to M7), and `BACKLOG.md` — MOD-A1 leaves when
phase 2 lands, not before.

## Adjacent issues found, not fixed (global rule 10)

- **`project_boards.set_status(board_id, status)`** at `project_boards.py:1641`
  is an unrelated method that collides with the notice contract's name. It sets
  a *project board's* status. Phase 1 must not adopt the mixin on that class
  without renaming one of the two; flagged, and the rename is not in scope.
- **`status_text_color` accepts legacy colour words** (`"red"`, `"green"`,
  `"white"`) alongside semantic names, and returns `kind` unchanged for an
  unknown string — so a typo becomes a Tk colour error at draw time rather than
  a caught mistake. Pre-existing; not fixed here.
