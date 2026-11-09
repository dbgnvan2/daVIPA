"""PRI-M1 and PRI-M2 — the create-time priority floor, and the 9999 cap.

Spec: docs/implementation_plan_2026-11-08_priority_defaults_and_cap.md
Plan: docs/implementation_plan_2026-11-08_pri_tests.md

Both criteria groups shipped on `main` with no test of any kind (`BACKLOG.md`
item 2). The three things that most need holding, in the order they would be
broken:

* **The cap is invisible in ordinary use.** The highest product below it is
  6400 and the lowest above it is 12800, so nothing between 6401 and 102399
  exists to notice; only a test that walks the whole 256-combination product
  set can see the clamp at all.
* **The floor is a create-time rule** that must never back-fill an existing
  row (D3). A single extra call site on the update path would rewrite factors
  the user never chose, silently, on every save.
* **Three copies of the product arithmetic were collapsed into one**, which is
  PRI-M2's stated purpose. A cap added to one copy and not its siblings is the
  defect that change was made to prevent, so one test parses the three modules
  and counts the remaining copies.
"""

import ast
import textwrap
from itertools import product
from pathlib import Path

import pytest

from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import (
    ActionItem,
    Defaults,
    PriorityFactors,
    apply_priority_floor,
    priority_score_from_factors,
    priority_score_label,
)
from src.getmoredone.time_block_layout import PRIORITY_BANDS

SRC = Path(__file__).resolve().parents[1] / "src" / "getmoredone"

FACTOR_NAMES = frozenset({"importance", "urgency", "size", "value"})

# The four factor fields, with the scale each one reads.
SCALES = (
    ("importance", PriorityFactors.IMPORTANCE),
    ("urgency", PriorityFactors.URGENCY),
    ("size", PriorityFactors.SIZE),
    ("value", PriorityFactors.VALUE),
)


@pytest.fixture
def manager(tmp_path):
    """A DatabaseManager on a database of this test's own.

    The default path resolves to the user's real application database and
    ``__init__`` runs migrations against it, so every manager in this suite
    takes an explicit one.
    """
    db = DatabaseManager(str(tmp_path / "priority.db"))
    try:
        yield db
    finally:
        db.close()


def _stored(manager, item_id):
    """The row as the database holds it, not the in-memory object (P6)."""
    return manager.get_action_item(item_id)


# ---------------------------------------------------------------------------
# PRI-M1 — a new item starts at the lowest value on every factor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_name,scale", SCALES)
def test_prim11_the_floor_is_the_minimum_of_each_scale(field_name, scale):
    """PRI-M1.1: the floor is read from the scale, not written out as a number."""
    assert PriorityFactors.floor()[field_name] == min(scale.values()), (
        f"the floor for {field_name} is {PriorityFactors.floor()[field_name]}, "
        f"not the minimum of its own scale ({min(scale.values())})"
    )


@pytest.mark.parametrize("field_name,scale_attr", [
    ("importance", "IMPORTANCE"),
    ("urgency", "URGENCY"),
    ("size", "SIZE"),
    ("value", "VALUE"),
])
def test_prim11_renumbering_a_scale_moves_its_floor(monkeypatch, field_name, scale_attr):
    """PRI-M1.1: and the minimum that moves is not 1 or 2.

    This is the half that makes the criterion mean something. With the scales
    as shipped, every floor is 1 or 2, so a hard-coded ``1`` or ``2`` in
    ``floor()`` would pass the test above. Here the scale's minimum is 7 --
    a value no literal in the module could be -- so only a floor that really
    reads the scale survives.
    """
    monkeypatch.setattr(PriorityFactors, scale_attr, {"Only": 7, "Higher": 19})

    item = ActionItem(who="Self", title="renumbered")
    apply_priority_floor(item)

    assert getattr(item, field_name) == 7, (
        f"{field_name} was floored to {getattr(item, field_name)} with a scale "
        "whose minimum is 7, so the floor is not read from the scale"
    )


