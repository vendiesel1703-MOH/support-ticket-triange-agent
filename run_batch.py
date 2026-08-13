"""
run_batch.py

Command-line batch runner. Reads a CSV of tickets (subject, body columns
required; ticket_id optional), classifies every ticket, and writes a
results CSV.

Usage:
    python run_batch.py data/sample_tickets.csv
    python run_batch.py data/sample_tickets.csv --model mistral --out results.csv
"""

import argparse
import sys

import pandas as pd

from ticket_agent import classify_batch, DEFAULT_MODEL


def main():
    parser = argparse.ArgumentParser(description="Batch-triage support tickets via a local Ollama model.")
    parser.add_argument("input_csv", help="Path to a CSV with 'subject' and 'body' columns")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--out", default="triage_results.csv", help="Path to write the results CSV")
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.input_csv)
    except FileNotFoundError:
        print(f"Error: could not find {args.input_csv}", file=sys.stderr)
        sys.exit(1)

    required_cols = {"subject", "body"}
    if not required_cols.issubset(df.columns):
        print(f"Error: CSV must contain columns {required_cols}, found {list(df.columns)}", file=sys.stderr)
        sys.exit(1)

    tickets = df.to_dict(orient="records")
    print(f"Triaging {len(tickets)} tickets with model '{args.model}'...")

    results = classify_batch(tickets, model=args.model)

    out_df = pd.DataFrame(results)
    out_df.to_csv(args.out, index=False)

    n_review = out_df["needs_human_review"].sum() if "needs_human_review" in out_df else 0
    print(f"Done. Wrote {len(out_df)} results to {args.out}")
    print(f"{n_review} ticket(s) flagged for human review (low confidence or error).")


if __name__ == "__main__":
    main()
