# AR Reconciliation AI Assistant

A small accounting-focused Python project for accounts receivable reconciliation, aging analysis, and AI-assisted exception notes.

This project is designed around a realistic junior accounting workflow:

- compare invoice records with bank receipt records
- identify matched, unmatched, and exception items
- calculate aging buckets for unpaid invoices
- export a reviewed Excel workbook
- draft a concise AI-assisted follow-up memo for finance review

The AI feature is intentionally practical: it does not send private financial data to an external model. It prepares a structured exception memo and a safe prompt that can be reviewed before use.

## Features

- One-to-one matching by invoice reference, customer, and amount
- Simple grouped matching for cases where one invoice is paid by multiple receipts
- Aging buckets: not due, 0-30, 31-60, 61-90, and over 90 days
- Excel report export with separate sheets for summary, matches, unpaid invoices, unmatched receipts, and AI notes
- Streamlit interface for non-technical review
- Command line workflow for repeatable processing
- Sample invoice and receipt data included

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Streamlit app:

```bash
streamlit run app.py
```

Run the command line workflow:

```bash
python -m ar_reconciliation.cli --invoices data/sample_invoices.csv --receipts data/sample_receipts.csv --output outputs/reconciliation_report.xlsx
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

## Why This Project Matters

For an accounting assistant or AR/AP role, the useful skill is not only knowing formulas. It is the ability to clean source data, compare business records, surface exceptions, and explain what needs follow-up.

This project shows:

- accounting process awareness
- Excel and data handling ability
- basic automation thinking
- careful use of AI as an assistant, with manual review for amounts and accounting judgement

