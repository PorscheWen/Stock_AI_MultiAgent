# Stock_AI_MultiAgent

持股操作建議系統 - Multi-Agent 架構，提供智能持股分析和操作建議。

## 🎯 主要功能

1. **持股管理** - 透過 LINE Bot 管理個人持股清單
2. **AI 分析** - Multi-Agent 協作：技術面、籌碼面（價量／法人持股代理）、情緒面、風控、回測
3. **操作建議** - Advisor 整體評估：買進／持有／賣出、停損／停利參考、短線／波段／長線持有建議與進出場策略
4. **股價 API** - RESTful API 供第三方軟體查詢股價

## 架構

```
Stock_AI_MultiAgent/
├── .github/workflows/
│   └── stock_analysis.yml   ⏰ GitHub Actions 排程（選用）
├── agents/
│   ├── orchestrator.py      🧠 主控 Agent（並行協調）
│   ├── scanner_agent.py     📡 技術面掃描（RSI/MACD/布林/成交量）
│   ├── sentiment_agent.py   🧬 情緒分析（Claude API）
│   ├── risk_agent.py        ⚖️  風控計算（ATR/停損/風報比）
│   ├── backtest_agent.py    ⚡ 回測驗證（3年歷史勝率）
│   ├── chips_agent.py       🧩 籌碼面（量能／季線／法人持股代理）
│   ├── advisor_agent.py     💡 操作建議（多面向加權、停損停利、持有期間）
│   ├── portfolio_view.py      📋 持股清單（報價、損益、排序）
│   ├── line_handler.py      📲 LINE Bot 指令處理
│   └── line_notifier.py     📨 LINE 訊息推播
├── database/
│   └── portfolio_db.py      💾 持股資料庫管理
├── config/settings.py       ⚙️  配置參數
├── app.py                   🌐 Flask API Server
├── main.py                  🚀 主程式進入點
└── requirements.txt
```

## Multi-Agent 協作流程

```
使用者新增持股（LINE Bot）
        ↓
    資料庫儲存
        ↓
使用者執行「分析持股」
        ↓
ORCHESTRATOR（主控）
    ├── ScannerAgent    技術面：RSI、MACD、布林通道、成交量
    ├── SentimentAgent  情緒面：新聞／社群與綜合情緒
    ├── RiskAgent       風控：ATR、停損、風報比、流動性
    ├── BacktestAgent   回測：歷史勝率、獲利因子
    └── ChipsAgent      籌碼面（代理）：量能結構、季線位置、法人持股（yfinance，非證交所即時主力表）
            ↓（並行）
    AdvisorAgent（整體評估：加權評分、停損／停利、短中長線建議）
            ↓
    JSON 報告 + LINE Flex Message 推播
```

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env` 填入以下必要金鑰：

```env
# LINE Bot 設定
CHANNEL_STOCK_ACCESS_TOKEN=your_line_channel_access_token
CHANNEL_STOCK_SECRET=your_line_channel_secret
CHANNEL_STOCK_USER_ID=your_line_user_id  # 或使用 CHANNEL_STOCK_USER_IDS

# Claude AI
ANTHROPIC_API_KEY=your_anthropic_api_key

# 選用
NOTION_API_KEY=your_notion_api_key
NOTION_DB_ID=your_notion_database_id
```

### 3. 啟動服務

```bash
# 啟動 Flask API Server（LINE Bot + 股價 API）
python app.py

# 或使用 Gunicorn（生產環境）
gunicorn app:app --bind 0.0.0.0:5000
```

### 4. 設定 LINE Bot Webhook

在 LINE Developers Console 設定 Webhook URL：

```
https://your-domain.com/webhook
```

## LINE Bot 指令

透過 LINE 與機器人互動：

| 指令 | 說明 | 範例 |
|------|------|------|
| `新增持股 <代碼>` | 新增持股到清單 | `新增持股 2330.TW`<br>`新增持股 AAPL` |
| `查看持股 [排序] [逆序]` | 名稱、持有成本、參考損益、更新日；可排序 | `查看持股`<br>`查看持股 股數 逆序`<br>`查看持股 依獲利` |
| `刪除持股 <代碼>` | 刪除特定持股 | `刪除持股 2330.TW` |
| `清空持股` | 移除所有持股 | `清空持股` |
| `分析持股` | AI 分析並推播建議 | `分析持股` |
| `股價 <代碼>` | 查詢即時股價 | `股價 NVDA` |
| `幫助` | 顯示指令列表 | `幫助` |

## 持股匯入/匯出

### 使用 CLI 工具

系統提供命令列工具方便批量管理持股：

```bash
# 從 CSV 檔案匯入持股
python portfolio_cli.py import --user YOUR_LINE_USER_ID --file portfolio.csv --format csv

