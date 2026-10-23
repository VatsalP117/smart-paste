"""Loading eval forms and cases.

A case is: which form, what was on the clipboard, and the correct value for
each field we care about. Loading validates every case against its form, so a
typo in a field ID fails loudly here instead of silently scoring as "missed".
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import BaseModel

from harness.contracts import FormSchema

EVALS_DIR = Path(__file__).parent
FORMS_DIR = EVALS_DIR / "forms"
CASES_DIR = EVALS_DIR / "cases"


class Case(BaseModel):
    id: str
    form: str
    """Name of a file in evals/forms/ without .json."""

    slices: list[str] = []
    """Tags like "run_on", "mixed_language", "missing_fields" (see LABELING_GUIDE.md)."""

    clipboard: str
    expected: dict[str, str | None]
    """field_id -> correct value. None means "this field must stay empty".
    Fields not listed are not scored."""

    notes: str | None = None


def load_form(name: str, forms_dir: Path = FORMS_DIR) -> FormSchema:
    path = forms_dir / f"{name}.json"
    return FormSchema.model_validate(json.loads(path.read_text()))


def load_cases(
    cases_dir: Path = CASES_DIR, forms_dir: Path = FORMS_DIR
) -> list[tuple[Case, FormSchema]]:
    """Load every case with its form, checking that they agree."""
    loaded: list[tuple[Case, FormSchema]] = []
    seen_ids: set[str] = set()
    forms: dict[str, FormSchema] = {}

    for path in sorted(cases_dir.glob("*.yaml")):
        case = Case.model_validate(yaml.safe_load(path.read_text()))

        if case.id in seen_ids:
            raise ValueError(f"{path.name}: duplicate case id {case.id!r}")
        seen_ids.add(case.id)

        if case.form not in forms:
            forms[case.form] = load_form(case.form, forms_dir)
        form = forms[case.form]

        unknown = set(case.expected) - form.field_ids
        if unknown:
            raise ValueError(
                f"{path.name}: expected values for fields not in form "
                f"{case.form!r}: {sorted(unknown)}"
            )

        for field_id, value in case.expected.items():
            field = form.field(field_id)
            if value is not None and field.options and value not in field.options:
                raise ValueError(
                    f"{path.name}: {field_id!r} expects {value!r}, "
                    f"which is not one of its options {field.options}"
                )

        loaded.append((case, form))

    return loaded
