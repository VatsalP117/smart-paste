"""Checks that every eval case is well-formed. Runs on every `pytest`."""

from evals.cases import load_cases


def test_all_cases_load_and_match_their_forms():
    cases = load_cases()
    assert cases, "no cases found in evals/cases/"


def test_every_case_has_at_least_one_slice():
    for case, _ in load_cases():
        assert case.slices, f"{case.id} has no slices; tag it so per-slice scores mean something"