# 從 JSON 檔案匯入持股
python portfolio_cli.py import --user YOUR_LINE_USER_ID --file portfolio.json --format json

# 匯出持股到 CSV
python portfolio_cli.py export --user YOUR_LINE_USER_ID --file backup.csv --format csv

# 查看持股清單（含報價參考損益；--sort / --desc）
python portfolio_cli.py list --user YOUR_LINE_USER_ID
python portfolio_cli.py list --user YOUR_LINE_USER_ID --sort pnl --desc

# 清空所有持股
python portfolio_cli.py clear --user YOUR_LINE_USER_ID --confirm
```

### 檔案格式

**CSV 格式範例：** [portfolio_example.csv](examples/portfolio_example.csv)
```csv
symbol,shares,avg_price,note
2330.TW,100,580,台積電
AAPL,30,185,蘋果
NVDA,20,495,輝達
```

**JSON 格式範例：** [portfolio_example.json](examples/portfolio_example.json)
```json
[
  {"symbol": "2330.TW", "shares": 100, "avg_price": 580, "note": "台積電"},
  {"symbol": "AAPL", "shares": 30, "avg_price": 185, "note": "蘋果"}
]
```

### 快速開始

1. 複製範例檔案：
   ```bash
   cp examples/portfolio_example.csv my_portfolio.csv
   ```

2. 編輯持股資料（使用 Excel 或文字編輯器）

3. 匯入系統：
   ```bash
   python portfolio_cli.py import --user YOUR_ID --file my_portfolio.csv --format csv
   ```

4. 在 LINE 輸入「分析持股」即可取得 AI 建議

📖 詳細說明請參考：
- [匯入功能完整指南](IMPORT_GUIDE.md)
- [快速入門](QUICKSTART_IMPORT.md)

## 股價查詢 REST API

提供 RESTful API 供第三方軟體使用：

### 查詢單一股票

```bash
GET /api/v1/stock/{symbol}
```

**範例：**

```bash
curl https://your-domain.com/api/v1/stock/2330.TW
```

**回應：**

```json
{
  "symbol": "2330.TW",
  "name": "台積電",
  "price": 580.0,
  "change": 5.0,
  "change_pct": 0.87,
  "volume": 25000000,
  "market_cap": 15000000000000,
  "timestamp": "2024-01-15T13:30:00",
  "open": 575.0,
  "high": 582.0,
  "low": 574.0,
  "close": 580.0
}
```

### 批量查詢多檔股票

```bash
GET /api/v1/stocks?symbols=2330.TW,AAPL,NVDA
```

**範例：**

```bash
curl "https://your-domain.com/api/v1/stocks?symbols=2330.TW,AAPL,NVDA"
```

**回應：**

```json
{
  "stocks": [
    {
      "symbol": "2330.TW",
      "name": "台積電",
      "price": 580.0,
      "change": 5.0,
      "change_pct": 0.87
    },
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "price": 185.5,
      "change": -2.3,
      "change_pct": -1.22
    },
    {
      "symbol": "NVDA",
      "name": "NVIDIA Corporation",
      "price": 495.2,
      "change": 8.7,
      "change_pct": 1.79
    }
  ]
}
```

## GitHub Actions 自動排程（選用）

保留原有的 GitHub Actions 功能，可定時自動分析固定的股票清單：

### 必要 Secrets

在 GitHub repo → Settings → Secrets and variables → Actions 設定：

| Secret | 說明 |
|--------|------|
| `ANTHROPIC_API_KEY` | Claude AI API Key |
| `CHANNEL_STOCK_ACCESS_TOKEN` | LINE Bot Access Token |
| `CHANNEL_STOCK_USER_ID` | LINE 推播目標用戶 ID |

## 部署

### Render.com 部署

1. Fork 此專案
2. 在 Render.com 建立新的 Web Service
3. 連接 GitHub repository
4. 設定環境變數（同上）
5. 部署完成後，設定 LINE Webhook URL

### Docker 部署

```bash
# 建立 Docker image
docker build -t stock-ai-multiagent .

