"""Daily technical indicators. Enough for swing / position research, not tick trading."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence


def _floats(values: Iterable[Optional[float]]) -> List[float]:
    out: List[float] = []
    for v in values:
        if v is None:
            continue
        out.append(float(v))
    return out


def sma(values: Sequence[float], n: int) -> Optional[float]:
    if n <= 0 or len(values) < n:
        return None
    window = values[-n:]
    return sum(window) / n


def ema_series(values: Sequence[float], n: int) -> List[Optional[float]]:
    if n <= 0 or not values:
        return []
    k = 2 / (n + 1)
    out: List[Optional[float]] = []
    prev: Optional[float] = None
    for i, v in enumerate(values):
        if prev is None:
            if i + 1 >= n:
                prev = sum(values[: n]) / n
                out.append(prev)
            else:
                out.append(None)
            continue
        prev = v * k + prev * (1 - k)
        out.append(prev)
    return out


def macd(closes: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    if len(closes) < slow + signal:
        return {"dif": None, "dea": None, "hist": None, "cross": "不足"}
    ema_fast = ema_series(closes, fast)
    ema_slow = ema_series(closes, slow)
    difs: List[float] = []
    for a, b in zip(ema_fast, ema_slow):
        if a is None or b is None:
            continue
        difs.append(a - b)
    if len(difs) < signal:
        return {"dif": None, "dea": None, "hist": None, "cross": "不足"}
    dea_series = ema_series(difs, signal)
    dea = dea_series[-1]
    dif = difs[-1]
    if dea is None:
        return {"dif": round(dif, 4), "dea": None, "hist": None, "cross": "不足"}
    hist = 2 * (dif - dea)
    prev_dif = difs[-2] if len(difs) >= 2 else dif
    prev_dea = dea_series[-2] if len(dea_series) >= 2 and dea_series[-2] is not None else dea
    cross = "无"
    if prev_dif <= prev_dea and dif > dea:
        cross = "金叉"
    elif prev_dif >= prev_dea and dif < dea:
        cross = "死叉"
    elif hist >= -1e-8:
        cross = "多头"
    else:
        cross = "空头"
    return {
        "dif": round(dif, 4),
        "dea": round(dea, 4),
        "hist": round(hist, 4),
        "cross": cross,
    }


def rsi(closes: Sequence[float], n: int = 14) -> Optional[float]:
    if len(closes) < n + 1:
        return None
    gains = []
    losses = []
    for i in range(-n, 0):
        chg = closes[i] - closes[i - 1]
        if chg >= 0:
            gains.append(chg)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(-chg)
    avg_gain = sum(gains) / n
    avg_loss = sum(losses) / n
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def volume_ratio(volumes: Sequence[float], n: int = 5) -> Optional[float]:
    if len(volumes) < n + 1:
        return None
    avg = sum(volumes[-(n + 1) : -1]) / n
    if avg == 0:
        return None
    return round(volumes[-1] / avg, 2)


def pct_change(closes: Sequence[float], days: int) -> Optional[float]:
    if len(closes) < days + 1:
        return None
    prev = closes[-(days + 1)]
    if prev == 0:
        return None
    return round((closes[-1] / prev - 1) * 100, 2)


def summarize_trend(closes: Sequence[float], volumes: Sequence[float]) -> dict:
    closes = _floats(closes)
    volumes = _floats(volumes)
    ma5 = sma(closes, 5)
    ma10 = sma(closes, 10)
    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60)
    last = closes[-1] if closes else None
    alignment = "数据不足"
    if last is not None and ma20 is not None and ma60 is not None:
        if last >= ma20 >= ma60:
            alignment = "多头排列"
        elif last <= ma20 <= ma60:
            alignment = "空头排列"
        elif last >= ma20:
            alignment = "站上短期均线"
        else:
            alignment = "跌破短期均线"
    return {
        "last": last,
        "ma5": None if ma5 is None else round(ma5, 3),
        "ma10": None if ma10 is None else round(ma10, 3),
        "ma20": None if ma20 is None else round(ma20, 3),
        "ma60": None if ma60 is None else round(ma60, 3),
        "alignment": alignment,
        "macd": macd(closes),
        "rsi14": rsi(closes),
        "vol_ratio": volume_ratio(volumes),
        "ret5": pct_change(closes, 5),
        "ret20": pct_change(closes, 20),
        "ret60": pct_change(closes, 60),
    }
