# Stock AI MultiAgent - GitHub Actions 推播模式

## ⚠️ 重要變更

本專案已改為 **GitHub Actions 自動推播模式**，不再接受 Webhook 互動。

### 已停用功能
- ❌ Flask Webhook 處理（`app.py` 僅保留健康檢查）
- ❌ Render.com 部署
- ❌ LINE Bot Webhook 互動

### 新架構
- ✅ GitHub Actions 自動排程
- ✅ 台灣時間每週一至週五 13:35 自動執行
- ✅ LINE Push API 主動推播

## 🚀 快速開始

### 1. 本機執行

```bash
# 安裝依賴
pip install -r requirements.txt

# 執行分析並推播  
python main.py
```

### 2. GitHub Actions 設定

#### 必要 Secrets
在 GitHub repo → Settings → Secrets and variables → Actions 中設定：

| Secret | 說明 |
|--------|------|
| `ANTHROPIC_API_KEY` | Claude AI API Key |
| `CHANNEL_STOCK_ACCESS_TOKEN` | LINE Bot Access Token |
| `CHANNEL_STOCK_USER_ID` | LINE 推播目標用戶 ID |
| `NOTION_API_KEY` | Notion API Key（選用）|
| `NOTION_DB_ID` | Notion Database ID（選用）|

#### Workflow 檔案
`.github/workflows/stock_analysis.yml` 已設定完成

#### 執行時間
- **自動執行**：週一至週五台灣時間 13:35（收盤後）
- **手動觸發**：GitHub repo → Actions → Stock AI 每日選股分析推播 → Run workflow

## 📊 系統架構

```
GitHub Actions Workflow
    ↓
執行 main.py
    ↓
OrchestratorAgent 協調各 Agent
    ├── Scanner Agent (選股)
    ├── Validation Agent (驗證)
    ├── Risk Agent (風險評估)
    ├── Backtest Agent (回測)
    └── Sentiment Agent (情緒分析)
    ↓
LINE Push API 推播報告
```

## 📁 專案結構

```
├── .github/workflows/      # GitHub Actions
│   └── stock_analysis.yml  # 主要 workflow
├── agents/                 # 各功能 Agent
├── config/                 # 設定檔
├── reports/                # 分析報告
├── main.py                 # 主程式進入點
├── app.py                  # 簡化版 Flask（僅健康檢查）
└── requirements.txt        # Python 依賴
```

## 🔧 開發說明

### 本機測試推播

```bash
# 確保 .env 已設定
CHANNEL_STOCK_ACCESS_TOKEN=your_token
CHANNEL_STOCK_USER_ID=your_user_id
ANTHROPIC_API_KEY=your_api_key

# 執行
python main.py
```

### 查看分析報告

報告會儲存在 `reports/report_YYYYMMDD_HHMMSS.json`

## ❓ 常見問題

### Q: 如何更改推播時間？
A: 編輯 `.github/workflows/stock_analysis.yml` 中的 cron 表達式

### Q: 如何手動觸發？
A: GitHub repo → Actions → 選擇 workflow → Run workflow

### Q: 為何移除 Render 部署？
A: GitHub Actions 提供免費的定時執行，無需額外的伺服器成本，且更容易維護

## 📞 支援

如有問題請查看 GitHub Issues 或聯繫維護者
