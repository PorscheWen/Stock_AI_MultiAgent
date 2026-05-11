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


def _get_api() -> "MessagingApi":
    """取得 LINE Messaging API 客戶端"""
    token = os.environ.get("CHANNEL_STOCK_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("CHANNEL_STOCK_ACCESS_TOKEN 未設定")
    return MessagingApi(ApiClient(Configuration(access_token=token)))


def _get_user_ids() -> list[str]:
    """
    訂閱者清單讀取順序（與 Stock_AI_Agent_ETF 一致）：
    1. CHANNEL_STOCK_USER_IDS 環境變數（逗號分隔，支援多用戶）
    2. CHANNEL_STOCK_USER_ID 環境變數（單人向下相容）
    """
    ids_env = os.environ.get("CHANNEL_STOCK_USER_IDS", "")
    if ids_env:
        ids = [uid.strip() for uid in ids_env.split(",") if uid.strip()]
        if ids:
            logger.info("[Push] 從 CHANNEL_STOCK_USER_IDS 讀取 %d 人", len(ids))
            return ids

    single = os.environ.get("CHANNEL_STOCK_USER_ID", "").strip()
    if single:
        return [single]

    raise RuntimeError("找不到任何訂閱者（CHANNEL_STOCK_USER_IDS、CHANNEL_STOCK_USER_ID 皆未設定）")


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
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"{rank_prefix}{s['symbol']}",
                                    "size": "xl",
                                    "weight": "bold",
                                    "color": "#FFFFFF",
                                },
                                {
                                    "type": "text",
                                    "text": s.get("name", s["symbol"]),
                                    "size": "sm",
                                    "color": "#FFFFFFcc",
                                    "margin": "xs",
                                },
                            ],
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
                    "type": "box",
                    "layout": "vertical",
                    "margin": "sm",
                    "backgroundColor": "#E8F5E9",
                    "paddingAll": "10px",
                    "cornerRadius": "8px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📋 操作建議",
                            "size": "xs",
                            "weight": "bold",
                            "color": "#2E7D32",
                        },
                        {
                            "type": "text",
                            "text": s.get("operation") or s.get("best_entry_time", ""),
                            "size": "xs",
                            "color": "#333333",
                            "wrap": True,
                            "margin": "xs",
                        },
                    ],
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


def push_text(message: str) -> bool:
    """推播純文字訊息給所有訂閱者（用於錯誤通知）。"""
    try:
        api = _get_api()
        user_ids = _get_user_ids()
        
        # 單人用 push_message，多人用 multicast
        if len(user_ids) == 1:
            api.push_message(PushMessageRequest(
                to=user_ids[0],
                messages=[TextMessage(text=message)]
            ))
        else:
            from linebot.v3.messaging import MulticastRequest
            api.multicast(MulticastRequest(
                to=user_ids,
                messages=[TextMessage(text=message)]
            ))
        
        logger.info(f"[LINE] 文字訊息推播成功（{len(user_ids)} 人）")
        return True
    except Exception as e:
        logger.error(f"[LINE] 文字訊息推播失敗: {e}")
        return False


def push_report(report: dict) -> bool:
    """推播選股報告給所有訂閱者"""
    try:
        api = _get_api()
        user_ids = _get_user_ids()
    except RuntimeError as e:
        logger.warning("[LINE] %s，跳過推播", e)
        return False

    try:
        sorted_stocks = sorted(
            report["stocks"],
            key=lambda x: x["scores"]["validation_confidence"],
            reverse=True,
        )

        bubbles = [_build_summary_bubble(report)]
        for rank, s in enumerate(sorted_stocks, 1):
            bubbles.append(_build_stock_bubble(s, rank))

        carousel = {"type": "carousel", "contents": bubbles[:12]}
        
        messages = [
            FlexMessage(
                alt_text=f"📊 今日選股報告 — {report['total_candidates']} 檔通過驗證",
                contents=FlexContainer.from_dict(carousel),
            )
        ]

        # 單人用 push_message，多人用 multicast
        if len(user_ids) == 1:
            api.push_message(PushMessageRequest(to=user_ids[0], messages=messages))
        else:
            from linebot.v3.messaging import MulticastRequest
            api.multicast(MulticastRequest(to=user_ids, messages=messages))

        logger.info("[LINE] 推播成功：%d 檔選股報告（%d 人）", report["total_candidates"], len(user_ids))
        return True

    except Exception as e:
        logger.error("[LINE] 推播失敗: %s", e)
        return False


def push_portfolio_report(user_id: str, report: dict) -> bool:
    """
    推播持股操作建議報告給指定使用者
    
    Args:
        user_id: LINE 使用者 ID
        report: 分析報告
    
    Returns:
        成功回傳 True
    """
    try:
        api = _get_api()
        
        # 建立操作建議泡泡卡片
        bubbles = [_build_portfolio_summary_bubble(report)]
        
        for rank, s in enumerate(report.get("stocks", []), 1):
            bubbles.append(_build_portfolio_stock_bubble(s, rank))
        
        carousel = {"type": "carousel", "contents": bubbles[:12]}
        
        messages = [
            FlexMessage(
                alt_text=f"📊 持股操作建議 — {len(report.get('stocks', []))} 檔",
                contents=FlexContainer.from_dict(carousel),
            )
        ]
        
        api.push_message(PushMessageRequest(to=user_id, messages=messages))
        
        logger.info(f"[LINE] 持股報告推播成功：user={user_id}, stocks={len(report.get('stocks', []))}")
        return True
        
    except Exception as e:
        logger.error(f"[LINE] 持股報告推播失敗: {e}")
        return False


