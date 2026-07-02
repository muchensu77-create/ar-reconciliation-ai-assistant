from __future__ import annotations

import pandas as pd


def build_exception_memo(
    summary: dict,
    unmatched_invoices: pd.DataFrame,
    unmatched_receipts: pd.DataFrame,
    exception_queue: pd.DataFrame | None = None,
) -> str:
    high_priority = _count_priority(unmatched_invoices, "high")
    medium_priority = _count_priority(unmatched_invoices, "medium")
    open_amount = summary.get("open_invoice_amount", 0)
    unapplied_amount = summary.get("unapplied_receipt_amount", 0)

    exception_queue = exception_queue if exception_queue is not None else pd.DataFrame()
    high_risk = int(summary.get("high_risk_exception_count", 0) or 0)
    data_quality = int(summary.get("data_quality_issue_count", 0) or 0)

    lines = [
        "# AR Reconciliation Review Memo",
        "",
        f"As of {summary.get('as_of')}, {summary.get('matched_invoice_count')} invoices were matched.",
        f"Open invoice amount: {open_amount:,.2f}. Unapplied receipt amount: {unapplied_amount:,.2f}.",
        f"Exception count: {summary.get('exception_count', 0)}. High-risk exceptions: {high_risk}. Data quality issues: {data_quality}.",
        "",
        "Recommended follow-up:",
    ]

    if high_priority:
        lines.append(f"- Review {high_priority} high-priority overdue invoice(s) first.")
    if medium_priority:
        lines.append(f"- Check {medium_priority} medium-priority invoice(s) and confirm expected collection date.")
    if len(unmatched_receipts):
        lines.append(f"- Review {len(unmatched_receipts)} receipt(s) that have not been applied to an invoice.")
    if not exception_queue.empty:
        top = exception_queue.head(3)
        lines.append("- Review the top exception queue items first:")
        for _, row in top.iterrows():
            lines.append(
                f"  - {row['source_id']} | {row['customer']} | {row['amount']:,.2f} | {row['priority']} priority | {row['owner_action']}"
            )
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


def build_control_checklist(summary: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "control": "Source completeness",
                "check": "Invoice and receipt exports were loaded with required columns.",
                "status": "review" if summary.get("data_quality_issue_count", 0) else "ok",
            },
            {
                "control": "Automated matching",
                "check": "Matched invoices were assigned a rule and confidence score.",
                "status": "ok",
            },
            {
                "control": "Exception ownership",
                "check": "Open invoices and unapplied receipts were added to an exception queue.",
                "status": "review" if summary.get("exception_count", 0) else "ok",
            },
            {
                "control": "AI review boundary",
                "check": "AI notes are treated as drafting support; amounts and accounting decisions require manual review.",
                "status": "ok",
            },
        ]
    )


def _count_priority(df: pd.DataFrame, priority: str) -> int:
    if df.empty or "follow_up_priority" not in df.columns:
        return 0
    return int((df["follow_up_priority"] == priority).sum())
