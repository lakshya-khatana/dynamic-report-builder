from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, create_engine

from compiler.compiler import compile_report
from compiler.request_schema import (
    Aggregate, FieldSelection, Filter, JoinConfig, JoinCondition, ReportRequest,
)


def _build_test_engine():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    customers = Table(
        "customers", metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
    )
    orders = Table(
        "orders", metadata,
        Column("id", Integer, primary_key=True),
        Column("customer_id", Integer, ForeignKey("customers.id")),
        Column("amount", Integer),
        Column("status", String),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(customers.insert(), [{"id": 1, "name": "Asha"}, {"id": 2, "name": "Ravi"}])
        conn.execute(
            orders.insert(),
            [
                {"id": 1, "customer_id": 1, "amount": 500, "status": "PAID"},
                {"id": 2, "customer_id": 1, "amount": 300, "status": "PAID"},
                {"id": 3, "customer_id": 2, "amount": 100, "status": "PENDING"},
            ],
        )
    return engine, metadata


def test_single_table_filter():
    engine, metadata = _build_test_engine()
    request = ReportRequest(
        source_id="test",
        base_table="orders",
        fields=[FieldSelection(column="orders.id"), FieldSelection(column="orders.amount")],
        filters=[Filter(column="orders.status", op="eq", value="PAID")],
    )
    compiled = compile_report(metadata, request, supported_join_types=("INNER", "LEFT"))
    with engine.connect() as conn:
        rows = conn.execute(compiled.statement).fetchall()
    assert len(rows) == 2


def test_join_and_aggregate_with_auto_group_by():
    engine, metadata = _build_test_engine()
    request = ReportRequest(
        source_id="test",
        base_table="orders",
        joins=[
            JoinConfig(
                target_table="customers",
                join_type="INNER",
                conditions=[JoinCondition(left_column="orders.customer_id", right_column="customers.id")],
            )
        ],
        fields=[FieldSelection(column="customers.name")],
        aggregates=[Aggregate(column="orders.amount", func="SUM", alias="total_spent")],
    )
    compiled = compile_report(metadata, request, supported_join_types=("INNER", "LEFT"))
    with engine.connect() as conn:
        rows = {row.name: row.total_spent for row in conn.execute(compiled.statement)}
    assert rows["Asha"] == 800
    assert rows["Ravi"] == 100
