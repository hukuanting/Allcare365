# 公開註冊、四級角色與登入修正

更新：2026-10-10。原視覺設計 Goal 保持暫停；此文件記錄使用者另行要求的帳號修正。

## 帳號與角色

公開 API 與 HTML 註冊均建立 active Viewer，可自行設定帳號與密碼後登入。API 不接受申請者指定角色、群組、staff 或 superuser；不在註冊回應簽發 token。Viewer 預設沒有病患綁定、研究權限或寫入權限。

- Viewer：查看明確授權的紀錄，不提供新增、匯入與研究入口。
- Researcher：研究群體摘要、報告申請；不能核准報告。
- Manager：研究審核、資料匯入與病患建檔；既有病患的讀寫仍需要個別授權。
- Admanager：Manager 的功能，加上 Django admin 的 ProductUser 查看／變更和 User 查看。

管理員在 Django admin 的 ProductUser 表單選擇上述角色並儲存，會呼叫 provision_workspace_role，配置 workspace:<role> 群組。Admanager 可進入管理後台，但不是 superuser。降級時移除前一個受管理群組；從 Admanager 降級會撤回這項 staff 存取。獨立手動授予的權限與其他群組保留，若要完整撤權必須一併檢查。既有 legacy 角色不做資料庫批次轉換。

角色名稱本身不授予全部病患存取權；後端個別資料授權仍是依據。Admanager 的臨床資料範圍也受此限制。Researcher、Manager、Admanager 仍須依現有後端設定完成 TOTP MFA。

## 登入介面

一般登入只顯示帳號與密碼。伺服器明確回傳 mfa_required 時顯示六位數驗證器代碼；mfa_enrollment_required 則沿用已實作的設定／驗證流程。沒有新增 Email/SMS 驗證碼服務，也沒有寄送按鈕。風險頁的未核准模型導入清單已撤除。

## 登出修正

- beforeunload 同時涵蓋重新整理與離開頁面，不能判斷是否關閉最後一個分頁。移除該事件中的全域登出，避免重新整理撤銷帳號憑證。
- 新登入重設共同 last-activity timestamp。實際鍵盤／指標／捲動事件更新活動；heartbeat 與 token refresh 不延長閒置期限。
- 15 分鐘閒置後清除前端登入並嘗試通知後端；恢復可見頁面與重新載入均檢查已過期的閒置時間。計時器每 10 秒檢查，正常前景分頁可能最多約 10 秒延遲。這是前端閒置控制，不是新增後端 idle-session enforcement。
- 公開登入／註冊／MFA 的 401 不觸發其他登入的登出。保護 API 的 401 僅在請求所用 bearer 仍是目前憑證時登出，並清除 local auth state。
- 延遲 token refresh 回應不能覆蓋新登入或恢復已登出的帳號。支援 Web Locks 的瀏覽器共用 refresh 鎖，避免同源分頁同時輪替憑證；不支援時仍有單分頁與延遲回應防護。
- 手動登出立即清除前端狀態，再送出後端撤銷請求。後端原有全域登出與 MFA 要求保留。

以上是已由測試重現並修正的程式問題，未宣稱已取得使用者昨天立即登出情境的瀏覽器網路紀錄或證明唯一根因。

## 驗證

- node node_modules/vitest/vitest.mjs run --maxWorkers=2：22 files / 123 tests passed。
- venv/Scripts/python.exe -m pytest tests/test_public_viewer_registration.py tests/test_auth_lifecycle.py tests/test_oauth_browser_security.py --ds=medical_system.settings_security_tests --reuse-db -q：23 passed。使用隔離 test_allcare365_security_v2 資料庫和合成帳號；未建立真實帳號。
- Django manage.py check：通過。
- Vite production build：通過。
- 尚無真實瀏覽器登入、15 分鐘等待或多分頁手動驗收證據。先前 Computer Use 因無法確認瀏覽器 URL 而停止。測試不替代這些證據。

沒有新增 migration；沒有對現有開發／病患資料執行 migrate、seed 或批次角色變更。start_system.bat 可啟動開發服務，也會執行 migrate。若既有後端仍是舊程序，需重新啟動該後端才會載入新 Python 程式。

參考：Django 權限與 admin 語意 https://docs.djangoproject.com/en/5.2/topics/auth/default/ ；beforeunload 行為 https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeunload_event 。
