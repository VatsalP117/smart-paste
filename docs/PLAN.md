# Smart Paste — Project Plan

The complete plan for Smart Paste: what we're building, why, how it works, and the
order we build it in. Written 23 Oct 2026 from the planning conversation; update it
as decisions change.

The project has two goals, in this order:

1. **Learn AI engineering and harness design** by building a real system end to end.
2. **Ship something regular people would actually use.**

---

## 1. The idea

Copy anything — a WhatsApp message with your dad's address, a group chat with
everyone's train details, your resume — press one hotkey on any form, and Smart
Paste fills it. It works out which piece goes in which field, picks the right
dropdown options, highlights anything it's unsure of, and **never fills a value it
can't trace back to what you copied.**

**Why it isn't just autofill:** browser autofill only knows *you*. Smart Paste knows
*whatever you just copied* — someone else's details, messy chat text, a document.

### v1 scenarios

| Scenario | Example | What it stresses |
| --- | --- | --- |
| Family details → any form | Dad's address from WhatsApp into Amazon, a school form, an exam form | Someone else's data, messy text, Indian addresses |
| Group chat → IRCTC passengers | "Rahul 24 M, Priya 23 F, Arjun 25 M" → all passenger rows | Repeated rows, speed (Tatkal), informal formats |
| Resume → job portal | Resume into a Workday-style application | Long forms, repeated sections (jobs, degrees), dates |

Value comes from **breadth**: any single use happens a few times a month, so one
hotkey that works everywhere is the product.

### Later paste targets (same engine, new schemas)

Invites → calendar events, bills → Splitwise, contact blocks → contacts, bank SMS →
expense tracker, order emails → warranty/claim forms, government and visa forms.

### Surfaces

| Surface | Status |
| --- | --- |
| Chrome extension | v1 |
| macOS menu bar app (any native or Electron app) | v2 |
| Android | Not planned |

---

## 2. Principles

1. **Evals before features.** Build the test set and scorer before the clever parts.
   No change is "better" until the evals say so.
2. **Cheapest tool that works.** Rules first, then Jev, then an LLM only for what's
   left. Each tier must earn its place in the evals.
3. **Never invent values.** Every value traces back to the clipboard or is an allowed
   transformation ("TN" → "Tamil Nadu"). Leaving a field empty beats guessing.
4. **Clipboard text is data, never instructions.** It's untrusted input.
5. **Contracts are the boundary.** Every stage takes and returns typed objects; model
   output is parsed into them or rejected.
6. **Never submit forms.** Fill, highlight, let the user check.

---

## 3. Architecture

```text
 Adapter (extension / macOS app)          Harness (Python, FastAPI)                 External
 ───────────────────────────────          ─────────────────────────                 ────────
 Form reader ──(schema + clipboard)──▶  1. Rules tier
   (schema built on focus, cached)       2. Segmenter
                                         3. Jev tier  ◀────────────────────────▶  Jev API
                                         4. Confidence gate
                                              │ low confidence     │ confident
                                              ▼                    │
                                         5. LLM tier  ◀──────────────────────▶  LLM provider
                                              │                    │
                                              ▼                    ▼
 Form filler ◀────(FillResult)────────  6. Validate + ground
   (highlights, undo)                    7. Trace (every stage) ──▶ trace store
```

### One paste, end to end

1. **Form focused** — the adapter builds the `FormSchema` in the background, before
   the paste, so it's off the latency path.
2. **Hotkey** — the adapter sends `{schema, clipboard_text}` to the harness.
3. **Rules tier** — regex detectors (PIN, phone, email, PAN, GSTIN, IFSC, dates) and
   direct mapping via HTML `autocomplete` attributes. Under 5 ms.
4. **Segmenter** — splits the remaining text into candidate spans with character
   offsets (newlines, commas; run-on text is the known weak spot).
5. **Jev tier** — in one parallel call: which field each span belongs to (Choice over
   field IDs + `none`), which dropdown option fits, plus confidence. Values are copied
   from the clipboard, so this tier cannot invent data.
6. **Confidence gate** — each field goes to auto-fill, fill-and-highlight, or escalate.
   Thresholds come from evals, not guesses.
