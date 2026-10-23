"""Fake pipelines used to test the evals themselves.

A pipeline is any function (FormSchema, clipboard_text) -> FillResult.
The real harness pipeline will have the same shape, so the runner can score
anything: these fakes today, the LLM baseline in Phase 1, the full tiered
pipeline after that.
"""

from __future__ import annotations

import uuid
from typing import Callable

from harness.contracts import FieldValue, FillResult, FormSchema

Pipeline = Callable[[FormSchema, str], FillResult]


def do_nothing(form: FormSchema, clipboard: str) -> FillResult:
    """Fills nothing. Expected: recall 0, precision None, nothing confidently wrong."""
    return FillResult(values=[], trace_id=str(uuid.uuid4()))


def make_oracle(expected_by_clipboard: dict[str, dict[str, str | None]]) -> Pipeline:
    """Returns a pipeline that 'knows' the right answers. Expected: every metric perfect.

    It looks answers up by clipboard text, so it only works on the cases it was built from.
    """

    def oracle(form: FormSchema, clipboard: str) -> FillResult:
        expected = expected_by_clipboard[clipboard]
        values = [
            FieldValue(
                field_id=field_id,
                value=value,
                source="test",
                confidence=1.0,
                status="auto",
            )
            for field_id, value in expected.items()
            if value is not None
        ]
        return FillResult(values=values, trace_id=str(uuid.uuid4()))

    return oracle
