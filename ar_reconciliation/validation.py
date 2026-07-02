from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd


INVOICE_COLUMNS = {"invoice_id", "customer", "invoice_date", "due_date", "amount"}
RECEIPT_COLUMNS = {"receipt_id", "customer", "receipt_date", "amount", "reference"}


@dataclass(frozen=True)
class DataQualityIssue:
    dataset: str
    severity: str
    issue: str
    row_count: int
    action: str


def normalize_customer(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.lower().strip()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text)


def prepare_invoices(invoices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    _require_columns(invoices, INVOICE_COLUMNS, "invoice")
    prepared = invoices.copy()
    prepared["invoice_id"] = prepared["invoice_id"].astype(str).str.strip()
    prepared["customer"] = prepared["customer"].astype(str).str.strip()
    prepared["customer_key"] = prepared["customer"].map(normalize_customer)
    prepared["invoice_date"] = pd.to_datetime(prepared["invoice_date"], errors="coerce")
    prepared["due_date"] = pd.to_datetime(prepared["due_date"], errors="coerce")
    prepared["amount"] = pd.to_numeric(prepared["amount"], errors="coerce").round(2)
    issues = quality_report(prepared, "invoice")
    return prepared, issues


def prepare_receipts(receipts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    _require_columns(receipts, RECEIPT_COLUMNS, "receipt")
    prepared = receipts.copy()
    prepared["receipt_id"] = prepared["receipt_id"].astype(str).str.strip()
    prepared["customer"] = prepared["customer"].astype(str).str.strip()
    prepared["reference"] = prepared["reference"].fillna("").astype(str).str.strip()
    prepared["customer_key"] = prepared["customer"].map(normalize_customer)
    prepared["receipt_date"] = pd.to_datetime(prepared["receipt_date"], errors="coerce")
    prepared["amount"] = pd.to_numeric(prepared["amount"], errors="coerce").round(2)
    issues = quality_report(prepared, "receipt")
    return prepared, issues


def quality_report(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    issues: list[DataQualityIssue] = []
    id_col = "invoice_id" if dataset == "invoice" else "receipt_id"
    date_cols = ["invoice_date", "due_date"] if dataset == "invoice" else ["receipt_date"]

    duplicate_ids = int(df[id_col].duplicated(keep=False).sum())
    if duplicate_ids:
        issues.append(
            DataQualityIssue(dataset, "high", f"Duplicate {id_col} values", duplicate_ids, "Confirm source export or remove duplicates.")
        )

    missing_customer = int((df["customer_key"] == "").sum())
    if missing_customer:
        issues.append(
            DataQualityIssue(dataset, "medium", "Missing customer name", missing_customer, "Fill customer names before final posting.")
        )

    invalid_amount = int(df["amount"].isna().sum() + (df["amount"].fillna(0) <= 0).sum())
    if invalid_amount:
        issues.append(
            DataQualityIssue(dataset, "high", "Invalid or non-positive amount", invalid_amount, "Check source amount fields.")
        )

    for col in date_cols:
        invalid_dates = int(df[col].isna().sum())
        if invalid_dates:
            issues.append(
                DataQualityIssue(dataset, "high", f"Invalid {col}", invalid_dates, "Check source date format.")
            )

    if dataset == "receipt":
        missing_reference = int((df["reference"] == "").sum())
        if missing_reference:
            issues.append(
                DataQualityIssue(dataset, "low", "Missing receipt reference", missing_reference, "Use customer and amount matching; confirm manually.")
            )

    return pd.DataFrame([issue.__dict__ for issue in issues])


def _require_columns(df: pd.DataFrame, required: set[str], dataset: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing {dataset} columns: {', '.join(sorted(missing))}")

