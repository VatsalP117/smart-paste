"""Run a pipeline over every eval case and report the scores.

    python -m evals.run --pipeline do_nothing
    python -m evals.run --pipeline oracle
    python -m evals.run --pipeline oracle --strict

Writes one JSONL file per run to evals/results/ so runs can be compared later.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from evals.baselines import Pipeline, do_nothing, make_oracle
from evals.cases import EVALS_DIR, load_cases
from evals.score import FieldScore, compute_metrics, score_case, unlabelled_fills

RESULTS_DIR = EVALS_DIR / "results"


def build_pipeline(name: str, cases) -> Pipeline:
    if name == "do_nothing":
        return do_nothing
    if name == "oracle":
        return make_oracle({case.clipboard: case.expected for case, _ in cases})
    raise SystemExit(f"unknown pipeline {name!r}")


def fmt(x: float | None) -> str:
    return f"{'-':>6}" if x is None else f"{x:6.1%}"


def print_row(label: str, scores: list[FieldScore]) -> None:
    m = compute_metrics(scores)
    print(
        f"{label:<22} {m.n_fields:>6}  {fmt(m.accuracy)}  {fmt(m.precision)}  "
        f"{fmt(m.recall)}  {fmt(m.confidently_wrong_rate):>10}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", default="do_nothing")
    parser.add_argument("--strict", action="store_true", help="exact match, no normalising")
    args = parser.parse_args()

    cases = load_cases()
    pipeline = build_pipeline(args.pipeline, cases)

    all_scores: list[FieldScore] = []
    warnings: list[str] = []
    for case, form in cases:
        result = pipeline(form, case.clipboard)
        all_scores += score_case(case.id, case.expected, result, case.slices, strict=args.strict)
        extra = unlabelled_fills(case.expected, result)
        if extra:
            warnings.append(f"{case.id}: filled unlabelled fields {extra}")

    print(f"\npipeline={args.pipeline}  cases={len(cases)}  strict={args.strict}\n")
    print(f"{'':<22} {'fields':>6}  {'acc':>6}  {'prec':>6}  {'rec':>6}  {'conf-wrong':>10}")
    print_row("ALL", all_scores)

    by_slice: dict[str, list[FieldScore]] = defaultdict(list)
    for s in all_scores:
        for tag in s.slices:
            by_slice[tag].append(s)
    print()
    for tag in sorted(by_slice):
        print_row(f"  {tag}", by_slice[tag])

    for w in warnings:
        print(f"\nwarning: {w}")

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / f"{stamp}-{args.pipeline}.jsonl"
    with out.open("w") as f:
        for s in all_scores:
            row = asdict(s)
            row["outcome"] = s.outcome.value
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\nwrote {out.relative_to(Path.cwd()) if out.is_relative_to(Path.cwd()) else out}")


if __name__ == "__main__":
    main()