7. **LLM tier** — only escalated fields: reformatting, splitting run-on text, combining
   pieces, messy multilingual input. Thinking off, strict output schema, clipboard in
   a marked data block.
8. **Validate and ground** — HTML `pattern` / `maxlength` / type / options, domain
   rules (PIN must match State), one repair retry with the specific error, then
   blank-and-flag. Every value must have clipboard evidence or be an allowed
   transformation.
9. **Fill** — native value setter + `input`/`change` events (so React forms accept it),
   colour by confidence, "why" tooltip, one-click undo.
10. **Trace** — input, output, timing and cost of every stage.

### Components and what each teaches

| Component | Job | Concept |
| --- | --- | --- |
| Form schema extractor | DOM → compact list of fields | Context engineering |
| Rules tier | Exact patterns, `autocomplete` mapping | Deterministic code beats models where it applies |
| Segmenter | Text → candidate spans | Decomposition into small, well-scoped questions |
| Jev tier | Span → field, dropdown choice, confidence | Decision models for decisions, generative models for generation |
| Confidence gate | Auto / review / escalate | Calibration; thresholds as data-driven product decisions |
| LLM tier | What needs real generation | Prompt and schema design, provider abstraction, injection defence |
| Validator + grounding | No broken or invented values | The harness, not the model, guarantees reliability |
| Filler + UX | Values the page accepts, easy review | Trust comes from showing uncertainty and cheap undo |

---

## 4. Models

### Jev (TypeSafe) — the decision model

Jev doesn't generate text. It answers typed questions about a state with calibrated
probabilities and confidence:

- **Choice** — pick from a list (field IDs, dropdown options; up to 255).
- **Score** — rate on a rubric.
- **Noul** — probability a statement is true.
- **Box** (Jev 1.14, preview) — where something is in an image.

All questions in a request run in parallel. TypeSafe's own "pre-parsed value
extraction" cookbook (regex candidates → Jev picks the span) matches our rules →
spans → Jev design.

**Jev 1.14 vision features are preview ("Dreamer-ready").** They need the
`TypeSafe-Danger-Zone-Images: true` header and `jev-preview` / `jev-1.14.0`. Images
must be PNG/JPEG, 280–1568 px per side. A Box answer always returns a box, so pair it
with a Noul ("is it there?"). Keep vision off the v1 path.

Docs: <https://docs.typesafe.ai/introduction>, <https://docs.typesafe.ai/primitives/box.md>,
<https://docs.typesafe.ai/images.md>

### The LLM — decision pending

Only handles escalated fields, so it runs on a minority of pastes. Decide from evals
in Phases 1 and 3, not from benchmarks:

| Candidate | Why | Watch |
| --- | --- | --- |
| Claude Haiku 5.5, **thinking off** | Quality, structured output, cheap | Reasoning modes add seconds — always turn thinking off |
| Open model on Groq / Cerebras (Qwen, GPT-OSS) | Very low time to first token | Weaker on messy Indian addresses; limited model catalogue |
| Gemini Flash-Lite tier | Fast and cheap | Another option to benchmark |
| Gemini Nano in Chrome | On-device, free, private | Desktop Chrome only, small context, less accurate |

**Network distance matters as much as model speed.** Measure from Chennai, not from
benchmark sites. Jev is currently US-hosted.

### Ruled out

- **JEPA-style models** — research-stage for text; nothing usable for extraction.
- **GLiNER2 / Schemer** — fast local extractors worth knowing; not in the main plan,
  possible future comparison.

---

## 5. Tech stack

| Part | Choice | Why |
| --- | --- | --- |
| Harness | Python 3.12, FastAPI, Pydantic, `asyncio` + `httpx` | Best eval/AI tooling and SDKs; `asyncio` runs Jev and LLM calls in parallel |
| Extension | Chrome Manifest V3, TypeScript, Vite | Standard, typed |
| macOS app (v2) | Swift menu bar app; prototype in Python with `pyobjc` | Accessibility API, EventKit, Contacts |
| Decision model | Jev | Fast calibrated choices |
| LLM | Behind one interface | Swap and compare in evals |
| Traces | SQLite + small local viewer | Simple, inspectable |
| Evals | pytest-style runner + pandas | Easy to diff runs |
| Config | One YAML per pipeline variant | Evals compare configs by name |

