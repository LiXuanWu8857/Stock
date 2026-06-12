# 股票庫存管理系統 (Stock Portfolio Manager)

個人 / 小團隊使用的台股 + 美股投資組合管理系統，支援即時報價。

## 功能（第一階段 MVP）

- 記錄買入：股票代號、買入日期、買入價格、買入股數
- 自動計算：即時股價、持股市值、損益、報酬率、總投資金額、資產配置比例
- 台股（如 `2330`、`00878`）與美股（如 `AAPL`）統一管理，自動偵測市場
- WebSocket 即時報價推播（每 30 秒更新，斷線自動重連）
- 交易紀錄（買入 / 賣出），自動以加權平均法更新持股成本

## 技術架構

```
Browser
   ↓
Next.js 14 + Tailwind CSS  (frontend, port 3000)
   ↓  REST + WebSocket
FastAPI                    (backend, port 8000)
   ↓
PostgreSQL 16              (port 5432)
   ↓
yfinance                   (台股 .TW / 美股報價，免費、無需 API key)
```

## 快速啟動（Docker）

```bash
docker compose up --build
```

- 前端 Dashboard：http://localhost:3000
- 後端 API 文件（Swagger）：http://localhost:8000/docs

## 本機開發

### 後端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 修改 DATABASE_URL 指向你的 PostgreSQL
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### 資料庫

啟動 PostgreSQL 後執行 `database/schema.sql`（使用 Docker 時會自動初始化）。
後端啟動時也會透過 SQLAlchemy 自動建表。

## API 一覽

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/holdings` | 持股清單 + 即時價格 + 投資組合摘要 |
| POST | `/api/holdings` | 新增持股（重複代號自動加權平均） |
| PUT | `/api/holdings/{id}` | 更新持股 |
| DELETE | `/api/holdings/{id}` | 刪除持股 |
| GET | `/api/transactions` | 交易紀錄（可用 `?symbol=` 篩選） |
| POST | `/api/transactions` | 新增交易（自動更新持股成本） |
| DELETE | `/api/transactions/{id}` | 刪除交易紀錄 |
| GET | `/api/quotes/{symbol}` | 單一股票即時報價（`?market=TW\|US`，可自動偵測） |
| WS | `/ws/quotes` | 即時報價推播，傳入 `{"symbols": ["2330:TW", "AAPL:US"]}` |

## 資料表

- `users` — 使用者（MVP 為單一使用者 id=1）
- `holdings` — 持股（symbol、market、shares、avg_cost）
- `transactions` — 交易紀錄（BUY / SELL、價格、股數、日期）
- `dividends` — 配息紀錄（第二階段使用）

## Roadmap

- **第二階段**：多次買進成本攤平 ✅（已內建加權平均）、配息紀錄、股票分割、匯率換算、美股盤前盤後、ETF 分析
- **第三階段**：技術指標、AI 分析、個股新聞、財報摘要、股價警示通知（Line Notify）

## 報價來源說明

MVP 使用 [yfinance](https://github.com/ranaroussi/yfinance)：免費、無需 API key、同時支援台股（自動加 `.TW` 後綴）與美股。延遲約 15 分鐘，對庫存管理已足夠。未來如需更即時的報價，可替換 `backend/app/services/stock_service.py` 為 Finnhub（美股 WebSocket）+ 台灣證交所 OpenAPI，介面已抽象化，不需改動其他程式。
