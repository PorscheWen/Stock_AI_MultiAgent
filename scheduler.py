"""
排程器：每日 08:00 自動執行 Orchestrator
使用方式：python scheduler.py
"""
import logging
import json
import schedule
import time
from datetime import datetime
from pathlib import Path

from agents.orchestrator import OrchestratorAgent
from config.settings import NOTIFY_EMAIL, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS

logger = logging.getLogger("Scheduler")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def send_email(report: dict):
    """發送 Email 通知（需設定 SMTP 環境變數）"""
    if not NOTIFY_EMAIL or not SMTP_USER:
        logger.info("未設定 Email，跳過通知")
        return

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    stocks = report.get("stocks", [])
    subject = f"📊 短期爆發股票報告 {datetime.now().strftime('%Y-%m-%d')} — {len(stocks)} 檔通過驗證"

    body_lines = [
        f"<h2>今日短期爆發股票報告</h2>",
        f"<p>產生時間：{report['generated_at']}</p>",
        f"<p>通過驗證：<b>{len(stocks)} 檔</b></p>",
        "<hr/>",
    ]

    for s in stocks:
        sc = s["scores"]
        r  = s["risk"]
        body_lines += [
            f"<h3>{s['symbol']} — ${s['close']:.2f}</h3>",
            f"<ul>",
            f"  <li>技術面：{sc['technical']} / 情緒面：{sc['sentiment']} / 風控：{sc['risk']}</li>",
            f"  <li>回測勝率：{sc['backtest_winrate']}% / 信心分數：{sc['validation_confidence']}%</li>",
            f"  <li>停損：${r['stop_loss_price']} ({r['stop_loss_pct']}%) → 目標：${r['target_price']}</li>",
            f"  <li>進場時機：{s['best_entry_time']}</li>",
            f"</ul>",
        ]

    body_lines.append(f"<hr/><p><b>AI 摘要：</b><br/>{report.get('ai_summary', '')}</p>")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_USER
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText("\n".join(body_lines), "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, NOTIFY_EMAIL, msg.as_string())
        logger.info(f"✉️  Email 已寄送至 {NOTIFY_EMAIL}")
    except Exception as e:
        logger.error(f"Email 發送失敗: {e}")


def daily_job():
    logger.info("🔔 每日選股任務啟動")
    agent  = OrchestratorAgent()
    report = agent.run()
    send_email(report)

    # 印出摘要
    print("\n" + "=" * 60)
    print(f"📊 今日通過驗證股票：{report['total_candidates']} 檔")
    print("=" * 60)
    for s in report["stocks"]:
        sc = s["scores"]
        print(
            f"  {s['symbol']:12s} "
            f"技術={sc['technical']:5.1f} "
            f"情緒={sc['sentiment']:5.1f} "
            f"風控={sc['risk']:5.1f} "
            f"勝率={sc['backtest_winrate']:4.1f}% "
            f"信心={sc['validation_confidence']:4.1f}%"
        )
    if report.get("ai_summary"):
        print("\n💬 AI 摘要：")
        print(report["ai_summary"])


if __name__ == "__main__":
    # 立即執行一次（測試用）
    logger.info("▶ 立即執行一次（測試）...")
    daily_job()

    # 設定每日 08:00 與 13:30 排程
    schedule.every().day.at("08:00").do(daily_job)
    schedule.every().day.at("13:30").do(daily_job)
    logger.info("⏰ 已設定每日 08:00 / 13:30 自動執行，等待中...")

    while True:
        schedule.run_pending()
        time.sleep(30)
