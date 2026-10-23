"""Scoring a pipeline's FillResult against a case's expected values.

Two levels:
  1. field_outcome()  - what happened to ONE field (correct, wrong, missed...)
  2. compute_metrics() - turn a pile of outcomes into the numbers we track

Both are yours to implement (see the TODOs). The tests in tests/test_score.py
describe exactly what they must do. Run `pytest` and make them pass.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum

from harness.contracts import FieldValue, FillResult


class Outcome(str, Enum):
    CORRECT = "correct"
    """Should be filled, was filled with the right value."""

    WRONG = "wrong"
    """Should be filled, was filled with a different value."""

    MISSED = "missed"
    """Should be filled, was left empty."""

    INVENTED = "invented"
    """Should be empty, was filled anyway. The worst kind of mistake."""

    CORRECT_EMPTY = "correct_empty"
    """Should be empty, was left empty."""


@dataclass
class FieldScore:
    case_id: str
    field_id: str
    expected: str | None
    predicted: str | None
    status: str | None
    """Status of the prediction ("auto" / "review"), None if not filled."""

    outcome: Outcome
    slices: tuple[str, ...] = ()


def normalize(value: str) -> str:
    """Loose comparison: ignore case, outer spaces and repeated inner spaces."""
    return re.sub(r"\s+", " ", value).strip().casefold()


def field_outcome(expected: str | None, predicted: FieldValue | None, strict: bool = False) -> Outcome:
    """Classify one field.

    expected:  the labelled value, or None if the field must stay empty.
    predicted: what the pipeline filled, or None if it left the field empty.
               (Callers already drop values with status "failed".)
    strict:    if True, compare exactly; otherwise compare normalize()d values.

    TODO(you): implement using the five Outcome definitions above.
    """
    raise NotImplementedError("field_outcome: see the docstring and tests/test_score.py")


@dataclass
class Metrics:
    n_fields: int
    counts: dict[str, int]
    accuracy: float
    precision: float | None
    recall: float | None
    confidently_wrong_rate: float


def compute_metrics(scores: list[FieldScore]) -> Metrics:
    """Summarise field scores.

    Definitions (c = CORRECT, w = WRONG, m = MISSED, i = INVENTED, e = CORRECT_EMPTY):

      accuracy  = (c + e) / all scored fields
      precision = c / (c + w + i)    - of the fields we filled, how many were right.
                                       None when nothing was filled.
      recall    = c / (c + w + m)    - of the fields that should be filled, how many
                                       we got right. None when no field should be filled.
      confidently_wrong_rate = (WRONG or INVENTED with status "auto") / all scored fields
                                     - the mistakes the user won't be warned about.

    counts maps each Outcome value (e.g. "correct") to how many fields had it,
    including outcomes with zero fields.

    TODO(you): implement. An empty list of scores should raise ValueError.
    """
    raise NotImplementedError("compute_metrics: see the docstring and tests/test_score.py")


def score_case(
    case_id: str,
    expected: dict[str, str | None],
    result: FillResult,
    slices: list[str] | tuple[str, ...] = (),
    strict: bool = False,
) -> list[FieldScore]:
    """Score every labelled field of one case. Unlabelled fields are ignored."""
    filled = result.filled()
    scores = []
    for field_id, expected_value in expected.items():
        predicted = filled.get(field_id)
        scores.append(
            FieldScore(
                case_id=case_id,
                field_id=field_id,
                expected=expected_value,
                predicted=predicted.value if predicted else None,
                status=predicted.status if predicted else None,
                outcome=field_outcome(expected_value, predicted, strict=strict),
                slices=tuple(slices),
            )
        )
    return scores


def unlabelled_fills(expected: dict[str, str | None], result: FillResult) -> list[str]:
    """Fields the pipeline filled that the case doesn't label. Worth a look:
    either the label is missing or the pipeline is filling things it shouldn't."""
    return sorted(set(result.filled()) - set(expected))


def outcome_counts(scores: list[FieldScore]) -> Counter:
    return Counter(s.outcome for s in scores)
