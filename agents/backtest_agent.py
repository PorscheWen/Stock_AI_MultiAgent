"""
⚡ BACKTEST AGENT
回測驗證 Agent
- 歷史相似模式比對（3年數據）
- 同類信號勝率統計
- 預期報酬/風險比計算
- 最佳進出場時機推估
輸出：歷史勝率 %
"""
import logging
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd
import yfinance as yf

from config.settings import (
    LOOKBACK_DAYS,
    VOLUME_SURGE_MULTIPLIER,
    RSI_OVERSOLD,
    BOLLINGER_PERIOD,
    BOLLINGER_STD,
)

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    symbol: str
    win_rate: float           # 歷史勝率 0~1
    avg_return: float         # 平均報酬率 %
    avg_loss: float           # 平均虧損率 %
    profit_factor: float      # 獲利因子 (avg_return * win) / (avg_loss * loss_count)
    total_signals: int        # 歷史觸發信號次數
    hold_days_avg: float      # 平均持有天數
    best_entry_time: str      # 建議進場時機描述
    backtest_score: float     # 0~100


class BacktestAgent:
    """回測驗證 Agent"""

    def __init__(self):
        self.name = "BacktestAgent"

    # ── 公開介面 ───────────────────────────────────────
    def run(self, symbols: list[str]) -> dict[str, BacktestResult]:
        results = {}
        for symbol in symbols:
            try:
                result = self._backtest(symbol)
                if result:
                    results[symbol] = result
                    logger.info(
                        f"[Backtest] {symbol} 勝率={result.win_rate:.1%} "
                        f"平均報酬={result.avg_return:.1f}%"
                    )
            except Exception as e:
                logger.warning(f"[Backtest] {symbol} 回測失敗: {e}")
        return results

    # ── 內部方法 ───────────────────────────────────────
    def _fetch(self, symbol: str) -> Optional[pd.DataFrame]:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{LOOKBACK_DAYS}d")
        if df.empty or len(df) < 120:
            return None
        return df

    def _calc_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def _find_signals(self, df: pd.DataFrame) -> pd.Series:
        """偵測歷史上同類進場信號（RSI 低檔 + 量能放大）"""
        close  = df["Close"]
        volume = df["Volume"]
        rsi    = self._calc_rsi(close)

        mid = close.rolling(BOLLINGER_PERIOD).mean()
        std = close.rolling(BOLLINGER_PERIOD).std()
        bb_lower = mid - BOLLINGER_STD * std

        avg_vol = volume.rolling(20).mean()
        vol_surge = volume >= (avg_vol * VOLUME_SURGE_MULTIPLIER)

        rsi_low   = rsi < (RSI_OVERSOLD + 5)
        near_support = close <= bb_lower * 1.03

        macd_line = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        macd_sig  = macd_line.ewm(span=9).mean()
        golden_cross = (macd_line > macd_sig) & (macd_line.shift(1) <= macd_sig.shift(1))

        signal = (vol_surge & rsi_low) | (golden_cross & near_support)
        return signal

    def _simulate(self, df: pd.DataFrame, signals: pd.Series,
                  hold_days: int = 10, target_pct: float = 0.05,
                  stop_pct: float = 0.03) -> dict:
        close = df["Close"]
        wins, losses, returns = [], [], []
        signal_dates = signals[signals].index

        for date in signal_dates:
            idx = close.index.get_loc(date)
            entry = float(close.iloc[idx])
            horizon = min(idx + hold_days, len(close) - 1)

            future = close.iloc[idx + 1: horizon + 1]
            if future.empty:
                continue

            hit_target = any(future >= entry * (1 + target_pct))
            hit_stop   = any(future <= entry * (1 - stop_pct))
            final_ret  = (float(future.iloc[-1]) - entry) / entry * 100

            if hit_target:
                wins.append(target_pct * 100)
            elif hit_stop:
                losses.append(-stop_pct * 100)
            else:
                if final_ret >= 0:
                    wins.append(final_ret)
                else:
                    losses.append(final_ret)

        total = len(wins) + len(losses)
        win_rate   = len(wins) / total if total > 0 else 0
        avg_return = float(np.mean(wins))  if wins   else 0.0
        avg_loss   = float(np.mean(losses)) if losses else 0.0

        profit_factor = (
            (avg_return * len(wins)) / abs(avg_loss * len(losses))
            if losses and avg_loss != 0 else float("inf")
        )

        return {
            "win_rate": win_rate,
            "avg_return": avg_return,
            "avg_loss": avg_loss,
            "total_signals": total,
            "profit_factor": min(profit_factor, 10.0),
        }

    def _backtest(self, symbol: str) -> Optional[BacktestResult]:
        df = self._fetch(symbol)
        if df is None:
            return None

        signals = self._find_signals(df)
        stats   = self._simulate(df, signals)

        win_rate  = stats["win_rate"]
        avg_ret   = stats["avg_return"]
        avg_loss  = stats["avg_loss"]
        total_sig = stats["total_signals"]
        pf        = stats["profit_factor"]

        # 回測綜合評分
        score = 50.0
        score += (win_rate - 0.5) * 80          # 勝率加成
        score += min(avg_ret, 10) * 2            # 平均報酬
        score += min(pf, 5) * 5                  # 獲利因子
        if total_sig < 5:
            score -= 15                           # 樣本不足扣分
        score = max(0.0, min(100.0, score))

        # 進場時機建議
        if win_rate >= 0.65:
            timing = "高信心信號，開盤後確認量能即可進場"
        elif win_rate >= 0.55:
            timing = "中等信號，建議等待盤中確認突破再進場"
        else:
            timing = "低勝率信號，建議觀望或小倉試探"

        return BacktestResult(
            symbol=symbol,
            win_rate=round(win_rate, 4),
            avg_return=round(avg_ret, 2),
            avg_loss=round(avg_loss, 2),
            profit_factor=round(pf, 2),
            total_signals=total_sig,
            hold_days_avg=10.0,
            best_entry_time=timing,
            backtest_score=round(score, 1),
        )
