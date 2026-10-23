"""Tests for the scorer. These define the behaviour; make them pass.

Run:  pytest            (all tests)
      pytest -k outcome (just the field_outcome tests)
"""

import pytest

from evals.baselines import do_nothing, make_oracle
from evals.cases import load_cases
from evals.score import (
    FieldScore,
    Outcome,
    compute_metrics,
    field_outcome,
    normalize,
    score_case,
)
from harness.contracts import FieldValue


def fv(value: str, status: str = "auto") -> FieldValue:
    return FieldValue(field_id="x", value=value, source="test", confidence=0.9, status=status)


def score(outcome: Outcome, status: str | None = "auto") -> FieldScore:
    return FieldScore(case_id="c", field_id="f", expected=None, predicted=None, status=status, outcome=outcome)


# --- normalize (already implemented) ---------------------------------------


def test_normalize_ignores_case_and_spacing():
    assert normalize("  Tamil   Nadu ") == normalize("tamil nadu")


# --- field_outcome ----------------------------------------------------------


def test_outcome_correct():
    assert field_outcome("Chennai", fv("Chennai")) is Outcome.CORRECT


def test_outcome_correct_after_normalising():
    assert field_outcome("Tamil Nadu", fv("  tamil  nadu")) is Outcome.CORRECT


def test_outcome_strict_does_not_normalise():
    assert field_outcome("Tamil Nadu", fv("tamil nadu"), strict=True) is Outcome.WRONG


def test_outcome_wrong():
    assert field_outcome("600020", fv("600017")) is Outcome.WRONG


def test_outcome_missed():
    assert field_outcome("600020", None) is Outcome.MISSED


def test_outcome_invented():
    assert field_outcome(None, fv("9840000000")) is Outcome.INVENTED


def test_outcome_correct_empty():
    assert field_outcome(None, None) is Outcome.CORRECT_EMPTY


# --- compute_metrics --------------------------------------------------------


def test_metrics_basic_arithmetic():
    scores = [
        score(Outcome.CORRECT),
        score(Outcome.CORRECT),
        score(Outcome.WRONG, status="review"),   # wrong but highlighted
        score(Outcome.MISSED, status=None),
        score(Outcome.INVENTED, status="auto"),  # wrong and silent
        score(Outcome.CORRECT_EMPTY, status=None),
    ]
    m = compute_metrics(scores)
    assert m.n_fields == 6
    assert m.accuracy == pytest.approx(3 / 6)    # 2 correct + 1 correct_empty
    assert m.precision == pytest.approx(2 / 4)   # filled: 2 correct, 1 wrong, 1 invented
    assert m.recall == pytest.approx(2 / 4)      # should fill: 2 correct, 1 wrong, 1 missed
    assert m.confidently_wrong_rate == pytest.approx(1 / 6)  # only the auto invented one


def test_metrics_counts_include_zeroes():
    m = compute_metrics([score(Outcome.CORRECT)])
    assert m.counts == {o.value: (1 if o is Outcome.CORRECT else 0) for o in Outcome}


def test_metrics_precision_none_when_nothing_filled():
    m = compute_metrics([score(Outcome.MISSED, status=None)])
    assert m.precision is None
    assert m.recall == 0


def test_metrics_recall_none_when_nothing_should_be_filled():
    m = compute_metrics([score(Outcome.CORRECT_EMPTY, status=None)])
    assert m.recall is None
    assert m.accuracy == 1


def test_metrics_empty_input_raises():
    with pytest.raises(ValueError):
        compute_metrics([])


# --- test the test: baselines over the real cases ---------------------------


def _run(pipeline):
    scores = []
    for case, form in load_cases():
        scores += score_case(case.id, case.expected, pipeline(form, case.clipboard), case.slices)
    return compute_metrics(scores)


def test_do_nothing_baseline():
    m = _run(do_nothing)
    assert m.precision is None
    assert m.recall == 0
    assert m.confidently_wrong_rate == 0


def test_oracle_baseline_is_perfect():
    cases = load_cases()
    oracle = make_oracle({case.clipboard: case.expected for case, _ in cases})
    m = _run(oracle)
    assert m.accuracy == 1
    assert m.precision == 1
    assert m.recall == 1
    assert m.confidently_wrong_rate == 0
