# 部署方式

## 適用範圍

正式服務採 Django API、React 靜態前端、PostgreSQL、TLS 保護的共用 Redis 與私有物件儲存。API 可部署在 AWS ECS/Fargate、Google Cloud Run，或其他能提供相同網路隔離、金鑰管理、備份與稽核能力的平台。網域可在 Route 53、Cloud DNS 或其他 DNS 註冊商管理；DNS 與 TLS 憑證需指向前端及 API 的 HTTPS 入口。

本專案不會代為建立雲端帳號、網域、資料庫或儲存桶。`render.yaml` 是需要填入正式服務設定的部署範本；Render free 與 Neon free 的組合只適合合成資料展示，不能承載臨床資料。上線前先完成 [Production security rollout](PRODUCTION_SECURITY.md)，並確認雲端合約、資料所在地、加密備份、存取稽核與復原程序符合實際用途。

第一次使用 Google Cloud 的展示版部署步驟見[Google Cloud 部署指南](GOOGLE_CLOUD_DEPLOYMENT.md)。

## 必要服務

- PostgreSQL：私有網路連線、TLS、加密備份、最小權限資料庫帳號。應用程式使用獨立資料庫和帳號。
- Redis：跨 API instances 共用、TLS（`rediss://`），供登入限流及共享快取使用。
- 私有物件儲存：S3 或 GCS bucket，禁止公開存取；只授予應用程式必要的讀寫權。匯出檔有效時間由簽名網址限制，儲存服務另設生命週期規則清理孤兒物件。
- Django API：HTTPS 入口、production settings、健康檢查、中央化且避免記錄 PHI 或 token 的應用程式日誌。
- React 前端：靜態 HTTPS 託管；`VITE_API_URL` 設為 API 的公開 HTTPS 網址。
- 密鑰管理：使用雲端 Secret Manager/Secrets Manager 或部署平台加密環境變數。`SECRET_KEY`、OIDC RSA 私鑰、資料庫密碼、雲端憑證不得提交到 Git。

`medical_system.settings_production` 會在啟動時強制要求設定；完整變數清單見 [`production.env.example`](../deploy/production.env.example)。production 啟動檢查會拒絕非 HTTPS 公開網址、HTTP CORS/CSRF 來源、萬用 host、短 Django secret、無 TLS 的 PostgreSQL URL、不安全 Redis URL、錯誤或弱於 2048-bit 的 OIDC RSA 私鑰，以及非私有儲存設定。

## 上線次序

1. 先建立正式資料庫、TLS Redis、私有 bucket、執行身分、Secrets 與 HTTPS 網域。只允許 API 服務連線資料庫和 Redis；管理介面限定管理網路或身分代理。
2. 以 secret manager 注入 production 環境變數，前端設定正式 API URL。確認 API、前端的 HTTPS 網域分別列入 `ALLOWED_HOSTS`、`CSRF_TRUSTED_ORIGINS` 和精確的 `CORS_ALLOWED_ORIGINS`。不要加入 `*`。
3. 部署版本並執行 `python manage.py check --deploy`、`python manage.py migrate --noinput` 和 `python manage.py collectstatic --noinput`。資料庫 migration 在維護窗口由單一部署工作執行，再啟動或擴增 web instances。
4. 建立第一位管理者：`python manage.py createsuperuser`。管理者第一次進入管理介面時註冊 TOTP MFA；先設定失去第二因素時的人工核身與重新註冊程序，並限制 superuser 數量。
5. 驗證核准一位一般使用者、停用該使用者、舊 access/refresh token 失效、無 MFA 的高權限帳號不能登入，並確認未授權病患資料和 Bulk Data 匯出檔無法讀取。
6. 監控錯誤率、登入失敗、資料庫與 Redis 健康、儲存量和備份工作。設定 `purge_expired_bulk_exports` 定期執行並驗證 bucket lifecycle；保存並定期演練資料庫與物件儲存復原。

上線時所有現存 bearer/session credentials 都應失效。部署者先執行 `python manage.py revoke_all_credentials` 查看只含總數的 dry-run，再安排使用者重新登入的維護時段，執行 `python manage.py revoke_all_credentials --apply`。該命令會撤銷所有帳號憑證，不要連到錯誤的資料庫執行。

## 服務帳號流程

新註冊帳號會停在 pending，不能取得 API token。具備帳號管理權限的管理者可在 Django Admin 核准或停用帳號；停用會撤銷 OAuth、JWT refresh 與版本化 access token。高權限帳號需透過 TOTP 完成 MFA。病患資料授權需另有明確的病患連結或有效照護關係，不會因為有登入帳號或一般 `view_patient` 權限而取得全體病歷。

## 限制

此部署設定與測試不構成 HIPAA、ONC 或其他法規認證，也不取代威脅建模、滲透測試、隱私/法務審查、供應商合約、事故應變及營運復原演練。Bulk Data 目前在 API request 中同步產生快照；大型資料集應在正式擴量前改由受控背景工作執行。前端 bearer token 目前由瀏覽器端管理，仍需搭配 CSP、XSS 防護與弱點掃描。
