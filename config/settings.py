"""
系統設定檔 — 所有 Agent 共用參數
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Anthropic ──────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-opus-4-6"          # 主力模型
CLAUDE_HAIKU  = "claude-haiku-4-5-20251001"  # 快速推論用

# ── 掃描目標股票池 ─────────────────────────────────────
WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "TSLA", "META",
    "GOOGL", "AMZN", "AMD", "SOFI", "PLTR",
    "2330.TW", "2317.TW", "2454.TW", "2382.TW", "3008.TW",
]

# ── 股票名稱對照表 ──────────────────────────────────────
STOCK_NAMES: dict[str, str] = {
    # 美股
    "AAPL":  "Apple",
    "MSFT":  "Microsoft",
    "NVDA":  "NVIDIA",
    "TSLA":  "Tesla",
    "META":  "Meta",
    "GOOGL": "Alphabet",
    "AMZN":  "Amazon",
    "AMD":   "AMD",
    "SOFI":  "SoFi",
    "PLTR":  "Palantir",
    # 台股
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "2382.TW": "廣達",
    "3008.TW": "大立光",
}

# ── 技術面門檻 ─────────────────────────────────────────
VOLUME_SURGE_MULTIPLIER = 2.5   # 成交量異常倍數
RSI_OVERSOLD            = 35
RSI_OVERBOUGHT          = 70
BOLLINGER_PERIOD        = 20
BOLLINGER_STD           = 2.0

# ── 風控門檻 ───────────────────────────────────────────
MAX_POSITION_PCT        = 0.10  # 單檔最大資金占比 10%
MAX_STOP_LOSS_PCT       = 0.07  # 最大停損 7%
MIN_RISK_REWARD_RATIO   = 2.0   # 最低風報比 2:1
LIQUIDITY_MIN_VOLUME    = 500_000  # 日均量門檻（股）

# ── 驗證層門檻 ─────────────────────────────────────────
CONFIDENCE_THRESHOLD    = 0.65  # 信心分數低於此值否決
BACKTEST_MIN_WINRATE    = 0.50  # 回測最低勝率

# ── 回測設定 ───────────────────────────────────────────
BACKTEST_YEARS          = 3
LOOKBACK_DAYS           = 365 * BACKTEST_YEARS

# ── 情緒分析 ───────────────────────────────────────────
SENTIMENT_SOURCES = ["news", "ptt", "reddit"]

# ── 輸出設定 ───────────────────────────────────────────
REPORT_DIR = "reports"
NOTION_API_KEY   = os.getenv("NOTION_API_KEY", "")
NOTION_DB_ID     = os.getenv("NOTION_DB_ID", "")
SMTP_HOST        = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT        = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER        = os.getenv("SMTP_USER", "")
SMTP_PASS        = os.getenv("SMTP_PASS", "")
NOTIFY_EMAIL     = os.getenv("NOTIFY_EMAIL", "")
