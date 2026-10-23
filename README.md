# Smart Paste

Copy anything — a WhatsApp message with your dad's address, a group chat with
everyone's train details, your resume — and paste it into any form. Smart Paste
works out which piece goes in which field, and never fills a value it can't
trace back to what you copied.

Built as a learning project in AI engineering: context engineering, structured
output, tiered routing (rules → Jev → LLM), calibrated confidence, grounding,
and eval-driven development.

The full plan, phase by phase, is in [`docs/PLAN.md`](docs/PLAN.md).

## Status

**Phase 0** — data contracts and the eval suite. No model calls yet, on purpose:
the test set comes before the system it tests.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Some scorer tests fail until `field_outcome()` and `compute_metrics()` in
`evals/score.py` are implemented. That's the first exercise.

Once they pass:

```bash
python -m evals.run --pipeline do_nothing   # recall 0%, nothing confidently wrong
python -m evals.run --pipeline oracle       # 100% everywhere
```

If either baseline gives different numbers, the scorer has a bug.

## Phase 0 checklist

- [ ] Implement `field_outcome()` and `compute_metrics()`; all tests pass
- [ ] Capture 5 real form schemas with `tools/capture_schema.js`
- [ ] Extend `evals/LABELING_GUIDE.md` as you label
- [ ] 30 cases in `evals/cases/` (about 10 per scenario), every case tagged with slices
- [ ] Label 5 cases with a friend separately; fix the guide where you disagree
- [ ] Answer the checkpoint questions without notes

## Layout

```text
harness/contracts.py   data types every stage speaks
evals/forms/           FormSchema snapshots (JSON)
evals/cases/           eval cases (YAML)
evals/score.py         per-field outcomes and metrics
evals/run.py           runs a pipeline over all cases
evals/baselines.py     do-nothing and oracle pipelines
tools/                 schema capture script
tests/                 pytest
```

The example forms in `evals/forms/` are hand-written approximations for
getting started. Replace them with real captures.
