"""
⚖️ RiskAgent 單元測試
"""
import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from datetime import datetime

from agents.risk_agent import RiskAgent, RiskResult


def _make_df(n=90, volatile=False):
    idx = pd.date_range(end=datetime.today(), periods=n, freq="D")
    noise = np.random.randn(n) * (2.0 if volatile else 0.3)
    close = pd.Series(np.cumsum(noise) + 100, index=idx).clip(lower=1)
    volume = pd.Series(np.random.randint(800_000, 2_000_000, n).astype(float), index=idx)
    return pd.DataFrame({
        "Open":   close * 0.99,
        "High":   close * 1.015,
        "Low":    close * 0.985,
        "Close":  close,
        "Volume": volume,
    })


class TestRiskAgent(unittest.TestCase):

    def setUp(self):
        self.agent = RiskAgent()

    def test_atr_positive(self):
        """ATR 應為正數"""
        df = _make_df()
        atr = self.agent._calc_atr(df)
        self.assertGreater(atr, 0)

    def test_max_drawdown_negative(self):
        """最大回撤應為負值或零"""
        df = _make_df()
        dd = self.agent._calc_max_drawdown(df["Close"])
        self.assertLessEqual(dd, 0)

    def test_risk_level_range(self):
        """風險等級應在 1~5"""
        with patch.object(self.agent, "_fetch", return_value=_make_df()):
            result = self.agent._analyze("AAPL")
            if result:
                self.assertIn(result.risk_level, [1, 2, 3, 4, 5])

    def test_high_volatility_higher_risk(self):
        """高波動股票風險等級應較高"""
        with patch.object(self.agent, "_fetch") as mock_fetch:
            # 低波動
            mock_fetch.return_value = _make_df(volatile=False)
            low_vol = self.agent._analyze("AAA")

            # 高波動
            mock_fetch.return_value = _make_df(volatile=True)
            high_vol = self.agent._analyze("BBB")

            if low_vol and high_vol:
                self.assertGreaterEqual(high_vol.risk_level, low_vol.risk_level)

    def test_stop_loss_within_limit(self):
        """停損幅度應 ≤ MAX_STOP_LOSS_PCT"""
        from config.settings import MAX_STOP_LOSS_PCT
        with patch.object(self.agent, "_fetch", return_value=_make_df()):
            result = self.agent._analyze("AAPL")
            if result:
                self.assertLessEqual(result.stop_loss_pct, MAX_STOP_LOSS_PCT * 100 + 0.01)

    def test_risk_score_range(self):
        """風控評分應在 0~100"""
        with patch.object(self.agent, "_fetch", return_value=_make_df()):
            result = self.agent._analyze("AAPL")
            if result:
                self.assertGreaterEqual(result.risk_score, 0)
                self.assertLessEqual(result.risk_score, 100)

    def test_run_returns_dict(self):
        """run() 應回傳 dict"""
        with patch.object(self.agent, "_fetch", return_value=None):
            result = self.agent.run(["AAPL"])
            self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main(verbosity=2)
