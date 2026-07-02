from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import combinations
import re

import pandas as pd


AGING_ORDER = ["not_due", "0_30", "31_60", "61_90", "over_90"]


@dataclass
class ReconciliationResult:
    summary: dict
    matches: pd.DataFrame
    unmatched_invoices: pd.DataFrame
    unmatched_receipts: pd.DataFrame
    aging: pd.DataFrame


def normalize_customer(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text)
    return text


def _prepare_invoices(invoices: pd.DataFrame) -> pd.DataFrame:
    required = {"invoice_id", "customer", "invoice_date", "due_date", "amount"}
    missing = required - set(invoices.columns)
    if missing:
        raise ValueError(f"Missing invoice columns: {', '.join(sorted(missing))}")

    prepared = invoices.copy()
    prepared["invoice_id"] = prepared["invoice_id"].astype(str).str.strip()
    prepared["customer_key"] = prepared["customer"].map(normalize_customer)
    prepared["invoice_date"] = pd.to_datetime(prepared["invoice_date"])
    prepared["due_date"] = pd.to_datetime(prepared["due_date"])
    prepared["amount"] = pd.to_numeric(prepared["amount"]).round(2)
    return prepared


def _prepare_receipts(receipts: pd.DataFrame) -> pd.DataFrame:
    required = {"receipt_id", "customer", "receipt_date", "amount", "reference"}
    missing = required - set(receipts.columns)
    if missing:
        raise ValueError(f"Missing receipt columns: {', '.join(sorted(missing))}")

    prepared = receipts.copy()
    prepared["receipt_id"] = prepared["receipt_id"].astype(str).str.strip()
    prepared["reference"] = prepared["reference"].fillna("").astype(str)
    prepared["customer_key"] = prepared["customer"].map(normalize_customer)
    prepared["receipt_date"] = pd.to_datetime(prepared["receipt_date"])
    prepared["amount"] = pd.to_numeric(prepared["amount"]).round(2)
    return prepared


def _same_amount(left: float, right: float, tolerance: float) -> bool:
    return abs(round(float(left) - float(right), 2)) <= tolerance


def _aging_bucket(days_overdue: int) -> str:
    if days_overdue <= 0:
        return "not_due"
    if days_overdue <= 30:
        return "0_30"
    if days_overdue <= 60:
        return "31_60"
    if days_overdue <= 90:
        return "61_90"
    return "over_90"


def reconcile(
    invoices: pd.DataFrame,
    receipts: pd.DataFrame,
    as_of: date | str | None = None,
    tolerance: float = 0.01,
) -> ReconciliationResult:
    invoice_df = _prepare_invoices(invoices)
    receipt_df = _prepare_receipts(receipts)

    as_of_date = pd.Timestamp(as_of or date.today()).normalize()
    used_receipts: set[str] = set()
    match_rows: list[dict] = []
    invoice_df = invoice_df.sort_values(["due_date", "invoice_id"])

    for _, invoice in invoice_df.iterrows():
        invoice_id = invoice["invoice_id"]
        amount = float(invoice["amount"])
        customer_key = invoice["customer_key"]

        available = receipt_df[~receipt_df["receipt_id"].isin(used_receipts)].copy()
        exact_ref = available[
            available["reference"].str.contains(re.escape(invoice_id), case=False, na=False)
            & available["amount"].map(lambda value: _same_amount(value, amount, tolerance))
        ]

        if not exact_ref.empty:
            receipt = exact_ref.sort_values("receipt_date").iloc[0]
            used_receipts.add(receipt["receipt_id"])
            match_rows.append(
                _match_row(invoice, [receipt], "invoice_reference", amount, float(receipt["amount"]))
            )
            continue

        same_customer = available[available["customer_key"] == customer_key]
        same_amount = same_customer[same_customer["amount"].map(lambda value: _same_amount(value, amount, tolerance))]
        if not same_amount.empty:
            receipt = same_amount.sort_values("receipt_date").iloc[0]
            used_receipts.add(receipt["receipt_id"])
            match_rows.append(_match_row(invoice, [receipt], "customer_amount", amount, float(receipt["amount"])))
            continue

        grouped = _find_grouped_receipts(same_customer, amount, tolerance)
        if grouped:
            for receipt in grouped:
                used_receipts.add(receipt["receipt_id"])
            total = sum(float(receipt["amount"]) for receipt in grouped)
            match_rows.append(_match_row(invoice, grouped, "grouped_receipts", amount, total))

    matches = pd.DataFrame(match_rows)
    matched_invoice_ids = set(matches["invoice_id"]) if not matches.empty else set()

    unmatched_invoices = invoice_df[~invoice_df["invoice_id"].isin(matched_invoice_ids)].copy()
    if unmatched_invoices.empty:
        unmatched_invoices = pd.DataFrame(
            columns=list(invoice_df.columns) + ["days_overdue", "aging_bucket", "follow_up_priority"]
        )
    else:
        unmatched_invoices["days_overdue"] = (as_of_date - unmatched_invoices["due_date"]).dt.days
        unmatched_invoices["aging_bucket"] = unmatched_invoices["days_overdue"].map(_aging_bucket)
        unmatched_invoices["follow_up_priority"] = unmatched_invoices["days_overdue"].map(_priority)

    unmatched_receipts = receipt_df[~receipt_df["receipt_id"].isin(used_receipts)].copy()

    aging = _aging_summary(unmatched_invoices)
    summary = {
        "invoice_count": int(len(invoice_df)),
        "receipt_count": int(len(receipt_df)),
        "matched_invoice_count": int(len(matched_invoice_ids)),
        "unmatched_invoice_count": int(len(unmatched_invoices)),
        "unmatched_receipt_count": int(len(unmatched_receipts)),
        "matched_amount": round(float(matches["invoice_amount"].sum()) if not matches.empty else 0.0, 2),
        "open_invoice_amount": round(float(unmatched_invoices["amount"].sum()) if not unmatched_invoices.empty else 0.0, 2),
        "unapplied_receipt_amount": round(float(unmatched_receipts["amount"].sum()) if not unmatched_receipts.empty else 0.0, 2),
        "as_of": str(as_of_date.date()),
    }

    return ReconciliationResult(
        summary=summary,
        matches=matches,
        unmatched_invoices=_display_invoice_columns(unmatched_invoices),
        unmatched_receipts=_display_receipt_columns(unmatched_receipts),
        aging=aging,
    )


