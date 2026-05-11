"""
💡 AdvisorAgent 單元測試
"""
import unittest
from agents.advisor_agent import AdvisorAgent, Recommendation


def _make_candidate(symbol="TEST", tech=80, sent=0.75, risk=85, back=70, close=100.0):
    """建立測試用候選股票數據"""
    return {
        "symbol": symbol,
        "close": close,
        "scores": {
            "technical": tech,
            "sentiment": sent * 100,  # 轉換為 0-100 分數
            "risk": risk,
            "backtest": back,
        },
        "risk": {
            "target_price": close * 1.15,
            "stop_loss_price": close * 0.93,
            "risk_reward_ratio": 2.5,
        },
        "backtest": {
            "win_rate": 0.65,
        },
        "signals": ["MACD 金叉", "成交量暴增"],
    }


class TestAdvisorAgent(unittest.TestCase):

    def setUp(self):
        self.agent = AdvisorAgent()

    # ── 強力買進建議 ───────────────────────────────────
    def test_strong_buy_recommendation(self):
        """高分數應該產生強力買進建議"""
        c = _make_candidate(tech=85, sent=0.80, risk=85, back=75)
        result = self.agent.analyze(c)
        
        self.assertEqual(result.recommendation, Recommendation.STRONG_BUY)
        self.assertGreater(result.confidence, 75)
        self.assertIn("技術面", result.reason)

    # ── 買進建議 ───────────────────────────────────────
    def test_buy_recommendation(self):
        """中上分數應該產生買進建議"""
        c = _make_candidate(tech=75, sent=0.70, risk=70, back=65)
        result = self.agent.analyze(c)
        
        self.assertIn(result.recommendation, [Recommendation.BUY, Recommendation.STRONG_BUY])
        self.assertGreater(result.confidence, 60)

    # ── 持有建議 ───────────────────────────────────────
    def test_hold_recommendation(self):
        """中等分數應該產生持有建議"""
        c = _make_candidate(tech=60, sent=0.60, risk=60, back=55)
        result = self.agent.analyze(c)
        
        self.assertEqual(result.recommendation, Recommendation.HOLD)
        self.assertGreater(result.confidence, 50)
        self.assertLess(result.confidence, 70)

    # ── 賣出建議 ───────────────────────────────────────
    def test_sell_recommendation(self):
        """低分數應該產生賣出建議"""
        c = _make_candidate(tech=45, sent=0.40, risk=45, back=40)
        result = self.agent.analyze(c)
        
        self.assertEqual(result.recommendation, Recommendation.SELL)
        self.assertLess(result.confidence, 55)

    # ── 強力賣出建議 ───────────────────────────────────
    def test_strong_sell_recommendation(self):
        """極低分數應該產生強力賣出建議"""
        c = _make_candidate(tech=30, sent=0.25, risk=30, back=25)
        result = self.agent.analyze(c)
        
        self.assertEqual(result.recommendation, Recommendation.STRONG_SELL)
        self.assertLess(result.confidence, 40)
        self.assertIn("技術面", result.reason)

    # ── 價格計算 ───────────────────────────────────────
    def test_target_and_stop_loss_prices(self):
        """測試目標價和停損價的計算"""
        c = _make_candidate(close=100.0)
        result = self.agent.analyze(c)
        
        self.assertGreater(result.target_price, 100.0)  # 目標價應高於現價
        self.assertLess(result.stop_loss, 100.0)        # 停損價應低於現價
        self.assertGreater(result.target_price, result.stop_loss)

    # ── 策略內容 ───────────────────────────────────────
    def test_entry_strategy_exists(self):
        """測試進場策略存在"""
        c = _make_candidate()
        result = self.agent.analyze(c)
        
        self.assertIsNotNone(result.entry_strategy)
        self.assertGreater(len(result.entry_strategy), 0)

    def test_exit_strategy_exists(self):
        """測試出場策略存在"""
        c = _make_candidate()
        result = self.agent.analyze(c)
        
        self.assertIsNotNone(result.exit_strategy)
        self.assertGreater(len(result.exit_strategy), 0)
        self.assertIn("達", result.exit_strategy)  # 應包含目標價描述

    # ── 理由說明 ───────────────────────────────────────
    def test_reason_provided(self):
        """測試建議理由存在"""
        c = _make_candidate()
        result = self.agent.analyze(c)
        
        self.assertIsNotNone(result.reason)
        self.assertGreater(len(result.reason), 0)

    # ── 信心度範圍 ─────────────────────────────────────
    def test_confidence_in_valid_range(self):
        """測試信心度在有效範圍內"""
        c = _make_candidate()
        result = self.agent.analyze(c)
        
        self.assertGreaterEqual(result.confidence, 0)
        self.assertLessEqual(result.confidence, 100)


if __name__ == "__main__":
    unittest.main()
