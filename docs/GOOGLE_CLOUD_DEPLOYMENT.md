# Google Cloud 部署指南（展示版）

本指南會把系統部署成可供外部人士瀏覽、申請帳號並由開發團隊審核開通的展示版。第一次部署只使用合成資料。專案 README 明確說明此系統不是可承載真實臨床資料的正式醫療服務；Google Cloud 的服務或資安設定不會自行把它變成臨床核可系統。

## 預計架構

- **Firebase Hosting**：提供 React 網站與免費的 `*.web.app` 網址；先不購買自訂網域。
- **Cloud Run**：提供 Django API，使用 `asia-east1`（台灣）區域，沒有流量時可縮到零。
- **Cloud SQL for PostgreSQL**：保存帳號、合成病患資料和系統資料；Cloud Run 透過 Cloud SQL Auth Proxy 掛載的 socket 連線。
- **Memorystore for Redis**：提供共享登入限流與快取，啟用 TLS，只讓 Cloud Run 透過私有網路連線。
- **Cloud Storage**：保存匯入/匯出檔案，開啟統一 bucket 權限與防止公開存取。
- **Secret Manager 與專用執行服務帳號**：保存 Django/OIDC/資料庫密鑰，並只授予 API 需要的存取權。

Cloud Run 使用 Python buildpack 從本機原始碼建置；`Procfile` 指定 Django/Gunicorn 啟動命令。前端建置後由 Firebase Hosting 發佈。Cloud SQL Auth Proxy 會自動加密資料庫連線；Memorystore 的 TLS 用戶端則需信任該 Redis 執行個體的 CA 憑證。GCS 會以 IAM 權限控管私有物件，不使用公開 ACL。[Cloud Run 從原始碼部署](https://docs.cloud.google.com/run/docs/deploying-source-code)、[Cloud SQL 從 Cloud Run 連線](https://docs.cloud.google.com/sql/docs/postgres/connect-run)、[Memorystore TLS](https://docs.cloud.google.com/memorystore/docs/redis/about-in-transit-encryption)、[GCS 統一 bucket 權限](https://docs.cloud.google.com/storage/docs/uniform-bucket-level-access)。

## 開始前的費用與資料限制

Cloud Run 可依請求計費並縮到零；Cloud SQL、Memorystore 與儲存空間則可能在沒有訪客時仍產生費用。建立資源前先在 Cloud Billing 設定預算通知，且檢查各服務的實際設定與估價。一般「提醒型」預算只寄通知，不會自動停掉資源，因此不能當作硬性支出上限。詳見 [Cloud Run 定價](https://cloud.google.com/run/pricing)、[Memorystore 定價](https://cloud.google.com/memorystore/docs/redis/pricing) 與 [Cloud Billing 預算提醒限制](https://docs.cloud.google.com/billing/docs/how-to/budgets)。

## 部署階段

1. 建立專用 Google Cloud 專案、啟用帳單，設定預算提醒；把專案 ID 記下來。不要把任何密碼或私鑰傳到聊天或提交 Git。
2. 在 Windows 安裝 Google Cloud CLI 與 Firebase CLI，以自己的 Google 帳號登入；確認目前選到剛建立的專案。
3. 啟用 Cloud Run、Cloud Build、Artifact Registry、Cloud SQL、Memorystore、Secret Manager、Cloud Storage、Firebase Hosting 與必要的網路服務 API。
4. 建立 API 專用執行服務帳號、Cloud SQL PostgreSQL、具 TLS 的 Memorystore、私有 GCS bucket 和所需密鑰；Cloud SQL 不設定外部授權網段，透過 Cloud SQL Auth Proxy 連線；Redis 只開放在私有 VPC。
5. 部署 Cloud Run API，記下 `run.app` 網址；建立資料庫 migration 工作並執行，接著建立第一位管理者。
6. 以 API 網址設定前端 `VITE_API_URL`，替換 `firebase.json` CSP 中的 `https://api.example.org`，建置並發佈 Firebase Hosting。若要用 SMART on FHIR 連外部院所，須先確認對方網域，再把該 HTTPS 網域加入 CSP 的 `connect-src`；若院所會把系統嵌在 iframe，還要另外依核准的院所網域調整嵌入限制。
7. 驗證 HTTPS、帳號申請待核准流程、管理者 MFA、一般使用者權限、病患資料隔離、匯出檔的私有權限、資料庫備份與錯誤紀錄。確認沒有真實病患資料再分享網址。

每個階段都要先確認前一步的輸出再繼續。Cloud Run 和 Firebase Hosting 的 URL 會依專案而異；資料庫名稱、Redis 私有 IP、bucket 名稱和憑證也必須在建立後使用真實值。第一次設定時不要直接照抄本文件的佔位文字部署。
