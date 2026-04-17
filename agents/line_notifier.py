"""
📲 LINE NOTIFIER
將選股報告推播至 LINE Stock_AI_agent Bot
使用 LINE Messaging API Push Message + Flex Message
"""
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer,
)
import json

load_dotenv()
logger = logging.getLogger(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_USER_ID              = os.getenv("LINE_USER_ID", "")


def _risk_color(level: int) -> str:
    colors = {1: "#27AE60", 2: "#F39C12", 3: "#E67E22", 4: "#E74C3C", 5: "#8E44AD"}
    return colors.get(level, "#95A5A6")


def _star_bar(score: float) -> str:
    filled = round(score / 20)
    return "★" * filled + "☆" * (5 - filled)


def _confidence_label(conf: float) -> str:
    if conf >= 80:
        return "強力推薦"
    elif conf >= 75:
        return "推薦"
    elif conf >= 70:
        return "中等推薦"
    else:
        return "謹慎觀察"


def _build_stock_bubble(s: dict, rank: int = 0) -> dict:
    """每檔股票一個 Flex Bubble"""
    sc   = s["scores"]
    risk = s["risk"]
    conf = sc["validation_confidence"]
    sigs = "　".join(s.get("signals", []))
    gain_pct = (risk["target_price"] - s["close"]) / s["close"] * 100
    rc   = _risk_color(risk["level"])
    rank_prefix = f"#{rank} " if rank else ""

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": rc,
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"{rank_prefix}{s['symbol']}",
                            "size": "xl",
                            "weight": "bold",
                            "color": "#FFFFFF",
                            "flex": 1,
                        },
                        {
                            "type": "text",
                            "text": f"信心 {conf:.1f}%",
                            "size": "sm",
                            "color": "#FFFFFF",
                            "align": "end",
                            "gravity": "center",
                        },
                    ],
                },
                {
                    "type": "text",
                    "text": f"${s['close']:,.1f}　　{_confidence_label(conf)}",
                    "size": "sm",
                    "color": "#FFFFFF",
                    "margin": "sm",
                },
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "16px",
            "contents": [
                # 評分列
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "技術", "size": "xs", "color": "#888888", "flex": 1},
                        {"type": "text", "text": "情緒", "size": "xs", "color": "#888888", "flex": 1},
                        {"type": "text", "text": "風控", "size": "xs", "color": "#888888", "flex": 1},
                        {"type": "text", "text": "回測勝率", "size": "xs", "color": "#888888", "flex": 2},
                    ],
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": f"{sc['technical']:.0f}", "size": "md", "weight": "bold", "flex": 1},
                        {"type": "text", "text": f"{sc['sentiment']:.0f}", "size": "md", "weight": "bold", "flex": 1},
                        {"type": "text", "text": f"{sc['risk']:.0f}", "size": "md", "weight": "bold", "flex": 1},
                        {"type": "text", "text": f"{sc['backtest_winrate']:.1f}%", "size": "md", "weight": "bold", "color": "#27AE60", "flex": 2},
                    ],
                },
                {"type": "separator", "margin": "sm"},
                # 觸發信號
                {
                    "type": "text",
                    "text": f"📡 {sigs}",
                    "size": "xs",
                    "color": "#555555",
                    "wrap": True,
                    "margin": "sm",
                },
                {"type": "separator", "margin": "sm"},
                # 風控三欄
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "進場", "size": "xs", "color": "#888888"},
                                {"type": "text", "text": f"${s['close']:,.1f}", "size": "sm", "weight": "bold"},
                            ],
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "停損", "size": "xs", "color": "#E74C3C"},
                                {"type": "text", "text": f"${risk['stop_loss_price']:,.1f}", "size": "sm", "weight": "bold", "color": "#E74C3C"},
                                {"type": "text", "text": f"-{risk['stop_loss_pct']:.1f}%", "size": "xs", "color": "#E74C3C"},
                            ],
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "目標", "size": "xs", "color": "#27AE60"},
                                {"type": "text", "text": f"${risk['target_price']:,.1f}", "size": "sm", "weight": "bold", "color": "#27AE60"},
                                {"type": "text", "text": f"+{gain_pct:.1f}%", "size": "xs", "color": "#27AE60"},
                            ],
                        },
                    ],
                },
                {"type": "separator", "margin": "sm"},
                # 操作建議
                {
                    "type": "text",
                    "text": f"💡 {s.get('best_entry_time', '')}",
                    "size": "xs",
                    "color": "#2C3E50",
                    "wrap": True,
                    "margin": "sm",
                },
            ],
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "paddingAll": "12px",
            "backgroundColor": "#F8F9FA",
            "contents": [
                {
                    "type": "text",
                    "text": f"風報比 {risk['risk_reward_ratio']:.1f}:1",
                    "size": "xs",
                    "color": "#555555",
                    "flex": 1,
                },
                {
                    "type": "text",
                    "text": f"風險 L{risk['level']}",
                    "size": "xs",
                    "color": rc,
                    "weight": "bold",
                    "align": "end",
                },
            ],
        },
    }


