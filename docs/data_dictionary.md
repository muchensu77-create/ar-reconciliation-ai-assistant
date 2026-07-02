# Data Dictionary

## Invoices

| Column | Meaning | Example |
| --- | --- | --- |
| `invoice_id` | Unique invoice number | `INV-1001` |
| `customer` | Customer name from sales or AR export | `Shanghai Fresh Retail` |
| `invoice_date` | Invoice issue date | `2026-03-05` |
| `due_date` | Expected payment due date | `2026-04-04` |
| `amount` | Invoice amount | `12800.00` |

## Receipts

| Column | Meaning | Example |
| --- | --- | --- |
| `receipt_id` | Unique bank receipt or cash application ID | `RCPT-9001` |
| `customer` | Customer name from receipt or bank remark | `Shanghai Fresh Retail` |
| `receipt_date` | Receipt date | `2026-03-28` |
| `amount` | Receipt amount | `12800.00` |
| `reference` | Bank remark, invoice reference, or settlement note | `Payment for INV-1001` |

## Output Fields

| Field | Meaning |
| --- | --- |
| `match_type` | Rule used to match invoice and receipt |
| `confidence` | Rule-based confidence score |
| `match_reason` | Plain-language explanation for the match |
| `exception_type` | Open invoice, partial payment candidate, or unapplied receipt |
| `risk_score` | Score based on amount, aging, and exception clues |
| `priority` | Normal, medium, or high follow-up priority |
| `owner_action` | Suggested next finance action |

