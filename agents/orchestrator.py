"""
🧠 ORCHESTRATOR AGENT（主控 Agent）
- 並行分派任務給 Scanner、Sentiment、Risk、Backtest
- 合併結果，傳給 Validation Agent 三重把關
- 輸出最終 JSON 報告
排程：每日 08:00
"""
import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import anthropic

from agents.scanner_agent    import ScannerAgent
from agents.sentiment_agent  import SentimentAgent
from agents.risk_agent       import RiskAgent
from agents.backtest_agent   import BacktestAgent
from agents.validation_agent import ValidationAgent
from agents.advisor_agent    import AdvisorAgent
from agents.line_notifier    import push_report
from config.settings import (
    ANTHROPIC_AUTH_TOKEN,
    CLAUDE_MODEL,
    REPORT_DIR,
    STOCK_NAMES,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Orchestrator")

client = anthropic.Anthropic(api_key=ANTHROPIC_AUTH_TOKEN)


class OrchestratorAgent:
    """主控 Agent — 並行協調所有子 Agent"""

    def __init__(self):
        self.scanner    = ScannerAgent()
        self.sentiment  = SentimentAgent()
        self.risk       = RiskAgent()
        self.backtest   = BacktestAgent()
        self.validator  = ValidationAgent()
        self.advisor    = AdvisorAgent()
        Path(REPORT_DIR).mkdir(exist_ok=True)

    # ══════════════════════════════════════════════════
    # 公開介面
    # ══════════════════════════════════════════════════
    def run(self) -> dict:
        """
        完整執行流程：
        1. 掃描 → 取得候選股清單
        2. 並行執行 Sentiment / Risk / Backtest
        3. 合併結果 → Validation 三重驗證
        4. 輸出最終報告
        """
        start_ts = datetime.now()
        logger.info("=" * 60)
        logger.info("🧠 Orchestrator 啟動")
        logger.info("=" * 60)

        # ── STEP 1：掃描技術面 ──────────────────────────
        logger.info("📡 [STEP 1] Scanner Agent 執行中...")
        scan_results = self.scanner.run()
        if not scan_results:
            logger.warning("掃描無候選股，流程終止")
            return self._empty_report(start_ts)

        symbols = [r.symbol for r in scan_results]
        logger.info(f"📡 Scanner 找到 {len(symbols)} 個候選：{symbols}")

        # ── STEP 2：並行執行三個 Agent ─────────────────
        logger.info("⚡ [STEP 2] 並行執行 Sentiment / Risk / Backtest...")
        sentiment_map, risk_map, backtest_map = self._run_parallel(symbols)

        # ── STEP 3：合併為候選清單 ─────────────────────
        candidates = self._merge(scan_results, sentiment_map, risk_map, backtest_map)
        logger.info(f"🔀 合併完成，{len(candidates)} 個候選進入驗證層")

        # ── STEP 4：Validation 三重驗證 ────────────────
        logger.info("🔍 [STEP 4] Validation Agent 三重把關...")
        validation_results = self.validator.run(candidates)

        # ── STEP 5：篩選通過者 ─────────────────────────
        passed = [
            (c, v) for c, v in zip(candidates, validation_results) if v.passed
        ]
        logger.info(f"✅ 通過驗證：{len(passed)} / {len(candidates)} 檔")

        # ── STEP 6：產生最終報告 ───────────────────────
        report = self._build_report(passed, start_ts)
        
        # ── STEP 7：生成操作摘要 ───────────────────────
        report["ai_summary"] = self._claude_summary(report)
        
        # ── STEP 8：儲存完整報告 ───────────────────────
        self._save_report(report)

        # ── STEP 9：LINE 推播 ──────────────────────────
        logger.info("📲 [STEP 9] 推播至 LINE Bot...")
        push_report(report)

        logger.info("🏁 Orchestrator 完成")
        return report

    # ══════════════════════════════════════════════════
    # 並行執行
    # ══════════════════════════════════════════════════
    def _run_parallel(self, symbols: list[str]) -> tuple[dict, dict, dict]:
        results = {}

        def run_sentiment():
            return "sentiment", self.sentiment.run(symbols)

        def run_risk():
            return "risk", self.risk.run(symbols)

        def run_backtest():
            return "backtest", self.backtest.run(symbols)

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [
                pool.submit(run_sentiment),
                pool.submit(run_risk),
                pool.submit(run_backtest),
            ]
            for future in as_completed(futures):
                key, data = future.result()
                results[key] = data

        return (
            results.get("sentiment", {}),
            results.get("risk", {}),
            results.get("backtest", {}),
        )

    # ══════════════════════════════════════════════════
    # 結果合併
    # ══════════════════════════════════════════════════
    def _merge(self, scan_results, sentiment_map, risk_map, backtest_map) -> list[dict]:
        merged = []
        for sr in scan_results:
            sym = sr.symbol
            sent = sentiment_map.get(sym)
            risk = risk_map.get(sym)
            bt   = backtest_map.get(sym)

            if not (sent and risk and bt):
                continue

            merged.append({
                "symbol":           sym,
                "close":            sr.close,
                # 技術面
                "technical_score":  sr.technical_score,
                "rsi":              sr.rsi,
                "macd":             sr.macd,
                "volume_ratio":     sr.volume_ratio,
                "breakout":         sr.breakout,
                "signals":          sr.signals,
                # 情緒面
                "sentiment_score":  sent.sentiment_score,
                "news_score":       sent.news_score,
                "social_score":     sent.social_score,
                "major_events":     sent.major_events,
                "sentiment_summary": sent.summary,
                # 風控
                "risk_level":       risk.risk_level,
                "risk_score":       risk.risk_score,
                "atr_pct":          risk.atr_pct,
                "stop_loss_price":  risk.stop_loss_price,
                "stop_loss_pct":    risk.stop_loss_pct,
                "target_price":     risk.target_price,
                "risk_reward_ratio": risk.risk_reward_ratio,
                "liquidity_ok":     risk.liquidity_ok,
                "max_drawdown":     risk.max_drawdown,
                # 回測
                "backtest_score":   bt.backtest_score,
                "win_rate":         bt.win_rate,
                "avg_return":       bt.avg_return,
                "avg_loss":         bt.avg_loss,
                "profit_factor":    bt.profit_factor,
                "best_entry_time":  bt.best_entry_time,
            })
        return merged

    # ══════════════════════════════════════════════════
    # 報告建立
    # ══════════════════════════════════════════════════
    def _build_report(self, passed: list[tuple], start_ts: datetime) -> dict:
        stocks = []
        for c, v in passed:
            sym = c["symbol"]
            stocks.append({
                "symbol":           sym,
                "name":             STOCK_NAMES.get(sym, sym),
                "close":            c["close"],
                "scores": {
                    "technical":    round(c["technical_score"], 1),
                    "sentiment":    round(c["sentiment_score"] * 100, 1),
                    "risk":         round(c["risk_score"], 1),
                    "backtest_winrate": round(c["win_rate"] * 100, 1),
                    "validation_confidence": round(v.confidence_score * 100, 1),
                },
                "signals":          c["signals"],
                "major_events":     c["major_events"],
                "sentiment_summary": c["sentiment_summary"],
                "risk": {
                    "level":        c["risk_level"],
                    "stop_loss_price": c["stop_loss_price"],
                    "stop_loss_pct":   c["stop_loss_pct"],
                    "target_price":    c["target_price"],
                    "risk_reward_ratio": c["risk_reward_ratio"],
                },
                "best_entry_time":  c["best_entry_time"],
                "operation":        v.final_verdict,
                "validation": {
                    "passed":       v.passed,
                    "check1_signal": v.check1_signal_consistent,
                    "check2_risk":   v.check2_risk_compliant,
                    "check3_bear":   v.check3_bear_case_cleared,
                    "bear_arguments": v.bear_arguments,
                    "verdict":       v.final_verdict,
                },
            })

        elapsed = (datetime.now() - start_ts).total_seconds()
        return {
            "generated_at": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "total_candidates": len(passed),
            "stocks": stocks,
            "ai_summary": "",  # 後續填入
        }

    def _save_report(self, report: dict):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = Path(REPORT_DIR) / f"report_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 報告儲存至 {path}")

    def _claude_summary(self, report: dict) -> str:
        """生成簡潔的操作摘要（格式：股票代號/進場/停損/目標/信心）"""
        if not report["stocks"]:
            return "本日無符合條件之股票，建議觀望。"

        lines = []
        lines.append("📊 今日精選操作清單\n")
        
        for idx, stock in enumerate(report["stocks"], 1):
            symbol = stock["symbol"]
            name = stock.get("name", symbol)
            close = stock["close"]
            risk = stock["risk"]
            conf = stock["scores"]["validation_confidence"]
            
            # 格式化價格
            if close >= 1000:
                price_fmt = f"${close:,.0f}"
                stop_fmt = f"${risk['stop_loss_price']:,.0f}"
                target_fmt = f"${risk['target_price']:,.0f}"
            else:
                price_fmt = f"${close:.1f}"
                stop_fmt = f"${risk['stop_loss_price']:.1f}"
                target_fmt = f"${risk['target_price']:.1f}"
            
            # 去除 .TW 後綴
            symbol_display = symbol.replace('.TW', '')
            
            line = f"{idx}. {name} ({symbol_display}) | 信心 {conf:.1f}% | 進場 {price_fmt}\n"
            line += f"   停損 {stop_fmt} (-{risk['stop_loss_pct']:.1f}%) | "
            line += f"目標 {target_fmt} (+{(risk['target_price']-close)/close*100:.1f}%)"
            
            lines.append(line)
        
        lines.append("\n⚠️ 本資訊僅供參考，投資有風險，請自行判斷。")
        
        return "\n".join(lines)

    def _empty_report(self, start_ts: datetime) -> dict:
        elapsed = (datetime.now() - start_ts).total_seconds()
        return {
            "generated_at": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "total_candidates": 0,
            "stocks": [],
            "ai_summary": "本日掃描無候選股，建議觀望。",
        }

    # ══════════════════════════════════════════════════
    # 持股分析模式
    # ══════════════════════════════════════════════════
    def run_for_user(self, user_id: str, symbols: list[str]) -> dict:
        """
        分析使用者持股，提供操作建議
        
        Args:
            user_id: LINE 使用者 ID
            symbols: 持股代碼列表 ["2330.TW", "AAPL", ...]
        
        Returns:
            報告字典
        """
        start_ts = datetime.now()
        logger.info("=" * 60)
        logger.info(f"🧠 Orchestrator 啟動（持股分析模式）")
        logger.info(f"📊 使用者: {user_id}, 持股: {len(symbols)} 檔")
        logger.info("=" * 60)
        
        if not symbols:
            logger.warning("持股清單為空，流程終止")
            return self._empty_report(start_ts)
        
        # ── STEP 1：掃描技術面（針對指定股票）──────────
        logger.info(f"📡 [STEP 1] Scanner Agent 分析 {len(symbols)} 檔持股...")
        scanner = ScannerAgent(watchlist=symbols)
        scan_results = scanner.run()
        
        if not scan_results:
            logger.warning("掃描無結果，流程終止")
            return self._empty_report(start_ts)
        
        # ── STEP 2：並行執行三個 Agent ─────────────────
        logger.info("⚡ [STEP 2] 並行執行 Sentiment / Risk / Backtest...")
        sentiment_map, risk_map, backtest_map = self._run_parallel(symbols)
        
        # ── STEP 3：合併為候選清單 ─────────────────────
        candidates = self._merge(scan_results, sentiment_map, risk_map, backtest_map)
        logger.info(f"🔀 合併完成，{len(candidates)} 個候選")
        
        # ── STEP 4：Advisor 提供操作建議 ───────────────
        logger.info("💡 [STEP 4] Advisor Agent 生成操作建議...")
        advised_stocks = []
        
        for candidate in candidates:
            try:
                advice = self.advisor.analyze(candidate)
                
                advised_stocks.append({
                    "symbol": candidate["symbol"],
                    "name": STOCK_NAMES.get(candidate["symbol"], candidate["symbol"]),
                    "close": candidate["close"],
                    "recommendation": advice.recommendation.value,
                    "confidence": advice.confidence,
                    "reason": advice.reason,
                    "target_price": advice.target_price,
                    "stop_loss": advice.stop_loss,
                    "entry_strategy": advice.entry_strategy,
                    "exit_strategy": advice.exit_strategy,
                    "scores": {
                        "technical": round(candidate["technical_score"], 1),
                        "sentiment": round(candidate["sentiment_score"] * 100, 1),
                        "risk": round(candidate["risk_score"], 1),
                        "backtest": round(candidate["backtest_score"], 1),
                    },
                    "signals": candidate.get("signals", []),
                })
            except Exception as e:
                logger.error(f"分析 {candidate['symbol']} 失敗: {e}")
        
        # ── STEP 5：產生報告 ───────────────────────────
        elapsed = (datetime.now() - start_ts).total_seconds()
        report = {
            "generated_at": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "user_id": user_id,
            "stocks": advised_stocks,
            "ai_summary": self._portfolio_summary(advised_stocks),
        }
        
        # ── STEP 6：儲存報告 ───────────────────────────
        self._save_report(report)
        
        logger.info(f"🏁 Orchestrator 完成（{len(advised_stocks)} 檔）")
        return report
    
    def _portfolio_summary(self, stocks: list[dict]) -> str:
        """生成持股操作摘要"""
        if not stocks:
            return "無持股數據"
        
        # 統計建議類型
        rec_count = {}
        for s in stocks:
            rec = s.get("recommendation", "HOLD")
            rec_count[rec] = rec_count.get(rec, 0) + 1
        
        lines = ["📊 持股操作摘要\n"]
        
        if rec_count.get("STRONG_BUY", 0) > 0:
            lines.append(f"🚀 強力買進: {rec_count['STRONG_BUY']} 檔")
        if rec_count.get("BUY", 0) > 0:
            lines.append(f"📈 買進: {rec_count['BUY']} 檔")
        if rec_count.get("HOLD", 0) > 0:
            lines.append(f"✋ 持有: {rec_count['HOLD']} 檔")
        if rec_count.get("SELL", 0) > 0:
            lines.append(f"📉 賣出: {rec_count['SELL']} 檔")
        if rec_count.get("STRONG_SELL", 0) > 0:
            lines.append(f"⚠️ 強力賣出: {rec_count['STRONG_SELL']} 檔")
        
        lines.append("\n⚠️ 本資訊僅供參考，投資有風險，請自行判斷。")
        
        return "\n".join(lines)


# ── CLI 進入點 ─────────────────────────────────────────
if __name__ == "__main__":
    agent = OrchestratorAgent()
    result = agent.run()
    print("\n" + "=" * 60)
    print("📊 最終報告")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
