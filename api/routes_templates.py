"""Spec §4: template persistence endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from compiler.request_schema import ReportRequest
from templates_store.repository import (
    clone_template, delete_template, get_template, list_templates,
    overwrite_template, save_template,
)

router = APIRouter()


class SaveTemplateRequest(BaseModel):
    name: str
    request: ReportRequest
    author: str | None = None


class CloneTemplateRequest(BaseModel):
    new_name: str


@router.post("")
def create_template(payload: SaveTemplateRequest):
    return save_template(payload.name, payload.request, payload.author)


@router.get("")
def get_all_templates():
    return list_templates()


@router.get("/{template_id}")
def get_one_template(template_id: str):
    return get_template(template_id)


@router.put("/{template_id}")
def update_template(template_id: str, payload: SaveTemplateRequest):
    return overwrite_template(template_id, payload.name, payload.request)


@router.post("/{template_id}/clone")
def clone_one_template(template_id: str, payload: CloneTemplateRequest):
    return clone_template(template_id, payload.new_name)


@router.delete("/{template_id}")
def delete_one_template(template_id: str):
    delete_template(template_id)
    return {"deleted": template_id}