def test_prim12_a_new_item_is_never_unscored(manager):
    """PRI-M1.2: no Defaults, no factors -> 1, 1, 2, 2 and a score of 4."""
    item = ActionItem(who="Self", title="brand new")
    item_id = manager.create_action_item(item)

    row = _stored(manager, item_id)

    assert (row.importance, row.urgency, row.size, row.value) == (1, 1, 2, 2), (
        "the stored factors are "
        f"{(row.importance, row.urgency, row.size, row.value)}, not the floor"
    )
    assert row.priority_score == 4, (
        f"the stored score is {row.priority_score}; an item created with no "
        "Defaults is unscored, which sorts below every rated item and draws in "
        "the unscored grey rather than the low band"
    )


def test_prim13_defaults_outrank_the_floor(manager):
    """PRI-M1.3: a configured default is never lowered to the floor."""
    manager.save_defaults(Defaults(scope_type="who", scope_key="Dave", importance=20))
    manager.save_defaults(Defaults(scope_type="system", urgency=10))

    item = ActionItem(who="Dave", title="defaulted")
    row = _stored(manager, manager.create_action_item(item))

    assert row.importance == 20, (
        f"the who default of 20 was lowered to {row.importance}"
    )
    assert row.urgency == 10, (
        f"the system default of 10 was lowered to {row.urgency}"
    )
    assert (row.size, row.value) == (2, 2), (
        f"the two factors no default names are {(row.size, row.value)}, not the floor"
    )


def test_prim14_the_floor_fills_only_what_is_missing(manager):
    """PRI-M1.4: a partially-configured default keeps its own value."""
    manager.save_defaults(Defaults(scope_type="system", importance=10))

    item = ActionItem(who="Self", title="partly defaulted")
    row = _stored(manager, manager.create_action_item(item))

    assert (row.importance, row.urgency, row.size, row.value) == (10, 1, 2, 2), (
        f"stored {(row.importance, row.urgency, row.size, row.value)}"
    )
    assert row.priority_score == 40, (
        f"the stored score is {row.priority_score}, not 10 x 1 x 2 x 2"
    )


def test_prim15_an_explicit_factor_survives_the_floor(manager):
    """PRI-M1.5: including on the ``apply_defaults=False`` path.

    That path is the reason the floor sits in ``create_action_item`` rather
    than inside ``_apply_defaults``: "Add Action Item" on the Weekly Items
    screen passes ``apply_defaults=False``, and before PRI-M1 it created
    unscored rows while the Item Editor did not.
    """
    item = ActionItem(who="Self", title="explicit", importance=5, size=8)
    row = _stored(manager, manager.create_action_item(item, apply_defaults=False))

    assert (row.importance, row.size) == (5, 8), (
        f"an explicitly set factor was lowered: {(row.importance, row.size)}"
    )
    assert (row.urgency, row.value) == (1, 2), (
        "the floor did not reach the apply_defaults=False path: "
        f"{(row.urgency, row.value)}"
    )
    assert row.priority_score == 5 * 1 * 8 * 2, row.priority_score


def test_prim16_editing_an_unscored_row_does_not_backfill(manager):
    """PRI-M1.6 (D3): an unscored row stays unscored across an update.

    A dirty-state test (P8): the row is written, re-read from the database,
    and updated, so the second call sees persisted state rather than the
    object the first call was given. Back-filling on save would write factors
    the user never chose onto a row they only opened to rename.
    """
    item = ActionItem(who="Self", title="unscored")
    item_id = manager.create_action_item(item, apply_defaults=False)

    # Make it unscored the only way the app can: clear the factors on a row
    # that already exists, which is the state every pre-PRI-M1 row is in.
    stored = _stored(manager, item_id)
    stored.importance = stored.urgency = stored.size = stored.value = None
    manager.update_action_item(stored)

    reread = _stored(manager, item_id)
    reread.title = "renamed, nothing else"
    manager.update_action_item(reread)

    row = _stored(manager, item_id)
    assert (row.importance, row.urgency, row.size, row.value) == (None, None, None, None), (
        "the update back-filled factors the user never chose: "
        f"{(row.importance, row.urgency, row.size, row.value)}"
    )
    assert row.priority_score == 0, (
        f"the row now scores {row.priority_score}; unscored is a different "
        "statement from scored-low and must survive an edit"
    )
    assert row.title == "renamed, nothing else", row.title