def _build_summary_bubble(report: dict) -> dict:
    """第一張：總覽摘要 Bubble"""
    date = report["generated_at"][:10]
    total = report["total_candidates"]
    ai_summary = report.get("ai_summary", "")
    # 只取前200字
    summary_short = ai_summary[:200] + "..." if len(ai_summary) > 200 else ai_summary

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#2C3E50",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "📊 短期爆發股票報告", "size": "lg", "weight": "bold", "color": "#FFFFFF"},
                {"type": "text", "text": date, "size": "sm", "color": "#BDC3C7", "margin": "xs"},
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "backgroundColor": "#EBF5FB",
                            "paddingAll": "12px",
                            "cornerRadius": "8px",
                            "contents": [
                                {"type": "text", "text": "通過驗證", "size": "xs", "color": "#888888", "align": "center"},
                                {"type": "text", "text": f"{total} 檔", "size": "xxl", "weight": "bold", "color": "#2980B9", "align": "center"},
                            ],
                        },
                        {"type": "box", "layout": "vertical", "flex": 0, "width": "12px", "contents": []},
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "backgroundColor": "#EAFAF1",
                            "paddingAll": "12px",
                            "cornerRadius": "8px",
                            "contents": [
                                {"type": "text", "text": "耗時", "size": "xs", "color": "#888888", "align": "center"},
                                {"type": "text", "text": f"{report['elapsed_seconds']}s", "size": "xxl", "weight": "bold", "color": "#27AE60", "align": "center"},
                            ],
                        },
                    ],
                },
                {
                    "type": "text",
                    "text": summary_short if summary_short else "分析完成，請查看個股報告",
                    "size": "xs",
                    "color": "#555555",
                    "wrap": True,
                    "margin": "md",
                },
            ],
        },
    }


def push_report(report: dict) -> bool:
    """推播選股報告至 LINE Bot"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        logger.warning("[LINE] 未設定 TOKEN 或 USER_ID，跳過推播")
        return False

    try:
        from linebot.v3.messaging import (
            Configuration, ApiClient, MessagingApi,
            PushMessageRequest, FlexMessage,
        )
    except ImportError:
        logger.error("[LINE] 請安裝 linebot v3: pip install line-bot-sdk")
        return False

    try:
        config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

        # 依信心分數由高到低排序 → Carousel 由左而右為強力推薦優先
        sorted_stocks = sorted(
            report["stocks"],
            key=lambda x: x["scores"]["validation_confidence"],
            reverse=True,
        )

        bubbles = [_build_summary_bubble(report)]
        for rank, s in enumerate(sorted_stocks, 1):
            bubbles.append(_build_stock_bubble(s, rank))

        # LINE Carousel 最多 12 個 bubble
        bubbles = bubbles[:12]

        carousel = {
            "type": "carousel",
            "contents": bubbles,
        }

        with ApiClient(config) as api_client:
            api = MessagingApi(api_client)
            api.push_message(
                PushMessageRequest(
                    to=LINE_USER_ID,
                    messages=[
                        FlexMessage(
                            alt_text=f"📊 今日選股報告 — {report['total_candidates']} 檔通過驗證",
                            contents=FlexContainer.from_dict(carousel),
                        )
                    ],
                )
            )

        logger.info(f"[LINE] 推播成功：{report['total_candidates']} 檔選股報告")
        return True

    except Exception as e:
        logger.error(f"[LINE] 推播失敗: {e}")
        return False
