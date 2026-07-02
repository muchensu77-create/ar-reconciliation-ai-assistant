from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from .config import ReconciliationConfig
from .matching import match_invoices, suggest_partial_payments
from .risk import aging_bucket, owner_action, priority_from_score, score_invoice_exception, score_receipt_exception
from .validation import normalize_customer, prepare_invoices, prepare_receipts


AGING_ORDER = ReconciliationConfig().aging_order


@dataclass
class ReconciliationResult:
    summary: dict
    matches: pd.DataFrame
    unmatched_invoices: pd.DataFrame
    unmatched_receipts: pd.DataFrame
    aging: pd.DataFrame
    exception_queue: pd.DataFrame
    data_quality: pd.DataFrame


def reconcile(
    invoices: pd.DataFrame,
    receipts: pd.DataFrame,
    as_of: date | str | None = None,
    tolerance: float | None = None,
    config: ReconciliationConfig | None = None,
) -> ReconciliationResult:
    settings = config or ReconciliationConfig()
    if tolerance is not None:
        settings = ReconciliationConfig(
            amount_tolerance=tolerance,
            date_window_days=settings.date_window_days,
            grouped_receipt_max_size=settings.grouped_receipt_max_size,
            partial_payment_min_ratio=settings.partial_payment_min_ratio,
            high_value_threshold=settings.high_value_threshold,
            medium_value_threshold=settings.medium_value_threshold,
            aging_buckets=settings.aging_buckets,
        )

    invoice_df, invoice_quality = prepare_invoices(invoices)
    receipt_df, receipt_quality = prepare_receipts(receipts)
    as_of_date = pd.Timestamp(as_of or date.today()).normalize()

    matches, matched_invoice_ids, used_receipt_ids = match_invoices(invoice_df, receipt_df, settings)
    unmatched_invoice_raw = invoice_df[~invoice_df["invoice_id"].isin(matched_invoice_ids)].copy()
    unmatched_receipt_raw = receipt_df[~receipt_df["receipt_id"].isin(used_receipt_ids)].copy()

    unmatched_invoice_raw = _enrich_unmatched_invoices(unmatched_invoice_raw, unmatched_receipt_raw, as_of_date, settings)
    unmatched_receipt_raw = _enrich_unmatched_receipts(unmatched_receipt_raw, settings)

    aging = _aging_summary(unmatched_invoice_raw, settings)
    exception_queue = _build_exception_queue(unmatched_invoice_raw, unmatched_receipt_raw)
    data_quality = pd.concat([invoice_quality, receipt_quality], ignore_index=True)

    summary = _summary(invoice_df, receipt_df, matches, unmatched_invoice_raw, unmatched_receipt_raw, exception_queue, data_quality, as_of_date)

    return ReconciliationResult(
        summary=summary,
        matches=_display_matches(matches),
        unmatched_invoices=_display_invoice_columns(unmatched_invoice_raw),
        unmatched_receipts=_display_receipt_columns(unmatched_receipt_raw),
        aging=aging,
        exception_queue=exception_queue,
        data_quality=data_quality,
    )


def _enrich_unmatched_invoices(
    unmatched_invoices: pd.DataFrame,
    unmatched_receipts: pd.DataFrame,
    as_of_date: pd.Timestamp,
    config: ReconciliationConfig,
) -> pd.DataFrame:
    if unmatched_invoices.empty:
        columns = list(unmatched_invoices.columns) + [
            "days_overdue",
            "aging_bucket",
            "suggested_receipt_ids",
            "suggested_receipt_amount",
            "remaining_amount_after_suggestion",
            "exception_type",
            "risk_score",
            "follow_up_priority",
            "owner_action",
        ]
        return pd.DataFrame(columns=columns)

    enriched = unmatched_invoices.copy()
    enriched["days_overdue"] = (as_of_date - enriched["due_date"]).dt.days
    enriched["aging_bucket"] = enriched["days_overdue"].map(lambda value: aging_bucket(int(value), config))
    enriched = suggest_partial_payments(enriched, unmatched_receipts, config)
    enriched["risk_score"] = enriched.apply(lambda row: score_invoice_exception(row, config), axis=1)
    enriched["follow_up_priority"] = enriched["risk_score"].map(priority_from_score)
    enriched["owner_action"] = enriched["exception_type"].map(owner_action)
    return enriched


def _enrich_unmatched_receipts(unmatched_receipts: pd.DataFrame, config: ReconciliationConfig) -> pd.DataFrame:
    if unmatched_receipts.empty:
        columns = list(unmatched_receipts.columns) + ["exception_type", "risk_score", "follow_up_priority", "owner_action"]
        return pd.DataFrame(columns=columns)

    enriched = unmatched_receipts.copy()
    enriched["exception_type"] = "unapplied_receipt"
    enriched["risk_score"] = enriched.apply(lambda row: score_receipt_exception(row, config), axis=1)
    enriched["follow_up_priority"] = enriched["risk_score"].map(priority_from_score)
    enriched["owner_action"] = enriched["exception_type"].map(owner_action)
    return enriched


