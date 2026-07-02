# AR Reconciliation AI Assistant

An accounting-focused Python project for accounts receivable reconciliation, aging analysis, exception prioritization, and AI-assisted review notes.

It is built around a realistic junior accountant workflow: import invoice and receipt exports, match items using transparent rules, surface risky exceptions, and export an Excel audit workbook for manual finance review.

## What It Does

- Validates invoice and receipt CSV files for required columns, duplicate IDs, missing customers, invalid amounts, invalid dates, and missing receipt references.
- Matches invoices to receipts using a rule engine:
  - invoice reference and amount
  - customer, amount, and configurable receipt-date window
  - grouped receipts that add up to one invoice
- Detects partial-payment candidates from same-customer unmatched receipts.
- Calculates aging buckets and open AR exposure.
- Builds a prioritized exception queue with risk score, priority, and recommended owner action.
- Exports a multi-sheet Excel audit workbook.
- Provides a Streamlit dashboard for non-technical review.
- Generates an AI-assisted memo and safe prompt without sending private data anywhere.
- Runs automated tests in GitHub Actions.

## Repository Structure

```text
ar_reconciliation/
  config.py        Business rule settings
  validation.py    Source data checks and normalization
  matching.py      Matching rule engine
  risk.py          Aging, risk score, and owner action logic
  core.py          Reconciliation orchestration
  report.py        Excel audit workbook export
  ai_notes.py      AI memo and safe prompt generation
app.py             Streamlit dashboard
data/              Sample invoice and receipt CSVs
tests/             Pytest coverage
docs/              Architecture notes
```

Useful docs:

- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data_dictionary.md)
- [Interview talking points](docs/interview_talking_points.md)

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the dashboard:

```bash
streamlit run app.py
```

Run the command line workflow:

```bash
python -m ar_reconciliation.cli --invoices data/sample_invoices.csv --receipts data/sample_receipts.csv --output outputs/reconciliation_report.xlsx --as-of 2026-06-30
```

Run tests:

```bash
pytest
```

## Input Format

Invoices:

```text
invoice_id,customer,invoice_date,due_date,amount
```

Receipts:

```text
receipt_id,customer,receipt_date,amount,reference
```

## Excel Workbook Sheets

- `summary`
- `matches`
- `exception_queue`
- `unmatched_invoices`
- `unmatched_receipts`
- `aging`
- `data_quality`
- `control_checklist`
- `ai_notes`

## Why This Project Is Useful

For accounting assistant, AR, AP, or junior accountant roles, the value is practical:

- understand source documents and matching rules
- maintain auditable Excel outputs
- prioritize exceptions instead of only listing them
- use AI carefully for draft explanations while keeping manual controls over amounts and accounting judgement
