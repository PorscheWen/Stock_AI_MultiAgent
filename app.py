"""
Flask App - 持股操作建議系統
提供 LINE Bot Webhook 及股價查詢 REST API
"""
import logging
import os
import threading
import uuid
from flask import Flask, jsonify, request, abort, render_template, send_from_directory
from dotenv import load_dotenv
from linebot.exceptions import InvalidSignatureError
import yfinance as yf
from database.portfolio_db import PortfolioDB
from agents.screenshot_agent import ScreenshotAgent

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# PWA 持股資料庫（與 LINE Bot 共用同一 JSON 檔）
db_pwa = PortfolioDB()

# AI 分析工作佇列 { job_id: {status, result, error} }
_analysis_jobs: dict = {}

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



# ══════════════════════════════════════════════════════
# PWA 應用程式路由
# ══════════════════════════════════════════════════════

@app.get("/app")
def pwa():
    """提供 PWA 首頁"""
    return render_template("pwa.html")


@app.get("/sw.js")
def service_worker():
    """Service Worker 必須在根路徑提供"""
    return send_from_directory("static", "sw.js",
                               mimetype="application/javascript")


# ── 持股 CRUD API ──────────────────────────────────────────────────────────────

@app.get("/api/portfolio")
def api_portfolio_get():
    """取得使用者持股清單"""
    user_id = request.headers.get("X-User-ID", "").strip()
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    return jsonify({"stocks": db_pwa.get_portfolio(user_id)})


@app.post("/api/portfolio")
def api_portfolio_add():
    """新增持股"""
    user_id = request.headers.get("X-User-ID", "").strip()
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    data = request.get_json(force=True) or {}
    symbol = str(data.get("symbol", "")).strip().upper()
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    ok = db_pwa.add_stock(
        user_id, symbol,
        float(data.get("shares", 0)),
        float(data.get("avg_price", 0)),
        str(data.get("note", "")),
    )
    return jsonify({"success": ok, "symbol": symbol})


@app.delete("/api/portfolio/<symbol>")
def api_portfolio_remove(symbol: str):
    """刪除持股"""
    user_id = request.headers.get("X-User-ID", "").strip()
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    ok = db_pwa.remove_stock(user_id, symbol.upper())
    return jsonify({"success": ok})


@app.delete("/api/portfolio")
def api_portfolio_clear():
    """清空持股"""
    user_id = request.headers.get("X-User-ID", "").strip()
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    db_pwa.clear_portfolio(user_id)
    return jsonify({"success": True})


@app.get("/api/portfolio/prices")
def api_portfolio_with_prices():
    """取得持股清單含即時股價"""
    user_id = request.headers.get("X-User-ID", "").strip()
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400

    stocks = db_pwa.get_portfolio(user_id)
    results = []
    for stock in stocks:
        symbol = stock["symbol"]
        entry = dict(stock)
        try:
            info = yf.Ticker(symbol).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            prev = info.get("previousClose") or 0
            change = round(price - prev, 2) if price and prev else 0
            pct = round(change / prev * 100, 2) if prev else 0
            entry.update({
                "current_price": round(float(price), 2),
                "change": change,
                "change_pct": pct,
                "name": info.get("shortName") or info.get("longName", symbol),
            })
        except Exception:
            entry.update({"current_price": 0, "change": 0, "change_pct": 0, "name": symbol})
        results.append(entry)

    return jsonify({"stocks": results})


# ── 截圖辨識 API ────────────────────────────────────────────────────────────────

@app.post("/api/screenshot")
def api_screenshot():
    """接收圖片檔案，辨識持股"""
    user_id = request.headers.get("X-User-ID", "").strip()
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    if "image" not in request.files:
        return jsonify({"error": "image file required"}), 400

    img_file = request.files["image"]
    img_bytes = img_file.read()
    content_type = img_file.content_type or "image/jpeg"

    result = ScreenshotAgent().analyze(img_bytes, image_type=content_type)
    return jsonify(result)


@app.post("/api/screenshot/import")
def api_screenshot_import():
    """將截圖辨識結果批量匯入持股"""
    user_id = request.headers.get("X-User-ID", "").strip()
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    data = request.get_json(force=True) or {}
    stocks = data.get("stocks", [])
    if not stocks:
        return jsonify({"error": "stocks required"}), 400
    result = db_pwa.batch_add_stocks(user_id, stocks)
    return jsonify(result)


# ── AI 分析 API（非同步 Job Queue）────────────────────────────────────────────

@app.post("/api/analysis")
def api_analysis_start():
    """啟動 AI 分析，立即返回 job_id"""
    user_id = request.headers.get("X-User-ID", "").strip()
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400

    symbols = db_pwa.get_all_symbols(user_id)
    if not symbols:
        return jsonify({"error": "portfolio is empty"}), 400

    job_id = str(uuid.uuid4())
    _analysis_jobs[job_id] = {"status": "pending", "result": None, "error": None}

    def _run():
        try:
            from agents.orchestrator import OrchestratorAgent
            report = OrchestratorAgent().run_for_user(user_id, symbols)
            _analysis_jobs[job_id].update({"status": "done", "result": report})
        except Exception as e:
            logger.error(f"PWA 分析失敗: {e}")
            _analysis_jobs[job_id].update({"status": "error", "error": str(e)})

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"job_id": job_id, "status": "pending", "symbols": symbols})


@app.get("/api/analysis/<job_id>")
def api_analysis_status(job_id: str):
    """查詢分析工作狀態"""
    job = _analysis_jobs.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Flask 服務啟動於 port {port}")
    logger.info("📊 功能：LINE Bot + 股價查詢 API + PWA")
    app.run(host="0.0.0.0", port=port, debug=False)
