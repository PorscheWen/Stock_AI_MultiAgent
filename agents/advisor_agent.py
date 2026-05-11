"""
💡 ADVISOR AGENT
持股整體評估：整合技術面、籌碼面（代理）、情緒面、風控、回測，
輸出停損／停利參考、短中長線持有建議與進出場策略說明。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Recommendation(Enum):
    """操作建議類型"""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class HoldingHorizon(Enum):
    """持有期間建議"""

    SHORT_TERM = "short_term"  # 數日～數週
    SWING = "swing"  # 數週～數月
    LONG_TERM = "long_term"  # 數月以上


HORIZON_LABEL_ZH = {
    HoldingHorizon.SHORT_TERM: "短線（數日～數週）",
    HoldingHorizon.SWING: "波段（數週～數月）",
    HoldingHorizon.LONG_TERM: "長線（數月以上）",
}


@dataclass
class AdvisorResult:
    """建議結果"""

    symbol: str
    recommendation: Recommendation
    confidence: float
    reason: str
    target_price: float
    take_profit_price: float
    take_profit_partial: float
    stop_loss: float
    entry_strategy: str
    exit_strategy: str
    holding_horizon: HoldingHorizon
    horizon_label_zh: str
    horizon_rationale: str


class AdvisorAgent:
    """持股操作建議 Agent（多面向加權）"""

    def __init__(self):
        self.name = "AdvisorAgent"

    def analyze(self, candidate: dict) -> AdvisorResult:
        """
        分析候選股票，提供操作建議。

        candidate 可為：
        - 含 scores / risk / backtest / signals / aspects 的完整 payload（Orchestrator 產生）
        - 或單元測試用最小 dict（仍須含 scores.risk 等鍵）
        """
        symbol = candidate["symbol"]
        close = float(candidate["close"])
        scores = self._normalize_scores(candidate)
        risk = candidate.get("risk") or {}
        aspects = candidate.get("aspects") or {}

        tech = float(scores.get("technical", 0) or 0)
        sent = float(scores.get("sentiment", 50) or 50)
        rscore = float(scores.get("risk", 0) or 0)
        back = float(scores.get("backtest", 0) or 0)
        chips = float(scores.get("chips", 50) or 50)

        overall = (
            tech * 0.28
            + sent * 0.22
            + rscore * 0.18
            + back * 0.17
            + chips * 0.15
        )

        recommendation, reason = self._decide_recommendation(
            overall, tech, sent, rscore, back, chips, aspects
        )

        target_price = float(risk.get("target_price") or close * 1.1)
        stop_loss = float(risk.get("stop_loss_price") or close * 0.93)

        take_profit_price = target_price
        take_profit_partial = close + (target_price - close) * 0.55

        horizon, horizon_zh, horizon_rationale = self._holding_horizon(
            close=close,
            tech=tech,
            sent=sent,
            chips=chips,
            back=back,
            risk_level=int(risk.get("level", 3) or 3),
            aspects=aspects,
        )

        entry_strategy = self._get_entry_strategy(candidate)
        exit_strategy = self._get_exit_strategy(
            candidate, target_price, stop_loss, take_profit_partial
        )

        return AdvisorResult(
            symbol=symbol,
            recommendation=recommendation,
            confidence=round(min(100.0, max(0.0, overall)), 1),
            reason=reason,
            target_price=round(target_price, 2),
            take_profit_price=round(take_profit_price, 2),
            take_profit_partial=round(take_profit_partial, 2),
            stop_loss=round(stop_loss, 2),
            entry_strategy=entry_strategy,
            exit_strategy=exit_strategy,
            holding_horizon=horizon,
            horizon_label_zh=horizon_zh,
            horizon_rationale=horizon_rationale,
        )

    def _normalize_scores(self, candidate: dict) -> dict:
        if "scores" in candidate and isinstance(candidate["scores"], dict):
            s = dict(candidate["scores"])
            raw_sent = float(s.get("sentiment", 50) or 50)
            if raw_sent <= 1.0:
                s["sentiment"] = raw_sent * 100.0
            if "chips" not in s:
                s["chips"] = 50.0
            return s

        raw_sent = float(candidate.get("sentiment_score", 0.5) or 0.5)
        sent100 = raw_sent * 100.0 if raw_sent <= 1.0 else raw_sent
        return {
            "technical": float(candidate.get("technical_score", 0) or 0),
            "sentiment": sent100,
            "risk": float(candidate.get("risk_score", 0) or 0),
            "backtest": float(candidate.get("backtest_score", 0) or 0),
            "chips": float(candidate.get("chip_score", 50) or 50),
        }

    def _decide_recommendation(
        self,
        overall: float,
        tech: float,
        sent: float,
        risk: float,
        back: float,
        chips: float,
        aspects: dict,
    ) -> tuple[Recommendation, str]:
        reasons: list[str] = []

        if overall >= 80 and tech >= 75 and sent >= 68 and chips >= 62:
            reasons.append(f"技術面強 ({tech:.0f})")
            reasons.append(f"籌碼面穩 ({chips:.0f})")
            reasons.append(f"情緒偏多 ({sent:.0f})")
            if back >= 65:
                reasons.append(f"回測品質佳 ({back:.0f})")
            return Recommendation.STRONG_BUY, "、".join(reasons)

        if overall >= 70:
            if tech >= 64:
                reasons.append(f"技術面偏多 ({tech:.0f})")
            if chips >= 58:
                reasons.append(f"籌碼尚可 ({chips:.0f})")
            if sent >= 58:
                reasons.append(f"情緒正向 ({sent:.0f})")
            return Recommendation.BUY, "、".join(reasons) or "綜合評分偏正向"

        if overall >= 55:
            if 48 <= tech < 72:
                reasons.append(f"技術中性 ({tech:.0f})")
            if 45 <= chips < 62:
                reasons.append(f"籌碼中性 ({chips:.0f})")
            return Recommendation.HOLD, "、".join(reasons) or "多空因素並存，宜控倉觀察"

        if overall >= 42:
            if tech < 52:
                reasons.append(f"技術偏弱 ({tech:.0f})")
            if chips < 48:
                reasons.append(f"籌碼偏弱 ({chips:.0f})")
            if sent < 48:
                reasons.append(f"情緒轉弱 ({sent:.0f})")
            return Recommendation.SELL, "、".join(reasons) or "評分偏低，注意風險"

        if tech < 40:
            reasons.append(f"技術轉弱 ({tech:.0f})")
        if chips < 40:
            reasons.append(f"籌碼結構偏空 ({chips:.0f})")
        if sent < 42:
            reasons.append(f"情緒悲觀 ({sent:.0f})")
        if risk < 42:
            reasons.append(f"風控分數偏低 ({risk:.0f})")
        return Recommendation.STRONG_SELL, "、".join(reasons) or "多面向轉弱"

    def _holding_horizon(
        self,
        close: float,
        tech: float,
        sent: float,
        chips: float,
        back: float,
        risk_level: int,
        aspects: dict,
    ) -> tuple[HoldingHorizon, str, str]:
        """短／波段／長線建議（規則式，非預測報酬）。"""
        bt = aspects.get("backtest") or {}
        win_rate = float(bt.get("win_rate") or 0.0)
        pvm = None
        ch = aspects.get("chips") or {}
        if ch.get("price_vs_ma60_pct") is not None:
            pvm = float(ch["price_vs_ma60_pct"])

        if risk_level >= 4 and tech < 58:
            h = HoldingHorizon.SHORT_TERM
            rationale = "波動與風險等級偏高，宜以短線纪律與停損為主。"
        elif tech >= 72 and chips >= 65 and sent >= 62 and (pvm is None or pvm >= 0):
            h = HoldingHorizon.LONG_TERM
            rationale = "趨勢與籌碼結構相對穩健，可偏向較長持有但仍需定期檢視。"
        elif win_rate >= 0.55 and back >= 62:
            h = HoldingHorizon.SWING
            rationale = "歷史訊號勝率尚可，適合波段進出並搭配分批停利。"
        elif tech >= 62 and chips >= 55:
            h = HoldingHorizon.SWING
            rationale = "技術與籌碼中性偏多，以數週至數月波段較吻合。"
        else:
            h = HoldingHorizon.SHORT_TERM
            rationale = "訊號一致性普通，建議以短線或減碼波段，嚴守停損。"

        return h, HORIZON_LABEL_ZH[h], rationale

    def _get_entry_strategy(self, candidate: dict) -> str:
        signals = candidate.get("signals", [])
        strategies: list[str] = []

        if any("金叉" in sig for sig in signals):
            strategies.append("等待 MACD 金叉確認後再分批進場")
        if any("暴增" in sig for sig in signals):
            strategies.append("量能放大時避免追高，確認站穩再介入")
        if any("支撐" in sig or "低檔" in sig for sig in signals):
            strategies.append("支撐區分批布局，跌破結構則取消")
        if any("突破" in sig for sig in signals):
            strategies.append("突破後回測不破再擴大部位")

        if not strategies:
            strategies.append("分批建倉，單筆風險控在可承受範圍內")
        return "；".join(strategies)

    def _get_exit_strategy(
        self,
        candidate: dict,
        target_price: float,
        stop_loss: float,
        take_profit_partial: float,
    ) -> str:
        close = float(candidate["close"])
        gain_pct = (target_price - close) / close * 100 if close else 0.0
        stop_pct = (stop_loss - close) / close * 100 if close else 0.0
        p1_pct = (take_profit_partial - close) / close * 100 if close else 0.0

        parts = [
            f"第一階停利參考 {take_profit_partial:.2f}（約 +{p1_pct:.1f}%）可減碼",
            f"主要停利目標 {target_price:.2f}（約 +{gain_pct:.1f}%）",
            f"停損參考 {stop_loss:.2f}（約 {stop_pct:.1f}%）",
        ]
        return "；".join(parts)

