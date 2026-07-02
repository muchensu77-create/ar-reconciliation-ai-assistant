from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .config import ReconciliationConfig
from .ai_notes import build_exception_memo
from .core import reconcile
from .report import write_excel_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile AR invoices and receipts.")
    parser.add_argument("--invoices", required=True, help="Path to invoice CSV file.")
    parser.add_argument("--receipts", required=True, help="Path to receipt CSV file.")
    parser.add_argument("--output", default="outputs/reconciliation_report.xlsx", help="Excel output path.")
    parser.add_argument("--as-of", default=None, help="Analysis date, for example 2026-06-30.")
    parser.add_argument("--tolerance", type=float, default=0.01, help="Amount matching tolerance.")
    parser.add_argument("--date-window-days", type=int, default=45, help="Receipt matching window after due date.")
    args = parser.parse_args()

    invoices = pd.read_csv(args.invoices)
    receipts = pd.read_csv(args.receipts)
    config = ReconciliationConfig(amount_tolerance=args.tolerance, date_window_days=args.date_window_days)
    result = reconcile(invoices, receipts, as_of=args.as_of, config=config)
    output = write_excel_report(result, Path(args.output))

    print(f"Report written to {output}")
    print(f"Match rate: {result.summary['match_rate']:.1%}")
    print(f"Exceptions: {result.summary['exception_count']} | High risk: {result.summary['high_risk_exception_count']}")
    print()
    print(build_exception_memo(result.summary, result.unmatched_invoices, result.unmatched_receipts, result.exception_queue))


if __name__ == "__main__":
    main()
