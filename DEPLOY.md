# 部署教學：Vercel（前端）+ Railway（後端 + PostgreSQL）

整體架構：

```
使用者瀏覽器
   ↓
Vercel        ← frontend/ (Next.js)，免費
   ↓ HTTPS / WSS
Railway       ← backend/ (FastAPI)，每月 $5 免費額度
   ↓
Railway PostgreSQL
```

> 注意：GitHub Pages 只能放靜態網頁，無法執行 FastAPI 後端與資料庫，
> 所以本系統不能部署在 `*.github.io`。部署完成後建議到
> Repo Settings → Pages 關閉 GitHub Pages。

---

## 事前準備

1. 把開發分支合併進 `main`（Vercel / Railway 預設追蹤 main）：
   - 到 GitHub 開 Pull Request：`claude/dazzling-pasteur-ql7r5c` → `main`，按 Merge。
2. 註冊帳號（都可以直接用 GitHub 登入）：
   - https://railway.app
   - https://vercel.com

---

## 第一步：Railway 部署後端 + 資料庫

1. 進入 Railway → **New Project** → **Deploy PostgreSQL**
   建立完成後會自動產生一個 Postgres 服務。

2. 在同一個專案按 **+ New** → **GitHub Repo** → 選 `LiXuanWu8857/Stock`

3. 點進剛建立的服務 → **Settings**：
   - **Root Directory** 填 `backend`
   - Builder 會自動偵測到 Dockerfile（`backend/railway.toml` 已設定好）

4. 切到 **Variables** 分頁，新增兩個環境變數：

   | 變數 | 值 |
   |------|-----|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}`（Railway 變數引用，自動連到同專案的 Postgres） |
   | `CORS_ORIGINS` | 先填 `http://localhost:3000`，等 Vercel 部署完再回來改 |

5. **Settings → Networking** → **Generate Domain**，會拿到一個網址，例如：
   `https://stock-backend-production-xxxx.up.railway.app`
   **記下這個網址**，下一步要用。

6. 驗證：瀏覽器開 `https://你的railway網址/health`，
   看到 `{"status":"healthy"}` 就成功了。
   也可以開 `/docs` 看 Swagger API 文件。

---

## 第二步：Vercel 部署前端

1. 進入 Vercel → **Add New** → **Project** → Import `LiXuanWu8857/Stock`

2. 設定：
   - **Root Directory**：點 Edit 改成 `frontend`
   - **Framework Preset**：自動偵測為 Next.js，不用改

3. 展開 **Environment Variables**，新增：

   | 變數 | 值 |
   |------|-----|
   | `NEXT_PUBLIC_API_URL` | `https://你的railway網址`（第一步第 5 點拿到的，**結尾不要加斜線**） |

4. 按 **Deploy**，完成後會拿到網址，例如：
   `https://stock-xxxx.vercel.app`

---

## 第三步：回頭設定 CORS

1. 回到 Railway 後端服務 → **Variables**
2. 把 `CORS_ORIGINS` 改成你的 Vercel 網址：
   ```
   https://stock-xxxx.vercel.app
   ```
   （多個來源用逗號分隔，例如要保留本機開發：
   `https://stock-xxxx.vercel.app,http://localhost:3000`）
3. Railway 會自動重新部署。

---

## 完成檢查清單

- [ ] `https://railway網址/health` 回傳 healthy
- [ ] 開啟 Vercel 網址，Dashboard 正常顯示
- [ ] 右上角顯示「即時報價連線中」（WebSocket 透過 WSS 連線成功）
- [ ] 新增一筆持股（如 `2330`），表格出現即時價格
- [ ] GitHub Repo Settings → Pages → Source 改為 **None**（關閉空白的 Pages）

---

## 費用說明

| 服務 | 免費額度 | 備註 |
|------|---------|------|
| Vercel | Hobby 方案免費 | 個人使用綽綽有餘 |
| Railway | 每月 $5 試用額度 | 後端 + Postgres 小流量約 $3–5/月 |

如果想完全免費，後端也可改部署到 Render（免費方案會休眠，
第一次打開要等約 30 秒喚醒）。

---

## 之後更新程式怎麼部署？

push 到 `main` 之後，Vercel 和 Railway 都會**自動重新部署**，不用做任何事。
