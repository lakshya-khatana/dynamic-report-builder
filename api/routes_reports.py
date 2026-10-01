"""Spec §5: execution, preview, export."""

import os
import uuid

from fastapi import APIRouter
from fastapi.responses import FileResponse, StreamingResponse

from compiler.compiler import compile_report
from compiler.request_schema import ReportRequest
from config import settings
from connectors.loader import load_connector
from execution.executor import execute_statement
from execution.paginator import apply_preview_cap, paginate, total_pages
from execution.streamer import stream_rows
from exporters.csv_export import stream_csv_response
from exporters.excel_export import export_to_excel
from reflection.cache import get_cached_metadata, set_cached_metadata
from reflection.metadata_extractor import reflect_metadata

router = APIRouter()


def _get_metadata_and_connector(source_id: str):
    connector = load_connector(source_id)
    metadata = get_cached_metadata(source_id)
    if metadata is None:
        metadata = reflect_metadata(connector.get_engine())
        set_cached_metadata(source_id, metadata)
    return metadata, connector


@router.post("/preview")
def preview_report(request: ReportRequest):
    metadata, connector = _get_metadata_and_connector(request.source_id)
    compiled = compile_report(metadata, request, connector.supported_join_types)

    # Spec §5.1 — preview ALWAYS hard-capped, regardless of request.page_size
    capped_stmt = apply_preview_cap(compiled.statement)

    result = execute_statement(connector.get_engine(), capped_stmt, compiled.count_statement)
    return {
        "columns": result.columns,
        "rows": [list(r) for r in result.rows],
        "latency_ms": round(result.latency_ms, 2),
        "total_record_estimate": result.row_count_estimate,
    }


@router.post("/run")
def run_report(request: ReportRequest):
    """Paginated, non-preview execution — what a saved/loaded template actually runs."""
    metadata, connector = _get_metadata_and_connector(request.source_id)
    compiled = compile_report(metadata, request, connector.supported_join_types)

    paged_stmt = paginate(compiled.statement, request.page, request.page_size)
    result = execute_statement(connector.get_engine(), paged_stmt, compiled.count_statement)

    return {
        "columns": result.columns,
        "rows": [list(r) for r in result.rows],
        "latency_ms": round(result.latency_ms, 2),
        "page": request.page,
        "page_size": request.page_size,
        "total_records": result.row_count_estimate,
        "total_pages": total_pages(result.row_count_estimate or 0, request.page_size),
    }


@router.post("/export/csv")
def export_csv(request: ReportRequest):
    metadata, connector = _get_metadata_and_connector(request.source_id)
    compiled = compile_report(metadata, request, connector.supported_join_types)

    engine = connector.get_engine()
    columns = [str(c["name"]) for c in compiled.statement.column_descriptions]
    row_iter = stream_rows(engine, compiled.statement)

    return StreamingResponse(
        stream_csv_response(columns, row_iter),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=report.csv"},
    )


@router.post("/export/xlsx")
def export_xlsx(request: ReportRequest):
    metadata, connector = _get_metadata_and_connector(request.source_id)
    compiled = compile_report(metadata, request, connector.supported_join_types)

    engine = connector.get_engine()
    columns = [str(c["name"]) for c in compiled.statement.column_descriptions]
    row_iter = stream_rows(engine, compiled.statement)

    output_path = os.path.join(settings.UPLOAD_DIR, f"report_{uuid.uuid4().hex}.xlsx")
    export_to_excel(columns, row_iter, output_path)

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="report.xlsx",
    )
