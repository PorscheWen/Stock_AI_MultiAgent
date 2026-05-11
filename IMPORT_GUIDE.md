# 持股匯入指南

本文檔說明如何匯入持股資料到系統中。

## 📁 支援的檔案格式

### 1. CSV 格式

**格式說明：**
- 第一行為標題列（header）
- 欄位：`symbol`, `shares`, `avg_price`, `note`
- 編碼：UTF-8

**範例檔案：** [portfolio_example.csv](examples/portfolio_example.csv)

```csv
symbol,shares,avg_price,note
2330.TW,100,580,台積電
2317.TW,200,110,鴻海
AAPL,30,185,蘋果
NVDA,20,495,輝達
```

### 2. JSON 格式

**格式說明：**
- 陣列格式（Array of Objects）
- 欄位：`symbol`, `shares`, `avg_price`, `note`
- 編碼：UTF-8

**範例檔案：** [portfolio_example.json](examples/portfolio_example.json)

```json
[
  {
    "symbol": "2330.TW",
    "shares": 100,
    "avg_price": 580,
    "note": "台積電"
  },
  {
    "symbol": "AAPL",
    "shares": 30,
    "avg_price": 185,
    "note": "蘋果"
  }
]
```

## 🔧 使用方法

### 方法一：使用 CLI 工具（推薦）

CLI 工具提供完整的匯入/匯出功能。

#### 1. 匯入持股

**從 CSV 匯入：**
```bash
python portfolio_cli.py import --user YOUR_LINE_USER_ID --file portfolio.csv --format csv
```

**從 JSON 匯入：**
```bash
python portfolio_cli.py import --user YOUR_LINE_USER_ID --file portfolio.json --format json
```

**匯入並清空現有資料：**
```bash
python portfolio_cli.py import --user YOUR_LINE_USER_ID --file portfolio.csv --format csv --clear
```

#### 2. 匯出持股

**匯出為 CSV：**
```bash
python portfolio_cli.py export --user YOUR_LINE_USER_ID --file my_portfolio.csv --format csv
```

**匯出為 JSON：**
```bash
python portfolio_cli.py export --user YOUR_LINE_USER_ID --file my_portfolio.json --format json
```

#### 3. 查看持股清單

```bash
python portfolio_cli.py list --user YOUR_LINE_USER_ID
```

輸出範例：
```
📊 持股清單 (6 檔):

代碼          股數       成本 備註
--------------------------------------------------
2330.TW       100      580.0 台積電
2317.TW       200      110.0 鴻海
AAPL           30      185.0 蘋果
NVDA           20      495.0 輝達
--------------------------------------------------
總成本                  80900
```

#### 4. 清空持股

```bash
python portfolio_cli.py clear --user YOUR_LINE_USER_ID --confirm
```

### 方法二：使用 Python 程式碼

```python
from database.portfolio_db import PortfolioDB

db = PortfolioDB()
user_id = "YOUR_LINE_USER_ID"

# 從 CSV 匯入
result = db.import_from_csv(user_id, "portfolio.csv", clear_existing=False)
print(f"成功: {result['success']}, 失敗: {result['failed']}")

# 從 JSON 匯入
result = db.import_from_json(user_id, "portfolio.json", clear_existing=False)

# 匯出為 CSV
db.export_to_csv(user_id, "my_portfolio.csv")

# 匯出為 JSON
db.export_to_json(user_id, "my_portfolio.json")

# 批量新增
stocks = [
    {"symbol": "2330.TW", "shares": 100, "avg_price": 580, "note": "台積電"},
    {"symbol": "AAPL", "shares": 30, "avg_price": 185, "note": "蘋果"}
]
result = db.batch_add_stocks(user_id, stocks)
```

## 📋 欄位說明

| 欄位 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `symbol` | ✅ | 股票代碼（台股需加 .TW） | `2330.TW`, `AAPL` |
| `shares` | ❌ | 持股數量（預設 0） | `100` |
| `avg_price` | ❌ | 平均成本（預設 0） | `580.5` |
| `note` | ❌ | 備註說明 | `台積電`, `長期持有` |

