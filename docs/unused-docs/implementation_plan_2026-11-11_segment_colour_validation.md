# Implementation plan — one authority for a segment colour (SCV)

**Status:** draft — approved by nobody, no implementation code written.
**Written:** 2026-11-11, measured at `6963d0a`.
**Closes:** `LRR-A1` (medium), filed 2026-11-10 by the LRR batch's cold pass.
**Scope:** `vps_manager.py`, `vps_manager_taxonomy.py`,
`screens/vps_segment_editor.py`, `priority_levels.py`.

## 1. What LRR-A1 says, and what measurement adds

The filing names one validator — `vps_segment_editor.validate_color`, which
checks `startswith("#")`, `len() == 7` and `int(color_hex[1:], 16)` — and one
consequence, a raw value reaching `ctk.CTkFrame(fg_color=…)`.

There is a **second validator with the identical defect**, and it is the worse
one. `VPSManager._is_valid_hex_color` (`vps_manager.py:159`) is the same three
checks, and it is the gate on the colour-repair pass inside
`get_vision_subsegments` and `get_vision_categories`: a row it calls valid is
`continue`d past, untouched. So the pass that exists to replace a bad colour is
blind to exactly this class of bad colour.

Measured here, not reasoned (`./venv/bin/python -c …` against the real
staticmethods at `6963d0a`):

| value | `_is_valid_hex_color` | `normalize_hex_color` | `_derive_subsegment_color` |
|---|---|---|---|
| `#0X1234` | `True` | `None` | **`ValueError: invalid literal for int() with base 16: '0X'`** |
| `#1_2345` | `True` | `None` | **`ValueError: … '1_'`** |
| `#+12345` | `True` | `None` | `#0B368D` — no error, a colour derived from garbage |
| `#0b1010` | `True` | `#0B1010` | `#35474A` — correct; six hex digits, not a defect |

So LRR-A1 has a failure mode the filing does not mention: an **uncaught
`ValueError` in a VPS read path**, independent of Tk. `_derive_subsegment_color`
asks its own gate, is told the value is fine, and then slices `base[1:3]` into
`int(…, 16)`. It needs a segment whose colour is malformed *and* a subsegment or
category with no usable colour of its own, which is the branch that calls it —
conjunctive, so not common, but it is a hard crash in
`get_vision_subsegments()`, not a cosmetic fault.

`color_contrast._HEX_COLOR_RE` is the authority, and its own module docstring
already spells out this exact hazard: "``int(text, 16)`` must not be used for
this, because Python accepts a leading sign, a ``0x`` prefix, PEP-515
underscores …". Two validators were written anyway. Same shape as the LRR batch
— a rule written by hand where an authority exists.

**Not re-measured:** the filing's Tk half, that the raw value reaching
`fg_color` raises `TclError` part-way through a refresh and takes the list
screen down. It is consistent with `normalize_hex_color`'s docstring and with
PLC-M2.5's reason for existing, but I did not put a widget on screen to confirm
it. SCV-M4 is written so the value never gets there, which does not depend on
the claim being exact.

## 2. Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| SCV-M1.1 | `validate_color` and `_is_valid_hex_color` both answer from `color_contrast`; no hand-rolled hex validator survives — an `int(…, 16)` whose argument is a slice of a colour, outside `color_contrast` | `tests/test_segment_colour_validation.py::test_scvm11_no_hand_rolled_hex_validator_survives` — AST walk, exact count 0 (parse it, assert counts, no floor) |
| SCV-M1.2 | The three measured accepts are refused, and `#0b1010` still passes | `::test_scvm12_the_validators_refuse_what_int_base_16_allows` — the §1 table as the fixture; confirm red first |
| SCV-M1.3 | What the editor **stores** is the normalised form, not the typed text, so `#abc` and `#AbC123` land as `#RRGGBB` | `::test_scvm13_the_editor_stores_the_normalised_form` |
| SCV-M2.1 | `_derive_subsegment_color` raises nothing for any string, and falls back to `#64748B` where it cannot read one | `::test_scvm21_deriving_from_a_malformed_colour_falls_back` — the two `ValueError` rows |
| SCV-M2.2 | `#+12345` falls back rather than deriving `#0B368D` from a misread slice | `::test_scvm22_a_colour_that_parses_wrongly_is_not_derived_from` — adversarial (P7): looks right, is wrong |
| SCV-M3.1 | The repair pass repairs a row holding `#0X1234` instead of skipping it, and the repair persists | `::test_scvm31_the_repair_pass_sees_a_malformed_stored_colour` — dirty state (P8): seed the row, read, reopen with a second `DatabaseManager`, assert the stored value |
| SCV-M4.1 | `row_fill` returns a `#RRGGBB` fill or none at all, never the raw stored value | `tests/test_priority_level_colors.py::test_scvm41_a_malformed_segment_colour_does_not_become_a_fill` |

