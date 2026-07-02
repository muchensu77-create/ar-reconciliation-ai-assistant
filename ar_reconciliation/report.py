from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .ai_notes import build_exception_memo, build_safe_ai_prompt
from .core import ReconciliationResult


def write_excel_report(result: ReconciliationResult, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    summary_df = pd.DataFrame([result.summary])
    memo = build_exception_memo(result.summary, result.unmatched_invoices, result.unmatched_receipts)
    prompt = build_safe_ai_prompt(result.summary, result.aging)
    ai_notes = pd.DataFrame({"section": ["exception_memo", "safe_ai_prompt"], "content": [memo, prompt]})

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="summary", index=False)
        result.matches.to_excel(writer, sheet_name="matches", index=False)
        result.unmatched_invoices.to_excel(writer, sheet_name="unmatched_invoices", index=False)
        result.unmatched_receipts.to_excel(writer, sheet_name="unmatched_receipts", index=False)
        result.aging.to_excel(writer, sheet_name="aging", index=False)
        ai_notes.to_excel(writer, sheet_name="ai_notes", index=False)

        for sheet in writer.book.worksheets:
            _format_sheet(sheet)

    return output


def _format_sheet(sheet) -> None:
    header_fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill

    for column_cells in sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        width = min(max(max_length + 2, 12), 48)
        sheet.column_dimensions[get_column_letter(column_cells[0].column)].width = width

    sheet.freeze_panes = "A2"