def _match_row(invoice: pd.Series, receipts: list[pd.Series], match_type: str, invoice_amount: float, receipt_amount: float) -> dict:
    return {
        "invoice_id": invoice["invoice_id"],
        "customer": invoice["customer"],
        "invoice_date": invoice["invoice_date"].date().isoformat(),
        "due_date": invoice["due_date"].date().isoformat(),
        "invoice_amount": round(invoice_amount, 2),
        "receipt_ids": ", ".join(str(receipt["receipt_id"]) for receipt in receipts),
        "receipt_dates": ", ".join(receipt["receipt_date"].date().isoformat() for receipt in receipts),
        "receipt_amount": round(receipt_amount, 2),
        "difference": round(invoice_amount - receipt_amount, 2),
        "match_type": match_type,
    }


def _find_grouped_receipts(receipts: pd.DataFrame, target_amount: float, tolerance: float) -> list[pd.Series]:
    rows = [row for _, row in receipts.sort_values("receipt_date").iterrows()]
    for size in (2, 3):
        for group in combinations(rows, size):
            total = sum(float(row["amount"]) for row in group)
            if _same_amount(total, target_amount, tolerance):
                return list(group)
    return []


def _priority(days_overdue: int) -> str:
    if days_overdue > 90:
        return "high"
    if days_overdue > 30:
        return "medium"
    return "normal"


def _aging_summary(unmatched_invoices: pd.DataFrame) -> pd.DataFrame:
    if unmatched_invoices.empty:
        return pd.DataFrame({"aging_bucket": AGING_ORDER, "invoice_count": [0] * 5, "amount": [0.0] * 5})

    grouped = (
        unmatched_invoices.groupby("aging_bucket", as_index=False)
        .agg(invoice_count=("invoice_id", "count"), amount=("amount", "sum"))
        .round({"amount": 2})
    )
    order = pd.DataFrame({"aging_bucket": AGING_ORDER})
    return order.merge(grouped, on="aging_bucket", how="left").fillna({"invoice_count": 0, "amount": 0.0})


def _display_invoice_columns(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "invoice_id",
        "customer",
        "invoice_date",
        "due_date",
        "amount",
        "days_overdue",
        "aging_bucket",
        "follow_up_priority",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)
    output = df[columns].copy()
    output["invoice_date"] = output["invoice_date"].dt.date.astype(str)
    output["due_date"] = output["due_date"].dt.date.astype(str)
    return output


def _display_receipt_columns(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["receipt_id", "customer", "receipt_date", "amount", "reference"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    output = df[columns].copy()
    output["receipt_date"] = output["receipt_date"].dt.date.astype(str)
    return output

