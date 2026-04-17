"""
⚖️ RISK AGENT
風控分析 Agent
- 波動率（ATR）計算
- 流動性評估（日均量門檻）
- 最大回撤風險評估
- 停損點位自動計算
輸出：風險等級 L1~L5
"""
import logging
from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd
import yfinance as yf

from config.settings import (
    MAX_STOP_LOSS_PCT,
    MIN_RISK_REWARD_RATIO,
    LIQUIDITY_MIN_VOLUME,
    MAX_POSITION_PCT,
)

logger = logging.getLogger(__name__)

RISK_LEVELS = {1: "極低風險", 2: "低風險", 3: "中等風險", 4: "高風險", 5: "極高風險"}


@dataclass
class RiskResult:
    symbol: str
    risk_level: int           # 1~5
    risk_label: str
    atr: float                # 平均真實波動幅度
    atr_pct: float            # ATR / 收盤價 %
    stop_loss_price: float    # 建議停損價
    stop_loss_pct: float      # 停損幅度 %
    target_price: float       # 目標價（風報比 2:1）
    max_drawdown: float       # 近期最大回撤 %
    liquidity_ok: bool        # 流動性是否達標
    risk_reward_ratio: float  # 風報比
    risk_score: float         # 0~100，越高越安全


class RiskAgent:
    """風控分析 Agent"""

    def __init__(self):
        self.name = "RiskAgent"

    # ── 公開介面 ───────────────────────────────────────
    def run(self, symbols: list[str]) -> dict[str, RiskResult]:
        results = {}
        for symbol in symbols:
            try:
                result = self._analyze(symbol)
                if result:
                    results[symbol] = result
                    logger.info(
                        f"[Risk] {symbol} 等級=L{result.risk_level} "
                        f"停損={result.stop_loss_pct:.1f}% 風報比={result.risk_reward_ratio:.1f}"
                    )
            except Exception as e:
                logger.warning(f"[Risk] {symbol} 分析失敗: {e}")
        return results

    # ── 內部方法 ───────────────────────────────────────
    def _fetch(self, symbol: str) -> Optional[pd.DataFrame]:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="90d")
        if df.empty or len(df) < 20:
            return None
        return df

    def _calc_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        high  = df["High"]
        low   = df["Low"]
        close = df["Close"]
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low  - prev_close).abs(),
        ], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])

    def _calc_max_drawdown(self, close: pd.Series) -> float:
        roll_max = close.cummax()
        drawdown = (close - roll_max) / roll_max
        return float(drawdown.min())  # 負值，例如 -0.15 代表 15% 回撤

    def _analyze(self, symbol: str) -> Optional[RiskResult]:
        df = self._fetch(symbol)
        if df is None:
            return None

        close      = df["Close"]
        volume     = df["Volume"]
        c_last     = float(close.iloc[-1])
        avg_vol    = float(volume.rolling(20).mean().iloc[-1])

        atr        = self._calc_atr(df)
        atr_pct    = atr / c_last if c_last > 0 else 0
        max_dd     = self._calc_max_drawdown(close)
        liquidity  = avg_vol >= LIQUIDITY_MIN_VOLUME

        # 停損：ATR 的 1.5 倍，最多不超過 MAX_STOP_LOSS_PCT
        stop_dist  = min(atr * 1.5, c_last * MAX_STOP_LOSS_PCT)
        stop_price = round(c_last - stop_dist, 4)
        stop_pct   = stop_dist / c_last

        # 目標價（2:1 風報比）
        target_price = round(c_last + stop_dist * MIN_RISK_REWARD_RATIO, 4)
        rr_ratio     = MIN_RISK_REWARD_RATIO  # 已按此計算

        # 風險等級評分（越高越安全）
        score = 100.0

        # ATR% 懲罰：波動越大扣分
        score -= min(atr_pct * 200, 30)

        # 最大回撤懲罰
        score -= min(abs(max_dd) * 150, 25)

        # 流動性獎勵
        if liquidity:
            score += 10
        else:
            score -= 20

        # 停損距離合理性
        if stop_pct > MAX_STOP_LOSS_PCT:
            score -= 15

        score = max(0.0, min(100.0, score))

        # 對映風險等級
        if score >= 80:
            level = 1
        elif score >= 65:
            level = 2
        elif score >= 50:
            level = 3
        elif score >= 35:
            level = 4
        else:
            level = 5

        return RiskResult(
            symbol=symbol,
            risk_level=level,
            risk_label=RISK_LEVELS[level],
            atr=round(atr, 4),
            atr_pct=round(atr_pct * 100, 2),
            stop_loss_price=stop_price,
            stop_loss_pct=round(stop_pct * 100, 2),
            target_price=target_price,
            max_drawdown=round(max_dd * 100, 2),
            liquidity_ok=liquidity,
            risk_reward_ratio=round(rr_ratio, 2),
            risk_score=round(score, 1),
        )
