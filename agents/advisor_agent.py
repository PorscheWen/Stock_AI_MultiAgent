"""
💡 ADVISOR AGENT
持股操作建議 Agent
根據技術面、情緒面、風控、回測數據提供操作建議
"""
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Recommendation(Enum):
    """操作建議類型"""
    STRONG_BUY = "strong_buy"      # 強力買進
    BUY = "buy"                     # 買進
    HOLD = "hold"                   # 持有
    SELL = "sell"                   # 賣出
    STRONG_SELL = "strong_sell"     # 強力賣出


@dataclass
class AdvisorResult:
    """建議結果"""
    symbol: str
    recommendation: Recommendation  # 操作建議
    confidence: float              # 信心度 0-100
    reason: str                    # 建議理由
    target_price: float           # 目標價
    stop_loss: float              # 停損價
    entry_strategy: str           # 進場策略
    exit_strategy: str            # 出場策略


class AdvisorAgent:
    """持股操作建議 Agent"""
    
    def __init__(self):
        self.name = "AdvisorAgent"
    
    def analyze(self, candidate: dict) -> AdvisorResult:
        """
        分析候選股票，提供操作建議
        
        Args:
            candidate: 包含所有分析數據的候選股票
                {
                    "symbol": "2330.TW",
                    "close": 580.0,
                    "scores": {"technical": 85, "sentiment": 75, ...},
                    "risk": {...},
                    "backtest": {...},
                    ...
                }
        
        Returns:
            AdvisorResult
        """
        symbol = candidate["symbol"]
        scores = candidate["scores"]
        risk = candidate["risk"]
        backtest = candidate.get("backtest", {})
        close = candidate["close"]
        
        # ── 計算綜合評分 ──────────────────────────────
        tech_score = scores.get("technical", 0)
        sent_score = scores.get("sentiment", 0)
        risk_score = scores.get("risk", 0)
        back_score = scores.get("backtest", 0)
        
        # 加權平均
        overall_score = (
            tech_score * 0.35 +
            sent_score * 0.25 +
            risk_score * 0.20 +
            back_score * 0.20
        )
        
        # ── 決定操作建議 ──────────────────────────────
        recommendation, reason = self._decide_recommendation(
            overall_score, tech_score, sent_score, risk_score, back_score
        )
        
        # ── 計算目標價和停損價 ────────────────────────
        target_price = risk.get("target_price", close * 1.1)
        stop_loss = risk.get("stop_loss_price", close * 0.93)
        
        # ── 進出場策略 ────────────────────────────────
        entry_strategy = self._get_entry_strategy(candidate)
        exit_strategy = self._get_exit_strategy(candidate, target_price)
        
        return AdvisorResult(
            symbol=symbol,
            recommendation=recommendation,
            confidence=overall_score,
            reason=reason,
            target_price=target_price,
            stop_loss=stop_loss,
            entry_strategy=entry_strategy,
            exit_strategy=exit_strategy
        )
    
    def _decide_recommendation(
        self, 
        overall: float,
        tech: float, 
        sent: float, 
        risk: float, 
        back: float
    ) -> tuple[Recommendation, str]:
        """
        決定操作建議
        
        Returns:
            (recommendation, reason)
        """
        reasons = []
        
        # ── 強力買進 ──────────────────────────────────
        if overall >= 80 and tech >= 75 and sent >= 70:
            reasons.append(f"技術面強勢 ({tech:.0f}分)")
            reasons.append(f"市場情緒樂觀 ({sent:.0f}分)")
            if back >= 70:
                reasons.append(f"歷史勝率高 ({back:.0f}分)")
            return (Recommendation.STRONG_BUY, "、".join(reasons))
        
        # ── 買進 ──────────────────────────────────────
        elif overall >= 70:
            if tech >= 65:
                reasons.append(f"技術面偏多 ({tech:.0f}分)")
            if sent >= 60:
                reasons.append(f"情緒面正向 ({sent:.0f}分)")
            return (Recommendation.BUY, "、".join(reasons) or "綜合評分良好")
        
        # ── 持有 ──────────────────────────────────────
        elif overall >= 55:
            if tech >= 50 and tech < 70:
                reasons.append(f"技術面中性 ({tech:.0f}分)")
            if sent >= 50 and sent < 70:
                reasons.append(f"情緒面持平 ({sent:.0f}分)")
            return (Recommendation.HOLD, "、".join(reasons) or "盤整觀望")
        
        # ── 賣出 ──────────────────────────────────────
        elif overall >= 40:
            if tech < 50:
                reasons.append(f"技術面轉弱 ({tech:.0f}分)")
            if sent < 50:
                reasons.append(f"情緒面悲觀 ({sent:.0f}分)")
            return (Recommendation.SELL, "、".join(reasons) or "評分偏低")
        
        # ── 強力賣出 ──────────────────────────────────
        else:
            if tech < 40:
                reasons.append(f"技術面崩壞 ({tech:.0f}分)")
            if sent < 40:
                reasons.append(f"市場恐慌 ({sent:.0f}分)")
            if risk < 40:
                reasons.append(f"風險過高 ({risk:.0f}分)")
            return (Recommendation.STRONG_SELL, "、".join(reasons) or "多項指標惡化")
    
    def _get_entry_strategy(self, candidate: dict) -> str:
        """取得進場策略"""
        signals = candidate.get("signals", [])
        close = candidate["close"]
        
        strategies = []
        
        # MACD 金叉
        if any("金叉" in sig for sig in signals):
            strategies.append("等待 MACD 金叉確認後進場")
        
        # 量能暴增
        if any("暴增" in sig for sig in signals):
            strategies.append("確認量能持續放大後介入")
        
        # 支撐反彈
        if any("支撐" in sig or "低檔" in sig for sig in signals):
            strategies.append("等待支撐位站穩後分批買進")
        
        # 突破
        if any("突破" in sig for sig in signals):
            strategies.append("突破後回測不破再進場")
        
        # 預設策略
        if not strategies:
            strategies.append("分批建倉，避免一次性重倉")
        
        return "；".join(strategies)
    
    def _get_exit_strategy(self, candidate: dict, target_price: float) -> str:
        """取得出場策略"""
        close = candidate["close"]
        stop_loss = candidate["risk"].get("stop_loss_price", close * 0.93)
        
        gain_pct = (target_price - close) / close * 100
        stop_pct = (stop_loss - close) / close * 100
        
        mid_target = close + (target_price - close) * 0.5
        
        strategies = []
        
        # 目標價策略
        strategies.append(
            f"達 {mid_target:.1f} (+{gain_pct/2:.1f}%) 時減半倉位"
        )
        strategies.append(
            f"達 {target_price:.1f} (+{gain_pct:.1f}%) 時全部出清"
        )
        
        # 停損策略
        strategies.append(
            f"跌破 {stop_loss:.1f} ({stop_pct:.1f}%) 嚴格停損"
        )
        
        return "；".join(strategies)
