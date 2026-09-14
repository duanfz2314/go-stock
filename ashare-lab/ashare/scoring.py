"""Explainable A-share research score. Not a buy/sell signal."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScorePart:
    name: str
    score: float
    max_score: float
    reasons: List[str] = field(default_factory=list)


@dataclass
class ResearchScore:
    total: float
    verdict: str
    verdict_note: str
    parts: List[ScorePart]
    risks: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "verdict": self.verdict,
            "verdict_note": self.verdict_note,
            "parts": [asdict(p) for p in self.parts],
            "risks": self.risks,
        }


def _n(v: Any) -> Optional[float]:
    if v is None or v == "" or v == "-":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _verdict(total: float, risks: List[str]) -> tuple[str, str]:
    hard = any("ST" in r or "亏损" in r or "负PE" in r for r in risks)
    if hard and total < 70:
        return "回避", "存在硬性风险标记，不建议作为进一步研究的优先对象。"
    if total >= 75:
        return "进一步研究", "质量和估值/趋势匹配较好，可作为研究候选，仍需看公告与行业。"
    if total >= 60:
        return "纳入观察", "有一定亮点，但需要等待财报、趋势或资金再确认。"
    if total >= 40:
        return "谨慎", "亮点不多或互相矛盾，只适合熟悉该行业的人跟踪。"
    return "回避", "综合质量、估值、趋势偏弱，性价比一般。"


def score_stock(
    *,
    name: str = "",
    pe_ttm: Any = None,
    pb: Any = None,
    pe_p30: Any = None,
    pe_p50: Any = None,
    pe_p70: Any = None,
    roe: Any = None,
    revenue_yoy: Any = None,
    profit_yoy: Any = None,
    gross_margin: Any = None,
    debt_ratio: Any = None,
    trend: Optional[Dict[str, Any]] = None,
    main_net_inflow: Any = None,
    turnover: Any = None,
    mkt_cap: Any = None,
) -> ResearchScore:
    trend = trend or {}
    risks: List[str] = []
    uname = name or ""
    if "ST" in uname.upper() or "退" in uname:
        risks.append("名称含 ST / 退市风险提示，财务或交易可能异常。")

    pe = _n(pe_ttm)
    pb_v = _n(pb)
    if pe is not None and pe < 0:
        risks.append("负PE：当前可能亏损，估值框架失效。")
    if pe is not None and pe > 80:
        risks.append("PE(TTM) 超过 80，估值极贵或盈利波动很大。")
    if pb_v is not None and pb_v > 12:
        risks.append("市净率很高，更依赖成长兑现，容错低。")
    debt = _n(debt_ratio)
    if debt is not None and debt >= 70:
        risks.append(f"资产负债率 {debt:.1f}%，财务杠杆偏高。")
    profit = _n(profit_yoy)
    if profit is not None and profit <= -20:
        risks.append(f"净利润同比 {profit:.1f}%，盈利正在收缩。")
    cap = _n(mkt_cap)
    if cap is not None and cap < 3e9:
        risks.append("总市值偏小，波动和流动性风险更大。")

    # ---- 估值 25 ----
    val_score = 0.0
    val_reasons: List[str] = []
    p30, p50, p70 = _n(pe_p30), _n(pe_p50), _n(pe_p70)
    if pe is None or pe <= 0:
        val_reasons.append("缺少有效 PE(TTM)，估值项按低分处理。")
        val_score += 4
    else:
        if p30 and p70 and p70 > p30:
            if pe <= p30:
                val_score += 16
                val_reasons.append(f"PE(TTM) {pe:.1f} 低于近3年 30 分位 {p30:.1f}，相对自身历史偏低。")
            elif pe <= p50:
                val_score += 12
                val_reasons.append(f"PE(TTM) {pe:.1f} 处于近3年 30–50 分位，估值中性偏低。")
            elif pe <= p70:
                val_score += 7
                val_reasons.append(f"PE(TTM) {pe:.1f} 处于近3年 50–70 分位，估值中性偏高。")
            else:
                val_score += 3
                val_reasons.append(f"PE(TTM) {pe:.1f} 高于近3年 70 分位 {p70:.1f}，相对自身历史偏贵。")
        else:
            if 8 <= pe <= 25:
                val_score += 12
                val_reasons.append(f"PE(TTM) {pe:.1f}，落在常识性合理区间 8–25。")
            elif 25 < pe <= 40:
                val_score += 7
                val_reasons.append(f"PE(TTM) {pe:.1f}，略贵，需要更好的增长来消化。")
            elif pe < 8:
                val_score += 8
                val_reasons.append(f"PE(TTM) {pe:.1f} 很低，可能便宜也可能有隐患。")
            else:
                val_score += 3
                val_reasons.append(f"PE(TTM) {pe:.1f} 偏高。")
        if pb_v is not None:
            if 0 < pb_v <= 2:
                val_score += 9
                val_reasons.append(f"市净率 {pb_v:.2f}，资产价格不贵。")
            elif pb_v <= 5:
                val_score += 6
                val_reasons.append(f"市净率 {pb_v:.2f}，中等。")
            else:
                val_score += 2
                val_reasons.append(f"市净率 {pb_v:.2f}，偏贵。")
        else:
            val_score += 3
            val_reasons.append("缺少市净率。")
    val_score = _clip(val_score, 0, 25)

    # ---- 质量 30 ----
    q_score = 0.0
    q_reasons: List[str] = []
    roe_v = _n(roe)
    if roe_v is None:
        q_reasons.append("缺少 ROE。")
    elif roe_v >= 15:
        q_score += 12
        q_reasons.append(f"ROE {roe_v:.1f}%，盈利能力强。")
    elif roe_v >= 10:
        q_score += 8
        q_reasons.append(f"ROE {roe_v:.1f}%，中等偏好。")
    elif roe_v >= 5:
        q_score += 4
        q_reasons.append(f"ROE {roe_v:.1f}%，一般。")
    else:
        q_reasons.append(f"ROE {roe_v:.1f}%，盈利能力弱。")

    rev = _n(revenue_yoy)
    if rev is None:
        q_reasons.append("缺少营收同比。")
    elif rev >= 15:
        q_score += 7
        q_reasons.append(f"营收同比 {rev:.1f}%，成长明确。")
    elif rev >= 5:
        q_score += 5
        q_reasons.append(f"营收同比 {rev:.1f}%，温和增长。")
    elif rev >= 0:
        q_score += 3
        q_reasons.append(f"营收同比 {rev:.1f}%，接近停滞。")
    else:
        q_score += 1
        q_reasons.append(f"营收同比 {rev:.1f}%，在收缩。")

    if profit is None:
        q_reasons.append("缺少净利润同比。")
    elif profit >= 15:
        q_score += 7
        q_reasons.append(f"净利润同比 {profit:.1f}%。")
    elif profit >= 0:
        q_score += 4
        q_reasons.append(f"净利润同比 {profit:.1f}%。")
    else:
        q_score += 1
        q_reasons.append(f"净利润同比 {profit:.1f}%。")

    gm = _n(gross_margin)
    if gm is not None:
        if gm >= 40:
            q_score += 4
            q_reasons.append(f"毛利率 {gm:.1f}%，生意质量较好。")
        elif gm >= 20:
            q_score += 2
            q_reasons.append(f"毛利率 {gm:.1f}%。")
        else:
            q_reasons.append(f"毛利率 {gm:.1f}%，偏薄。")
    q_score = _clip(q_score, 0, 30)

    # ---- 趋势 25 ----
    t_score = 0.0
    t_reasons: List[str] = []
    align = trend.get("alignment") or "数据不足"
    if align == "多头排列":
        t_score += 10
        t_reasons.append("价格与均线多头排列。")
    elif align == "站上短期均线":
        t_score += 7
        t_reasons.append("收盘站上 MA20，但尚未形成完整多头。")
    elif align == "跌破短期均线":
        t_score += 3
        t_reasons.append("收盘跌破 MA20。")
    elif align == "空头排列":
        t_score += 1
        t_reasons.append("均线空头排列，趋势偏弱。")
    else:
        t_reasons.append("K 线样本不足，趋势项打折。")
        t_score += 5

    macd = trend.get("macd") or {}
    cross = macd.get("cross")
    if cross == "金叉":
        t_score += 8
        t_reasons.append("MACD 金叉。")
    elif cross == "多头":
        t_score += 5
        t_reasons.append("MACD 柱为正，动能偏多。")
    elif cross == "死叉":
        t_score += 1
        t_reasons.append("MACD 死叉。")
    elif cross == "空头":
        t_score += 2
        t_reasons.append("MACD 柱为负。")
    else:
        t_score += 3

    rsi_v = _n(trend.get("rsi14"))
    if rsi_v is None:
        t_score += 2
    elif 45 <= rsi_v <= 70:
        t_score += 5
        t_reasons.append(f"RSI(14) {rsi_v:.1f}，不热不冷。")
    elif rsi_v > 75:
        t_score += 1
        t_reasons.append(f"RSI(14) {rsi_v:.1f}，短期偏热。")
        risks.append("RSI 过高，注意短期回吐。")
    elif rsi_v < 30:
        t_score += 3
        t_reasons.append(f"RSI(14) {rsi_v:.1f}，超卖，可能反弹也可能继续跌。")
    else:
        t_score += 3
        t_reasons.append(f"RSI(14) {rsi_v:.1f}。")

    ret20 = _n(trend.get("ret20"))
    if ret20 is not None:
        t_reasons.append(f"近 20 日涨跌 {ret20:.1f}%。")
    t_score = _clip(t_score, 0, 25)

    # ---- 资金 20 ----
    f_score = 0.0
    f_reasons: List[str] = []
    flow = _n(main_net_inflow)
    if flow is None:
        f_score += 6
        f_reasons.append("缺少主力净流入，资金项中性。")
    elif flow > 0:
        f_score += 12
        f_reasons.append(f"主力净流入 {flow / 1e8:.2f} 亿元。")
    else:
        f_score += 3
        f_reasons.append(f"主力净流出 {abs(flow) / 1e8:.2f} 亿元。")
    vr = _n(trend.get("vol_ratio"))
    if vr is None:
        f_score += 3
    elif 0.8 <= vr <= 2.2:
        f_score += 5
        f_reasons.append(f"量比 {vr:.2f}，成交活跃度正常。")
    elif vr > 2.2:
        f_score += 3
        f_reasons.append(f"量比 {vr:.2f}，放量，需区分是进攻还是出货。")
    else:
        f_score += 2
        f_reasons.append(f"量比 {vr:.2f}，交投清淡。")
    to = _n(turnover)
    if to is not None:
        f_reasons.append(f"换手率 {to:.2f}%。")
        if 0.5 <= to <= 8:
            f_score += 3
    f_score = _clip(f_score, 0, 20)

    parts = [
        ScorePart("估值", round(val_score, 1), 25, val_reasons),
        ScorePart("质量", round(q_score, 1), 30, q_reasons),
        ScorePart("趋势", round(t_score, 1), 25, t_reasons),
        ScorePart("资金", round(f_score, 1), 20, f_reasons),
    ]
    total = round(sum(p.score for p in parts), 1)
    verdict, note = _verdict(total, risks)
    return ResearchScore(total=total, verdict=verdict, verdict_note=note, parts=parts, risks=risks)


def lightweight_score(row: Dict[str, Any]) -> ResearchScore:
    """Score a screener row using quote fields only (no K-line)."""
    return score_stock(
        name=row.get("name") or "",
        pe_ttm=row.get("pe_ttm"),
        pb=row.get("pb"),
        roe=row.get("roe"),
        main_net_inflow=row.get("main_net_inflow"),
        turnover=row.get("turnover"),
        mkt_cap=row.get("mkt_cap"),
        trend={
            "alignment": "数据不足",
            "macd": {},
            "rsi14": None,
            "vol_ratio": row.get("vol_ratio"),
        },
    )
