"""
主程式進入點
執行方式：
  python main.py       # 立即執行一次
  python main.py --json  # 只輸出 JSON 報告
"""
import argparse
import io
import json
import sys

# 強制 stdout 使用 UTF-8，解決 Windows cp950 emoji 編碼問題
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from agents.orchestrator import OrchestratorAgent


# ── 評分轉星級 ─────────────────────────────────────────
def _stars(score: float) -> str:
    if score >= 80:
        return "★★★★★"
    elif score >= 70:
        return "★★★★☆"
    elif score >= 60:
        return "★★★☆☆"
    else:
        return "★★☆☆☆"


# ── 風險等級標籤 ───────────────────────────────────────
def _risk_badge(level: int) -> str:
    badges = {1: "🟢 極低", 2: "🟡 低", 3: "🟠 中", 4: "🔴 高", 5: "⛔ 極高"}
    return badges.get(level, "")


# ── 信心分數建議 ───────────────────────────────────────
def _confidence_advice(conf: float) -> str:
    if conf >= 80:
        return "強力推薦，可正常倉位進場"
    elif conf >= 75:
        return "推薦，建議七成倉位試單"
    elif conf >= 70:
        return "中等推薦，建議半倉觀察"
    else:
        return "謹慎，建議小倉或觀望"


# ── 進場策略描述 ───────────────────────────────────────
def _entry_strategy(s: dict) -> str:
    signals = s.get("signals", [])
    rr = s["risk"]["risk_reward_ratio"]
    stop_pct = s["risk"]["stop_loss_pct"]
    entry_hint = s.get("best_entry_time", "")

    lines = []

    # 進場時機
    if any("金叉" in sig for sig in signals):
        lines.append("MACD 金叉確認 → 開盤前5分鐘掛單")
    elif any("暴增" in sig for sig in signals):
        lines.append("量能暴增信號 → 開盤確認續量再進場，避免追高")
    elif any("低檔" in sig or "支撐" in sig for sig in signals):
        lines.append("支撐反彈信號 → 等待止跌K棒後進場")
    elif any("突破" in sig for sig in signals):
        lines.append("突破信號 → 回測突破點不破即可介入")
    else:
        lines.append(entry_hint)

    # 分批策略
    stop = s["risk"]["stop_loss_pct"]
    target = s["risk"]["target_price"]
    close  = s["close"]
    gain_pct = (target - close) / close * 100
    mid_target = round(close + (target - close) * 0.5, 1)

    lines.append(f"分批出場：達 {mid_target} (+{gain_pct/2:.1f}%) 減半，剩半倉守至 {target} (+{gain_pct:.1f}%)")
    lines.append(f"嚴格停損：跌破 {s['risk']['stop_loss_price']} 即出，不拗單")

    return "\n      ".join(lines)


# ── 主輸出函式 ─────────────────────────────────────────
def print_report(report: dict):
    stocks = report["stocks"]
    date   = report["generated_at"][:10]

    print()
    print("=" * 65)
    print(f"  📊 短期爆發股票報告　{date}")
    print(f"  通過三重驗證：{len(stocks)} 檔　　耗時：{report['elapsed_seconds']}s")
    print("=" * 65)

    for rank, s in enumerate(stocks, 1):
        sc   = s["scores"]
        risk = s["risk"]
        val  = s["validation"]
        conf = sc["validation_confidence"]
        close = s["close"]

        # ── 標題列 ─────────────────────────────────────
        print()
        print(f"  {'─'*61}")
        print(f"  #{rank}  {s['symbol']:10s}  "
              f"現價 ${close:,.1f}　　"
              f"信心 {conf:.1f}%  {_stars(conf)}")
        print(f"  {'─'*61}")

        # ── 評分面板 ───────────────────────────────────
        print(f"  【評分面板】")
        print(f"    技術面  {sc['technical']:5.1f}/100  {_stars(sc['technical'])}")
        print(f"    情緒面  {sc['sentiment']:5.1f}/100  {_stars(sc['sentiment'])}")
        print(f"    風控    {sc['risk']:5.1f}/100  {_stars(sc['risk'])}")
        print(f"    回測勝率 {sc['backtest_winrate']:5.1f}%")

        # ── 觸發信號 ───────────────────────────────────
        sigs = "　".join(s.get("signals", []))
        print(f"\n  【觸發信號】　{sigs}")

        # ── 風控參數 ───────────────────────────────────
        print(f"\n  【風控參數】　{_risk_badge(risk['level'])}")
        print(f"    進場參考價　　${close:,.1f}")
        print(f"    停損價　　　　${risk['stop_loss_price']:,.1f}　（-{risk['stop_loss_pct']:.1f}%）")
        print(f"    目標價　　　　${risk['target_price']:,.1f}　（+{(risk['target_price']-close)/close*100:.1f}%）")
        print(f"    風報比　　　　{risk['risk_reward_ratio']:.1f} : 1")

        # ── 操作建議 ───────────────────────────────────
        print(f"\n  【操作建議】　{_confidence_advice(conf)}")
        print(f"      {_entry_strategy(s)}")

        # ── 空方風險提示 ───────────────────────────────
        if val.get("bear_arguments"):
            bear = val["bear_arguments"][0]
            # 截取前 80 字
            bear_short = bear[:80] + "..." if len(bear) > 80 else bear
            print(f"\n  【空方警示】")
            print(f"      {bear_short}")

        # ── 驗證摘要 ───────────────────────────────────
        c1 = "✅" if val["check1_signal"] else "❌"
        c2 = "✅" if val["check2_risk"]   else "❌"
        c3 = "✅" if val["check3_bear"]   else "❌"
        print(f"\n  【三重驗證】　{c1}信號一致　{c2}風控合規　{c3}空方通過")

    # ── AI 摘要 ────────────────────────────────────────
    if report.get("ai_summary"):
        print()
        print("=" * 65)
        print("  💬 AI 操作摘要")
        print("=" * 65)
        for line in report["ai_summary"].split("\n"):
            print(f"  {line}")

    print()
    print("=" * 65)
    print(f"  ⚠️  本報告僅供參考，投資有風險，請自行判斷。")
    print("=" * 65)
    print()


# ── 主流程 ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="短期爆發股票 MultiAgent 系統")
    parser.add_argument("--json", action="store_true", help="只輸出 JSON 報告")
    args = parser.parse_args()

    agent  = OrchestratorAgent()
    report = agent.run()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
