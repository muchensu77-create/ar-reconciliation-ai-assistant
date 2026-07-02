from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from ar_reconciliation.ai_notes import build_exception_memo, build_safe_ai_prompt
from ar_reconciliation.core import reconcile
from ar_reconciliation.report import write_excel_report


ROOT = Path(__file__).parent


st.set_page_config(page_title="AR Reconciliation AI Assistant", layout="wide")
st.title("AR Reconciliation AI Assistant")
st.caption("Accounts receivable matching, aging analysis, and AI-assisted exception notes.")


def load_csv(uploaded_file, sample_path: Path) -> pd.DataFrame:
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)
    return pd.read_csv(sample_path)


with st.sidebar:
    st.header("Input")
    invoice_file = st.file_uploader("Invoices CSV", type=["csv"])
    receipt_file = st.file_uploader("Receipts CSV", type=["csv"])
    as_of = st.date_input("As-of date")
    st.info("No files uploaded? The app uses sample data.")

invoices = load_csv(invoice_file, ROOT / "data" / "sample_invoices.csv")
receipts = load_csv(receipt_file, ROOT / "data" / "sample_receipts.csv")
result = reconcile(invoices, receipts, as_of=as_of)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Matched invoices", result.summary["matched_invoice_count"])
col2.metric("Open invoices", result.summary["unmatched_invoice_count"])
col3.metric("Open amount", f"{result.summary['open_invoice_amount']:,.2f}")
col4.metric("Unapplied receipts", result.summary["unmatched_receipt_count"])

tab_summary, tab_matches, tab_exceptions, tab_ai = st.tabs(
    ["Summary", "Matches", "Exceptions", "AI notes"]
)

with tab_summary:
    st.subheader("Aging")
    st.dataframe(result.aging, use_container_width=True)
    st.subheader("Input preview")
    st.dataframe(invoices.head(20), use_container_width=True)

with tab_matches:
    st.dataframe(result.matches, use_container_width=True)

with tab_exceptions:
    st.subheader("Unmatched invoices")
    st.dataframe(result.unmatched_invoices, use_container_width=True)
    st.subheader("Unmatched receipts")
    st.dataframe(result.unmatched_receipts, use_container_width=True)

with tab_ai:
    st.subheader("AI-assisted exception memo")
    st.markdown(build_exception_memo(result.summary, result.unmatched_invoices, result.unmatched_receipts))
    st.subheader("Safe prompt for manual AI review")
    st.code(build_safe_ai_prompt(result.summary, result.aging), language="text")

buffer = BytesIO()
temp_path = ROOT / "outputs" / "reconciliation_report.xlsx"
write_excel_report(result, temp_path)
buffer.write(temp_path.read_bytes())
buffer.seek(0)

st.download_button(
    "Download Excel report",
    data=buffer,
    file_name="reconciliation_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