def _build_portfolio_summary_bubble(report: dict) -> dict:
    """持股報告總覽 Bubble"""
    date = report["generated_at"][:10]
    total = len(report.get("stocks", []))
    ai_summary = report.get("ai_summary", "")
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
                {"type": "text", "text": "📊 持股操作建議", "size": "lg", "weight": "bold", "color": "#FFFFFF"},
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
                                {"type": "text", "text": "分析持股", "size": "xs", "color": "#888888", "align": "center"},
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
                                {"type": "text", "text": f"{report.get('elapsed_seconds', 0)}s", "size": "xxl", "weight": "bold", "color": "#27AE60", "align": "center"},
                            ],
                        },
                    ],
                },
                {
                    "type": "text",
                    "text": summary_short if summary_short else "分析完成，請查看個股建議",
                    "size": "xs",
                    "color": "#555555",
                    "wrap": True,
                    "margin": "md",
                },
            ],
        },
    }


def _build_portfolio_stock_bubble(s: dict, rank: int = 0) -> dict:
    """持股操作建議 Bubble"""
    recommendation = s.get("recommendation", "HOLD")
    rec_emoji = {
        "STRONG_BUY": "🚀",
        "BUY": "📈",
        "HOLD": "✋",
        "SELL": "📉",
        "STRONG_SELL": "⚠️"
    }
    
    rec_color = {
        "STRONG_BUY": "#27AE60",
        "BUY": "#2ECC71",
        "HOLD": "#F39C12",
        "SELL": "#E67E22",
        "STRONG_SELL": "#E74C3C"
    }
    
    rec_text = {
        "STRONG_BUY": "強力買進",
        "BUY": "買進",
        "HOLD": "持有",
        "SELL": "賣出",
        "STRONG_SELL": "強力賣出"
    }
    
    emoji = rec_emoji.get(recommendation, "📊")
    color = rec_color.get(recommendation, "#95A5A6")
    rec_label = rec_text.get(recommendation, recommendation)
    
    sc = s.get("scores", {})
    confidence = s.get("confidence", 0)
    reason = s.get("reason", "")
    
    rank_prefix = f"#{rank} " if rank else ""
    
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": color,
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
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"{rank_prefix}{s.get('symbol', '')}",
                                    "size": "xl",
                                    "weight": "bold",
                                    "color": "#FFFFFF",
                                },
                                {
                                    "type": "text",
                                    "text": s.get("name", s.get("symbol", "")),
                                    "size": "sm",
                                    "color": "#FFFFFFcc",
                                    "margin": "xs",
                                },
                            ],
                        },
                        {
                            "type": "text",
                            "text": f"{emoji} {rec_label}",
                            "size": "md",
                            "color": "#FFFFFF",
                            "weight": "bold",
                            "align": "end",
                            "gravity": "center",
                        },
                    ],
                },
                {
                    "type": "text",
                    "text": f"信心度 {confidence:.1f}%",
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
                        {"type": "text", "text": "回測", "size": "xs", "color": "#888888", "flex": 1},
                    ],
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": f"{sc.get('technical', 0):.0f}", "size": "md", "weight": "bold", "flex": 1},
                        {"type": "text", "text": f"{sc.get('sentiment', 0):.0f}", "size": "md", "weight": "bold", "flex": 1},
                        {"type": "text", "text": f"{sc.get('risk', 0):.0f}", "size": "md", "weight": "bold", "flex": 1},
                        {"type": "text", "text": f"{sc.get('backtest', 0):.0f}", "size": "md", "weight": "bold", "flex": 1},
                    ],
                },
                {"type": "separator", "margin": "sm"},
                # 建議理由
                {
                    "type": "text",
                    "text": f"💡 {reason}",
                    "size": "xs",
                    "color": "#555555",
                    "wrap": True,
                    "margin": "sm",
                },
                {"type": "separator", "margin": "sm"},
                # 價格資訊
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
                                {"type": "text", "text": "目前價", "size": "xs", "color": "#888888"},
                                {"type": "text", "text": f"${s.get('close', 0):,.1f}", "size": "sm", "weight": "bold"},
                            ],
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "停損價", "size": "xs", "color": "#E74C3C"},
                                {"type": "text", "text": f"${s.get('stop_loss', 0):,.1f}", "size": "sm", "weight": "bold", "color": "#E74C3C"},
                            ],
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "目標價", "size": "xs", "color": "#27AE60"},
                                {"type": "text", "text": f"${s.get('target_price', 0):,.1f}", "size": "sm", "weight": "bold", "color": "#27AE60"},
                            ],
                        },
                    ],
                },
                {"type": "separator", "margin": "sm"},
                # 進場策略
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "sm",
                    "backgroundColor": "#E3F2FD",
                    "paddingAll": "10px",
                    "cornerRadius": "8px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📋 進場策略",
                            "size": "xs",
                            "weight": "bold",
                            "color": "#1976D2",
                        },
                        {
                            "type": "text",
                            "text": s.get("entry_strategy", "分批建倉"),
                            "size": "xs",
                            "color": "#333333",
                            "wrap": True,
                            "margin": "xs",
                        },
                    ],
                },
                # 出場策略
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "sm",
                    "backgroundColor": "#FFF3E0",
                    "paddingAll": "10px",
                    "cornerRadius": "8px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🚪 出場策略",
                            "size": "xs",
                            "weight": "bold",
                            "color": "#F57C00",
                        },
                        {
                            "type": "text",
                            "text": s.get("exit_strategy", "達目標分批出場"),
                            "size": "xs",
                            "color": "#333333",
                            "wrap": True,
                            "margin": "xs",
                        },
                    ],
                },
            ],
        },
    }
