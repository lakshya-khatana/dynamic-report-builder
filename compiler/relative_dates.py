"""Spec §3.4 DateTime operators: 'Relative Dates — Last 30 Days, This Month'."""

from datetime import date, datetime, timedelta

from errors.exceptions import CompileError


def resolve_relative_range(keyword: str) -> tuple[datetime, datetime]:
    today = date.today()
    now = datetime.combine(today, datetime.min.time())

    if keyword == "last_7_days":
        return now - timedelta(days=7), now + timedelta(days=1)
    if keyword == "last_30_days":
        return now - timedelta(days=30), now + timedelta(days=1)
    if keyword == "this_month":
        start = now.replace(day=1)
        return start, now + timedelta(days=1)
    if keyword == "last_month":
        first_of_this_month = now.replace(day=1)
        last_month_end = first_of_this_month
        last_month_start = (first_of_this_month - timedelta(days=1)).replace(day=1)
        return last_month_start, last_month_end
    if keyword == "this_year":
        return now.replace(month=1, day=1), now + timedelta(days=1)

    raise CompileError(f"Unknown relative date keyword: '{keyword}'")
