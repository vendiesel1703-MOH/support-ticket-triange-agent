"""
ticket_agent.py

Core logic for the Support Ticket Triage Agent.

Pipeline:
    ticket (subject + body)
        -> LLM classification call (local Ollama)
        -> parsed JSON: category, urgency, confidence, reasoning
        -> routing decision (category -> team)
        -> "unsure" flag if confidence < threshold

This module has no UI dependency so it can be used from the CLI,
Streamlit app, or a test script equally.
"""

import json
import re
import requests

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3"          # change to whatever you've pulled, e.g. "mistral", "phi3"
CONFIDENCE_THRESHOLD = 0.6        # below this -> flagged for human review

CATEGORIES = [
    "Billing",
    "Technical / Bug",
    "Account & Access",
    "Feature Request",
    "General Feedback",
    "Other",
]

URGENCY_LEVELS = ["Low", "Medium", "High", "Critical"]

# Category -> owning team. This is the "routing table" — in a real system
# this might come from a config file or a ticketing platform's own taxonomy.
ROUTING_TABLE = {
    "Billing": "Billing & Payments Team",
    "Technical / Bug": "Engineering / Support Tier 2",
    "Account & Access": "Account Support Team",
    "Feature Request": "Product Team",
    "General Feedback": "Customer Success",
    "Other": "General Support Queue",
}

SYSTEM_PROMPT = f"""You are a support ticket triage assistant for a SaaS company.

Given a ticket's subject and body, classify it and respond with ONLY a
single valid JSON object — no markdown fences, no extra text. The JSON
object must have exactly these keys:

- "category": one of {CATEGORIES}
- "urgency": one of {URGENCY_LEVELS}
- "confidence": a number between 0.0 and 1.0 representing how confident
  you are in this category AND urgency assignment together
- "reasoning": a one-sentence explanation of your classification

Guidance for urgency:
- "Critical": production/business-critical outage, active data loss, security issue
- "High": blocks the user from core functionality, time-sensitive
- "Medium": impacts the user but has a workaround or isn't time-critical
- "Low": cosmetic, informational, or a nice-to-have request

Guidance for confidence:
- Use a LOWER confidence (below 0.5) when the ticket is vague, could
  plausibly fit multiple categories, or lacks enough detail to be sure.
- Use a HIGH confidence (above 0.8) only when the category and urgency
  are unambiguous from the text.

Respond with ONLY the JSON object.
"""


class TriageError(Exception):
    """Raised when the agent cannot get a usable classification."""


def _extract_json(text: str) -> dict:
    """
    LLMs (especially smaller local models) sometimes wrap JSON in
    markdown fences or add a stray sentence. This pulls out the first
    {...} block and parses it, rather than trusting the raw output.
    """
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise TriageError(f"No JSON object found in model output: {text[:200]!r}")

    return json.loads(match.group(0))


def classify_ticket(subject: str, body: str, model: str = DEFAULT_MODEL, timeout: int = 60) -> dict:
    """
    Calls the local Ollama model and returns a structured classification.

    Returns a dict:
        {
            "category": str,
            "urgency": str,
            "confidence": float,
            "reasoning": str,
            "routing_team": str,
            "needs_human_review": bool,
        }

    Raises TriageError if Ollama is unreachable or returns unparseable output.
    """
    user_content = f"Subject: {subject}\n\nBody: {body}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "format": "json",  # Ollama structured-output hint (supported models honor this)
        "options": {"temperature": 0.1},
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        raise TriageError(
            "Could not reach Ollama at http://localhost:11434 — "
            "is `ollama serve` running and did you `ollama pull "
            f"{model}`?"
        ) from e
    except requests.exceptions.RequestException as e:
        raise TriageError(f"Ollama request failed: {e}") from e

    raw_content = resp.json().get("message", {}).get("content", "")

    try:
        parsed = _extract_json(raw_content)
    except (json.JSONDecodeError, TriageError) as e:
        raise TriageError(f"Failed to parse model output as JSON: {e}") from e

    category = parsed.get("category", "Other")
    if category not in CATEGORIES:
        category = "Other"

    urgency = parsed.get("urgency", "Medium")
    if urgency not in URGENCY_LEVELS:
        urgency = "Medium"

    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    reasoning = parsed.get("reasoning", "").strip()

    return {
        "category": category,
        "urgency": urgency,
        "confidence": round(confidence, 2),
        "reasoning": reasoning,
        "routing_team": ROUTING_TABLE.get(category, "General Support Queue"),
        "needs_human_review": confidence < CONFIDENCE_THRESHOLD,
    }


def classify_batch(tickets: list, model: str = DEFAULT_MODEL) -> list:
    """
    tickets: list of dicts with at least 'subject' and 'body' keys
             (an optional 'ticket_id' is passed through if present).

    Returns a list of result dicts, each merging the input ticket with
    its classification. Individual ticket failures do not stop the batch —
    they are recorded with an 'error' field instead.
    """
    results = []
    for ticket in tickets:
        row = dict(ticket)
        try:
            classification = classify_ticket(ticket["subject"], ticket["body"], model=model)
            row.update(classification)
            row["error"] = None
        except TriageError as e:
            row.update(
                {
                    "category": None,
                    "urgency": None,
                    "confidence": None,
                    "reasoning": None,
                    "routing_team": None,
                    "needs_human_review": True,
                    "error": str(e),
                }
            )
        results.append(row)
    return results
