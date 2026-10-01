"""Spec §2: schema discovery/reflection endpoints."""

from dataclasses import asdict

from fastapi import APIRouter

from connectors.loader import load_connector
from reflection.cache import get_cached_metadata, set_cached_metadata
from reflection.inspector import list_tables, list_views
from reflection.join_recommender import recommend_joins
from reflection.metadata_extractor import extract_all_tables, reflect_metadata

router = APIRouter()


def _get_metadata(source_id: str):
    metadata = get_cached_metadata(source_id)
    if metadata is not None:
        return metadata
    connector = load_connector(source_id)
    metadata = reflect_metadata(connector.get_engine())
    set_cached_metadata(source_id, metadata)
    return metadata


@router.get("/{source_id}/tables")
def get_tables(source_id: str):
    connector = load_connector(source_id)
    engine = connector.get_engine()
    return {
        "tables": list_tables(engine),
        "views": list_views(engine),
    }


@router.get("/{source_id}/columns")
def get_columns(source_id: str):
    metadata = _get_metadata(source_id)
    tables = extract_all_tables(metadata)
    return [asdict(t) for t in tables]


@router.get("/{source_id}/join-suggestions")
def get_join_suggestions(source_id: str, table_a: str, table_b: str):
    metadata = _get_metadata(source_id)
    candidates = recommend_joins(metadata, table_a, table_b)
    return [asdict(c) for c in candidates]
