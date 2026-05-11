# 持股匯入快速入門

## 🚀 三步驟快速匯入持股

### 步驟 1：準備持股資料

選擇以下任一格式：

**選項 A：使用 CSV 格式（推薦初學者）**

建立檔案 `my_portfolio.csv`：
```csv
symbol,shares,avg_price,note
2330.TW,100,580,台積電
2454.TW,50,920,聯發科
AAPL,30,185,Apple
NVDA,20,495,NVIDIA
```

**選項 B：使用 JSON 格式**

建立檔案 `my_portfolio.json`：
```json
[
  {"symbol": "2330.TW", "shares": 100, "avg_price": 580, "note": "台積電"},
  {"symbol": "AAPL", "shares": 30, "avg_price": 185, "note": "Apple"}
]
```

### 步驟 2：匯入到系統

```bash
# 從 CSV 匯入
python portfolio_cli.py import --user YOUR_LINE_USER_ID --file my_portfolio.csv --format csv

# 從 JSON 匯入
python portfolio_cli.py import --user YOUR_LINE_USER_ID --file my_portfolio.json --format json
```

### 步驟 3：驗證結果

```bash
# 查看持股清單
python portfolio_cli.py list --user YOUR_LINE_USER_ID
```

輸出：
```
📊 持股清單 (4 檔):

代碼          股數       成本 備註
--------------------------------------------------
2330.TW       100      580.0 台積電
2454.TW        50      920.0 聯發科
AAPL           30      185.0 Apple
NVDA           20      495.0 NVIDIA
--------------------------------------------------
總成本                  110,450
```

## 📱 使用 LINE Bot 分析

完成匯入後，在 LINE 輸入：
```
分析持股
```

系統會自動分析並推送 AI 操作建議！

## 💡 常用指令

```bash
# 匯入（保留現有持股）
python portfolio_cli.py import --user USER_ID --file portfolio.csv --format csv

# 匯入（清空現有持股）
python portfolio_cli.py import --user USER_ID --file portfolio.csv --format csv --clear

# 匯出持股備份
python portfolio_cli.py export --user USER_ID --file backup.csv --format csv

# 查看持股
python portfolio_cli.py list --user USER_ID

# 清空所有持股
python portfolio_cli.py clear --user USER_ID --confirm
```

## 📦 範例檔案

使用內建範例快速開始：

```bash
# 複製範例檔案
cp examples/portfolio_example.csv my_portfolio.csv

# 編輯檔案後匯入
python portfolio_cli.py import --user YOUR_ID --file my_portfolio.csv --format csv
```

## ⚠️ 注意事項

1. **股票代碼格式**
   - 台股：必須加 `.TW` 後綴（例：`2330.TW`）
   - 美股：直接使用代碼（例：`AAPL`）

2. **檔案編碼**
   - 使用 UTF-8 編碼
   - Excel 儲存時選擇「CSV UTF-8」

3. **如何取得 LINE User ID**
   - 在 LINE Bot 中輸入「幫助」
   - 或先使用「新增持股 2330.TW」建立帳號

## 🔍 完整文檔

詳細使用方式請參考：[IMPORT_GUIDE.md](IMPORT_GUIDE.md)

## 問題排查

### 匯入失敗？

檢查檔案格式：
```bash
# 查看檔案內容
head my_portfolio.csv

# 確認編碼
file my_portfolio.csv
```

### 找不到持股？

確認 User ID 正確：
```bash
# 列出所有用戶（需要直接存取資料庫）
cat database/data/portfolios.json | jq 'keys'
```

### 需要更多幫助？

```bash
# 查看指令說明
python portfolio_cli.py --help
python portfolio_cli.py import --help
```
