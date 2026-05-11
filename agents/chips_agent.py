"""
🧩 CHIPS AGENT（籌碼面代理）
以公開市場資料推估籌碼結構，非證交所即時主力表（無 API 時之合理替代）：
- yfinance：法人持股比例（若有）
- 近端量能相對中期均量
- 收盤價相對 MA60 位置（趨勢／套牢區代理）

輸出：chip_score 0~100 與文字摘要，供 Advisor 與 LINE 顯示。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class ChipResult:
    symbol: str
    chip_score: float
    summary: str
    institutional_pct: Optional[float]  # 0~1 或 None
    volume_ratio_5d_vs_15d: float
    price_vs_ma60_pct: float
    metrics: dict[str, Any]


class ChipsAgent:
    """籌碼面分析 Agent（價量＋法人持股代理）"""

    def __init__(self):
        self.name = "ChipsAgent"

    def run(self, symbols: list[str]) -> dict[str, ChipResult]:
        out: dict[str, ChipResult] = {}
        for symbol in symbols:
            try:
                r = self._analyze(symbol)
                if r:
                    out[symbol] = r
                    logger.info(
                        "[Chips] %s score=%.1f inst=%s vol5/15=%.2f",
                        symbol,
                        r.chip_score,
                        f"{r.institutional_pct:.0%}" if r.institutional_pct is not None else "n/a",
                        r.volume_ratio_5d_vs_15d,
                    )
            except Exception as e:
                logger.warning("[Chips] %s 失敗: %s", symbol, e)
                out[symbol] = ChipResult(
                    symbol=symbol,
                    chip_score=50.0,
                    summary="籌碼資料不足，採中性分數。",
                    institutional_pct=None,
                    volume_ratio_5d_vs_15d=1.0,
                    price_vs_ma60_pct=0.0,
                    metrics={"error": str(e)},
                )
        return out

    def _fetch(self, symbol: str) -> Optional[pd.DataFrame]:
        df = yf.Ticker(symbol).history(period="120d")
        if df is None or df.empty or len(df) < 65:
            return None
        return df

    def _institutional_pct(self, symbol: str) -> Optional[float]:
        try:
            info = yf.Ticker(symbol).info or {}
            v = info.get("heldPercentInstitutions")
            if v is None:
                return None
            x = float(v)
            if x > 1.0:
                x = x / 100.0
            if 0 <= x <= 1:
                return x
        except Exception:
            return None
        return None

    def _analyze(self, symbol: str) -> Optional[ChipResult]:
        df = self._fetch(symbol)
        if df is None:
            return None

        close = df["Close"].astype(float)
        vol = df["Volume"].astype(float)
        c_last = float(close.iloc[-1])
        ma60 = float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else float(close.mean())
        price_vs_ma60 = (c_last - ma60) / ma60 * 100 if ma60 else 0.0

        v5 = float(vol.iloc[-5:].mean())
        v15 = float(vol.iloc[-20:-5].mean()) if len(vol) >= 20 else float(vol.iloc[:-5].mean())
        vol_ratio = (v5 / v15) if v15 > 0 else 1.0

        inst = self._institutional_pct(symbol)

        score = 50.0
        notes: list[str] = []

        if inst is not None:
            if inst >= 0.55:
                score += 14
                notes.append("法人持股比偏高")
            elif inst >= 0.35:
                score += 9
                notes.append("法人持股比中等偏上")
            elif inst >= 0.15:
                score += 4
                notes.append("法人持股比尚可")
            else:
                score -= 4
                notes.append("法人持股比偏低")
        else:
            notes.append("無法人持股資料")

        if vol_ratio >= 1.35:
            score += 10
            notes.append("近5日均量顯著高於前段")
        elif vol_ratio >= 1.12:
            score += 5
            notes.append("量能溫和放大")
        elif vol_ratio <= 0.75:
            score -= 8
            notes.append("量能萎縮／觀望")

        if price_vs_ma60 >= 8:
            score += 10
            notes.append("價格明顯高於季線")
        elif price_vs_ma60 >= 2:
            score += 5
            notes.append("價格在季線之上")
        elif price_vs_ma60 <= -12:
            score -= 12
            notes.append("價格深於季線下方")
        elif price_vs_ma60 <= -4:
            score -= 6
            notes.append("價格偏弱於季線")

        score = float(max(0.0, min(100.0, score)))
        summary = "；".join(notes) if notes else "籌碼面中性。"

        return ChipResult(
            symbol=symbol,
            chip_score=score,
            summary=summary,
            institutional_pct=inst,
            volume_ratio_5d_vs_15d=round(vol_ratio, 3),
            price_vs_ma60_pct=round(price_vs_ma60, 2),
            metrics={
                "close": c_last,
                "ma60": ma60,
            },
        )
