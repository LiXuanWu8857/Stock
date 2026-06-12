# 部署教學：Vercel（前端）+ Render（後端）+ Supabase（資料庫）

全部免費，三個服務都可以用 GitHub 帳號直接登入。

```
使用者瀏覽器
   ↓
Vercel          ← frontend/ (Next.js)  — 永久免費
   ↓ HTTPS / WSS
Render          ← backend/ (FastAPI)   — 免費，閒置 15 分鐘後休眠
   ↓
Supabase        ← PostgreSQL           — 永久免費 500MB
```

> **注意**：GitHub Pages 只能放靜態網頁，無法執行 FastAPI 後端與資料庫，
> 所以本系統不能部署在 `*.github.io`。部署完成後請到
> Repo Settings → Pages → Source 改為 **None**，關閉那個空白頁面。

---

## 事前準備：把分支合併進 main

Vercel / Render 預設追蹤 `main` 分支，先把開發分支合進來：

1. 到 GitHub → 這個 Repo → 點 **Pull requests** → **New pull request**
2. base: `main`，compare: `claude/dazzling-pasteur-ql7r5c`，按 **Create pull request** → **Merge**

---

## 第一步：Supabase 建立資料庫（約 3 分鐘）

1. 前往 https://supabase.com，用 GitHub 登入
2. **New project** → 填 Project name（如 `stock-db`）、設一個 Database Password（記下來）、選離你最近的 Region
3. 等建立完成（約 1 分鐘）後，進入專案 → 左側 **Settings** → **Database**
4. 找到 **Connection string** → 選 **URI** → 複製，長這樣：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```
   把 `[YOUR-PASSWORD]` 換成你剛設的密碼，**整串複製備用**。

> 一週內沒有任何請求時 Supabase 免費方案會暫停 DB，但資料不會刪。
> 只要打開 Supabase 後台按 Restore 就能恢復（部署後正常使用不會觸發）。

---

## 第二步：Render 部署後端（約 5 分鐘）

1. 前往 https://render.com，用 GitHub 登入
2. **New** → **Web Service** → 選 `LiXuanWu8857/Stock`
3. 設定：
   - **Name**：`stock-backend`（隨意）
   - **Root Directory**：`backend`
   - **Runtime**：Docker（自動偵測 Dockerfile）
   - **Instance Type**：Free
4. 展開 **Environment Variables**，新增兩個：

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | 第一步複製的 Supabase 連線字串 |
   | `CORS_ORIGINS` | 先填 `http://localhost:3000`，等 Vercel 部署完再改 |

5. 按 **Create Web Service**，等部署完成（約 3–5 分鐘）。

6. 部署完成後頁面上方會顯示你的網址，例如：
   ```
   https://stock-backend-xxxx.onrender.com
   ```
   **記下這個網址**，下一步要用。

7. 瀏覽器開 `https://stock-backend-xxxx.onrender.com/health`，
   看到 `{"status":"healthy"}` 就成功了。

---

## 第三步：Vercel 部署前端（約 3 分鐘）

1. 前往 https://vercel.com，用 GitHub 登入
2. **Add New** → **Project** → Import `LiXuanWu8857/Stock`
3. 設定：
   - **Root Directory**：點 Edit 改成 `frontend`
   - **Framework Preset**：自動偵測為 Next.js，不用改
4. 展開 **Environment Variables**，新增：

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | `https://stock-backend-xxxx.onrender.com`（第二步的網址，**結尾不加斜線**） |

5. 按 **Deploy**，完成後會拿到網址，例如：
   ```
   https://stock-xxxx.vercel.app
   ```

---

## 第四步：回頭設定 CORS（最後一步）

1. 回到 Render → 你的 stock-backend 服務 → **Environment**
2. 把 `CORS_ORIGINS` 的值改成 Vercel 網址：
   ```
   https://stock-xxxx.vercel.app
   ```
   如果也想保留本機開發，用逗號分隔：
   ```
   https://stock-xxxx.vercel.app,http://localhost:3000
   ```
3. 按 **Save Changes**，Render 會自動重新部署。

---

## 完成檢查清單

- [ ] 關閉 GitHub Pages：Repo → Settings → Pages → Source → **None**
- [ ] `https://stock-backend-xxxx.onrender.com/health` 回傳 `{"status":"healthy"}`
- [ ] 開啟 Vercel 網址，Dashboard 正常顯示（不是白屏）
- [ ] 右上角顯示「即時報價連線中」（WebSocket WSS 連線成功）
- [ ] 新增一筆持股（如 `2330`），表格出現即時價格

---

## 費用說明

| 服務 | 費用 | 限制 |
|------|------|------|
| Vercel Hobby | 永久免費 | 個人使用無限制 |
| Render Free | 永久免費 | 閒置 15 分鐘後休眠，首次請求喚醒約 30 秒 |
| Supabase Free | 永久免費 | 500MB，1 週無請求自動暫停（資料保留，手動恢復） |

對個人庫存管理來說 30 秒 cold start 完全可以接受。
若想要秒開，可升級 Render 到 $7/月方案（不休眠）。

---

## 之後更新程式怎麼部署？

push 到 `main` 之後，Vercel 和 Render 都會**自動重新部署**，不用做任何事。