def _aging_summary(unmatched_invoices: pd.DataFrame, config: ReconciliationConfig) -> pd.DataFrame:
    order = pd.DataFrame({"aging_bucket": config.aging_order})
    if unmatched_invoices.empty:
        order["invoice_count"] = 0
        order["amount"] = 0.0
        order["risk_score_avg"] = 0.0
        return order

    grouped = (
        unmatched_invoices.groupby("aging_bucket", as_index=False)
        .agg(
            invoice_count=("invoice_id", "count"),
            amount=("amount", "sum"),
            risk_score_avg=("risk_score", "mean"),
        )
        .round({"amount": 2, "risk_score_avg": 1})
    )
    return order.merge(grouped, on="aging_bucket", how="left").fillna({"invoice_count": 0, "amount": 0.0, "risk_score_avg": 0.0})


def _build_exception_queue(unmatched_invoices: pd.DataFrame, unmatched_receipts: pd.DataFrame) -> pd.DataFrame:
    invoice_rows = []
    for _, row in unmatched_invoices.iterrows():
        invoice_rows.append(
            {
                "exception_type": row["exception_type"],
                "source_id": row["invoice_id"],
                "customer": row["customer"],
                "amount": round(float(row["amount"]), 2),
                "risk_score": int(row["risk_score"]),
                "priority": row["follow_up_priority"],
                "owner_action": row["owner_action"],
                "details": _invoice_details(row),
            }
        )

    receipt_rows = []
    for _, row in unmatched_receipts.iterrows():
        receipt_rows.append(
            {
                "exception_type": row["exception_type"],
                "source_id": row["receipt_id"],
                "customer": row["customer"],
                "amount": round(float(row["amount"]), 2),
                "risk_score": int(row["risk_score"]),
                "priority": row["follow_up_priority"],
                "owner_action": row["owner_action"],
                "details": f"Receipt date {row['receipt_date'].date().isoformat()}, reference: {row.get('reference', '') or 'blank'}",
            }
        )

    queue = pd.DataFrame(invoice_rows + receipt_rows)
    if queue.empty:
        return pd.DataFrame(columns=["exception_type", "source_id", "customer", "amount", "risk_score", "priority", "owner_action", "details"])
    return queue.sort_values(["risk_score", "amount"], ascending=[False, False]).reset_index(drop=True)


def _invoice_details(row: pd.Series) -> str:
    suggested = row.get("suggested_receipt_ids", "")
    if suggested:
        return (
            f"Due {row['due_date'].date().isoformat()}, overdue {int(row['days_overdue'])} days; "
            f"possible partial receipts: {suggested}; remaining {row['remaining_amount_after_suggestion']:,.2f}"
        )
    return f"Due {row['due_date'].date().isoformat()}, overdue {int(row['days_overdue'])} days"


def _summary(
    invoice_df: pd.DataFrame,
    receipt_df: pd.DataFrame,
    matches: pd.DataFrame,
    unmatched_invoices: pd.DataFrame,
    unmatched_receipts: pd.DataFrame,
    exception_queue: pd.DataFrame,
    data_quality: pd.DataFrame,
    as_of_date: pd.Timestamp,
) -> dict:
    matched_amount = round(float(matches["invoice_amount"].sum()) if not matches.empty else 0.0, 2)
    total_invoice_amount = round(float(invoice_df["amount"].sum()), 2)
    high_risk = int((exception_queue["priority"] == "high").sum()) if not exception_queue.empty else 0
    match_rate = round(len(matches) / len(invoice_df), 4) if len(invoice_df) else 0.0
    value_match_rate = round(matched_amount / total_invoice_amount, 4) if total_invoice_amount else 0.0

    return {
        "invoice_count": int(len(invoice_df)),
        "receipt_count": int(len(receipt_df)),
        "matched_invoice_count": int(len(matches)),
        "unmatched_invoice_count": int(len(unmatched_invoices)),
        "unmatched_receipt_count": int(len(unmatched_receipts)),
        "exception_count": int(len(exception_queue)),
        "high_risk_exception_count": high_risk,
        "data_quality_issue_count": int(len(data_quality)),
        "matched_amount": matched_amount,
        "open_invoice_amount": round(float(unmatched_invoices["amount"].sum()) if not unmatched_invoices.empty else 0.0, 2),
        "unapplied_receipt_amount": round(float(unmatched_receipts["amount"].sum()) if not unmatched_receipts.empty else 0.0, 2),
        "match_rate": match_rate,
        "value_match_rate": value_match_rate,
        "as_of": str(as_of_date.date()),
    }


def _display_matches(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "invoice_id",
        "customer",
        "invoice_date",
        "due_date",
        "invoice_amount",
        "receipt_ids",
        "receipt_dates",
        "receipt_amount",
        "difference",
        "match_type",
        "confidence",
        "match_reason",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)
    return df[columns].copy()


def _display_invoice_columns(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "invoice_id",
        "customer",
        "invoice_date",
        "due_date",
        "amount",
        "days_overdue",
        "aging_bucket",
        "exception_type",
        "suggested_receipt_ids",
        "suggested_receipt_amount",
        "remaining_amount_after_suggestion",
        "risk_score",
        "follow_up_priority",
        "owner_action",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)
    output = df[columns].copy()
    output["invoice_date"] = output["invoice_date"].dt.date.astype(str)
    output["due_date"] = output["due_date"].dt.date.astype(str)
    return output


def _display_receipt_columns(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "receipt_id",
        "customer",
        "receipt_date",
        "amount",
        "reference",
        "exception_type",
        "risk_score",
        "follow_up_priority",
        "owner_action",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)
    output = df[columns].copy()
    output["receipt_date"] = output["receipt_date"].dt.date.astype(str)
    return output

