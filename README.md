# Stock_AI_MultiAgent

🤖 多智能體股票選股系統 | Multi-Agent 架構自動掃描台股+美股，三重驗證後推播 LINE 操作建議 | GitHub Actions 自動排程

## 架構

```
Stock_AI_MultiAgent/
├── .github/workflows/
│   └── daily_analysis.yml   ⏰ GitHub Actions 排程（週一至週五 13:35）
├── agents/
│   ├── orchestrator.py      🧠 主控 Agent（並行協調）
│   ├── scanner_agent.py     📡 技術面掃描（RSI/MACD/布林/成交量）
│   ├── sentiment_agent.py   🧬 情緒分析（Claude API + Reddit）
│   ├── risk_agent.py        ⚖️  風控計算（ATR/停損/風報比）
│   ├── backtest_agent.py    ⚡ 回測驗證（3年歷史勝率）
│   ├── validation_agent.py  🔍 三重獨立驗證
│   └── line_notifier.py     📲 LINE Flex Message 推播
├── tests/
│   ├── test_scanner.py      ✅ 7 tests
│   ├── test_risk.py         ✅ 7 tests
│   ├── test_backtest.py     ✅ 7 tests
│   └── test_validation.py   ✅ 12 tests
├── config/settings.py       所有門檻參數
├── main.py                  CLI 進入點
├── requirements.txt
└── .env.example
```

```
ORCHESTRATOR（主控）
    ├── ScannerAgent    技術面：RSI、MACD、布林通道、成交量
    ├── SentimentAgent  情緒面：Claude API 新聞分析、Reddit
    ├── RiskAgent       風控：ATR 停損、風報比、流動性
    └── BacktestAgent   回測：3年歷史勝率、獲利因子
            ↓（並行）
    ValidationAgent（三重把關）
            ↓
    最終 JSON 報告 + LINE Flex Message 推播 + Notion 寫入
```

## GitHub Actions 自動排程

每週一至週五台灣時間 **13:35**（台股收盤後）自動執行，無需本機常駐。

支援手動觸發：GitHub repo → Actions → 每日收盤選股分析 → Run workflow

### 必要 Secrets（GitHub repo → Settings → Secrets and variables → Actions）

| Secret | 說明 |
|--------|------|
| `ANTHROPIC_API_KEY` | Claude API 金鑰 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot Token |
| `LINE_USER_ID` | 推播目標用戶 ID |

### 選用 Secrets

| Secret | 說明 |
|--------|------|
| `NOTION_API_KEY` | Notion 整合 Token |
| `NOTION_DB_ID` | Notion 資料庫 ID |
| `NOTIFY_EMAIL` | Email 通知收件地址 |
| `SMTP_USER` / `SMTP_PASS` | Gmail 應用程式密碼 |

## 快速開始（本機執行）

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 設定 API 金鑰
cp .env.example .env
# 編輯 .env 填入所需金鑰

# 3. 立即執行一次
python main.py

# 4. 只輸出 JSON 報告
python main.py --json

# 5. 執行測試
python -m pytest tests/ -v
```

## 驗證門檻

| 項目 | 門檻 |
|------|------|
| 信心分數 | ≥ 65% |
| 停損距離 | ≤ 7% |
| 風報比 | ≥ 2:1 |
| 單檔資金上限 | ≤ 10% |
| 回測最低勝率 | ≥ 50% |

> ⚠️ 本專案資訊僅供參考，不構成任何投資建議。
