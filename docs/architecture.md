# Architecture

The project is split around a finance review workflow rather than a single script.

```text
CSV exports
  -> validation.py       required columns, duplicates, missing references
  -> matching.py         exact reference, customer/date/amount, grouped receipts
  -> risk.py             aging bucket, risk score, priority, owner action
  -> core.py             orchestration and result object
  -> report.py           Excel audit workbook
  -> ai_notes.py         safe exception memo and AI prompt
  -> app.py              Streamlit review dashboard
```

## Business Rules

- Exact invoice reference and amount receives the highest confidence.
- Customer, amount, and date-window matches are accepted but scored lower.
- Multiple receipts can be grouped when they sum to one invoice.
- Open invoices are scored by days overdue, amount, and partial-payment clues.
- Unapplied receipts are scored by amount and missing reference.
- AI text is used only to draft exception notes; source documents and accounting judgement remain manual controls.

## Report Outputs

The Excel workbook includes:

- summary
- matches with confidence and match reason
- exception_queue
- unmatched_invoices
- unmatched_receipts
- aging
- data_quality
- control_checklist
- ai_notes