# 執行容器
docker run -d \
  -p 5000:5000 \
  -e ANTHROPIC_API_KEY=your_key \
  -e CHANNEL_STOCK_ACCESS_TOKEN=your_token \
  -e CHANNEL_STOCK_SECRET=your_secret \
  stock-ai-multiagent
```

## 技術架構

### Multi-Agent 協作

- **ScannerAgent** - 技術指標分析（RSI、MACD、布林通道、成交量）
- **SentimentAgent** - 使用 Claude AI 與公開資訊分析市場情緒
- **RiskAgent** - 計算 ATR 停損、風報比、流動性
- **BacktestAgent** - 3年歷史數據回測
- **ChipsAgent** - 籌碼面代理分數（量能、價格與季線、法人持股比例等公開欄位）
- **AdvisorAgent** - 技術／籌碼／情緒／風控／回測加權，輸出建議、停損、主要停利與分批停利參考、持有期間（短線／波段／長線）說明

### 操作建議類型

- 🚀 **強力買進** (STRONG_BUY) - 綜合分數高且技術、情緒、籌碼偏多
- 📈 **買進** (BUY) - 綜合評分偏正向
- ✋ **持有** (HOLD) - 多空因素並存，宜控倉觀察
- 📉 **賣出** (SELL) - 評分偏低或籌碼／技術轉弱
- ⚠️ **強力賣出** (STRONG_SELL) - 多面向顯著轉弱

停損／停利價主要依 **RiskAgent** 之波動與風報結構；**AdvisorAgent** 另給分批停利參考價。實際下單請自行判斷。

## 測試

```bash
# 執行所有測試
python -m pytest tests/ -v

# 執行特定測試
python -m pytest tests/test_scanner.py -v
python -m pytest tests/test_risk.py -v
python -m pytest tests/test_backtest.py -v
```

## 注意事項

⚠️ **投資風險警告**

本系統提供的資訊僅供參考，不構成投資建議。投資有風險，請謹慎評估並自行承擔投資決策的責任。

- 股市有風險，投資需謹慎
- 過去績效不代表未來表現
- 建議與專業財務顧問諮詢
- 請勿過度依賴 AI 建議

## 授權

MIT License

## 貢獻

歡迎提交 Pull Request 或開 Issue 討論功能改進！

## 更新日誌

### v2.0.0 (2026-05-11)

- ✨ 重構為持股操作建議系統
- ✨ 新增 LINE Bot 互動功能
- ✨ 新增持股資料庫管理
- ✨ 新增 AdvisorAgent 提供操作建議
- ✨ 新增股價查詢 REST API
- ✨ 支援買進/持有/賣出建議
- ✨ 提供進出場策略建議

### v1.0.0

- 短期爆發股票掃描系統
- GitHub Actions 自動推播
- 🤖 **即時互動**：透過 LINE 接收選股報告
- 📊 **Flex Message**：精美卡片式報告
- ⚡ **指令支援**：
  - `選股` / `分析` / `報告` - 執行選股分析
  - `說明` / `help` - 顯示指令說明

#### 部署 LINE Bot
詳細部署說明請參考 [LINEBOT_DEPLOY.md](LINEBOT_DEPLOY.md)

**LINE Bot ID**: `@799htpuy`

## 驗證門檻

| 項目 | 門檻 |
|------|------|
| 信心分數 | ≥ 65% |
| 停損距離 | ≤ 7% |
| 風報比 | ≥ 2:1 |
| 單檔資金上限 | ≤ 10% |
| 回測最低勝率 | ≥ 50% |

> ⚠️ 本專案資訊僅供參考，不構成任何投資建議。
