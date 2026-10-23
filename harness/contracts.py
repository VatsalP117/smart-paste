"""Data contracts for Smart Paste.

Every stage of the pipeline takes one of these types and returns one. They are
the boundary between deterministic code and the probabilistic parts (Jev, the
LLM): anything a model returns is parsed into these types, and if it doesn't
fit, it is rejected here instead of reaching the form.

Read this file top to bottom before anything else in the repo.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field as PydanticField, model_validator

FieldKind = Literal[
    "text", "email", "tel", "number", "date", "textarea", "select", "radio", "checkbox"
]


class Field(BaseModel):
    """One fillable input on a form, as the adapter (extension / macOS app) sees it."""

    id: str
    """Stable ID assigned by the adapter, e.g. "email" or "passenger.1.age".
    The model only ever sees and returns these IDs, never raw HTML."""

    kind: FieldKind
    label: str | None = None
    placeholder: str | None = None
    autocomplete: str | None = None
    """HTML autocomplete token, e.g. "postal-code". Free signal when present."""

    nearby_text: str | None = None
    pattern: str | None = None
    max_length: int | None = None
    required: bool = False
    options: list[str] | None = None
    """Choices for select / radio fields. A value for this field must be one of them."""

    group: str | None = None
    """Repeated section this field belongs to, e.g. "passenger" or "education"."""

    row: int | None = None
    """Index within the group: 0 for passenger 1, 1 for passenger 2, ..."""

    @model_validator(mode="after")
    def _check_choices_and_groups(self) -> "Field":
        if self.kind in ("select", "radio") and not self.options:
            raise ValueError(f"field {self.id!r}: {self.kind} fields need options")
        if (self.group is None) != (self.row is None):
            raise ValueError(f"field {self.id!r}: set both group and row, or neither")
        return self


class FormSchema(BaseModel):
    """Everything the harness knows about the form being filled."""

    name: str
    url_host: str | None = None
    fields: list[Field]

    @model_validator(mode="after")
    def _unique_ids(self) -> "FormSchema":
        ids = [f.id for f in self.fields]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"form {self.name!r}: duplicate field ids {sorted(dupes)}")
        return self

    def field(self, field_id: str) -> Field:
        for f in self.fields:
            if f.id == field_id:
                return f
        raise KeyError(field_id)

    @property
    def field_ids(self) -> set[str]:
        return {f.id for f in self.fields}


class Span(BaseModel):
    """A piece of the clipboard text, with its position so values stay traceable."""

    text: str
    start: int
    end: int
    detected_as: str | None = None
    """Set when a rule matched it: "pin", "phone", "email"..."""


Source = Literal["rule", "jev", "llm", "test"]
"""Which tier produced a value. "test" is for baselines and fakes in evals."""

Status = Literal["auto", "review", "failed"]
"""auto = filled silently, review = filled and highlighted, failed = left blank."""


class FieldValue(BaseModel):
    field_id: str
    value: str
    source: Source
    confidence: float = PydanticField(ge=0.0, le=1.0)
    evidence: list[Span] = []
    """Where in the clipboard the value came from. Empty only for allowed
    transformations (e.g. "TN" -> "Tamil Nadu" in a dropdown)."""

    status: Status
    note: str | None = None


class FillResult(BaseModel):
    """What the harness hands back to the adapter. Never raw model output."""

    values: list[FieldValue]
    unfilled_required: list[str] = []
    trace_id: str

    def filled(self) -> dict[str, FieldValue]:
        """Values the user will actually see in the form (status != failed)."""
        return {v.field_id: v for v in self.values if v.status != "failed"}
