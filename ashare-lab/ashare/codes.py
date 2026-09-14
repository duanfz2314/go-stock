"""A-share code helpers. Only Shanghai / Shenzhen / Beijing listed equities."""

from __future__ import annotations

import re
from typing import Optional

_NON_DIGIT = re.compile(r"\D+")

# East Money market: 1 = SH, 0 = SZ/BJ (BJ also uses 0 in quote APIs).
SH_PREFIXES = ("60", "68")
SZ_PREFIXES = ("00", "30")
BJ_PREFIXES = ("43", "82", "83", "87", "88", "92")


def digits(code: str) -> str:
    return _NON_DIGIT.sub("", (code or "").strip())


def is_a_share_equity(code: str, name: str = "") -> bool:
    """True for 沪深京 A-share stocks (including STAR/ChiNext/BSE). Excludes funds/index."""
    raw = (code or "").strip().upper()
    name = name or ""
    if any(tag in name.upper() for tag in ("ETF", "LOF", "REIT")):
        return False
    d = digits(raw)
    if len(d) != 6:
        return False
    # Bond / repo / index-like
    if d.startswith(("10", "11", "12", "13", "14", "15", "16", "17", "18", "19")):
        return False
    if d.startswith(SH_PREFIXES + SZ_PREFIXES + BJ_PREFIXES):
        return True
    return False


def market_of(code: str) -> Optional[str]:
    d = digits(code)
    if not d:
        return None
    if d.startswith(("60", "68", "90")):
        return "SH"
    if d.startswith(("00", "30", "20")):
        return "SZ"
    if d.startswith(BJ_PREFIXES):
        return "BJ"
    return None


def em_secid(code: str) -> str:
    d = digits(code)
    m = market_of(d)
    if m == "SH":
        return f"1.{d}"
    return f"0.{d}"


def tencent_symbol(code: str) -> str:
    d = digits(code)
    m = market_of(d)
    if m == "SH":
        return f"sh{d}"
    if m == "BJ":
        return f"bj{d}"
    return f"sz{d}"


def sina_symbol(code: str) -> str:
    return tencent_symbol(code)


def ts_code(code: str) -> str:
    d = digits(code)
    m = market_of(d) or "SZ"
    return f"{d}.{m}"


def display_code(code: str) -> str:
    return ts_code(code)
