"""
Flask App - 持股操作建議系統
提供 LINE Bot Webhook 及股價查詢 REST API
"""
import logging
import os
import threading
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from linebot.exceptions import InvalidSignatureError
import yfinance as yf

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 導入 LINE Bot Handler
from agents.line_handler import handler


@app.get("/")
def index():
    return "Stock AI MultiAgent - Portfolio Advisor 📊", 200


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "mode": "portfolio_advisor",
        "message": "持股操作建議系統運行中",
        "features": ["LINE Bot", "Stock Price API", "Multi-Agent Analysis"]
    }), 200


# ══════════════════════════════════════════════════════
# LINE Bot Webhook
# ══════════════════════════════════════════════════════
@app.post("/webhook")
def webhook():
    """LINE Bot Webhook 處理"""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    logger.info(f"Webhook 收到請求: {body[:200]}")

    # ── 在背景執行，立即回傳 200 避免 LINE 逾時 ────────────────
    def _process():
        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            logger.warning("LINE 簽章驗證失敗（X-Line-Signature 錯誤）")
        except Exception as e:
            logger.error(f"Webhook 處理失敗: {e}", exc_info=True)

    threading.Thread(target=_process, daemon=True).start()
    return "OK", 200


# ══════════════════════════════════════════════════════
# 股價查詢 REST API（供第三方軟體使用）
# ══════════════════════════════════════════════════════
@app.get("/api/v1/stock/<symbol>")
def get_stock_price(symbol: str):
    """
    查詢股票即時資訊
    
    GET /api/v1/stock/2330.TW
    GET /api/v1/stock/AAPL
    
    Returns:
        {
            "symbol": "2330.TW",
            "name": "台積電",
            "price": 580.0,
            "change": 5.0,
            "change_pct": 0.87,
            "volume": 25000000,
            "market_cap": 15000000000000,
            "timestamp": "2024-01-15T13:30:00"
        }
    """
    try:
        symbol = symbol.upper()
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="1d")
        
        if hist.empty:
            return jsonify({"error": "Stock not found"}), 404
        
        current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        prev_close = info.get("previousClose", 0)
        change = current_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        
        response = {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName", symbol),
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": info.get("volume", 0),
            "market_cap": info.get("marketCap", 0),
            "timestamp": hist.index[-1].isoformat() if not hist.empty else None,
            "open": round(float(hist["Open"].iloc[-1]), 2),
            "high": round(float(hist["High"].iloc[-1]), 2),
            "low": round(float(hist["Low"].iloc[-1]), 2),
            "close": round(float(hist["Close"].iloc[-1]), 2),
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"查詢股價失敗 {symbol}: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/v1/stocks")
def get_multiple_stocks():
    """
    批量查詢多檔股票
    
    GET /api/v1/stocks?symbols=2330.TW,AAPL,NVDA
    
    Returns:
        {
            "stocks": [
                {"symbol": "2330.TW", "price": 580.0, ...},
                {"symbol": "AAPL", "price": 185.5, ...}
            ]
        }
    """
    try:
        symbols_param = request.args.get("symbols", "")
        if not symbols_param:
            return jsonify({"error": "Missing symbols parameter"}), 400
        
        symbols = [s.strip().upper() for s in symbols_param.split(",")]
        results = []
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
                prev_close = info.get("previousClose", 0)
                change = current_price - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0
                
                results.append({
                    "symbol": symbol,
                    "name": info.get("shortName", symbol),
                    "price": round(current_price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                })
            except Exception as e:
                logger.error(f"查詢 {symbol} 失敗: {e}")
                results.append({
                    "symbol": symbol,
                    "error": str(e)
                })
        
        return jsonify({"stocks": results}), 200
        
    except Exception as e:
        logger.error(f"批量查詢失敗: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Flask 服務啟動於 port {port}")
    logger.info("📊 功能：LINE Bot + 股價查詢 API")
    app.run(host="0.0.0.0", port=port, debug=False)