# ---------------------------------------------------------------------------
# PRI-M2 — the score is capped at 9999
# ---------------------------------------------------------------------------


def test_prim21_the_cap_is_four_digits_and_leaves_every_band_reachable():
    """PRI-M2.1: four digits wide, and above the top band threshold."""
    assert PriorityFactors.MAX_SCORE == 9999, PriorityFactors.MAX_SCORE
    assert len(str(PriorityFactors.MAX_SCORE)) == 4, (
        f"the cap is {len(str(PriorityFactors.MAX_SCORE))} digits wide; the "
        "column it exists to fit holds four"
    )

    top_threshold = max(threshold for threshold, _name in PRIORITY_BANDS)
    assert PriorityFactors.MAX_SCORE > top_threshold, (
        f"the cap {PriorityFactors.MAX_SCORE} is not above the top band "
        f"threshold {top_threshold}, so the highest band is no longer "
        "reachable by any capped score"
    )


def test_prim22_every_factor_combination_is_capped():
    """PRI-M2.2: all 256 combinations are ``min(product, MAX_SCORE)``.

    With exact counts rather than a floor. The counts are the finding: 33 of
    the 256 combinations collapse onto one flat tier, which is the ordering
    the cap costs (D1), and a change that narrowed the clamp would show up
    here as a different number rather than as a still-passing test.
    """
    cap = PriorityFactors.MAX_SCORE
    importance = sorted(PriorityFactors.IMPORTANCE.values())
    urgency = sorted(PriorityFactors.URGENCY.values())
    size = sorted(PriorityFactors.SIZE.values())
    value = sorted(PriorityFactors.VALUE.values())

    combinations = list(product(importance, urgency, size, value))
    assert len(combinations) == 256, len(combinations)

    clamped = []
    unchanged = []
    for i, u, s, v in combinations:
        raw = i * u * s * v
        got = priority_score_from_factors(i, u, s, v)
        assert got == min(raw, cap), (
            f"{i}x{u}x{s}x{v} = {raw} scored {got}, not min({raw}, {cap})"
        )
        (clamped if raw > cap else unchanged).append(raw)

    assert len(unchanged) == 223, len(unchanged)
    assert len(clamped) == 33, len(clamped)

    # What makes the clamp detectable at all: the raw products jump straight
    # over the cap, so no combination lands on 9999 by arithmetic and every
    # 9999 in the database is a capped one.
    assert sorted(set(clamped)) == [12800, 25600, 51200, 102400], sorted(set(clamped))
    assert max(unchanged) == 6400, max(unchanged)
    assert min(unchanged) == 4, min(unchanged)
    assert cap not in set(clamped) | set(unchanged), (
        f"{cap} is reachable as a raw product, so a stored {cap} no longer "
        "means the score was capped"
    )


@pytest.mark.parametrize("missing_position", range(4))
@pytest.mark.parametrize("missing_value", [None, 0])
def test_prim23_a_missing_factor_is_still_unscored(missing_position, missing_value):
    """PRI-M2.3: unscored survives the change -- not the cap, not the floor."""
    factors = [20, 20, 16, 16]
    factors[missing_position] = missing_value

    got = priority_score_from_factors(*factors)

    assert got == 0, (
        f"{factors} scored {got}; a factor nobody has rated makes the item "
        "unscored, which the bands draw in their own grey"
    )
    assert got != PriorityFactors.MAX_SCORE, got
    assert got != 4, "an unscored item was given the create-time floor's score"


