# Manual check: SVU/LRP, the Projects right-hand panel

**Date:** 2026-11-17 **Batch:** `f136044`..`bd510a2`
**Spec:** [`docs/spec_2026-11-16_status_vocabulary.md`](../../spec_2026-11-16_status_vocabulary.md)

The batch's 44 criteria are green under pytest, including widget-level checks
that build the real panel. What pytest does **not** do is launch the app
against the real database, and this session does not drive the machine. So the
list below is for a human at the keyboard.

Quit `/Applications/daVIPA.app` first — a source launch exits silently while it
holds the database lock.

```bash
./start.sh
```

## The migration (do this first — it runs on launch)

1. The app opens without an error dialog, and `app.log` has no traceback.
2. Projects screen: every project that was there before is still there, with
   its status and its notes. The rebuild copies the table; this is the check
   that it copied *yours*.
3. Open a project's notes list: the notes are still attached. (Foreign keys
   are off during the rebuild precisely so the cascade cannot take them.)

## The project editor

4. Pencil icon on a tile → the **Status** dropdown offers four: active,
   pending, canceled, completed.
5. Set one to **canceled** and save. It saves without an error — before this
   batch the table's CHECK constraint rejected that value.
6. Reopen the editor: it still reads canceled.
7. The project has left the board. Tick **Show Canceled** in the toolbar: it
   is back. Untick it: gone again. This is the step that matters most — before
   the sweep fix there was no way back.
8. With it showing, set it Active from its tile and confirm it stays visible
   once Show Canceled is unticked again.
9. Narrow the window until the toolbar wraps: Show Pending / Show Complete /
   Show Canceled stay on the first row and only the size controls wrap.

## The right-hand panel

10. Click a project. The header line reads `Action Items`, then the count,
   then three checkboxes — **Open**, **Completed**, **Canceled** — all
   left-justified on one line. Open is ticked, the other two are not.
11. There is no `Next Step:` line in the detail header above it, and no
   separate right-justified `Show Completed` row.
12. The count reads `N items`, or `N shown • M hidden` when something is
   filtered out.
13. Select All is the unlabelled checkbox at the left of the column heading
    strip, directly above each row's own checkbox — the two line up.
14. Tick **Completed**: completed items appear, and completed Project Notes
    appear too. Untick it: both go away.
15. Untick all three: the list is empty and says how many are hidden.
16. Project Notes shows only its header line — `▸ Project Notes` and the
    count. Click the triangle: the notes list opens. Click again: it folds.
    The count stays visible either way.
17. Resize the window: the four item columns still fill the width and the
    heading strip still sits over the rows (Select All replaced one of
    `build_header`'s heading labels, so this is the check that it did not
    disturb the column widths).

## Known, not defects

- The label is **Canceled**, one `l`. That is the stored value and the
  spelling used everywhere else in the code.
- Nothing cancels an action item from the panel, and nothing cancels a project
  in one click from the board toolbar. Both are filed as `SVU-A1` and `SVU-A2`
  in `BACKLOG.md`. A project is canceled from its editor, and `Show Canceled`
  brings it back.
