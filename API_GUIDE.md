# API 使用範例

本文檔提供股價查詢 API 的詳細使用範例。

## 基本資訊

- **Base URL**: `https://your-domain.com`
- **API Version**: v1
- **回應格式**: JSON
- **認證**: 不需要（公開 API）

## 端點列表

### 1. 查詢單一股票

取得指定股票的即時價格和詳細資訊。

**請求：**

```http
GET /api/v1/stock/{symbol}
```

**參數：**

| 參數 | 類型 | 說明 | 範例 |
|------|------|------|------|
| symbol | string | 股票代碼（路徑參數） | 2330.TW, AAPL, NVDA |

**範例請求：**

```bash
# 查詢台積電
curl https://your-domain.com/api/v1/stock/2330.TW

# 查詢 Apple
curl https://your-domain.com/api/v1/stock/AAPL

# 查詢 NVIDIA
curl https://your-domain.com/api/v1/stock/NVDA
```

**成功回應 (200 OK)：**

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

**錯誤回應 (404 Not Found)：**

```json
{
  "error": "Stock not found"
}
```

**錯誤回應 (500 Internal Server Error)：**

```json
{
  "error": "Error message here"
}
```

### 2. 批量查詢多檔股票

一次查詢多檔股票的價格資訊。

**請求：**

```http
GET /api/v1/stocks?symbols={symbol1},{symbol2},{symbol3}
```

**參數：**

| 參數 | 類型 | 說明 | 範例 |
|------|------|------|------|
| symbols | string | 股票代碼列表（逗號分隔） | 2330.TW,AAPL,NVDA |

**範例請求：**

```bash
# 查詢多檔股票
curl "https://your-domain.com/api/v1/stocks?symbols=2330.TW,AAPL,NVDA"

# 只查詢台股
curl "https://your-domain.com/api/v1/stocks?symbols=2330.TW,2317.TW,2454.TW"

# 只查詢美股
curl "https://your-domain.com/api/v1/stocks?symbols=AAPL,MSFT,GOOGL,NVDA"
```

**成功回應 (200 OK)：**

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

**錯誤回應 (400 Bad Request)：**

```json
{
  "error": "Missing symbols parameter"
}
```

## 股票代碼格式

### 台股

台股代碼需加上 `.TW` 後綴：

- 台積電: `2330.TW`
- 鴻海: `2317.TW`
- 聯發科: `2454.TW`
- 廣達: `2382.TW`

### 美股

美股直接使用代號：

- Apple: `AAPL`
- Microsoft: `MSFT`
- NVIDIA: `NVDA`
- Tesla: `TSLA`
- Meta: `META`

## Python 範例

```python
import requests

# 單一股票查詢
def get_stock_price(symbol):
    url = f"https://your-domain.com/api/v1/stock/{symbol}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"{data['name']} ({data['symbol']})")
        print(f"價格: ${data['price']}")
        print(f"漲跌: {data['change']:+.2f} ({data['change_pct']:+.2f}%)")
    else:
        print(f"錯誤: {response.json().get('error', 'Unknown error')}")

# 批量查詢
def get_multiple_stocks(symbols):
    url = f"https://your-domain.com/api/v1/stocks"
    params = {"symbols": ",".join(symbols)}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        for stock in data["stocks"]:
            if "error" not in stock:
                print(f"{stock['symbol']}: ${stock['price']} ({stock['change_pct']:+.2f}%)")
    else:
        print(f"錯誤: {response.json().get('error', 'Unknown error')}")

# 使用範例
get_stock_price("2330.TW")
get_multiple_stocks(["AAPL", "NVDA", "TSLA"])
```

## JavaScript 範例

```javascript
// 單一股票查詢
async function getStockPrice(symbol) {
  const url = `https://your-domain.com/api/v1/stock/${symbol}`;
  
  try {
    const response = await fetch(url);
    const data = await response.json();
    
    if (response.ok) {
      console.log(`${data.name} (${data.symbol})`);
      console.log(`價格: $${data.price}`);
      console.log(`漲跌: ${data.change >= 0 ? '+' : ''}${data.change} (${data.change_pct >= 0 ? '+' : ''}${data.change_pct}%)`);
    } else {
      console.error(`錯誤: ${data.error}`);
    }
  } catch (error) {
    console.error(`請求失敗: ${error.message}`);
  }
}

// 批量查詢
async function getMultipleStocks(symbols) {
  const url = `https://your-domain.com/api/v1/stocks?symbols=${symbols.join(',')}`;
  
  try {
    const response = await fetch(url);
    const data = await response.json();
    
    if (response.ok) {
      data.stocks.forEach(stock => {
        if (!stock.error) {
          console.log(`${stock.symbol}: $${stock.price} (${stock.change_pct >= 0 ? '+' : ''}${stock.change_pct}%)`);
        }
      });
    } else {
      console.error(`錯誤: ${data.error}`);
    }
  } catch (error) {
    console.error(`請求失敗: ${error.message}`);
  }
}

// 使用範例
getStockPrice('2330.TW');
getMultipleStocks(['AAPL', 'NVDA', 'TSLA']);
```

## 回應欄位說明

### 單一股票回應欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| symbol | string | 股票代碼 |
| name | string | 股票名稱 |
| price | number | 目前價格 |
| change | number | 漲跌金額 |
| change_pct | number | 漲跌百分比 |
| volume | number | 成交量 |
| market_cap | number | 市值 |
| timestamp | string | 資料時間戳記 (ISO 8601) |
| open | number | 開盤價 |
| high | number | 最高價 |
| low | number | 最低價 |
| close | number | 收盤價 |

### 批量查詢回應欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| symbol | string | 股票代碼 |
| name | string | 股票名稱 |
| price | number | 目前價格 |
| change | number | 漲跌金額 |
| change_pct | number | 漲跌百分比 |

## 注意事項

1. **資料來源**: 使用 yfinance 作為資料來源
2. **更新頻率**: 即時資料，但可能有 15-20 分鐘延遲
3. **速率限制**: 目前無速率限制，但請勿過度頻繁請求
4. **資料準確性**: 僅供參考，請勿作為投資決策依據

## 常見問題

### Q: 為什麼查詢失敗？

A: 請檢查：
- 股票代碼是否正確
- 台股是否加上 `.TW` 後綴
- 網路連線是否正常

### Q: 資料多久更新一次？

A: 資料為即時查詢，但可能有 15-20 分鐘延遲（取決於 yfinance）。

### Q: 支援哪些市場？

A: 目前支援：
- 台灣股市 (需加 .TW 後綴)
- 美國股市
- 其他 yfinance 支援的市場

### Q: 有速率限制嗎？

A: 目前沒有硬性限制，但建議合理使用，避免過度頻繁請求。

## 技術支援

如有問題請開 GitHub Issue 或聯繫維護團隊。
