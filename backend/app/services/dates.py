import calendar
from datetime import date, timedelta


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def advance(d: date, cycle: str) -> date:
    if cycle in ("daily",):
        return d + timedelta(days=1)
    if cycle == "weekly":
        return d + timedelta(weeks=1)
    if cycle == "monthly":
        return add_months(d, 1)
    if cycle == "quarterly":
        return add_months(d, 3)
    if cycle == "yearly":
        return add_months(d, 12)
    raise ValueError(cycle)


MONTHLY_FACTOR = {"weekly": 52 / 12, "monthly": 1, "quarterly": 1 / 3, "yearly": 1 / 12}
