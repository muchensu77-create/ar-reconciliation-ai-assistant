from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import re

import pandas as pd

from .config import ReconciliationConfig


@dataclass(frozen=True)
class MatchDecision:
    invoice_id: str
    receipt_ids: list[str]
    match_type: str
    confidence: int
    reason: str
    receipt_amount: float
    difference: float


def match_invoices(invoice_df: pd.DataFrame, receipt_df: pd.DataFrame, config: ReconciliationConfig) -> tuple[pd.DataFrame, set[str], set[str]]:
    used_receipts: set[str] = set()
    matched_invoices: set[str] = set()
    decisions: list[dict] = []

    for _, invoice in invoice_df.sort_values(["due_date", "invoice_id"]).iterrows():
        available = receipt_df[~receipt_df["receipt_id"].isin(used_receipts)].copy()
        decision = _match_one(invoice, available, config)
        if decision is None:
            continue

        matched_invoices.add(decision.invoice_id)
        used_receipts.update(decision.receipt_ids)
        decisions.append(_match_row(invoice, decision, receipt_df))

    return pd.DataFrame(decisions), matched_invoices, used_receipts


def suggest_partial_payments(unmatched_invoices: pd.DataFrame, unmatched_receipts: pd.DataFrame, config: ReconciliationConfig) -> pd.DataFrame:
    if unmatched_invoices.empty:
        return unmatched_invoices

    output = unmatched_invoices.copy()
    output["suggested_receipt_ids"] = ""
    output["suggested_receipt_amount"] = 0.0
    output["remaining_amount_after_suggestion"] = output["amount"].round(2)
    output["exception_type"] = "open_invoice"

    for idx, invoice in output.iterrows():
        same_customer = unmatched_receipts[unmatched_receipts["customer_key"] == invoice["customer_key"]]
        if same_customer.empty:
            continue
        candidate = same_customer.sort_values("receipt_date")
        running = []
        total = 0.0
        for _, receipt in candidate.iterrows():
            if total + float(receipt["amount"]) <= float(invoice["amount"]):
                running.append(str(receipt["receipt_id"]))
                total += float(receipt["amount"])
        ratio = total / float(invoice["amount"]) if float(invoice["amount"]) else 0
        if running and ratio >= config.partial_payment_min_ratio:
            output.at[idx, "suggested_receipt_ids"] = ", ".join(running)
            output.at[idx, "suggested_receipt_amount"] = round(total, 2)
            output.at[idx, "remaining_amount_after_suggestion"] = round(float(invoice["amount"]) - total, 2)
            output.at[idx, "exception_type"] = "partial_payment_candidate"
    return output


def _match_one(invoice: pd.Series, receipts: pd.DataFrame, config: ReconciliationConfig) -> MatchDecision | None:
    amount = float(invoice["amount"])
    invoice_id = str(invoice["invoice_id"])
    same_customer = receipts[receipts["customer_key"] == invoice["customer_key"]]
    same_window = _within_date_window(same_customer, invoice, config)

    exact_ref = receipts[
        receipts["reference"].str.contains(re.escape(invoice_id), case=False, na=False)
        & receipts["amount"].map(lambda value: _same_amount(value, amount, config.amount_tolerance))
    ]
    if not exact_ref.empty:
        receipt = exact_ref.sort_values("receipt_date").iloc[0]
        return MatchDecision(
            invoice_id,
            [str(receipt["receipt_id"])],
            "invoice_reference",
            98,
            "Invoice ID appears in receipt reference and amount matches.",
            float(receipt["amount"]),
            round(amount - float(receipt["amount"]), 2),
        )

    customer_amount = same_window[same_window["amount"].map(lambda value: _same_amount(value, amount, config.amount_tolerance))]
    if not customer_amount.empty:
        receipt = customer_amount.sort_values("receipt_date").iloc[0]
        return MatchDecision(
            invoice_id,
            [str(receipt["receipt_id"])],
            "customer_amount_date_window",
            88,
            "Customer, amount, and receipt date are within configured window.",
            float(receipt["amount"]),
            round(amount - float(receipt["amount"]), 2),
        )

    grouped = _find_grouped_receipts(same_window, amount, config)
    if grouped:
        receipt_ids = [str(receipt["receipt_id"]) for receipt in grouped]
        total = sum(float(receipt["amount"]) for receipt in grouped)
        return MatchDecision(
            invoice_id,
            receipt_ids,
            "grouped_receipts",
            82,
            "Multiple receipts from the same customer sum to the invoice amount.",
            round(total, 2),
            round(amount - total, 2),
        )

    return None


def _within_date_window(receipts: pd.DataFrame, invoice: pd.Series, config: ReconciliationConfig) -> pd.DataFrame:
    start = invoice["invoice_date"]
    end = invoice["due_date"] + pd.Timedelta(days=config.date_window_days)
    return receipts[(receipts["receipt_date"] >= start) & (receipts["receipt_date"] <= end)]


def _find_grouped_receipts(receipts: pd.DataFrame, target_amount: float, config: ReconciliationConfig) -> list[pd.Series]:
    rows = [row for _, row in receipts.sort_values("receipt_date").iterrows()]
    max_size = min(config.grouped_receipt_max_size, len(rows))
    for size in range(2, max_size + 1):
        for group in combinations(rows, size):
            total = sum(float(row["amount"]) for row in group)
            if _same_amount(total, target_amount, config.amount_tolerance):
                return list(group)
    return []


def _same_amount(left: float, right: float, tolerance: float) -> bool:
    return abs(round(float(left) - float(right), 2)) <= tolerance


def _match_row(invoice: pd.Series, decision: MatchDecision, receipt_df: pd.DataFrame) -> dict:
    receipts = receipt_df[receipt_df["receipt_id"].astype(str).isin(decision.receipt_ids)].sort_values("receipt_date")
    return {
        "invoice_id": invoice["invoice_id"],
        "customer": invoice["customer"],
        "invoice_date": invoice["invoice_date"].date().isoformat(),
        "due_date": invoice["due_date"].date().isoformat(),
        "invoice_amount": round(float(invoice["amount"]), 2),
        "receipt_ids": ", ".join(decision.receipt_ids),
        "receipt_dates": ", ".join(receipts["receipt_date"].dt.date.astype(str)),
        "receipt_amount": round(decision.receipt_amount, 2),
        "difference": round(decision.difference, 2),
        "match_type": decision.match_type,
        "confidence": decision.confidence,
        "match_reason": decision.reason,
    }

