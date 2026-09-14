import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ashare.codes import em_secid, is_a_share_equity, market_of, tencent_symbol, ts_code
from ashare.indicators import macd, rsi, sma, summarize_trend
from ashare.scoring import lightweight_score, score_stock


class CodeTests(unittest.TestCase):
    def test_a_share_filter(self):
        self.assertTrue(is_a_share_equity("600519"))
        self.assertTrue(is_a_share_equity("000001.SZ"))
        self.assertTrue(is_a_share_equity("300750"))
        self.assertTrue(is_a_share_equity("688981"))
        self.assertTrue(is_a_share_equity("830799"))
        self.assertFalse(is_a_share_equity("00700"))
        self.assertFalse(is_a_share_equity("AAPL"))
        self.assertFalse(is_a_share_equity("510300", "沪深300ETF"))
        self.assertFalse(is_a_share_equity("110059"))
        self.assertFalse(is_a_share_equity("900901"))
        self.assertFalse(is_a_share_equity("200011"))

    def test_market_maps(self):
        self.assertEqual(market_of("600519"), "SH")
        self.assertEqual(em_secid("600519"), "1.600519")
        self.assertEqual(em_secid("000001"), "0.000001")
        self.assertEqual(tencent_symbol("300750"), "sz300750")
        self.assertEqual(ts_code("600519"), "600519.SH")


class IndicatorTests(unittest.TestCase):
    def test_sma_and_rsi(self):
        vals = list(range(1, 21))
        self.assertEqual(sma(vals, 5), 18.0)
        self.assertIsNone(sma(vals, 50))
        rising = [float(i) for i in range(1, 30)]
        self.assertGreater(rsi(rising), 70)

    def test_macd_uptrend(self):
        closes = [100 * (1.008 ** i) for i in range(80)]
        result = macd(closes)
        self.assertIsNotNone(result["dif"])
        self.assertIn(result["cross"], {"金叉", "多头"})

    def test_trend_alignment(self):
        closes = [10 + i * 0.2 for i in range(80)]
        volumes = [1000.0] * 80
        trend = summarize_trend(closes, volumes)
        self.assertEqual(trend["alignment"], "多头排列")
        self.assertIsNotNone(trend["ma60"])


class ScoreTests(unittest.TestCase):
    def test_quality_leader_high_score(self):
        result = score_stock(
            name="贵州茅台",
            pe_ttm=18,
            pb=6.3,
            pe_p30=22,
            pe_p50=29,
            pe_p70=35,
            roe=30,
            revenue_yoy=12,
            profit_yoy=10,
            gross_margin=90,
            debt_ratio=20,
            trend={
                "alignment": "多头排列",
                "macd": {"cross": "多头"},
                "rsi14": 55,
                "vol_ratio": 1.1,
                "ret20": 4.2,
            },
            main_net_inflow=8e8,
            turnover=0.4,
            mkt_cap=1.6e12,
        )
        self.assertGreaterEqual(result.total, 70)
        self.assertIn(result.verdict, {"进一步研究", "纳入观察"})

    def test_st_and_loss_are_flagged(self):
        result = score_stock(
            name="*ST示例",
            pe_ttm=-12,
            pb=18,
            roe=-8,
            revenue_yoy=-30,
            profit_yoy=-40,
            debt_ratio=82,
            trend={"alignment": "空头排列", "macd": {"cross": "死叉"}, "rsi14": 82, "vol_ratio": 3.5},
            main_net_inflow=-5e8,
            mkt_cap=2e9,
        )
        self.assertTrue(any("ST" in r for r in result.risks))
        self.assertTrue(any("负PE" in r for r in result.risks))
        self.assertLess(result.total, 50)

    def test_screener_score_dict(self):
        data = lightweight_score(
            {"name": "宁德时代", "pe_ttm": 22, "pb": 4, "roe": 16, "main_net_inflow": 1e8, "turnover": 1.2, "mkt_cap": 8e11}
        ).to_dict()
        self.assertEqual(set(data), {"total", "verdict", "verdict_note", "parts", "risks"})
        self.assertEqual(len(data["parts"]), 4)


if __name__ == "__main__":
    unittest.main()
