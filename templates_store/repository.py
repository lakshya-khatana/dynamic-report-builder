"""Spec §4: 'list, load, execute, overwrite, or clone existing templates.'"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, insert, select, update

from compiler.request_schema import ReportRequest, ReportTemplate
from errors.exceptions import TemplateNotFoundError
from templates_store.models import get_app_engine, report_templates


def _row_to_template(row) -> ReportTemplate:
    return ReportTemplate(
        id=row.id,
        name=row.name,
        author=row.author,
        request=ReportRequest.model_validate_json(row.request_json),
        created_at=str(row.created_at),
        updated_at=str(row.updated_at),
    )


def save_template(name: str, request: ReportRequest, author: str | None = None) -> ReportTemplate:
    template_id = str(uuid.uuid4())
    engine = get_app_engine()
    with engine.begin() as conn:
        conn.execute(
            insert(report_templates).values(
                id=template_id,
                name=name,
                author=author,
                request_json=request.model_dump_json(),
            )
        )
    return get_template(template_id)


def get_template(template_id: str) -> ReportTemplate:
    engine = get_app_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(report_templates).where(report_templates.c.id == template_id)
        ).first()
    if row is None:
        raise TemplateNotFoundError(f"Template '{template_id}' not found.")
    return _row_to_template(row)


def list_templates() -> list[ReportTemplate]:
    engine = get_app_engine()
    with engine.connect() as conn:
        rows = conn.execute(select(report_templates)).fetchall()
    return [_row_to_template(r) for r in rows]


def overwrite_template(template_id: str, name: str, request: ReportRequest) -> ReportTemplate:
    engine = get_app_engine()
    with engine.begin() as conn:
        result = conn.execute(
            update(report_templates)
            .where(report_templates.c.id == template_id)
            .values(name=name, request_json=request.model_dump_json())
        )
        if result.rowcount == 0:
            raise TemplateNotFoundError(f"Template '{template_id}' not found.")
    return get_template(template_id)


def clone_template(template_id: str, new_name: str) -> ReportTemplate:
    original = get_template(template_id)
    return save_template(new_name, original.request, author=original.author)


def delete_template(template_id: str) -> None:
    engine = get_app_engine()
    with engine.begin() as conn:
        result = conn.execute(delete(report_templates).where(report_templates.c.id == template_id))
        if result.rowcount == 0:
            raise TemplateNotFoundError(f"Template '{template_id}' not found.")
