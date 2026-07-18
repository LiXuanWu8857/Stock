# 資安白皮書：股票庫存管理系統

> 版本 0.1（草稿，供討論）｜適用範圍：本 repo 全部元件（Next.js 前端、FastAPI 後端、PostgreSQL、部署環境）
>
> 本文件的定位：**從零建立資安健全網站的設計藍圖與路線圖**。以現有系統的真實缺口為起點，而非泛用理論清單。每一項都標註優先級與落地方式，作為後續開發的依據。

---

## 目錄

1. [目的與範圍](#1-目的與範圍)
2. [現況資安盤點（差距分析）](#2-現況資安盤點差距分析)
3. [威脅模型](#3-威脅模型)
4. [安全設計原則](#4-安全設計原則)
5. [分層防護藍圖](#5-分層防護藍圖)
6. [實施路線圖](#6-實施路線圖)
7. [安全開發流程（SDLC）](#7-安全開發流程sdlc)
8. [附錄：檢查清單與參考標準](#8-附錄檢查清單與參考標準)

---

## 1. 目的與範圍

### 1.1 目的

本系統管理使用者的**投資組合資料**（持股、成本、交易紀錄、資產總額）。這類資料具有高度隱私性與財務敏感性：

- 洩漏 → 曝光個人資產規模與投資行為
- 竄改 → 破壞損益計算，造成錯誤決策
- 刪除 → 損失多年交易紀錄，難以重建

因此資安目標依 CIA 三要素定義：

| 要素 | 目標 |
|------|------|
| 機密性 (Confidentiality) | 只有資料擁有者本人能讀取自己的投資組合 |
| 完整性 (Integrity) | 只有擁有者能新增/修改/刪除自己的資料；所有變更可追溯 |
| 可用性 (Availability) | 服務不因惡意流量或單點故障而中斷；資料可從備份還原 |

### 1.2 範圍

```
Browser ── Next.js 14 (Vercel) ── REST/WS ── FastAPI (Render) ── PostgreSQL (Supabase)
                                                   └── yfinance / TWSE / TPEX（外部報價源）
```

涵蓋：前端、後端 API、WebSocket、資料庫、CI/CD、第三方依賴、部署平台設定。
不涵蓋：使用者端裝置安全、部署平台（Vercel/Render/Supabase）本身的內部安全。

---

## 2. 現況資安盤點（差距分析）

誠實面對現況是一切的起點。以下依嚴重性排列：

### 🔴 嚴重（公開部署後立即可被利用）

| # | 缺口 | 位置 | 影響 |
|---|------|------|------|
| G1 | **API 完全無認證** — 任何人只要知道網址即可呼叫全部 API | `backend/app/main.py`（無任何 auth middleware）、所有 routers | 任何人可讀取、竄改、刪除全部持股與交易紀錄 |
| G2 | **無授權模型** — 所有資料寫死 `user_id=1`，沒有「這筆資料屬於誰」的隔離 | `backend/app/main.py:55`、各 service | 無法多使用者；即使加了登入，資料仍不隔離 |
| G3 | **Swagger UI 公開** — `/docs` 與 `/openapi.json` 對外開放，等於附上攻擊說明書 | FastAPI 預設行為 | 攻擊者可枚舉全部端點與參數格式 |
| G4 | **WebSocket 無認證** — `/ws/quotes` 任何人可連線並訂閱 | `backend/app/routers/quotes.py` | 資源濫用、放大 DoS 面 |

### 🟠 高（放大攻擊面或加重事故後果）

| # | 缺口 | 位置 | 影響 |
|---|------|------|------|
| G5 | 預設資料庫密碼寫在程式碼裡（`postgres:password`） | `backend/app/config.py:6` | 若環境變數漏設，直接以弱密碼連線；也養成壞習慣 |
| G6 | CORS `allow_methods=["*"]`、`allow_headers=["*"]` 且 `allow_credentials=True` | `backend/app/main.py:23-29` | 設定過寬；未來加上 cookie 認證後風險放大 |
| G7 | 無速率限制（rate limiting） | 全部端點 | 暴力嘗試、爬取、資源耗盡皆無門檻 |
| G8 | 無安全性 HTTP 標頭（CSP、HSTS、X-Frame-Options…） | 前後端皆無 | XSS/點擊劫持等攻擊缺少最後防線 |
| G9 | `POST /api/performance/backfill` 等重操作端點無保護 | `backend/app/routers/performance.py` | 任何人可觸發大量外部 API 呼叫與資料重建（DoS 向量） |

### 🟡 中（衛生與流程面）

| # | 缺口 | 影響 |
|---|------|------|
| G10 | 無依賴掃描（CI 中沒有 `pip-audit` / `npm audit`） | 已知 CVE 無法及時發現 |
| G11 | 無 secret 掃描與 pre-commit 防護 | 金鑰誤 commit 難以攔截 |
| G12 | 錯誤處理未統一 — 例外可能將內部細節（stack trace、SQL）洩漏給客戶端 | 資訊洩漏協助攻擊者 |
| G13 | 無結構化安全日誌與告警 | 被攻擊了也不知道 |
| G14 | 無備份與還原演練（依賴 Supabase 免費層的有限備份） | 資料遺失無法復原 |

**結論**：目前系統只適合在「本機或私有網路」運行。在公網部署前，🔴 四項為絕對前置條件（見第 6 章路線圖 Phase 1）。

---

## 3. 威脅模型

### 3.1 資產（我們要保護什麼）

1. **投資組合資料**（持股、成本、交易、每日快照）— 最高價值
2. **使用者身分憑證**（未來的密碼/token）
3. **服務可用性**（API、報價推播）
4. **基礎設施憑證**（DB 連線字串、部署平台 token、CI secrets）

### 3.2 威脅主體（誰會攻擊）

| 主體 | 動機 | 能力 |
|------|------|------|
| 網路掃描機器人 | 無差別掃描公網服務、找開放 API 與已知漏洞 | 自動化、量大、但淺層 |
| 機會型攻擊者 | 發現無認證 API 後竊取/破壞資料 | 會讀 Swagger、寫腳本 |
| 有目標的攻擊者 | 針對特定使用者的資產資訊 | 釣魚、憑證填充（credential stuffing）、社交工程 |
| 惡意/被入侵的依賴套件 | 供應鏈攻擊（npm/PyPI） | 隨依賴更新進入系統 |
| 誤操作的自己人 | 非惡意，但誤刪資料、誤 commit 金鑰 | 最常見的實際事故來源 |

### 3.3 主要威脅情境（STRIDE 對照）

| STRIDE | 情境 | 對應防線（§5） |
|--------|------|----------------|
| **S**poofing 冒充 | 冒用他人身分登入；偽造 API 請求 | 認證（5.1）、token 簽章 |
| **T**ampering 竄改 | 未授權修改持股/交易；中間人竄改流量 | 授權（5.1）、TLS（5.5） |
| **R**epudiation 否認 | 無法追查「誰在何時改了什麼」 | 稽核日誌（5.7） |
| **I**nfo Disclosure 洩漏 | 無認證 API 被讀取；錯誤訊息洩漏內部；DB 外洩 | 認證、統一錯誤處理（5.2）、DB 加密與最小權限（5.4） |
| **D**oS 阻斷 | backfill 端點濫用；WS 連線洪水；報價源被打掛 | 速率限制（5.2）、WS 授權（5.6）、快取 |
| **E**levation 提權 | user A 存取 user B 的資料（IDOR/BOLA） | 資源層授權檢查 + DB Row-Level Security（5.4） |

> **特別注意 IDOR/BOLA**（Broken Object Level Authorization，OWASP API Security Top 10 第 1 名）：本系統的 `PUT /api/holdings/{id}`、`DELETE /api/transactions/{id}` 都以流水號 id 定址，未來多使用者化後，**每一個** 以 id 定址的端點都必須驗證「該資源屬於目前登入者」，缺一不可。

---

## 4. 安全設計原則

之後所有設計決策以下列原則為準（發生衝突時，安全預設優先於便利）：

1. **預設拒絕（Deny by default）** — 每個端點預設需要認證；「公開」是需要明文標註的例外，而不是反過來。
2. **縱深防禦（Defense in depth）** — 不依賴單一防線。例：授權檢查在 API 層做一次，資料庫 RLS 再做一次；即使程式漏寫，DB 仍擋住。
3. **最小權限（Least privilege）** — API 使用的 DB 帳號只擁有必要的 CRUD 權限，不用 superuser；CI token 只給部署所需 scope。
4. **不信任任何輸入** — 所有外部輸入（HTTP body、query、WS 訊息、**外部報價 API 的回應**）都經過 schema 驗證。
5. **秘密不進版本庫** — 一律環境變數/secret manager；程式碼中不得有可用的預設密碼。
6. **失敗要安全（Fail closed）** — 認證服務出錯時拒絕請求，而不是放行。
7. **可觀測** — 安全相關事件（登入失敗、授權拒絕、異常流量）必須留下結構化紀錄。
8. **簡單優先** — 攻擊面與程式碼量成正比。用平台內建能力（Vercel/Render 的 TLS、Supabase Auth/RLS）取代自造輪子。

---

## 5. 分層防護藍圖

### 5.1 身分認證與授權（最優先）

**認證（AuthN）— 你是誰**

- 方案建議：**委外給成熟的身分服務**，不自己儲存密碼。
  - 首選 **Supabase Auth**（已在技術棧內，零額外成本）：Email/密碼 + OAuth（Google）皆支援，核發 JWT，FastAPI 端只需驗證 JWT 簽章（JWKS）。
  - 備選：Auth.js（NextAuth）+ 後端 session、或 Firebase Auth。
- 若未來自行實作密碼：Argon2id 雜湊、密碼最低長度 12、比對 HIBP 外洩清單、登入失敗節流。
- Token 策略：短效 access token（≤1 小時）+ refresh token 輪替；登出即撤銷 refresh token。
- MFA（TOTP）列為第二階段目標。

**授權（AuthZ）— 你能做什麼**

- 資料模型改造：所有資料表已有 `user_id` 欄位概念，補上外鍵與索引，**移除寫死的 `user_id=1`**。
- API 層：FastAPI dependency 統一注入 `current_user`，每個資源操作驗證 `resource.user_id == current_user.id`。
- DB 層（縱深防禦）：啟用 PostgreSQL **Row-Level Security**，policy 限定 `user_id = auth.uid()`（Supabase 原生支援）。即使 API 有漏洞，DB 仍不會跨用戶回資料。

### 5.2 API 安全

- **輸入驗證**：Pydantic schema 全面收緊 — 股數/價格必須 `> 0` 且設上限、`symbol` 用白名單正規表示式（`^[A-Z0-9.]{1,10}$`）、日期不可為未來、字串設最大長度。
- **統一錯誤處理**：全域 exception handler，對外只回標準化錯誤（`{"error": {"code": ..., "message": ...}}`），stack trace 只進伺服器日誌。
- **速率限制**：`slowapi` 或反向代理層限流。一般端點 60 req/min/IP；`backfill`、`snapshot` 等重端點 2 req/min/user；登入端點 5 req/min/IP。
- **生產環境關閉 Swagger**：`docs_url=None, redoc_url=None, openapi_url=None`（以環境變數切換，開發環境保留）。
- **重操作端點**：`backfill` 改為需認證 + 冪等 + 背景任務化，避免同步阻塞被當 DoS 槓桿。
- **HTTP 方法與 CORS 收斂**：CORS 只允許實際使用的方法（GET/POST/PUT/DELETE）與標頭（`Authorization`, `Content-Type`），origin 僅列正式前端網域。

### 5.3 前端安全

- **XSS**：React 預設已跳脫輸出；禁用 `dangerouslySetInnerHTML`；股票名稱等來自外部 API 的字串一律當純文字渲染。
- **安全標頭**（Next.js `headers()` 設定 + 後端 middleware）：
  - `Content-Security-Policy`：`default-src 'self'`，僅放行實際需要的 connect-src（後端 API/WS 網域）
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains`
  - `X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Referrer-Policy: strict-origin-when-cross-origin`、`Permissions-Policy` 關閉不用的能力
- **Token 存放**：優先 HttpOnly + Secure + SameSite=Lax cookie（防 XSS 竊取）；若用 Supabase JS SDK 的預設 localStorage 方案，則以嚴格 CSP 補償，並在白皮書層面明確接受此取捨。
- **CSRF**：採 cookie 認證時必須加 CSRF 防護（SameSite + double-submit token）；純 `Authorization` header 方案則天然免疫。
- **不在前端存任何秘密**：`NEXT_PUBLIC_*` 變數視同公開資訊。

### 5.4 資料庫安全

- **最小權限帳號**：應用程式使用專用 role，只授與業務表的 SELECT/INSERT/UPDATE/DELETE；不得使用 `postgres` superuser。
- **Row-Level Security**：如 5.1，所有含 `user_id` 的表啟用 RLS。
- **SQL Injection**：現況使用 SQLAlchemy ORM 參數化查詢（良好），規範：**永不**字串拼接 SQL；若需 raw SQL 一律 `text()` + bound parameters。
- **傳輸加密**：DB 連線強制 `sslmode=require`。
- **靜態加密**：Supabase 預設磁碟加密；敏感欄位（未來若存 API 金鑰等）再加應用層加密。
- **備份**：每日自動備份 + **每季實際演練還原**（沒演練過的備份等於沒有備份）；MVP 階段至少提供手動 `pg_dump` 匯出腳本。
- **遷移管理**：以 Alembic 管理 schema（已有依賴），停用生產環境的 `create_tables()` 自動建表。

### 5.5 傳輸與基礎設施

- **TLS 全面強制**：Vercel/Render 內建憑證；後端拒絕 http（平台層 redirect）+ HSTS。
- **Secrets 管理**：所有金鑰只存在平台的環境變數/secret 功能；`config.py` 移除可用預設值，改為缺少必要變數即啟動失敗（fail fast）。
- **Docker 強化**：非 root 使用者執行（`USER app`）、多階段建置、pin base image digest、`.dockerignore` 排除 `.env`。
- **最小暴露**：資料庫不開公網（僅允許後端來源）；後端只暴露 443。

### 5.6 WebSocket 安全

- 連線握手時驗證 token（query param ticket 或首則訊息認證），未認證 5 秒內斷線。
- 訊息 schema 驗證：`symbols` 清單長度上限（如 50）、格式白名單。
- 每使用者連線數上限（如 3），總連線數上限，心跳逾時清理。

### 5.7 日誌、監控與事件回應

- **結構化日誌**（JSON）：認證成功/失敗、授權拒絕（403）、資源變更（誰、何時、改了哪筆）、限流觸發。
- **不記錄敏感值**：密碼、token、完整連線字串永不落地日誌。
- **告警**：登入失敗尖峰、5xx 比率、來自單一 IP 的異常流量。免費做法：Render 日誌 + 簡單 cron 檢查 + Line Notify（roadmap 第三階段已規劃 Line 通知，可共用）。
- **事件回應預案**（一頁即可）：發現入侵時的順序 — 撤銷憑證 → 隔離服務 → 保存日誌 → 從備份還原 → 事後檢討。

### 5.8 供應鏈與第三方

- 依賴鎖定：`requirements.txt` 已 pin 版本（良好）、`package-lock.json` 已存在（良好）。
- CI 加入 `pip-audit` 與 `npm audit --audit-level=high`，高危漏洞擋 merge。
- 啟用 GitHub Dependabot（security updates）與 secret scanning。
- 外部報價 API（yfinance/TWSE/TPEX）的回應**視為不可信輸入**：驗證型別與數值範圍後才入庫；對其設 timeout 與失敗降級，避免外部服務異常拖垮本系統。

---

## 6. 實施路線圖

### Phase 0 — 立即（一天內，公網部署前的絕對底線）

| 項目 | 對應缺口 |
|------|----------|
| 生產環境關閉 Swagger（`docs_url=None` 等，環境變數切換） | G3 |
| 移除 `config.py` 中的預設 DB 密碼，必要環境變數缺失即啟動失敗 | G5 |
| CORS 收斂：明列 methods/headers，origin 僅正式網域 | G6 |
| 全域統一錯誤處理，遮蔽內部細節 | G12 |
| 臨時止血：以單一 API key（環境變數 + `Authorization` header 檢查）保護全部端點，作為正式認證上線前的過渡 | G1（過渡） |

### Phase 1 — 認證與授權（1–2 週，核心工程）

| 項目 | 對應缺口 |
|------|----------|
| 導入 Supabase Auth（或選定之替代方案），前端登入流程 + 後端 JWT 驗證 dependency | G1 |
| 資料模型多使用者化：外鍵 + 每端點 ownership 檢查，移除 `user_id=1` | G2 |
| PostgreSQL RLS 上線（縱深第二道） | G2 |
| WebSocket 握手認證 + 訊息限制 | G4 |
| 速率限制（含登入端點嚴格限流） | G7 |

### Phase 2 — 強化（2–4 週，逐步落地）

- 安全標頭全套（CSP/HSTS/XFO…）（G8）
- `backfill` 等重端點背景任務化 + 冪等（G9）
- 輸入驗證全面收緊（schema 上下界、白名單）
- Docker 非 root、DB 最小權限帳號、Alembic 正式接管 schema
- CI：pip-audit、npm audit、Dependabot、secret scanning、pre-commit（G10、G11）
- 備份腳本 + 第一次還原演練（G14）

### Phase 3 — 成熟（持續）

- 結構化安全日誌 + 告警（G13）
- MFA（TOTP）
- 每季：還原演練、依賴大版本更新、自我滲透測試（用 OWASP ZAP 掃一輪）
- 撰寫 `SECURITY.md`（漏洞回報管道）

---

## 7. 安全開發流程（SDLC）

資安不是一次性工程，而是流程：

1. **設計期**：新功能若引入新端點/新資料表，先回答三個問題 — 誰能呼叫？資料屬於誰？最壞情況是什麼？
2. **開發期**：pre-commit hook 跑 secret 掃描（gitleaks）與 linter；遵循本文件 §4 原則。
3. **審查期**：PR 檢查清單（見附錄 8.1）；任何觸及認證/授權的變更需要額外仔細審查。
4. **CI**：測試 + 依賴稽核 + 型別檢查，紅燈不得 merge。**授權測試為必寫項目**：每個資源端點都要有「user A 存取 user B 資料應得 403/404」的測試。
5. **部署期**：secrets 只在平台環境變數；部署後煙霧測試包含「未帶 token 呼叫受保護端點應得 401」。
6. **營運期**：告警值班（個人專案 = Line 通知自己）、每季演練。

---

## 8. 附錄：檢查清單與參考標準

### 8.1 PR 資安檢查清單

- [ ] 新端點是否要求認證？若公開，是否明文註記理由？
- [ ] 以 id 定址的操作是否驗證資源擁有者？
- [ ] 所有輸入是否經 Pydantic/zod schema 驗證（含上下界與長度）？
- [ ] 是否有任何秘密進入程式碼或日誌？
- [ ] 錯誤回應是否洩漏內部細節？
- [ ] 新依賴是否必要？來源是否可信？
- [ ] 是否附上授權測試（跨使用者存取應失敗）？

### 8.2 公網上線前檢查清單（Go-Live Gate）

- [ ] Phase 0 全部完成、Phase 1 認證授權上線
- [ ] HTTPS + HSTS 生效（SSL Labs 測 A 以上）
- [ ] `/docs`、`/openapi.json` 於生產環境回 404
- [ ] 未認證請求全部端點回 401（自動化測試驗證）
- [ ] user A 無法讀寫 user B 資料（自動化測試驗證）
- [ ] 資料庫非 superuser 連線、RLS 啟用、`sslmode=require`
- [ ] 速率限制生效（實測觸發 429）
- [ ] 備份已設定且至少成功還原過一次
- [ ] securityheaders.com 掃描 A 以上

### 8.3 參考標準

| 標準 | 用途 |
|------|------|
| OWASP Top 10 (2021) | Web 應用最常見風險總覽 |
| OWASP API Security Top 10 (2023) | 本系統為 API-first，此清單最貼身（尤其 BOLA） |
| OWASP ASVS 4.0 Level 1 | 具體可驗證的需求清單，本文件多數控制項對應 L1 |
| NIST SP 800-63B | 密碼與認證強度依據（若自建認證） |
| CIS Docker Benchmark | 容器強化依據 |

---

## 待討論的開放決策

以下決策會影響 Phase 1 的實作方向，需要先定案：

1. **使用對象**：確定要開放多使用者註冊？還是永遠只有你自己（＋家人）？→ 若僅自用，Phase 1 可簡化為「單帳號登入 + API 全面要求認證」，RLS 可延後。
2. **認證方案**：Supabase Auth（推薦，已在技術棧內）vs Auth.js vs 自建？
3. **Token 存放**：HttpOnly cookie（較安全、需處理 CSRF）vs Authorization header + localStorage（較簡單、依賴 CSP 防 XSS）？
4. **部署模型**：維持 Vercel + Render + Supabase 免費層？免費層的限制（Render 冷啟動、備份保留天數）是否可接受？
