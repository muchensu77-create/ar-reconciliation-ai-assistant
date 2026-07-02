from __future__ import annotations

import pandas as pd


def build_exception_memo(summary: dict, unmatched_invoices: pd.DataFrame, unmatched_receipts: pd.DataFrame) -> str:
    high_priority = _count_priority(unmatched_invoices, "high")
    medium_priority = _count_priority(unmatched_invoices, "medium")
    open_amount = summary.get("open_invoice_amount", 0)
    unapplied_amount = summary.get("unapplied_receipt_amount", 0)

    lines = [
        "# AR Reconciliation Review Memo",
        "",
        f"As of {summary.get('as_of')}, {summary.get('matched_invoice_count')} invoices were matched.",
        f"Open invoice amount: {open_amount:,.2f}. Unapplied receipt amount: {unapplied_amount:,.2f}.",
        "",
        "Recommended follow-up:",
    ]

    if high_priority:
        lines.append(f"- Review {high_priority} high-priority overdue invoice(s) first.")
    if medium_priority:
        lines.append(f"- Check {medium_priority} medium-priority invoice(s) and confirm expected collection date.")
    if len(unmatched_receipts):
        lines.append(f"- Review {len(unmatched_receipts)} receipt(s) that have not been applied to an invoice.")
    if not high_priority and not medium_priority and not len(unmatched_receipts):
        lines.append("- No urgent exception was found in the sample data.")

    lines.extend(
        [
            "",
            "Manual review reminder:",
            "- Confirm customer names, invoice references, amounts, and receipt dates before posting adjustments.",
            "- Do not rely on AI output for accounting judgement without checking source documents.",
        ]
    )
    return "\n".join(lines)


def build_safe_ai_prompt(summary: dict, aging: pd.DataFrame) -> str:
    aging_text = aging.to_csv(index=False)
    return f"""You are helping an accounting assistant draft a short AR follow-up note.

Use only the aggregated reconciliation data below. Do not invent customer names, amounts, or payment promises.

Summary:
{summary}

Aging:
{aging_text}

Draft:
1. A concise review summary.
2. The main follow-up priorities.
3. A reminder that finance staff should manually verify source documents.
"""


def _count_priority(df: pd.DataFrame, priority: str) -> int:
    if df.empty or "follow_up_priority" not in df.columns:
        return 0
    return int((df["follow_up_priority"] == priority).sum())