Every `DatabaseManager` and `VPSManager` in these tests takes a `tmp_path`
database.

## 3. Order

1. **SCV-M1** — one authority, both validators. Everything else is downstream
   of it, and it is where the adversarial table belongs.
2. **SCV-M2** — `_derive_subsegment_color`. It is the measured crash; its test
   is the one to write first within the batch (fix→test map).
3. **SCV-M3** — the repair gate, once M1 makes it able to see the class.
4. **SCV-M4** — `row_fill`. `LRR-A1` records that it deliberately passes the
   raw value through as the fill while computing the normalised form for the
   text colour; this is the change that ends that, and it is last because it is
   the only one that alters what the user sees.

Then, in the same change (global rule 13): delete the `LRR-A1` entry from
`BACKLOG.md`; correct `row_fill`'s docstring where it explains passing the raw
value; check `docs/USER_GUIDE.md` for a sentence about segment colour and say
in the status report what it found rather than assuming.

## 4. One decision the plan takes, rather than leaving implicit

**SCV-M1.3 widens what the editor accepts.** `validate_color` requires
`len() == 7` today, so `#abc` is refused; `normalize_hex_color` expands the
three-digit form. Delegating therefore makes `#abc` valid. That is accepted
here — it is a form people type, every browser takes it, and the module already
decided it — but only together with storing the normalised `#AABBCC`. Accepting
the short form and storing it raw would put a value in the database that every
reader has to expand again, which is how this class of defect started.

## 5. Adjacent issues found, not fixed (global rule 10)

* `drag_schedule_support.interpolate_hex_color` slices into `int(…, 16)` with
  no guard, exactly as `_derive_subsegment_color` does. Not on this path — its
  only caller is the gradient in its own module, over theme colours — so it is
  not in scope, but it is the third copy of the same slice-and-parse and will
  behave the same way the day something hands it a stored colour.
* `vps_manager.py:1388` — `get_segment_colors_by_id` hands callers
  `(row["color_hex"] or "").strip() or "#334155"`, i.e. the raw stored value.
  SCV-M4 protects the row fill specifically; the map itself still hands out
  whatever the database holds, and the other readers of it are not surveyed in
  this batch.
* `item_editor_weekly_tactic_dialog._text_color_for_background` does the same
  slicing but wraps it in `try/except ValueError` with a fallback. Correct
  already — listed so the next reader does not "fix" it.

## 6. Manual checklist (the part no test covers)

1. VSP → segment editor: type `#0X1234` into the colour entry and save. It is
   refused, with the error naming the `#RRGGBB` form.
2. Type `#abc` and save: accepted, and the stored value reads back `#AABBCC`.
3. A segment whose colour is already malformed in the database (if `app.log`
   shows `Segment colour … is not a #RRGGBB value`): its rows still draw, its
   subsegment list still opens, and the colour is repaired on next read.

## 7. Verification

```
GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest \
  tests/test_segment_colour_validation.py tests/test_priority_level_colors.py \
  tests/test_vps_integration.py -q
```

`tests/test_vps_integration.py` is in the run because SCV-M3 changes what
`get_vision_subsegments` and `get_vision_categories` write. Commit tests and
`src/` separately, by explicit path. One cold `learning-qa` pass over the
`src/` diff — this is `src/`, a data path and a crash path, so the full sweep
budget applies.
