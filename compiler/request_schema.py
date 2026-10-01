"""
This is the JSON contract the whole system is built around — the frontend
sends this shape, templates_store saves this shape, compiler.py consumes it.
Getting this schema right first is why the build order puts this before
join_builder/filter_builder/etc.
"""

from typing import Literal

from pydantic import BaseModel, Field

JoinType = Literal["INNER", "LEFT", "RIGHT", "FULL"]
AggregateFunc = Literal["COUNT", "SUM", "AVG", "MIN", "MAX"]
SortDirection = Literal["ASC", "DESC"]

# Spec §3.4 operator table, one Literal per data-type family
StringOp = Literal["eq", "ne", "contains", "starts_with", "ends_with", "in"]
NumericOp = Literal["eq", "ne", "gt", "gte", "lt", "lte", "between"]
DateOp = Literal["eq", "before", "after", "between", "relative"]
FilterOp = StringOp | NumericOp | DateOp


class JoinCondition(BaseModel):
    left_column: str      # "orders.customer_id"
    right_column: str     # "customers.id"
    boolean_op: Literal["AND", "OR"] = "AND"  # how this condition combines with the next one


class JoinConfig(BaseModel):
    target_table: str
    join_type: JoinType = "INNER"
    conditions: list[JoinCondition]


class FieldSelection(BaseModel):
    column: str            # "customers.first_name"
    alias: str | None = None  # Spec §3.2 custom aliasing, e.g. "First Name"


class Aggregate(BaseModel):
    column: str
    func: AggregateFunc
    alias: str


class Filter(BaseModel):
    column: str
    op: FilterOp
    value: object | None = None  # scalar, [start, end] for between, list for "in"
    # Spec §3.4 relative dates: "last_7_days" | "last_30_days" | "this_month" | "last_month"
    relative: str | None = None


class SortRule(BaseModel):
    column: str            # can reference an aggregate alias
    direction: SortDirection = "ASC"
    priority: int = 0       # lower = applied first


class ReportRequest(BaseModel):
    source_id: str
    base_table: str
    joins: list[JoinConfig] = Field(default_factory=list)
    fields: list[FieldSelection]
    aggregates: list[Aggregate] = Field(default_factory=list)
    filters: list[Filter] = Field(default_factory=list)
    having: list[Filter] = Field(default_factory=list)  # same shape, applied post-aggregation
    sort: list[SortRule] = Field(default_factory=list)
    page: int = 1
    page_size: int = 50


class ReportTemplate(BaseModel):
    """Spec §4 persisted shape — a ReportRequest plus audit/identity fields."""
    id: str | None = None
    name: str
    author: str | None = None
    request: ReportRequest
    created_at: str | None = None
    updated_at: str | None = None
