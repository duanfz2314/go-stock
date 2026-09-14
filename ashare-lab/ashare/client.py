"""Free public A-share data: East Money delayed quotes/F10, Tencent/Sina daily K-line."""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .codes import digits, em_secid, is_a_share_equity, market_of, sina_symbol, tencent_symbol, ts_code

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


class DataError(RuntimeError):
    pass


def _headers(referer: str) -> Dict[str, str]:
    return {
        "User-Agent": random.choice(UA_POOL),
        "Referer": referer,
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


def http_get(url: str, referer: str, timeout: int = 15, retries: int = 3, extra_headers: Optional[Dict[str, str]] = None) -> bytes:
    last: Optional[Exception] = None
    for i in range(retries):
        headers = _headers(referer)
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (400, 404):
                raise DataError(f"HTTP {e.code} {url}") from e
        except Exception as e:
            last = e
        time.sleep(0.4 * (i + 1))
    raise DataError(f"{type(last).__name__}: {last}") from last


def http_json(url: str, referer: str, timeout: int = 15, extra_headers: Optional[Dict[str, str]] = None) -> Any:
    raw = http_get(url, referer, timeout=timeout, extra_headers=extra_headers)
    text = raw.decode("utf-8", "replace")
    if text.startswith("data(") and text.endswith(")"):
        text = text[5:-1]
    return json.loads(text)


def _num(v: Any) -> Optional[float]:
    if v is None or v == "" or v == "-" or v == "—":
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        if f != f:
            return None
        return f
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


class AShareClient:
    def fetch_indices(self) -> List[Dict[str, Any]]:
        query = (
            "/api/qt/ulist.np/get?fltt=2&invt=2&fields=f2,f3,f4,f5,f6,f12,f13,f14"
            "&secids=1.000001,0.399001,0.399006,1.000688,1.000300"
        )
        data = None
        errors = []
        for host in ("push2delay.eastmoney.com", "push2.eastmoney.com"):
            try:
                data = http_json(f"https://{host}{query}", "https://quote.eastmoney.com/")
                break
            except Exception as e:
                errors.append(f"{host}:{e}")
        if data is None:
            raise DataError("指数行情失败: " + "; ".join(errors))
        rows = (data.get("data") or {}).get("diff") or []
        out = []
        for r in rows:
            out.append(
                {
                    "code": r.get("f12"),
                    "name": r.get("f14"),
                    "price": _num(r.get("f2")),
                    "pct": _num(r.get("f3")),
                    "change": _num(r.get("f4")),
                    "amount": _num(r.get("f6")),
                }
            )
        return out

    def fetch_market_breadth(self) -> Dict[str, Any]:
        url = "https://x-quote.cls.cn/quote/index/home?app=CailianpressWeb&os=web&sv=8.4.6"
        data = http_json(url, "https://www.cls.cn/")
        payload = data.get("data") or {}
        dis = payload.get("up_down_dis") or {}
        quotes = []
        for q in payload.get("index_quote") or []:
            code = (q.get("secu_code") or "").replace("sh", "").replace("sz", "")
            if not is_a_share_equity(code) and code not in {"000001", "399001", "399006", "000688", "000300"}:
                # keep major A-share indexes only
                if not str(q.get("secu_code", "")).startswith(("sh000", "sz399")):
                    continue
            chg = _num(q.get("change"))
            quotes.append(
                {
                    "code": q.get("secu_code"),
                    "name": q.get("secu_name"),
                    "price": _num(q.get("last_px")),
                    "pct": None if chg is None else round(chg * 100, 2),
                    "up": q.get("up_num"),
                    "down": q.get("down_num"),
                }
            )
        return {
            "up": dis.get("rise_num"),
            "down": dis.get("fall_num"),
            "flat": dis.get("flat_num"),
            "limit_up": dis.get("up_10"),
            "limit_down": dis.get("down_10"),
            "avg_pct": None if _num(dis.get("average_rise")) is None else round(_num(dis.get("average_rise")) * 100, 2),
            "suspend": dis.get("suspend_num"),
            "histogram": {
                "down10": dis.get("down_10"),
                "down8": dis.get("down_8"),
                "down6": dis.get("down_6"),
                "down4": dis.get("down_4"),
                "down2": dis.get("down_2"),
                "flat": dis.get("flat_num"),
                "up2": dis.get("up_2"),
                "up4": dis.get("up_4"),
                "up6": dis.get("up_6"),
                "up8": dis.get("up_8"),
                "up10": dis.get("up_10"),
            },
            "index_updown": quotes,
        }

    def fetch_sectors(self, limit: int = 16) -> List[Dict[str, Any]]:
        url = (
            "https://push2delay.eastmoney.com/api/qt/clist/get"
            f"?pn=1&pz={limit}&po=1&np=1&fltt=2&invt=2&fid=f3"
            "&fs=m:90+t:2+f:!50&fields=f12,f14,f2,f3,f62,f184"
        )
        data = http_json(url, "https://quote.eastmoney.com/center/gridlist.html")
        rows = (data.get("data") or {}).get("diff") or []
        if isinstance(rows, dict):
            rows = list(rows.values())
        out = []
        for r in rows:
            out.append(
                {
                    "code": r.get("f12"),
                    "name": r.get("f14"),
                    "price": _num(r.get("f2")),
                    "pct": _num(r.get("f3")),
                    "main_net_inflow": _num(r.get("f62")),
                    "main_net_pct": _num(r.get("f184")),
                }
            )
        return out

    def search(self, keyword: str, count: int = 12) -> List[Dict[str, Any]]:
        q = urllib.parse.quote(keyword.strip())
        url = (
            "https://searchapi.eastmoney.com/api/suggest/get"
            f"?input={q}&type=14&token=FAKESECRET_k3l4m5n6o7p8q9r0s1t2"
            f"&markettype=&mktnum=&jys=&classify=&securitytype=1,2,23&status=&count={count}"
        )
        data = http_json(url, "https://quote.eastmoney.com/")
        table = (data.get("QuotationCodeTable") or {}).get("Data") or []
        out = []
        for row in table:
            code = str(row.get("Code") or "")
            name = str(row.get("Name") or "")
            classify = str(row.get("Classify") or "")
            type_name = str(row.get("SecurityTypeName") or "")
            if classify and classify not in {"AStock", "A股"}:
                if type_name not in {"沪A", "深A", "京A", "创业板", "科创板", "北证A"}:
                    continue
            if not is_a_share_equity(code, name) and type_name not in {"沪A", "深A", "京A", "创业板", "科创板"}:
                continue
            if not digits(code):
                continue
            out.append(
                {
                    "code": digits(code),
                    "ts_code": ts_code(code),
                    "name": name,
                    "type": type_name or "A股",
                    "market": market_of(code),
                }
            )
        return out

    def fetch_quote(self, code: str) -> Dict[str, Any]:
        url = (
            "https://push2delay.eastmoney.com/api/qt/stock/get?fltt=2&invt=2"
            f"&secid={em_secid(code)}"
            "&fields=f57,f58,f43,f46,f44,f45,f47,f48,f60,f169,f170,f168,f50,"
            "f162,f167,f116,f117,f127,f183,f92,f55,f84,f85,f189,f62,f135,f136"
        )
        data = http_json(url, "https://quote.eastmoney.com/")
        r = data.get("data") or {}
        if not r:
            raise DataError("行情为空")
        return {
            "code": str(r.get("f57") or digits(code)),
            "ts_code": ts_code(code),
            "name": r.get("f58"),
            "price": _num(r.get("f43")),
            "open": _num(r.get("f46")),
            "high": _num(r.get("f44")),
            "low": _num(r.get("f45")),
            "prev_close": _num(r.get("f60")),
            "change": _num(r.get("f169")),
            "pct": _num(r.get("f170")),
            "volume": _num(r.get("f47")),
            "amount": _num(r.get("f48")),
            "turnover": _num(r.get("f168")),
            "vol_ratio": _num(r.get("f50")),
            "pe_ttm": _num(r.get("f162")),
            "pb": _num(r.get("f167")),
            "mkt_cap": _num(r.get("f116")),
            "circ_cap": _num(r.get("f117")),
            "industry": r.get("f127"),
            "eps": _num(r.get("f55")),
            "navps": _num(r.get("f92")),
            "list_date": r.get("f189"),
            "main_net_inflow": _num(r.get("f62")),
        }

    def fetch_kline(self, code: str, limit: int = 180) -> Tuple[List[Dict[str, Any]], str]:
        errors = []
        try:
            bars = self._kline_tencent(code, limit)
            if bars:
                return bars, "tencent"
        except Exception as e:
            errors.append(f"tencent:{e}")
        try:
            bars = self._kline_sina(code, limit)
            if bars:
                return bars, "sina"
        except Exception as e:
            errors.append(f"sina:{e}")
        try:
            bars = self._kline_eastmoney(code, limit)
            if bars:
                return bars, "eastmoney"
        except Exception as e:
            errors.append(f"eastmoney:{e}")
        raise DataError("日K获取失败: " + "; ".join(errors))

    def _kline_tencent(self, code: str, limit: int) -> List[Dict[str, Any]]:
        symbol = tencent_symbol(code)
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{limit},qfq"
        data = http_json(url, "https://gu.qq.com/")
        node = ((data.get("data") or {}).get(symbol) or {})
        rows = node.get("qfqday") or node.get("day") or []
        bars = []
        for row in rows:
            if not row or len(row) < 6:
                continue
            bars.append(
                {
                    "date": str(row[0])[:10],
                    "open": _num(row[1]),
                    "close": _num(row[2]),
                    "high": _num(row[3]),
                    "low": _num(row[4]),
                    "volume": _num(row[5]),
                }
            )
        return [b for b in bars if b["close"] is not None]

    def _kline_sina(self, code: str, limit: int) -> List[Dict[str, Any]]:
        symbol = sina_symbol(code)
        url = (
            "https://quotes.sina.cn/cn/api/jsonp_v2.php/_/"
            f"CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={limit}"
        )
        raw = http_get(url, "https://finance.sina.com.cn").decode("utf-8", "replace")
        start = raw.find("[")
        end = raw.rfind("]")
        if start < 0 or end < 0:
            raise DataError("sina kline parse")
        rows = json.loads(raw[start : end + 1])
        bars = []
        for row in rows:
            bars.append(
                {
                    "date": str(row.get("day") or "")[:10],
                    "open": _num(row.get("open")),
                    "close": _num(row.get("close")),
                    "high": _num(row.get("high")),
                    "low": _num(row.get("low")),
                    "volume": _num(row.get("volume")),
                }
            )
        return [b for b in bars if b["close"] is not None]

    def _kline_eastmoney(self, code: str, limit: int) -> List[Dict[str, Any]]:
        url = (
            "https://push2delay.eastmoney.com/api/qt/stock/kline/get"
            f"?secid={em_secid(code)}&klt=101&fqt=1&lmt={limit}&end=20500101"
            "&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        )
        data = http_json(url, "https://quote.eastmoney.com/")
        klines = ((data.get("data") or {}).get("klines")) or []
        bars = []
        for item in klines:
            p = str(item).split(",")
            if len(p) < 6:
                continue
            bars.append(
                {
                    "date": p[0][:10],
                    "open": _num(p[1]),
                    "close": _num(p[2]),
                    "high": _num(p[3]),
                    "low": _num(p[4]),
                    "volume": _num(p[5]),
                }
            )
        return bars

    def _f10(self, report: str, secu: str, columns: str, page_size: int = 1, sort_col: str = "REPORT_DATE") -> List[Dict[str, Any]]:
        filt = urllib.parse.quote(f'(SECUCODE="{secu}")', safe="()")
        cols = urllib.parse.quote(columns, safe="")
        url = (
            "https://datacenter.eastmoney.com/securities/api/data/v1/get"
            f"?reportName={report}&columns={cols}&quoteColumns=&filter={filt}"
            f"&sortTypes=-1&sortColumns={sort_col}&pageNumber=1&pageSize={page_size}"
            f"&source=HSF10&client=PC&v={int(time.time())}"
        )
        data = http_json(
            url,
            "https://emweb.securities.eastmoney.com/",
            extra_headers={"Origin": "https://emweb.securities.eastmoney.com"},
        )
        if not data.get("success"):
            return []
        return ((data.get("result") or {}).get("data")) or []

    def fetch_finance(self, code: str) -> Dict[str, Any]:
        secu = ts_code(code)
        latest_cols = (
            "SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,REPORT_DATE,REPORT_TYPE,EPSJB,BPS,ROEJQ,"
            "TOTAL_OPERATEINCOME,TOTALOPERATEREVETZ,PARENT_NETPROFIT,PARENTNETPROFITTZ,"
            "KCFJCXSYJLRTZ,XSMLL,ZCFZL,MGJYXJJE"
        )
        qtr_cols = (
            "SECUCODE,SECURITY_NAME_ABBR,REPORT_DATE,EPSJB,ROE_DILUTED,TOTALOPERATEREVE,"
            "TOTALOPERATEREVETZ,PARENTNETPROFIT,PARENTNETPROFITTZ,GROSS_PROFIT_RATIO"
        )
        latest_rows = self._f10("RPT_PCF10_FINANCEMAINFINADATA", secu, latest_cols, page_size=1)
        qtr = self._f10("RPT_F10_QTR_MAINFINADATA", secu, qtr_cols, page_size=8)
        latest = latest_rows[0] if latest_rows else {}
        return {
            "latest": {
                "report_date": str(latest.get("REPORT_DATE") or "")[:10],
                "report_type": latest.get("REPORT_TYPE") or latest.get("REPORT_DATE_NAME"),
                "eps": _num(latest.get("EPSJB")),
                "bps": _num(latest.get("BPS")),
                "roe": _num(latest.get("ROEJQ")),
                "revenue": _num(latest.get("TOTAL_OPERATEINCOME")),
                "revenue_yoy": _num(latest.get("TOTALOPERATEREVETZ")),
                "profit": _num(latest.get("PARENT_NETPROFIT")),
                "profit_yoy": _num(latest.get("PARENTNETPROFITTZ")),
                "deducted_profit_yoy": _num(latest.get("KCFJCXSYJLRTZ")),
                "gross_margin": _num(latest.get("XSMLL")),
                "debt_ratio": _num(latest.get("ZCFZL")),
                "ocf_ps": _num(latest.get("MGJYXJJE")),
            },
            "quarters": [
                {
                    "report_date": str(r.get("REPORT_DATE") or "")[:10],
                    "eps": _num(r.get("EPSJB")),
                    "roe": _num(r.get("ROE_DILUTED")),
                    "revenue": _num(r.get("TOTALOPERATEREVE")),
                    "revenue_yoy": _num(r.get("TOTALOPERATEREVETZ")),
                    "profit": _num(r.get("PARENTNETPROFIT")),
                    "profit_yoy": _num(r.get("PARENTNETPROFITTZ")),
                    "gross_margin": _num(r.get("GROSS_PROFIT_RATIO")),
                }
                for r in qtr
            ],
        }

    def fetch_pe_percentile(self, code: str) -> Dict[str, Any]:
        secu = urllib.parse.quote(f'(SECUCODE="{ts_code(code)}")(INDEX_TYPE="1")(STATISTICS_CYCLE="3")', safe="()")
        url = (
            "https://datacenter.eastmoney.com/securities/api/data/v1/get"
            "?reportName=RPT_STOCKVALUATIONTANTILE&columns=SECUCODE,STATISTICS_CYCLE,INDEX_TYPE,PERCENTILE_THIRTY,PERCENTILE_FIFTY,PERCENTILE_SEVENTY"
            f"&filter={secu}&pageNumber=1&pageSize=1&source=HSF10&client=PC"
        )
        data = http_json(
            url,
            "https://emweb.securities.eastmoney.com/",
            extra_headers={"Origin": "https://emweb.securities.eastmoney.com"},
        )
        rows = ((data.get("result") or {}).get("data")) or []
        if not rows:
            return {}
        r = rows[0]
        return {
            "p30": _num(r.get("PERCENTILE_THIRTY")),
            "p50": _num(r.get("PERCENTILE_FIFTY")),
            "p70": _num(r.get("PERCENTILE_SEVENTY")),
            "cycle": r.get("STATISTICS_CYCLE"),
        }

    def fetch_screener(self, page: int = 1, size: int = 80, sort: str = "amount") -> List[Dict[str, Any]]:
        fid_map = {"amount": "f6", "pct": "f3", "mktcap": "f20", "turnover": "f8"}
        fid = fid_map.get(sort, "f6")
        fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"
        url = (
            "https://push2delay.eastmoney.com/api/qt/clist/get"
            f"?np=1&fltt=2&invt=2&fs={urllib.parse.quote(fs, safe='+:!')}"
            "&fields=f12,f13,f14,f2,f3,f8,f9,f10,f20,f23,f37,f62,f100,f115,f184"
            f"&fid={fid}&pn={page}&pz={size}&po=1"
        )
        data = http_json(url, "https://quote.eastmoney.com/center/gridlist.html")
        rows = (data.get("data") or {}).get("diff") or []
        if isinstance(rows, dict):
            rows = list(rows.values())
        out = []
        for r in rows:
            code = str(r.get("f12") or "")
            name = str(r.get("f14") or "")
            if not is_a_share_equity(code, name):
                continue
            out.append(
                {
                    "code": code,
                    "ts_code": ts_code(code),
                    "name": name,
                    "price": _num(r.get("f2")),
                    "pct": _num(r.get("f3")),
                    "turnover": _num(r.get("f8")),
                    "pe": _num(r.get("f9")),
                    "pe_ttm": _num(r.get("f115")),
                    "vol_ratio": _num(r.get("f10")),
                    "mkt_cap": _num(r.get("f20")),
                    "pb": _num(r.get("f23")),
                    "roe": _num(r.get("f37")),
                    "main_net_inflow": _num(r.get("f62")),
                    "industry": r.get("f100"),
                    "main_net_pct": _num(r.get("f184")),
                }
            )
        return out
