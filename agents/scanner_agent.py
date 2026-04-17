"""
📡 SCANNER AGENT
技術面分析 Agent
- yfinance 抓取 OHLCV 數據
- RSI、MACD、布林通道計算
- 成交量異常偵測（>2.5x 均量）
- 支撐壓力突破判斷
輸出：候選股票清單
"""
import logging
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import numpy as np
import yfinance as yf

from config.settings import (
    WATCHLIST, VOLUME_SURGE_MULTIPLIER,
    RSI_OVERSOLD, RSI_OVERBOUGHT,
    BOLLINGER_PERIOD, BOLLINGER_STD,
    LOOKBACK_DAYS,
)

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    symbol: str
    close: float
    rsi: float
    macd: float
    macd_signal: float
    bb_upper: float
    bb_lower: float
    volume: float
    avg_volume: float
    volume_ratio: float
    breakout: bool           # 突破壓力位
    support_bounce: bool     # 支撐反彈
    technical_score: float   # 0~100
    signals: list = field(default_factory=list)


class ScannerAgent:
    """技術面掃描 Agent"""

    def __init__(self, watchlist: list[str] = None):
        self.watchlist = watchlist or WATCHLIST
        self.name = "ScannerAgent"

    # ── 公開介面 ───────────────────────────────────────
    def run(self) -> list[ScanResult]:
        """掃描所有標的，回傳候選清單"""
        results = []
        for symbol in self.watchlist:
            try:
                result = self._analyze(symbol)
                if result and result.technical_score >= 60:
                    results.append(result)
                    logger.info(f"[Scanner] {symbol} 評分={result.technical_score:.1f}")
            except Exception as e:
                logger.warning(f"[Scanner] {symbol} 分析失敗: {e}")
        results.sort(key=lambda x: x.technical_score, reverse=True)
        return results

    # ── 內部方法 ───────────────────────────────────────
    def _fetch(self, symbol: str) -> Optional[pd.DataFrame]:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{LOOKBACK_DAYS}d")
        if df.empty or len(df) < 60:
            return None
        return df

    def _calc_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def _calc_macd(self, close: pd.Series):
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        return macd, signal

    def _calc_bollinger(self, close: pd.Series):
        mid = close.rolling(BOLLINGER_PERIOD).mean()
        std = close.rolling(BOLLINGER_PERIOD).std()
        upper = mid + BOLLINGER_STD * std
        lower = mid - BOLLINGER_STD * std
        return upper, lower

    def _analyze(self, symbol: str) -> Optional[ScanResult]:
        df = self._fetch(symbol)
        if df is None:
            return None

        close  = df["Close"]
        volume = df["Volume"]

        rsi         = self._calc_rsi(close)
        macd, sig   = self._calc_macd(close)
        bb_up, bb_dn = self._calc_bollinger(close)

        # 最新數值
        c_last   = float(close.iloc[-1])
        rsi_last = float(rsi.iloc[-1])
        macd_last = float(macd.iloc[-1])
        sig_last  = float(sig.iloc[-1])
        bbu_last  = float(bb_up.iloc[-1])
        bbl_last  = float(bb_dn.iloc[-1])
        vol_last  = float(volume.iloc[-1])
        avg_vol   = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = vol_last / avg_vol if avg_vol > 0 else 0

        signals = []
        score   = 50.0

        # RSI 評分
        if RSI_OVERSOLD < rsi_last < 50:
            score += 10
            signals.append("RSI 低檔反彈區")
        elif rsi_last < RSI_OVERSOLD:
            score += 5
            signals.append("RSI 超賣")
        elif rsi_last > RSI_OVERBOUGHT:
            score -= 10
            signals.append("RSI 超買")

        # MACD 金叉
        if macd_last > sig_last and macd.iloc[-2] <= sig.iloc[-2]:
            score += 15
            signals.append("MACD 金叉")
        elif macd_last > sig_last:
            score += 8
            signals.append("MACD 多頭")

        # 布林通道突破
        breakout       = c_last > bbu_last
        support_bounce = c_last <= bbl_last * 1.02  # 在下軌附近反彈
        if breakout:
            score += 12
            signals.append("布林上軌突破")
        if support_bounce:
            score += 8
            signals.append("布林下軌支撐")

        # 成交量異常
        if vol_ratio >= VOLUME_SURGE_MULTIPLIER:
            score += 15
            signals.append(f"成交量暴增 {vol_ratio:.1f}x")
        elif vol_ratio >= 1.5:
            score += 7
            signals.append(f"成交量放大 {vol_ratio:.1f}x")

        score = max(0.0, min(100.0, score))

        return ScanResult(
            symbol=symbol,
            close=c_last,
            rsi=rsi_last,
            macd=macd_last,
            macd_signal=sig_last,
            bb_upper=bbu_last,
            bb_lower=bbl_last,
            volume=vol_last,
            avg_volume=avg_vol,
            volume_ratio=vol_ratio,
            breakout=breakout,
            support_bounce=support_bounce,
            technical_score=score,
            signals=signals,
        )
