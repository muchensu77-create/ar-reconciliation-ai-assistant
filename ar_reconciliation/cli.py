from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .ai_notes import build_exception_memo
from .core import reconcile
from .report import write_excel_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile AR invoices and receipts.")
    parser.add_argument("--invoices", required=True, help="Path to invoice CSV file.")
    parser.add_argument("--receipts", required=True, help="Path to receipt CSV file.")
    parser.add_argument("--output", default="outputs/reconciliation_report.xlsx", help="Excel output path.")
    parser.add_argument("--as-of", default=None, help="Analysis date, for example 2026-06-30.")
    args = parser.parse_args()

    invoices = pd.read_csv(args.invoices)
    receipts = pd.read_csv(args.receipts)
    result = reconcile(invoices, receipts, as_of=args.as_of)
    output = write_excel_report(result, Path(args.output))

    print(f"Report written to {output}")
    print()
    print(build_exception_memo(result.summary, result.unmatched_invoices, result.unmatched_receipts))


if __name__ == "__main__":
    main()

