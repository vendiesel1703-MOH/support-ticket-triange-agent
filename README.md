# Support Ticket Triage Agent

Classifies incoming support tickets by **category** and **urgency**, assigns a
**confidence score**, routes each ticket to the right team, and flags
low-confidence tickets for **human review** instead of guessing.

Built for the Rooman Technologies 24-Hour AI Agent Challenge.

---

## What it takes / produces

> This agent takes a ticket (subject + body) and produces a category, an
> urgency level, a routing decision, a confidence score, and a one-line
> reasoning — flagging the ticket for human review when confidence is low.

---

## How it works

```
ticket (subject + body)
        │
        ▼
  system prompt + ticket sent to a LOCAL LLM via Ollama
        │
        ▼
  model returns strict JSON: {category, urgency, confidence, reasoning}
        │
        ▼
  category → routing_table → owning team
  confidence < 0.6          → needs_human_review = True
        │
        ▼
  structured result (per ticket, or batch CSV)
```

All the "intelligence" lives in the system prompt in `ticket_agent.py` — no
training or fine-tuning involved. The Python code around it is the "glue":
calling the model, validating its output, applying the routing table, and
applying the confidence threshold.

---

## Setup

### 1. Install Ollama and pull a model
This agent runs entirely against a **local** model — no API key needed.

```bash
# install Ollama: https://ollama.com/download
ollama serve            # starts the local server on :11434
ollama pull llama3      # or: mistral, phi3, qwen2.5, etc.
```

Any Ollama-supported model works — just make sure the name matches what you
pass to the app/CLI (default is `llama3`).

### 2. Install Python dependencies

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run it

**Web UI (recommended for demoing):**
```bash
streamlit run app.py
```
Open the local URL Streamlit prints, upload a CSV (or click "Use bundled
sample_tickets.csv"), and hit **Run triage on this batch**. There's also a
**Single ticket test** tab for quick one-off checks.

**CLI (for batch runs / scripting):**
```bash
python run_batch.py data/sample_tickets.csv --model llama3 --out triage_results.csv
```

---

## Files

| File | Purpose |
|---|---|
| `ticket_agent.py` | Core agent: prompt, Ollama call, JSON parsing, routing, confidence logic |
| `app.py` | Streamlit UI — batch view + single-ticket tester |
| `run_batch.py` | CLI batch runner over a CSV |
| `data/sample_tickets.csv` | 10 sample tickets spanning categories, urgencies, and one deliberately vague ticket |
| `data/example_output_reference.csv` | Hand-authored reference showing the **expected shape** of output (see note below) — not a captured run |

> **Note on the reference output:** `example_output_reference.csv` was
> authored by hand to show reviewers the expected output shape and reasoning
> style before running anything. It is **not** a captured run of the live
> agent, since this repo was built in an environment without a running local
> Ollama instance to call. Running `python run_batch.py data/sample_tickets.csv`
> (or the Streamlit batch tab) after setup produces the real, model-generated
> output — that's the one to evaluate.

---

## Decision boundary: how routing and "needs review" are decided

**Category → team routing** is a simple fixed lookup table
(`ROUTING_TABLE` in `ticket_agent.py`):

| Category | Team |
|---|---|
| Billing | Billing & Payments Team |
| Technical / Bug | Engineering / Support Tier 2 |
| Account & Access | Account Support Team |
| Feature Request | Product Team |
| General Feedback | Customer Success |
| Other | General Support Queue |

**Urgency** is defined in the prompt with concrete anchors (production
outage / data loss / security → Critical; blocks core functionality →
High; has a workaround → Medium; cosmetic/informational → Low) rather than
left to the model's own judgment of what "urgent" means.

**"Needs human review"** is a single rule: `confidence < 0.6`. The model is
explicitly instructed to lower its own confidence when a ticket is vague or
could plausibly fit more than one category (see `T-008` in the sample set —
"Weird behavior... not sure what exactly"). This threshold is intentionally
a knob, not a hardcoded assumption: raise it for a stricter reviewer-heavy
workflow, lower it to trust the model more.

Any ticket where the model's output can't be parsed as valid JSON is also
routed to human review with the parse error preserved, rather than silently
dropped or force-guessed into a category.

---

## Design tradeoffs & what I'd improve with more time

- **Local model choice over an API.** Chose Ollama for zero API cost and no
  key management, at the cost of classification quality varying by which
  model you pull — a small local model may be less reliable at strict JSON
  formatting than GPT-4/Claude. Mitigated with `format: "json"`, a low
  temperature (0.1), and a regex fallback that extracts the first `{...}`
  block even if the model adds stray text.
- **Confidence is self-reported by the model**, not derived from a separate
  calibration step (e.g. comparing against a held-out labeled set). This is
  fast to build but not a true statistical confidence — with more time I'd
  validate it against a small hand-labeled set and calibrate the threshold
  empirically rather than picking 0.6 by feel.
- **Fixed category list** rather than an open-ended one. Keeps routing
  deterministic and the routing table simple, but a ticket that doesn't
  cleanly fit any of the six categories gets forced into "Other" — with more
  time I'd let the model propose new categories above a frequency threshold
  for human review.
- **No retry/backoff on transient Ollama failures** — a single failed call
  is recorded as an error and routed to human review rather than retried.
  Fine for a 24h build; a production version would retry with backoff
  before giving up.
- **Batch processing is sequential**, not parallelized. Fine for 10-50
  tickets; a real high-volume triage system would batch/parallelize calls
  or use a queue.
