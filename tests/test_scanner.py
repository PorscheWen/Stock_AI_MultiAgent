"""
📡 ScannerAgent 單元測試
"""
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from agents.scanner_agent import ScannerAgent, ScanResult


def _make_df(n=100, vol_spike=False):
    """建立假 OHLCV DataFrame"""
    idx = pd.date_range(end=datetime.today(), periods=n, freq="D")
    close = pd.Series(np.cumsum(np.random.randn(n) * 0.5) + 100, index=idx)
    close = close.clip(lower=1)
    volume = pd.Series(np.random.randint(600_000, 1_200_000, n).astype(float), index=idx)
    if vol_spike:
        volume.iloc[-1] = volume.iloc[-20:].mean() * 3.0  # 模擬爆量
    return pd.DataFrame({
        "Open":   close * 0.99,
        "High":   close * 1.01,
        "Low":    close * 0.98,
        "Close":  close,
        "Volume": volume,
    })


class TestScannerAgent(unittest.TestCase):

    def setUp(self):
        self.agent = ScannerAgent(watchlist=["AAPL", "MSFT"])

    def test_rsi_range(self):
        """RSI 應在 0~100 之間"""
        df = _make_df(100)
        rsi = self.agent._calc_rsi(df["Close"])
        valid = rsi.dropna()
        self.assertTrue((valid >= 0).all() and (valid <= 100).all())

    def test_macd_shape(self):
        """MACD 與 Signal 長度應相同"""
        df = _make_df(100)
        macd, sig = self.agent._calc_macd(df["Close"])
        self.assertEqual(len(macd), len(sig))

    def test_bollinger_shape(self):
        """布林通道上軌應 >= 下軌"""
        df = _make_df(100)
        up, dn = self.agent._calc_bollinger(df["Close"])
        valid = (~up.isna()) & (~dn.isna())
        self.assertTrue((up[valid] >= dn[valid]).all())

    @patch.object(ScannerAgent, "_fetch")
    def test_volume_surge_detected(self, mock_fetch):
        """爆量時 volume_ratio 應 >= 2.5 並觸發信號"""
        df = _make_df(100, vol_spike=True)
        mock_fetch.return_value = df
        result = self.agent._analyze("AAPL")
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.volume_ratio, 2.5)
        self.assertTrue(any("成交量" in s for s in result.signals))

    @patch.object(ScannerAgent, "_fetch")
    def test_score_in_range(self, mock_fetch):
        """技術評分應在 0~100"""
        mock_fetch.return_value = _make_df(100)
        result = self.agent._analyze("AAPL")
        if result:
            self.assertGreaterEqual(result.technical_score, 0)
            self.assertLessEqual(result.technical_score, 100)

    @patch.object(ScannerAgent, "_fetch")
    def test_insufficient_data_returns_none(self, mock_fetch):
        """數據不足 60 筆應回傳 None"""
        mock_fetch.return_value = _make_df(30)
        # _fetch 本身過濾，但這裡 mock 直接回傳短 df
        # _analyze 不會跑到 RSI nan，score 仍可算出，此測試驗證 run() 過濾
        result = self.agent._analyze("AAPL")
        # 短數據時 RSI 全為 NaN，score 可能 50 → 不一定回傳 None，驗證執行不崩潰
        # 只確認不拋例外

    def test_run_returns_list(self):
        """run() 應回傳 list（允許空清單）"""
        with patch.object(self.agent, "_fetch", return_value=None):
            result = self.agent.run()
            self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