def test_prim24_the_stored_score_is_capped_on_create_and_on_update(manager):
    """PRI-M2.4: the row in the database reads 9999, on both paths."""
    item = ActionItem(who="Self", title="top of every scale",
                      importance=20, urgency=20, size=16, value=16)
    item_id = manager.create_action_item(item)

    assert _stored(manager, item_id).priority_score == 9999, (
        f"created at {_stored(manager, item_id).priority_score}; 20x20x16x16 is "
        "102400, which is eight characters in a four-digit column"
    )

    row = _stored(manager, item_id)
    row.urgency = 16
    manager.update_action_item(row)

    assert _stored(manager, item_id).priority_score == 9999, (
        f"updated to {_stored(manager, item_id).priority_score}; 20x16x16x16 is "
        "81920, so the update path has its own uncapped arithmetic"
    )


def _four_factor_products(source: str, skip_functions=()):
    """Every expression multiplying four factor-named operands together.

    Parsed rather than grepped, per the repo rule, and returns the list so the
    caller can assert an exact count instead of a floor.
    """
    found = []

    def operands(node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            return operands(node.left) + operands(node.right)
        return [node]

    def identifier(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    tree = ast.parse(source)
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if function.name in skip_functions:
            continue
        for node in ast.walk(function):
            if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult)):
                continue
            parts = operands(node)
            if len(parts) != 4:
                continue
            names = [identifier(part) for part in parts]
            if all(name in FACTOR_NAMES for name in names):
                found.append((function.name, node.lineno))
    return found


def test_prim25_the_product_detector_finds_a_product():
    """A positive control for the walk PRI-M2.5 uses.

    Without this, a detector that silently matched nothing would make
    ``test_prim25_only_one_function_multiplies_the_factors`` pass for the
    wrong reason -- the classic "looks right but is wrong" input (P7). The
    count is exact, so a detector that matched the same product twice fails
    here too.
    """
    sample = textwrap.dedent(
        """
        def a_second_copy(self):
            return self.importance * self.urgency * self.size * self.value

        def not_a_product(self):
            return importance * urgency
        """
    )

    found = _four_factor_products(sample)

    assert [name for name, _line in found] == ["a_second_copy"], found


def test_prim25_only_one_function_multiplies_the_factors():
    """PRI-M2.5: no module multiplies the four factors itself.

    PRI-M2's whole purpose was collapsing three copies of this arithmetic into
    one, because a cap added to one copy and not its siblings is P5 by
    construction. ``priority_score_from_factors`` accumulates in a loop rather
    than writing the four-way product, so the expected count is zero
    everywhere, in that function included.
    """
    modules = [
        SRC / "models.py",
        SRC / "screens" / "item_editor.py",
        SRC / "screens" / "inline_editors.py",
    ]

    copies = {}
    for path in modules:
        assert path.exists(), path
        found = _four_factor_products(path.read_text())
        if found:
            copies[path.name] = found

    assert copies == {}, (
        "these places multiply the four factors themselves rather than calling "
        f"priority_score_from_factors: {copies}"
    )


def test_prim26_the_label_says_capped_only_above_the_cap():
    """PRI-M2.6, the model half: the boundary, from both sides.

    The two numbers are the only ones that matter -- 6400 is the highest
    product below the cap and 12800 the lowest above it, so these two labels
    are where a wrong comparison (``>=`` for ``>``) shows up. The UI half of
    this criterion, both render sites, is in
    ``tests/test_priority_floor_form.py``.
    """
    highest_uncapped = priority_score_label(20, 20, 16, 1)
    assert highest_uncapped == "6400 (20×20×16×1)", highest_uncapped
    assert "capped" not in highest_uncapped, (
        f"{highest_uncapped!r} says it was capped; 6400 is below the cap and "
        "its breakdown does multiply out to the number beside it"
    )

    lowest_capped = priority_score_label(20, 20, 16, 2)
    assert lowest_capped == "9999 (capped — 20×20×16×2)", lowest_capped
    assert "capped" in lowest_capped, (
        f"{lowest_capped!r} does not say it was capped, so the breakdown reads "
        "as arithmetic that does not add up"
    )