**Go was considered** for the live path (concurrency, single binary). Python won:
eval tooling, SDK support (TypeSafe ships a Python SDK), and the speed difference is
small next to network calls.

### Repo layout (target)

```text
smart-paste/
  extension/          # v1 Chrome extension
    src/schema/       # DOM -> FormSchema
    src/fill/         # write values, events, highlights, undo
  macos/              # v2 Swift menu bar app
    Reader/ Filler/ Integrations/
  harness/
    contracts.py      # the Pydantic types
    pipeline.py       # runs stages in order, writes the trace
    stages/           # rules, segment, jev_tier, gate, llm_tier, validate, ground
    providers/        # one file per LLM, same interface
    data/pin_codes.csv
    api.py            # FastAPI endpoint
    configs/          # baseline.yaml, tiered.yaml ...
  evals/
    forms/ cases/ score.py run.py baselines.py compare.py results/
  tools/              # schema capture script
  traces/
  docs/PLAN.md        # this file
```

---

## 6. Data contracts

Defined in `harness/contracts.py`. Every stage takes one and returns one.

- **`Field`** — id, kind, label, placeholder, `autocomplete`, nearby text, pattern,
  max length, required, options; **`group` + `row`** for repeated sections (IRCTC
  passengers, resume jobs/degrees).
- **`FormSchema`** — name, host, fields (unique IDs).
- **`Span`** — clipboard text with start/end offsets and what rule matched it.
- **`FieldValue`** — field ID, value, source (`rule` / `jev` / `llm`), confidence,
  evidence spans, status (`auto` / `review` / `failed`).
- **`FillResult`** — values, unfilled required fields, trace ID. The adapter never
  sees raw model output.

`evidence` makes grounding checkable; `source` lets evals score each tier separately.

---

## 7. Evals

The most important thing we build. Start with 30 hand-labelled cases, grow to ~200.

**A case** = a saved form schema + clipboard text + the correct value for each field
we care about (`null` = must stay empty). Rules live in `evals/LABELING_GUIDE.md`.

**Forms** are saved snapshots, not live sites, so scores are reproducible.

**Slices** (tags on every case): clean, run_on, abbreviations, landmarks,
mixed_language, missing_fields, noise, conflicts, injection, family, group_chat,
repeated_rows, signature. Add more as needed.

**Metrics**

| Metric | Meaning |
| --- | --- |
| Confidently wrong rate | Wrong or invented values filled silently — minimise above all |
| Accuracy | (correct + correctly empty) / scored fields |
| Precision | Correct / fields we filled |
| Recall | Correct / fields that should be filled |
| Ungrounded rate | Values with no clipboard evidence — must be 0 |
| Escalation rate | Pastes needing the LLM |
| Latency p50 / p95 | Per paste and per stage |
| Cost per paste | Jev + LLM |

Normalised comparison by default, strict exact match alongside.

**Baselines:** do-nothing (recall 0), oracle (100%) to test the scorer; LLM-only
(Phase 1) as the number every later tier must beat.

**The loop:** run evals → read 20 failures by hand → group by cause → fix the biggest
group → re-run and check nothing regressed. Reading failures by hand is the habit
that matters most.

---

## 8. Observability and latency

Every paste writes one trace: per stage, its input summary, output summary, duration,
tokens/cost, errors. Store clipboard hashes by default, not raw text.

### Latency targets (p95, to be measured)

| Stage | Target |
| --- | --- |
| Schema extraction | 0 ms on the paste path (done on focus) |
| Extension → harness | < 20 ms local, < 80 ms hosted in India |
| Rules + segmenter | < 10 ms |
| Jev call | Measure (US-hosted today) |
| LLM call (escalated only) | Measure |
| Validate + ground | < 10 ms |
| **Total without LLM** | **< 300 ms** |
| **Total with LLM** | **< 1.2 s** |

Speed tricks to test once the baseline works: start the LLM in parallel with Jev on
messy input (cancel if Jev is confident); stream fields into the form as they're ready.

---