## 📌 注意事項

### 股票代碼格式

- **台股**：必須加上 `.TW` 後綴
  - ✅ `2330.TW` （台積電）
  - ✅ `2317.TW` （鴻海）
  - ❌ `2330` （錯誤）

- **美股**：直接使用代號
  - ✅ `AAPL` （蘋果）
  - ✅ `NVDA` （輝達）
  - ✅ `MSFT` （微軟）

### 檔案編碼

- 請使用 **UTF-8** 編碼
- Excel 儲存 CSV 時選擇「UTF-8 CSV」

### 匯入模式

- **預設模式**（`clear_existing=False`）：
  - 保留現有持股，新增匯入的股票
  - 如果股票代碼已存在，會更新資料

- **清空模式**（`clear_existing=True` 或 `--clear`）：
  - 先清空所有持股，再匯入新資料
  - ⚠️ 謹慎使用！會刪除現有所有資料

## 🔄 常見使用情境

### 情境 1：Excel 轉換為 CSV

1. 在 Excel 中整理持股資料
2. 第一列為標題：`symbol`, `shares`, `avg_price`, `note`
3. 另存新檔 → 選擇「CSV UTF-8 (逗號分隔)」
4. 使用 CLI 工具匯入

### 情境 2：備份持股資料

```bash
# 定期備份持股
python portfolio_cli.py export --user USER123 --file backup_$(date +%Y%m%d).csv --format csv
```

### 情境 3：多帳號持股轉移

```bash
# 從 USER1 匯出
python portfolio_cli.py export --user USER1 --file user1_portfolio.csv --format csv

# 匯入到 USER2
python portfolio_cli.py import --user USER2 --file user1_portfolio.csv --format csv
```

### 情境 4：批次更新持股

```python
from database.portfolio_db import PortfolioDB

db = PortfolioDB()

# 準備更新資料
stocks = [
    {"symbol": "2330.TW", "shares": 150, "avg_price": 590, "note": "加碼"},
    {"symbol": "AAPL", "shares": 50, "avg_price": 180, "note": "長期投資"}
]

# 清空舊資料並匯入新資料
result = db.import_from_json(user_id, "updated_portfolio.json", clear_existing=True)
```

## ❓ 常見問題

### Q: 如何取得我的 LINE User ID？

A: 目前需要透過 LINE Bot 互動時由系統記錄。建議先使用 LINE Bot 新增一檔持股，系統會自動建立您的帳號。

### Q: 匯入時發生錯誤怎麼辦？

A: CLI 工具會顯示詳細的錯誤訊息：
```bash
python portfolio_cli.py import --user USER123 --file portfolio.csv --format csv
```

輸出會顯示：
- ✅ 成功筆數
- ❌ 失敗筆數
- 詳細錯誤訊息

### Q: 可以同時管理多個帳號的持股嗎？

A: 可以！每個 User ID 的持股是獨立的：
```bash
# 帳號 A
python portfolio_cli.py list --user USER_A

# 帳號 B
python portfolio_cli.py list --user USER_B
```

### Q: 資料儲存在哪裡？

A: 所有持股資料統一儲存在：
```
database/data/portfolios.json
```

建議定期備份此檔案。

## 🎯 快速開始

1. **下載範例檔案**
   ```bash
   # 複製範例檔案
   cp examples/portfolio_example.csv my_portfolio.csv
   ```

2. **編輯持股資料**
   - 使用 Excel 或文字編輯器修改 `my_portfolio.csv`
   - 填入您的股票代碼、股數、成本

3. **匯入系統**
   ```bash
   python portfolio_cli.py import --user YOUR_LINE_USER_ID --file my_portfolio.csv --format csv
   ```

4. **驗證結果**
   ```bash
   python portfolio_cli.py list --user YOUR_LINE_USER_ID
   ```

5. **使用 LINE Bot 分析**
   - 在 LINE 輸入：`分析持股`
   - 系統會自動分析並推送建議

## 📞 技術支援

如有問題請開 GitHub Issue 或參考 [README.md](README.md)。
