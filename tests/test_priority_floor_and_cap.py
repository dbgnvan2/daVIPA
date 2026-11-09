"""PRI-M1 and PRI-M2 — the create-time priority floor, and the 9999 cap.

Spec: docs/unused-docs/implementation_plan_2026-11-08_priority_defaults_and_cap.md
Plan: docs/unused-docs/implementation_plan_2026-11-08_pri_tests.md

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


def _four_operand_products(source: str, skip_functions=()):
    """Every expression multiplying four operands together, anywhere.

    Deliberately **not** filtered by operand name. The first version of this
    helper matched only operands named ``importance``/``urgency``/``size``/
    ``value``, which made it blind at the one site most likely to regress:
    ``screens/inline_editors.py::update_score`` already binds its four factors
    as ``i``, ``u``, ``s`` and ``v``, so a re-introduced ``i * u * s * v``
    would have left the guard green at count 0 while a second scorer existed.
    Widening the name list would only move the blind spot to the next set of
    names someone picks.

    Measured: the three modules contain **no** four-operand product of any
    kind, so dropping the name filter costs no false positive today.

    **What this still cannot see, which is the larger half.** It matches one
    shape: a single expression whose top-level ``*`` chain flattens to exactly
    four operands. The real scorer does not have that shape --
    ``priority_score_from_factors`` accumulates in a loop -- so the most likely
    way a second scorer appears, copying that function, is invisible here.
    Measured on sample sources, none of these is detected: the loop verbatim;
    ``reduce(mul, [i, u, s, v])``; ``math.prod([i, u, s, v])``; two halves
    multiplied through intermediate variables; four ``*=`` statements; and
    ``i * u * s / 1 * v``, because any ``/`` in the chain parses as a Div node
    at the top and nothing reaches four operands.

    So this is a tripwire for one shape, not a proof that one function scores.
    **The guard that actually holds PRI-M2.5 is behavioural**:
    ``tests/test_priority_floor_form.py::test_prim26_a_capped_label_says_it_is_capped``
    drives both render sites and asserts the capped label at each, so a second
    scorer that lost the cap fails there whatever shape it is written in. This
    walk is the cheap structural check beside it.

    The one cost that is a false positive: an unrelated four-way product added
    to one of these three modules fails the guard, and the failure message says
    what to do about it.

    Parsed rather than grepped, per the repo rule, and returns the list so the
    caller can assert an exact count instead of a floor. Walks the whole
    module, not only function bodies, so a product at module or class level is
    seen too.
    """
    def operands(node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            return operands(node.left) + operands(node.right)
        return [node]

    def describe(node):
        """A label for a failure message, not an identity.

        ``self.importance`` and a bare ``importance`` both describe as
        ``importance``, and a call or subscript gives only its node type. The
        line number beside it is what locates the expression.
        """
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"...{node.attr}"
        return f"<{type(node).__name__}>"

    tree = ast.parse(source)

    # Every node inside a function this caller excuses, so the walk below can
    # cover the whole module and still skip those bodies.
    excused = set()
    for function in ast.walk(tree):
        if (isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
                and function.name in skip_functions):
            excused.update(id(node) for node in ast.walk(function))

    found = []
    for node in ast.walk(tree):
        if id(node) in excused:
            continue
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult)):
            continue
        parts = operands(node)
        if len(parts) == 4:
            found.append((node.lineno, [describe(part) for part in parts]))
    return found


@pytest.mark.parametrize("product,why", [
    ("self.importance * self.urgency * self.size * self.value",
     "the field names, as models.py would write them"),
    ("i * u * s * v",
     "single letters, as inline_editors.update_score already names its factors"),
    ("imp * urg * sz * val",
     "any other names someone picks"),
    ("PriorityFactors.IMPORTANCE[a] * b * c * d",
     "a subscript among the operands"),
])
def test_prim25_the_product_detector_finds_a_product(product, why):
    """A positive control for the walk PRI-M2.5 uses, at four namings.

    Without this, a detector that silently matched nothing would make
    ``test_prim25_only_one_function_multiplies_the_factors`` pass for the wrong
    reason -- the classic "looks right but is wrong" input (P7).

    The second case is the one that matters. An earlier version of the detector
    filtered operands by name, so ``i * u * s * v`` -- which is exactly how
    ``screens/inline_editors.py::update_score`` names its four factors today --
    slipped past it, and the guard would have reported one scorer while a
    second one existed at the render site PRI-M2 was written to protect.

    The count is exact, so a detector that matched one product twice fails here
    too, and the three-operand line proves it is not matching everything.
    """
    sample = textwrap.dedent(
        f"""
        def a_second_copy(self):
            return {product}

        def not_a_product(self):
            return importance * urgency * size
        """
    )

    found = _four_operand_products(sample)

    assert len(found) == 1, (
        f"the detector found {len(found)} four-operand products in a sample "
        f"holding one ({why}): {found}"
    )


def test_prim25_the_product_detector_excuses_the_one_scorer():
    """And ``skip_functions`` excuses the whole of a named function's body.

    **The guard below excuses nothing**, and this is the only caller that
    passes ``skip_functions`` at all. The parameter is there because the
    criterion is "one function multiplies the factors", which reads as though
    that one function must be excused -- and it does not need to be, because
    ``priority_score_from_factors`` accumulates in a loop and holds no
    four-way product. Covered here so the parameter is not silently broken for
    whoever first has a reason to use it.

    It excuses a named function's whole subtree, which includes its decorators
    and argument defaults and any function nested inside it, and it matches
    every function of that name in the module rather than one.
    """
    sample = textwrap.dedent(
        """
        def priority_score_from_factors(i, u, s, v):
            return i * u * s * v

        def somewhere_else(i, u, s, v):
            return i * u * s * v
        """
    )

    assert len(_four_operand_products(sample)) == 2, "the control sample is wrong"

    found = _four_operand_products(
        sample, skip_functions=("priority_score_from_factors",)
    )
    assert len(found) == 1, (
        f"excusing one function of two left {len(found)} products: {found}"
    )


def test_prim25_only_one_function_multiplies_the_factors():
    """PRI-M2.5: no module multiplies four operands together itself.

    PRI-M2's whole purpose was collapsing three copies of this arithmetic into
    one, because a cap added to one copy and not its siblings is P5 by
    construction. ``priority_score_from_factors`` accumulates in a loop rather
    than writing the four-way product, so the expected count is zero
    everywhere, in that function included -- and the walk is excused nothing.

    What this does and does not see is in ``_four_operand_products``, and the
    limits matter more than the coverage. It catches a product under **any**
    operand names, which the name-based first version did not. It does **not**
    catch a scorer written in any other shape -- a loop (which is how the real
    one is written), ``reduce``, ``math.prod``, intermediate variables,
    ``*=``, or any chain containing a ``/``. Nor does it look beyond these
    three modules by name.

    So this is a structural tripwire, not a proof. The criterion is held by
    ``tests/test_priority_floor_form.py::test_prim26_a_capped_label_says_it_is_capped``,
    which drives both render sites and asserts the capped label at each: a
    second scorer that dropped the cap fails there in whatever shape it was
    written. This test adds the cheap check that no one pasted the obvious
    four-way product.

    The walk is excused nothing -- ``skip_functions`` exists for the helper's
    own control test and is not used here, because the real scorer holds no
    four-way product to excuse.
    """
    modules = [
        SRC / "models.py",
        SRC / "screens" / "item_editor.py",
        SRC / "screens" / "inline_editors.py",
    ]

    copies = {}
    for path in modules:
        assert path.exists(), path
        found = _four_operand_products(path.read_text())
        if found:
            copies[path.name] = found

    assert copies == {}, (
        "these places multiply four operands together rather than calling "
        f"priority_score_from_factors: {copies}. If one of them is not a "
        "priority score, this guard needs narrowing deliberately -- not "
        "raising above an exact count of 0. And note what a clean run here "
        "does not prove: a scorer written as a loop, a reduce, a prod, through "
        "intermediate variables, or with any / in the chain is not a "
        "four-operand product and is invisible to this walk"
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