## 9. Adapters

Every surface is an adapter with two jobs: build a `FormSchema`, apply a `FillResult`.
The harness and evals don't change when an adapter is added.

| Adapter | Reads fields from | Writes by | When |
| --- | --- | --- | --- |
| Chrome extension | Page HTML | Native value setter + events | v1 |
| macOS menu bar app | Accessibility API (`AXUIElement` tree) | Setting AX value; typing fallback | v2 |
| macOS app integrations | The app's API | EventKit (Calendar, Reminders), Contacts | v2 |

### macOS specifics

- Needs Accessibility permission; distribute outside the Mac App Store.
- Electron apps (Slack, Notion, Discord) hide fields until `AXManualAccessibility` is set.
- Some apps ignore values set from outside → focus and type instead.
- Dropdowns: press the pop-up, pick the menu item.
- Thinner context than HTML (no `autocomplete`, `pattern`, often no labels).
- For Calendar / Contacts / Reminders, calling the API beats filling the UI.

### Jev vision on macOS (preview, Phase 6 experiments)

| Use | How |
| --- | --- |
| Screen fallback when AX tree is empty | Screenshot → Box "the PIN field" → click centre → type |
| Labelling unlabelled fields | Crop around field → Choice "name / phone / PIN / city / other?" |
| Checking a fill worked | Screenshot → Noul "is the PIN field filled with 6 digits?" |
| Image pastes | Choice "what is this?" → Box the useful region → OCR/LLM on the crop |

---

## 10. Build plan

Each phase ends with something working and a checkpoint you can explain in your own
words. Phase 1 is deliberately naive so every later tier is measured against it.

### Phase 0 — Contracts and the first 30 eval cases (week 1) ← current

- [x] Repo scaffold: contracts, case loader, example cases, scorer skeleton, runner,
      baselines, capture script, `CLAUDE.md`
- [ ] Implement `field_outcome()` and `compute_metrics()` in `evals/score.py`; all 17 tests pass
- [ ] Capture 5 real form schemas (address form, school/exam form, IRCTC passengers,
      Workday-style job form, simple contact form)
- [ ] Extend `LABELING_GUIDE.md` while labelling
- [ ] 30 cases (~10 per scenario), every case tagged with slices, fake data only
- [ ] Label 5 cases with a friend separately; fix the guide where you disagree

**Concepts:** eval-driven development, test-set coverage, contracts as the boundary
around uncertainty, reproducible snapshots, labelling ambiguity and inter-annotator
agreement, abstention as a skill, testing the test (do-nothing / oracle).

**Checkpoint:**
1. Why do evals exist before the pipeline?
2. What does high recall with a high confidently-wrong rate mean, and why is it dangerous?
3. Which cases do you expect to be hardest, and why?
4. Where do the contracts protect you from model errors?

### Phase 1 — LLM-only baseline, end to end (week 2)

- Minimal extension: extract schema, fill fields.
- Harness: schema + text → one LLM with structured output. No rules, no Jev.
- Run evals; record accuracy, confidently-wrong rate, latency. This is the number to beat.
- **Exercise:** change only the schema format (verbose vs compact) and measure.
- **Checkpoint:** you know where the baseline's time goes and which slices it fails.

### Phase 2 — Traces and the eval runner (week 3)

- Per-stage tracing, trace viewer, `compare.py` to diff runs case by case.
- **Checkpoint:** for any failing case, open its trace and name the stage that went wrong.

### Phase 3 — Rules, segmenter and Jev (weeks 4–5)

- Rules tier → segmenter + Jev → confidence gate with escalation to the LLM.
- Compare against Phase 1: accuracy, escalation rate, p95 latency, cost.
- Measure real Jev and LLM round trips from Chennai; finalise the LLM choice.
- **Exercise:** plot confidently-wrong rate against the gate threshold; pick the threshold from the curve.
- **Checkpoint:** show with numbers what each tier adds and costs.

### Phase 4 — Validation, repair and grounding (week 6)

- Validators, PIN → state check, one repair retry, grounding check, injection slice.
- **Exercise:** attack your own system with clipboard text; every working attack becomes a case.
- **Checkpoint:** ungrounded rate is 0 and you can explain why it can't rise silently.

