# Production security rollout

這份清單適用於設定正式雲端服務前的應用程式準備。它不代表部署已完成，也不是合規認證。

## 五項已實作的控制

1. **病歷授權**：一般登入權限不再等於看見所有病患。病患端使用明確核准的 `PatientUserLink`；臨床人員使用有效照護關係與逐病患讀寫權限。SMART `user/*` scope 也必須符合相同患者關係；不明病歷關係採拒絕。研究匯入與全體資料分析需各自具備明確權限。
2. **OAuth 瀏覽器保護**：移除舊 CSRF bypass 與全來源 CORS 相容層；Django OAuth consent POST 受 CSRF 驗證，帳密/API credential endpoint 會拒絕未設定的跨來源 Origin。production 僅接受明列的 HTTPS CORS/CSRF 來源。
3. **依賴套件**：`requirements.txt` 固定到已稽核的安全版本，CI 使用 PostgreSQL 跑 migration 與後端測試。Python 和前端相依套件都在 CI 執行漏洞掃描。
4. **停用與 MFA**：待核准的新帳號不能取得 token。管理者核准/停用使用者時會撤銷版本化 access token、OAuth token、JWT refresh token。高權限帳號登入、refresh 和 SMART OAuth consent 都要求 TOTP MFA。前端登入流程支援首次 enrollment。
5. **Bulk Data 匯出**：NDJSON 快照寫入資料庫索引與私有持久化儲存，下載端點逐次驗證 OAuth client 與 scope，不提供公開物件網址；逾期 job 可由 `purge_expired_bulk_exports` 刪除。物件儲存與資料庫沒有跨系統交易，程序遭強制終止仍可能留下孤兒物件，必須另設 bucket lifecycle。

## 第一次部署的建議順序

1. 用新的 production DB；不要把真實資料匯入開發或測試資料庫。以 `medical_system.settings_production` 啟動，依 `deploy/production.env.example` 從 secret manager 注入設定。
2. 單一部署工作執行 `manage.py check --deploy`、`manage.py migrate --noinput` 和 `manage.py collectstatic --noinput`。確認 migration 狀態後才啟動 API instances。
3. 建立第一位 superuser，進管理頁完成 TOTP MFA。先設定失去第二因素時的人工核身與重新註冊程序，限制 superuser 名單；日常操作用具體 Django model permission，不授予 staff 就取得全部 PHI。
4. 若允許使用者自行註冊，逐筆審查 pending 帳號；確認身分和組織後才由 Django Admin 核准。建立/審查病患帳號連結時，先核對本人和病患，再指派 `PatientUserLink`。
5. 切換 production 前，先對正確資料庫執行 `manage.py revoke_all_credentials`，確認輸出只有預期 aggregate counts。安排使用者重新登入的維護時段後執行 `manage.py revoke_all_credentials --apply`，以撤銷部署前所有 JWT/OAuth 憑證。不要在共用正式資料庫以外的環境誤執行。
6. 驗證使用者核准、停用、密碼更改、TOTP、patient A/B 隔離、跨來源 login/consent、OAuth refresh 撤銷和 Bulk file client 隔離。確認正常使用者只能下載仍有效且屬於該 client 的匯出快照。
7. 安排 `purge_expired_bulk_exports` 排程和物件儲存生命週期規則；檢查刪除和下載 log 不包含 bearer token、OTP、個資或 provisioning URI。

## 已知邊界

- Django/DRF 權限仍需依照實際臨床組織設計與人工覆核角色矩陣。建立照護連結是敏感的授權操作，應限制管理權並留下營運稽核紀錄。
- TOTP 種子存於 MFA 裝置資料列；資料庫必須加密、受限存取並備份。遺失第二因素需人工核身、移除舊裝置並重新註冊。
- Bulk export 目前同步生成檔案，不適合沒有容量限制的大型匯出；建議擴量前加上受控 queue、工作者、並行上限和取消/逾時計畫。
- 前端 bearer token 目前存在瀏覽器可存取的儲存空間，因此仍受同源 XSS 影響。正式上線需設定嚴格 CSP、依賴弱點掃描與 XSS 測試；若威脅模型要求抵抗 XSS，需另規劃 HttpOnly cookie/BFF 認證設計。
- 這裡未建立雲端資源、網域、正式資料庫、DNS、私鑰或客戶帳號；也未執行正式 DB migration 或憑證全撤銷。
