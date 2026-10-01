from sqlalchemy import Column, Integer, MetaData, Table, create_engine, select

from execution.paginator import apply_preview_cap, paginate, total_pages


def test_total_pages_exact_division():
    assert total_pages(100, 50) == 2


def test_total_pages_with_remainder():
    assert total_pages(101, 50) == 3


def test_paginate_offset_math():
    metadata = MetaData()
    t = Table("t", metadata, Column("id", Integer, primary_key=True))
    stmt = select(t)

    page2 = paginate(stmt, page=2, page_size=10)
    compiled = page2.compile(compile_kwargs={"literal_binds": True})
    assert "LIMIT 10" in str(compiled)
    assert "OFFSET 10" in str(compiled)


def test_preview_cap_applied():
    metadata = MetaData()
    t = Table("t", metadata, Column("id", Integer, primary_key=True))
    stmt = select(t)
    capped = apply_preview_cap(stmt)
    compiled = capped.compile(compile_kwargs={"literal_binds": True})
    assert "LIMIT 100" in str(compiled)
