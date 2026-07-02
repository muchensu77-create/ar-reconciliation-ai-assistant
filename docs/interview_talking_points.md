# Interview Talking Points

## One-Minute Summary

I built a small AR reconciliation tool for a junior accounting workflow. It compares invoice and receipt exports, applies several matching rules, creates an exception queue, calculates aging exposure, and exports an Excel workbook for finance review. I also added AI-assisted memo drafting, but the tool keeps amount checks and accounting judgement as manual controls.

## Business Problem

In AR work, the time-consuming part is often not only entering vouchers. It is checking whether receipts match invoices, finding unapplied receipts, tracking overdue balances, and explaining exceptions clearly enough for follow-up.

## What I Built

- CSV import for invoices and receipts
- data quality checks for duplicate IDs, missing customers, missing references, invalid dates, and invalid amounts
- rule-based matching by invoice reference, customer, amount, date window, and grouped receipts
- partial-payment candidate detection
- aging analysis and risk scoring
- exception queue with owner action
- Excel audit workbook export
- Streamlit dashboard
- AI-assisted exception memo and safe prompt
- automated tests and GitHub Actions

## How To Explain The AI Part

The AI part is not used to decide accounting treatment. It helps draft a follow-up memo and summarize exception priorities. The amounts, references, and accounting conclusions still need to be checked against source documents. This is safer and more realistic for finance work.

## If Asked About Improvements

- connect directly to ERP exports
- add customer master data and payment terms
- add approval status and exception owner tracking
- add monthly trend charts
- add user login for finance team review

