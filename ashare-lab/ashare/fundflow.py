"""Summarize daily main-force net inflow series (newest first)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _n(v: Any) -> Optional[float]:
    if v is None or v == "" or v == "-":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:
        return None
    return f


def consecutive_flow(nets: List[Optional[float]]) -> int:
    """Positive = consecutive inflow days, negative = consecutive outflow days."""
    vals = [_n(v) for v in nets]
    vals = [v for v in vals if v is not None]
    if not vals:
        return 0
    first = vals[0]
    if first > 0:
        sign = 1
    elif first < 0:
        sign = -1
    else:
        return 0
    n = 0
    for v in vals:
        if (v > 0 and sign > 0) or (v < 0 and sign < 0):
            n += 1
        else:
            break
    return sign * n


def window_sum(nets: List[Optional[float]], days: int) -> Optional[float]:
    vals = [_n(v) for v in nets[:days]]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return sum(vals)


def inflow_day_count(nets: List[Optional[float]], days: int) -> int:
    vals = [_n(v) for v in nets[:days]]
    return sum(1 for v in vals if v is not None and v > 0)


def summarize_fund_flow(days: List[Dict[str, Any]]) -> Dict[str, Any]:
    """days: newest-first list of {date, main_net, extra_large_net, large_net, medium_net, small_net, main_pct}."""
    ordered = [d for d in days if d.get("date")]
    nets = [d.get("main_net") for d in ordered]
    today = ordered[0] if ordered else {}
    sum5 = window_sum(nets, 5)
    sum10 = window_sum(nets, 10)
    sum20 = window_sum(nets, 20)
    consec = consecutive_flow(nets)
    extra = _n(today.get("extra_large_net"))
    large = _n(today.get("large_net"))
    return {
        "today_main": _n(today.get("main_net")),
        "today_pct": _n(today.get("main_pct")),
        "today_extra_large": extra,
        "today_large": large,
        "today_medium": _n(today.get("medium_net")),
        "today_small": _n(today.get("small_net")),
        "sum_5": None if sum5 is None else round(sum5, 2),
        "sum_10": None if sum10 is None else round(sum10, 2),
        "sum_20": None if sum20 is None else round(sum20, 2),
        "inflow_days_5": inflow_day_count(nets, 5),
        "consecutive": consec,
        "days": ordered[:20],
        "source": today.get("source") or "",
    }
