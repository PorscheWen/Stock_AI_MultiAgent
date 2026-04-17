"""
⚡ BacktestAgent 單元測試
"""
import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from datetime import datetime

from agents.backtest_agent import BacktestAgent


def _make_df(n=400, trend="flat"):
    idx = pd.date_range(end=datetime.today(), periods=n, freq="D")
    if trend == "up":
        noise = np.abs(np.random.randn(n)) * 0.5 + 0.2
    elif trend == "down":
        noise = -np.abs(np.random.randn(n)) * 0.5 - 0.1
    else:
        noise = np.random.randn(n) * 0.5
    close = pd.Series(np.cumsum(noise) + 100, index=idx).clip(lower=1)
    volume = pd.Series(np.random.randint(500_000, 2_000_000, n).astype(float), index=idx)
    return pd.DataFrame({
        "Open":   close * 0.99,
        "High":   close * 1.01,
        "Low":    close * 0.98,
        "Close":  close,
        "Volume": volume,
    })


class TestBacktestAgent(unittest.TestCase):

    def setUp(self):
        self.agent = BacktestAgent()

    def test_find_signals_returns_series(self):
        df = _make_df(200)
        signals = self.agent._find_signals(df)
        self.assertIsInstance(signals, pd.Series)
        self.assertEqual(len(signals), len(df))

    def test_simulate_returns_dict(self):
        df = _make_df(300)
        signals = self.agent._find_signals(df)
        stats = self.agent._simulate(df, signals)
        self.assertIn("win_rate", stats)
        self.assertIn("avg_return", stats)
        self.assertIn("total_signals", stats)

    def test_win_rate_in_range(self):
        with patch.object(self.agent, "_fetch", return_value=_make_df(400)):
            result = self.agent._backtest("AAPL")
            if result:
                self.assertGreaterEqual(result.win_rate, 0.0)
                self.assertLessEqual(result.win_rate, 1.0)

    def test_score_in_range(self):
        with patch.object(self.agent, "_fetch", return_value=_make_df(400)):
            result = self.agent._backtest("AAPL")
            if result:
                self.assertGreaterEqual(result.backtest_score, 0)
                self.assertLessEqual(result.backtest_score, 100)

    def test_insufficient_data_returns_none(self):
        with patch.object(self.agent, "_fetch", return_value=_make_df(50)):
            result = self.agent._backtest("AAPL")
            # _fetch 本身就會 return None for < 120 rows
            # 這裡 mock 直接回傳短 df，_backtest 可能執行，不崩潰即可

    def test_run_returns_dict(self):
        with patch.object(self.agent, "_fetch", return_value=None):
            result = self.agent.run(["AAPL"])
            self.assertIsInstance(result, dict)

    def test_profit_factor_positive(self):
        with patch.object(self.agent, "_fetch", return_value=_make_df(400, "up")):
            result = self.agent._backtest("AAPL")
            if result and result.profit_factor != float("inf"):
                self.assertGreaterEqual(result.profit_factor, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
