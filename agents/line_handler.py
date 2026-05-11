"""
LINE Bot 訊息處理器
處理使用者互動指令
"""
import logging
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage,
    FlexSendMessage, BubbleContainer, BoxComponent,
    TextComponent, ButtonComponent, MessageAction
)
from linebot.exceptions import InvalidSignatureError
import os
from database.portfolio_db import PortfolioDB
from agents.orchestrator import OrchestratorAgent
from agents.screenshot_agent import ScreenshotAgent
from agents.portfolio_view import format_portfolio_lines, parse_list_sort_args

logger = logging.getLogger(__name__)

# LINE Bot 設定
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_STOCK_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.getenv("CHANNEL_STOCK_SECRET", "")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 資料庫
db = PortfolioDB()

# 截圖待確認暫存：{ user_id: [stock_dict, ...] }
_pending_screenshots: dict[str, list[dict]] = {}


def get_help_message() -> str:
    """取得幫助訊息"""
    return """📊 持股操作建議系統

📝 指令列表：
• 新增持股 <代碼>
  例：新增持股 2330.TW
  例：新增持股 AAPL

• 查看持股 [排序] [逆序]
  顯示名稱、持有成本、參考損益、資料更新日
  排序：代碼、股數、成本、獲利、獲利%、名稱、更新
  例：查看持股 股數 逆序　查看持股 依獲利

• 刪除持股 <代碼>
  例：刪除持股 2330.TW

• 分析持股
  取得所有持股的 AI 操作建議

• 清空持股
  移除所有持股

• 股價 <代碼>
  查詢即時股價
  例：股價 2330.TW

📸 截圖匯入：
• 直接傳送券商 App 持倉截圖
  系統自動辨識持股並更新
  （支援台股/美股）

• 幫助
  顯示此訊息"""


def parse_command(text: str) -> tuple[str, list[str]]:
    """
    解析使用者指令
    
    Returns:
        (command, args)
    """
    parts = text.strip().split()
    if not parts:
        return ("", [])
    
    cmd = parts[0]
    args = parts[1:]
    
    return (cmd, args)


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """處理文字訊息"""
    user_id = event.source.user_id
    text = event.message.text.strip()
    
    logger.info(f"收到訊息: user={user_id}, text={text}")
    
    cmd, args = parse_command(text)
    
    # ── 幫助 ──────────────────────────────────────────
    if cmd in ["幫助", "help", "?"]:
        reply = get_help_message()
    
    # ── 新增持股 ───────────────────────────────────────
    elif cmd == "新增持股":
        if not args:
            reply = "❌ 請提供股票代碼\n例：新增持股 2330.TW"
        else:
            symbol = args[0].upper()
            db.add_stock(user_id, symbol)
            reply = f"✅ 已新增持股：{symbol}"
    
    # ── 查看持股 ───────────────────────────────────────
    elif cmd == "查看持股":
        portfolio = db.get_portfolio(user_id)
        if not portfolio:
            reply = "📭 您目前沒有持股\n使用「新增持股 <代碼>」來新增"
        else:
            sort_key, reverse = parse_list_sort_args(args)
            try:
                reply = format_portfolio_lines(portfolio, sort_key, reverse)
            except Exception as e:
                logger.exception("查看持股格式化失敗")
                reply = f"❌ 無法產生持股清單：{e}"
    
    # ── 刪除持股 ───────────────────────────────────────
    elif cmd == "刪除持股":
        if not args:
            reply = "❌ 請提供股票代碼\n例：刪除持股 2330.TW"
        else:
            symbol = args[0].upper()
            if db.remove_stock(user_id, symbol):
                reply = f"✅ 已刪除持股：{symbol}"
            else:
                reply = f"❌ 找不到持股：{symbol}"
    
    # ── 清空持股 ───────────────────────────────────────
    elif cmd == "清空持股":
        db.clear_portfolio(user_id)
        reply = "✅ 已清空所有持股"
    
    # ── 分析持股 ───────────────────────────────────────
    elif cmd == "分析持股":
        symbols = db.get_all_symbols(user_id)
        if not symbols:
            reply = "📭 您目前沒有持股\n使用「新增持股 <代碼>」來新增"
        else:
            reply = f"🔄 開始分析 {len(symbols)} 檔持股...\n請稍候，分析需要 1-2 分鐘"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply)
            )
            
            # 執行分析（在背景執行）
            try:
                orchestrator = OrchestratorAgent()
                report = orchestrator.run_for_user(user_id, symbols)
                
                # 推送分析結果
                from agents.line_notifier import push_portfolio_report
                push_portfolio_report(user_id, report)
                
            except Exception as e:
                logger.error(f"分析失敗: {e}")
                line_bot_api.push_message(
                    user_id,
                    TextSendMessage(text=f"❌ 分析失敗：{str(e)}")
                )
            return  # 已經回覆，不需要再次回覆
    
    # ── 股價查詢 ───────────────────────────────────────
    elif cmd == "股價":
        if not args:
            reply = "❌ 請提供股票代碼\n例：股價 2330.TW"
        else:
            symbol = args[0].upper()
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                info = ticker.info
                current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
                prev_close = info.get("previousClose", 0)
                change = current_price - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0
                
                reply = f"💰 {symbol} 即時股價\n\n"
                reply += f"目前價格：${current_price:.2f}\n"
                reply += f"漲跌：{change:+.2f} ({change_pct:+.2f}%)\n"
                reply += f"昨收：${prev_close:.2f}"
                
            except Exception as e:
                logger.error(f"查詢股價失敗: {e}")
                reply = f"❌ 查詢失敗：{symbol}\n請確認代碼是否正確"
    
    # ── 確認截圖匯入 ────────────────────────────────────
    elif text in ["確認截圖匯入", "✅ 確認匯入"]:
        pending = _pending_screenshots.pop(user_id, None)
        if not pending:
            reply = "⚠️ 沒有待確認的截圖匯入\n請先傳送持倉截圖"
        else:
            result = db.batch_add_stocks(user_id, pending)
            count = result.get("success", 0)
            symbols = [s["symbol"] for s in pending]
            reply = f"✅ 已匯入 {count} 檔持股：\n" + "、".join(symbols)
            if result.get("failed", 0):
                reply += f"\n⚠️ {result['failed']} 檔匯入失敗"

    # ── 取消截圖匯入 ────────────────────────────────────
    elif text in ["取消截圖匯入", "❌ 取消匯入"]:
        _pending_screenshots.pop(user_id, None)
        reply = "✅ 已取消截圖匯入"

    # ── 未知指令 ───────────────────────────────────────
    else:
        reply = f"❓ 未知指令：{cmd}\n\n" + get_help_message()
    
    # 回覆訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )


@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    """處理圖片訊息 → 截圖辨識持股"""
    user_id = event.source.user_id
    message_id = event.message.id

    logger.info(f"收到圖片訊息: user={user_id}, message_id={message_id}")

    # 立即回覆「分析中」，避免逾時
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="📸 正在辨識截圖中...\n請稍候 10-20 秒")
    )

    try:
        # ── 1. 從 LINE 下載圖片 ──────────────────────────
        content_response = line_bot_api.get_message_content(message_id)
        image_bytes = b"".join(content_response.iter_content())

        # ── 2. 呼叫 Claude Vision 辨識 ──────────────────
        agent = ScreenshotAgent()
        result = agent.analyze(image_bytes, image_type="image/jpeg")

        stocks = result.get("stocks", [])
        confidence = result.get("confidence", 0)
        note = result.get("note", "")

        # ── 3. 處理辨識結果 ──────────────────────────────
        if not stocks:
            msg = f"❌ 無法辨識持倉截圖\n\n"
            if note:
                msg += f"原因：{note}\n\n"
            msg += "請確認：\n" \
                   "• 截圖為券商 App 持倉頁面\n" \
                   "• 圖片清晰無遮擋\n" \
                   "• 支援台股（4碼數字）及美股（英文代碼）"
            line_bot_api.push_message(user_id, TextSendMessage(text=msg))
            return

        # ── 4. 存入暫存，等待使用者確認 ──────────────────
        _pending_screenshots[user_id] = stocks

        preview = agent.format_preview(stocks)
        confidence_pct = int(confidence * 100)

        msg = f"📊 辨識結果（信心度 {confidence_pct}%）：\n\n"
        msg += preview
        if note:
            msg += f"\n\n⚠️ 備註：{note}"
        msg += "\n\n" \
               "確認無誤請回傳：確認截圖匯入\n" \
               "取消請回傳：取消截圖匯入"

        line_bot_api.push_message(user_id, TextSendMessage(text=msg))

    except Exception as e:
        logger.error(f"截圖處理失敗: {e}")
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=f"❌ 截圖處理失敗：{str(e)}")
        )