### Phase 5 — Real-world hardening (week 7+)

- React/framework forms, iframes, `div` dropdowns, undo, "why" tooltip.
- Grow evals to ~200 cases from real failures.
- **Checkpoint:** works on 10 sites you didn't test during development.

### Phase 6 — macOS app (after v1 is solid)

- **Spike (2–3 days):** `pyobjc` — read and fill one native app form and one Electron app (Slack).
- **Build:** Swift menu bar app, global hotkey, AX reader/filler, typing fallback,
  send-to-Calendar and send-to-Contacts via APIs.
- **Vision experiments (Jev preview):** Box screen fallback, labelling unlabelled
  fields, screenshot checks after filling — each with its own eval slice.
- **Evals:** macOS `FormSchema` snapshots as their own slice.
- **Exercise:** same cases through browser vs macOS schema of the same kind of form; compare.
- **Checkpoint:** when to automate UI vs call an API, and when a vision call is worth its latency.

### After v1 — pick a stretch

Screenshots on the clipboard (multimodal + OCR), a local profile vault (memory +
privacy), or a new paste target such as invites → calendar.

---

## 11. Working setup

- **Repo:** <https://github.com/VatsalP117/smart-paste>
- **Coding:** Claude Code cloud sessions (run on the Pro/Max plan, share its usage
  limits, no separate container charge). `CLAUDE.md` tells sessions this is a
  learning project: explain choices, don't implement `TODO(you)` functions or write
  eval cases unless asked.
- **Learning split:** let Claude Code scaffold boilerplate; write contracts, the
  labelling guide, eval cases and scorer metrics yourself, and ask for reviews.
- **Secrets:** API keys in environment variables only (`.env.example`); never commit `.env`.

---

## 12. Open questions

- [ ] Which LLM? Decide from Phase 1 and Phase 3 eval runs.
- [ ] Jev latency from Chennai — if too slow, start the LLM in parallel more often.
- [ ] Where to host the harness once it leaves the laptop (India region).
- [ ] Segmenter for run-on text: rules only, Jev boundary questions, or straight to the LLM.
- [ ] Privacy stance: what users are told about which services see the clipboard;
      is a local-only mode (Gemini Nano) worth it?
- [ ] State fields: always full names, or match the form's own style?
- [ ] macOS: for Calendar/Contacts, when to fill the UI vs call the API.

---

## 13. Future project ideas

Not part of Smart Paste — saved for later.

| Idea | What it teaches |
| --- | --- |
| Scam shield for parents (SMS/WhatsApp scam warnings in Tamil/Hindi) | Calibrated classification, adversarial evals, false-positive trade-offs |
| Voice assistant grandparents can phone | Real-time voice latency, turn-taking, confirmation steps |
| "Can I cancel this?" fine-print reader | Grounded answers with citations, refusing to guess |
| A searchable memory of your own chats, notes, photos | Retrieval engineering, local-first privacy |
| Complaint agent that chases refunds | Long-running agents, browser automation, approval gates |
| Game with real-time thinking NPCs (Jev + LLM) | Real-time AI under a cost budget |
| Agent that improves itself against an eval suite | Automated prompt optimisation, overfitting, held-out sets |
| WhatsApp forward fact-checker | Claim decomposition, search grounding, calibrated "unverified" |
| Lab reports over the years | Messy extraction, unit normalisation, medical guardrails |
| Bank statement detective | LLM for understanding, code for arithmetic |
| Fridge-to-meals | Vision, preference memory, purchase approval |
| Tutor that finds your exact mistake | Multimodal reasoning, evaluating teaching quality |
| Codebase tour that verifies its claims by running code | Self-verifying agents |
| Indian-context LLM benchmark + leaderboard | Eval design at its deepest |
| Simulated customer interviews | Multi-agent simulation, persona consistency |
| Tiny on-device model for one task | Distillation, synthetic data, fine-tuning |
| Flight recorder for AI agents | Observability as a product |

Top picks: scam shield (impact), voice assistant (hardest engineering), self-improving
agent (natural follow-on to Smart Paste's evals), Indian-context benchmark (career).
