"""Assemble market / stock / screener payloads for the web UI."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Optional

from .client import AShareClient, DataError
from .codes import digits, is_a_share_equity
from .indicators import summarize_trend
from .scoring import lightweight_score, score_stock


class TTLCache:
    def __init__(self) -> None:
        self._data: Dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            exp, val = item
            if exp < time.time():
                self._data.pop(key, None)
                return None
            return val

    def set(self, key: str, val: Any, ttl: int) -> Any:
        with self._lock:
            self._data[key] = (time.time() + ttl, val)
            return val


class ResearchService:
    def __init__(self, client: Optional[AShareClient] = None) -> None:
        self.client = client or AShareClient()
        self.cache = TTLCache()

    def _cached(self, key: str, ttl: int, fn: Callable[[], Any]) -> Any:
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        val = fn()
        return self.cache.set(key, val, ttl)

    def market_overview(self) -> Dict[str, Any]:
        def load() -> Dict[str, Any]:
            indices, breadth, sectors, hot = [], {}, [], []
            errors = []
            try:
                indices = self.client.fetch_indices()
            except Exception as e:
                errors.append(f"指数: {e}")
            try:
                breadth = self.client.fetch_market_breadth()
            except Exception as e:
                errors.append(f"市场宽度: {e}")
            try:
                sectors = self.client.fetch_sectors(18)
            except Exception as e:
                errors.append(f"行业: {e}")
            try:
                hot = self.client.fetch_screener(page=1, size=12, sort="amount")
                for row in hot:
                    row["score"] = lightweight_score(row).to_dict()
            except Exception as e:
                errors.append(f"热门: {e}")
            return {
                "as_of": time.strftime("%Y-%m-%d %H:%M:%S"),
                "indices": indices,
                "breadth": breadth,
                "sectors": sectors,
                "hot": hot,
                "partial_errors": errors,
                "disclaimer": "数据来自东方财富 / 财联社 / 腾讯财经等免费公开接口，可能有延迟。本工具只做研究辅助，不构成投资建议。",
            }

        return self._cached("market", 120, load)

    def search(self, q: str) -> Dict[str, Any]:
        q = (q or "").strip()
        if not q:
            return {"items": []}
        items = self.client.search(q)
        return {"items": items}

    def stock_research(self, code: str) -> Dict[str, Any]:
        code = digits(code)
        if not is_a_share_equity(code):
            raise DataError("仅支持沪深京 A 股股票代码")

        def load() -> Dict[str, Any]:
            quote = self.client.fetch_quote(code)
            finance = {"latest": {}, "quarters": []}
            try:
                finance = self.client.fetch_finance(code)
            except Exception:
                finance = {"latest": {}, "quarters": []}
            percentile = {}
            try:
                percentile = self.client.fetch_pe_percentile(code)
            except Exception:
                percentile = {}
            kline, k_source = [], ""
            try:
                kline, k_source = self.client.fetch_kline(code, 180)
            except Exception:
                kline, k_source = [], "暂不可用"
            closes = [b["close"] for b in kline if b.get("close") is not None]
            volumes = [b.get("volume") or 0 for b in kline]
            trend = summarize_trend(closes, volumes)
            latest = finance.get("latest") or {}
            score = score_stock(
                name=quote.get("name") or "",
                pe_ttm=quote.get("pe_ttm"),
                pb=quote.get("pb"),
                pe_p30=percentile.get("p30"),
                pe_p50=percentile.get("p50"),
                pe_p70=percentile.get("p70"),
                roe=latest.get("roe"),
                revenue_yoy=latest.get("revenue_yoy"),
                profit_yoy=latest.get("profit_yoy"),
                gross_margin=latest.get("gross_margin"),
                debt_ratio=latest.get("debt_ratio"),
                trend=trend,
                main_net_inflow=quote.get("main_net_inflow"),
                turnover=quote.get("turnover"),
                mkt_cap=quote.get("mkt_cap"),
            )
            return {
                "quote": quote,
                "finance": finance,
                "valuation": percentile,
                "kline": kline[-120:],
                "kline_source": k_source,
                "trend": trend,
                "score": score.to_dict(),
                "disclaimer": "研究评分用于缩小关注范围，不是买卖建议。请结合公告、行业和自身风险承受能力。",
            }

        return self._cached(f"stock:{code}", 180, load)

    def screener(self, params: Dict[str, Any]) -> Dict[str, Any]:
        def load() -> Dict[str, Any]:
            rows = self.client.fetch_screener(page=1, size=100, sort=str(params.get("sort") or "amount"))
            pe_max = _opt_float(params.get("pe_max"))
            pb_max = _opt_float(params.get("pb_max"))
            roe_min = _opt_float(params.get("roe_min"))
            cap_min = _opt_float(params.get("cap_min"))  # 亿元
            exclude_st = str(params.get("exclude_st") or "1") != "0"
            industry = (params.get("industry") or "").strip()
            filtered = []
            for row in rows:
                name = row.get("name") or ""
                if exclude_st and ("ST" in name.upper() or "退" in name):
                    continue
                pe = row.get("pe_ttm") if row.get("pe_ttm") is not None else row.get("pe")
                if pe_max is not None and (pe is None or pe <= 0 or pe > pe_max):
                    continue
                if pb_max is not None and (row.get("pb") is None or row["pb"] > pb_max):
                    continue
                if roe_min is not None and (row.get("roe") is None or row["roe"] < roe_min):
                    continue
                if cap_min is not None:
                    cap_yi = None if row.get("mkt_cap") is None else row["mkt_cap"] / 1e8
                    if cap_yi is None or cap_yi < cap_min:
                        continue
                if industry and industry not in str(row.get("industry") or ""):
                    continue
                scored = lightweight_score({**row, "pe_ttm": pe})
                item = dict(row)
                item["score"] = scored.to_dict()
                filtered.append(item)
            filtered.sort(key=lambda x: x["score"]["total"], reverse=True)
            return {
                "total": len(filtered),
                "items": filtered[:50],
                "note": "候选来自当日成交额靠前的 A 股（延迟行情），再用估值/质量规则打初筛分。点进个股页会补上日 K，完整分可能更高或更低。",
            }

        key = "screen:" + "&".join(f"{k}={params.get(k)}" for k in sorted(params))
        return self._cached(key, 180, load)


def _opt_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
