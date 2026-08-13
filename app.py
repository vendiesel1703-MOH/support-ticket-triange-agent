"""
app.py

Streamlit UI for the Support Ticket Triage Agent.

Run with:
    streamlit run app.py

Requires a local Ollama server running (`ollama serve`) with a model
pulled (default: llama3 — change DEFAULT_MODEL in ticket_agent.py or
pick a different one in the sidebar).
"""

import pandas as pd
import streamlit as st

from ticket_agent import classify_batch, classify_ticket, TriageError, DEFAULT_MODEL

st.set_page_config(page_title="Support Ticket Triage Agent", page_icon="🎫", layout="wide")

URGENCY_COLORS = {
    "Critical": "#e03131",
    "High": "#f08c00",
    "Medium": "#1971c2",
    "Low": "#2f9e44",
}


def urgency_badge(urgency: str) -> str:
    color = URGENCY_COLORS.get(urgency, "#868e96")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:0.85em;">{urgency}</span>'


st.title("🎫 Support Ticket Triage Agent")
st.caption("Classifies tickets by category + urgency, routes them to a team, and flags low-confidence cases for human review.")

with st.sidebar:
    st.header("Settings")
    model = st.text_input("Ollama model", value=DEFAULT_MODEL, help="Must already be pulled, e.g. `ollama pull llama3`")
    st.markdown("---")
    st.markdown(
        "**Setup reminder**\n\n"
        "1. `ollama serve` running\n"
        "2. `ollama pull " + model + "`\n"
        "3. This app talks to `localhost:11434`"
    )

tab1, tab2 = st.tabs(["📦 Batch triage", "🔍 Single ticket test"])

# --------------------------------------------------------------------
# Tab 1: batch
# --------------------------------------------------------------------
with tab1:
    st.subheader("Batch triage from CSV")
    uploaded = st.file_uploader("Upload a CSV with 'subject' and 'body' columns", type="csv")
    use_sample = st.button("Use bundled sample_tickets.csv instead")

    df = None
    if uploaded is not None:
        df = pd.read_csv(uploaded)
    elif use_sample:
        df = pd.read_csv("data/sample_tickets.csv")

    if df is not None:
        if not {"subject", "body"}.issubset(df.columns):
            st.error(f"CSV must contain 'subject' and 'body' columns. Found: {list(df.columns)}")
        else:
            st.write(f"Loaded {len(df)} tickets.")
            if st.button("Run triage on this batch", type="primary"):
                tickets = df.to_dict(orient="records")
                progress = st.progress(0.0, text="Starting...")
                results = []
                for i, t in enumerate(tickets):
                    try:
                        classification = classify_ticket(t["subject"], t["body"], model=model)
                        row = {**t, **classification, "error": None}
                    except TriageError as e:
                        row = {
                            **t,
                            "category": None,
                            "urgency": None,
                            "confidence": None,
                            "reasoning": None,
                            "routing_team": None,
                            "needs_human_review": True,
                            "error": str(e),
                        }
                    results.append(row)
                    progress.progress((i + 1) / len(tickets), text=f"Triaging ticket {i + 1}/{len(tickets)}")

                result_df = pd.DataFrame(results)
                st.session_state["last_results"] = result_df

    if "last_results" in st.session_state:
        result_df = st.session_state["last_results"]

        n_review = int(result_df["needs_human_review"].sum()) if "needs_human_review" in result_df else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Tickets processed", len(result_df))
        c2.metric("Flagged for human review", n_review)
        c3.metric("Errors", int(result_df["error"].notna().sum()) if "error" in result_df else 0)

        st.markdown("### Results")
        for _, row in result_df.iterrows():
            with st.container(border=True):
                left, right = st.columns([4, 1])
                with left:
                    st.markdown(f"**{row.get('ticket_id', '')} — {row['subject']}**")
                    st.caption(row["body"])
                    if row.get("error"):
                        st.error(row["error"])
                    else:
                        st.markdown(
                            f"{urgency_badge(row['urgency'])} &nbsp; **{row['category']}** &nbsp; "
                            f"→ routed to *{row['routing_team']}*",
                            unsafe_allow_html=True,
                        )
                        st.caption(f"Confidence: {row['confidence']} — {row['reasoning']}")
                        if row["needs_human_review"]:
                            st.warning("⚠️ Flagged for human review (low confidence)")
                with right:
                    st.metric("Confidence", row.get("confidence", "—"))

        csv_bytes = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download results as CSV", csv_bytes, "triage_results.csv", "text/csv")

# --------------------------------------------------------------------
# Tab 2: single ticket
# --------------------------------------------------------------------
with tab2:
    st.subheader("Test a single ticket")
    subject = st.text_input("Subject", value="Cannot log into my account")
    body = st.text_area(
        "Body",
        value="I have tried resetting my password three times but still get 'invalid credentials'. "
        "This is blocking an important client demo in 2 hours.",
        height=120,
    )

    if st.button("Classify this ticket", type="primary"):
        with st.spinner("Calling local model..."):
            try:
                result = classify_ticket(subject, body, model=model)
            except TriageError as e:
                st.error(str(e))
            else:
                st.markdown(
                    f"{urgency_badge(result['urgency'])} &nbsp; **{result['category']}**",
                    unsafe_allow_html=True,
                )
                st.write(f"**Routed to:** {result['routing_team']}")
                st.write(f"**Confidence:** {result['confidence']}")
                st.write(f"**Reasoning:** {result['reasoning']}")
                if result["needs_human_review"]:
                    st.warning("⚠️ Flagged for human review (confidence below threshold)")
