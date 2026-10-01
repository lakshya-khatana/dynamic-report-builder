"""
Spec §5.3: 'Formatted header rows, preserved numerical precision, proper
date formats, auto-adjusted column widths.' write_only=True is what keeps
this from buffering the whole sheet in RAM the way normal openpyxl does.
"""

from collections.abc import Iterator

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter


def export_to_excel(columns: list[str], row_iterator: Iterator[tuple], output_path: str) -> str:
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Report")

    header_font = Font(bold=True)
    header_cells = [WriteOnlyCell(ws, value=c) for c in columns]
    for cell in header_cells:
        cell.font = header_font
    ws.append(header_cells)

    max_widths = [len(c) for c in columns]

    for row in row_iterator:
        ws.append(list(row))
        for i, value in enumerate(row):
            length = len(str(value)) if value is not None else 0
            if length > max_widths[i]:
                max_widths[i] = length

    # Column width auto-adjust has to happen after the fact in write_only
    # mode — there's no per-cell column-width API while streaming rows.
    for i, width in enumerate(max_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = min(width + 2, 60)

    wb.save(output_path)
    return output_path
