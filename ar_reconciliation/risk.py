from __future__ import annotations

import pandas as pd

from .config import ReconciliationConfig


def aging_bucket(days_overdue: int, config: ReconciliationConfig) -> str:
    for bucket, lower, upper in config.aging_buckets:
        if lower is None and days_overdue <= (upper or 0):
            return bucket
        if upper is None and days_overdue >= (lower or 0):
            return bucket
        if lower is not None and upper is not None and lower <= days_overdue <= upper:
            return bucket
    return "unclassified"


def score_invoice_exception(row: pd.Series, config: ReconciliationConfig) -> int:
    days_overdue = int(row.get("days_overdue", 0) or 0)
    amount = float(row.get("amount", 0) or 0)
    score = 0

    if days_overdue > 90:
        score += 50
    elif days_overdue > 60:
        score += 38
    elif days_overdue > 30:
        score += 24
    elif days_overdue > 0:
        score += 12

    if amount >= config.high_value_threshold:
        score += 35
    elif amount >= config.medium_value_threshold:
        score += 20
    else:
        score += 8

    if row.get("suggested_receipt_ids"):
        score += 10

    return min(score, 100)


def score_receipt_exception(row: pd.Series, config: ReconciliationConfig) -> int:
    amount = float(row.get("amount", 0) or 0)
    score = 20
    if amount >= config.high_value_threshold:
        score += 40
    elif amount >= config.medium_value_threshold:
        score += 25
    if not str(row.get("reference", "")).strip():
        score += 15
    return min(score, 100)


def priority_from_score(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "normal"


def owner_action(exception_type: str) -> str:
    actions = {
        "open_invoice": "Confirm collection status or expected payment date.",
        "partial_payment_candidate": "Verify whether receipts are partial payments and update remaining balance.",
        "unapplied_receipt": "Identify customer or invoice reference before applying receipt.",
        "data_quality": "Correct source data and rerun reconciliation.",
    }
    return actions.get(exception_type, "Review source documents.")

