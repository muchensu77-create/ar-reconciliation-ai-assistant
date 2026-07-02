import pandas as pd

from ar_reconciliation.core import reconcile
from ar_reconciliation.ai_notes import build_exception_memo


def test_reconcile_matches_reference_and_grouped_receipts():
    invoices = pd.DataFrame(
        [
            {
                "invoice_id": "INV-1",
                "customer": "Alpha Co",
                "invoice_date": "2026-03-01",
                "due_date": "2026-03-31",
                "amount": 100.0,
            },
            {
                "invoice_id": "INV-2",
                "customer": "Beta Co",
                "invoice_date": "2026-03-02",
                "due_date": "2026-04-01",
                "amount": 120.0,
            },
        ]
    )
    receipts = pd.DataFrame(
        [
            {
                "receipt_id": "R-1",
                "customer": "Alpha Co",
                "receipt_date": "2026-03-20",
                "amount": 100.0,
                "reference": "INV-1",
            },
            {
                "receipt_id": "R-2",
                "customer": "Beta Co",
                "receipt_date": "2026-04-02",
                "amount": 70.0,
                "reference": "",
            },
            {
                "receipt_id": "R-3",
                "customer": "Beta Co",
                "receipt_date": "2026-04-03",
                "amount": 50.0,
                "reference": "",
            },
        ]
    )

    result = reconcile(invoices, receipts, as_of="2026-06-30")

    assert result.summary["matched_invoice_count"] == 2
    assert set(result.matches["match_type"]) == {"invoice_reference", "grouped_receipts"}
    assert result.summary["open_invoice_amount"] == 0.0


def test_exception_memo_mentions_unapplied_receipts():
    invoices = pd.DataFrame(
        [
            {
                "invoice_id": "INV-1",
                "customer": "Alpha Co",
                "invoice_date": "2026-03-01",
                "due_date": "2026-03-31",
                "amount": 100.0,
            }
        ]
    )
    receipts = pd.DataFrame(
        [
            {
                "receipt_id": "R-1",
                "customer": "Unknown",
                "receipt_date": "2026-04-02",
                "amount": 90.0,
                "reference": "",
            }
        ]
    )

    result = reconcile(invoices, receipts, as_of="2026-06-30")
    memo = build_exception_memo(result.summary, result.unmatched_invoices, result.unmatched_receipts)

    assert "high-priority" in memo
    assert "receipt" in memo

