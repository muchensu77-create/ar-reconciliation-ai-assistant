from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from ar_reconciliation.ai_notes import build_exception_memo, build_safe_ai_prompt
from ar_reconciliation.config import ReconciliationConfig
from ar_reconciliation.core import reconcile
from ar_reconciliation.report import write_excel_report


ROOT = Path(__file__).parent


st.set_page_config(page_title="AR Reconciliation AI Assistant", layout="wide")
st.title("AR Reconciliation AI Assistant")
st.caption("Accounts receivable matching, aging analysis, exception prioritization, and AI-assisted review notes.")


def load_csv(uploaded_file, sample_path: Path) -> pd.DataFrame:
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)
    return pd.read_csv(sample_path)


with st.sidebar:
    st.header("Input")
    invoice_file = st.file_uploader("Invoices CSV", type=["csv"])
    receipt_file = st.file_uploader("Receipts CSV", type=["csv"])
    as_of = st.date_input("As-of date")

    st.header("Rules")
    amount_tolerance = st.number_input("Amount tolerance", min_value=0.0, max_value=100.0, value=0.01, step=0.01)
    date_window_days = st.slider("Receipt date window after due date", min_value=0, max_value=120, value=45)
    high_value_threshold = st.number_input("High value threshold", min_value=0.0, value=10000.0, step=500.0)
    st.info("No files uploaded? The app uses sample data.")

invoices = load_csv(invoice_file, ROOT / "data" / "sample_invoices.csv")
receipts = load_csv(receipt_file, ROOT / "data" / "sample_receipts.csv")
config = ReconciliationConfig(
    amount_tolerance=amount_tolerance,
    date_window_days=date_window_days,
    high_value_threshold=high_value_threshold,
)
result = reconcile(invoices, receipts, as_of=as_of, config=config)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Match rate", f"{result.summary['match_rate']:.1%}")
col2.metric("Matched amount", f"{result.summary['matched_amount']:,.2f}")
col3.metric("Open amount", f"{result.summary['open_invoice_amount']:,.2f}")
col4.metric("Exceptions", result.summary["exception_count"])
col5.metric("High risk", result.summary["high_risk_exception_count"])

tabs = st.tabs(
    [
        "Executive summary",
        "Matches",
        "Exception queue",
        "Aging",
        "Data quality",
        "AI notes",
    ]
)

with tabs[0]:
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Aging exposure")
        st.bar_chart(result.aging.set_index("aging_bucket")["amount"])
    with right:
        st.subheader("Summary")
        st.dataframe(pd.DataFrame([result.summary]), use_container_width=True)
    st.subheader("Input preview")
    st.dataframe(invoices.head(20), use_container_width=True)

with tabs[1]:
    st.dataframe(result.matches, use_container_width=True)

with tabs[2]:
    st.subheader("Prioritized follow-up list")
    st.dataframe(result.exception_queue, use_container_width=True)
    st.subheader("Unmatched invoices")
    st.dataframe(result.unmatched_invoices, use_container_width=True)
    st.subheader("Unmatched receipts")
    st.dataframe(result.unmatched_receipts, use_container_width=True)

with tabs[3]:
    st.dataframe(result.aging, use_container_width=True)

with tabs[4]:
    if result.data_quality.empty:
        st.success("No data quality issues detected in the loaded files.")
    else:
        st.dataframe(result.data_quality, use_container_width=True)

with tabs[5]:
    st.subheader("AI-assisted exception memo")
    st.markdown(build_exception_memo(result.summary, result.unmatched_invoices, result.unmatched_receipts, result.exception_queue))
    st.subheader("Safe prompt for manual AI review")
    st.code(build_safe_ai_prompt(result.summary, result.aging), language="text")

buffer = BytesIO()
temp_path = ROOT / "outputs" / "reconciliation_report.xlsx"
write_excel_report(result, temp_path)
buffer.write(temp_path.read_bytes())
buffer.seek(0)

st.download_button(
    "Download Excel audit workbook",
    data=buffer,
    file_name="reconciliation_audit_workbook.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
