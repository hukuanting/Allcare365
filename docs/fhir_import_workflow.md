# 臨床資料匯入：FHIR 優先

臨床資料匯入頁預設選取「FHIR（主要）」。FHIR R4 有三種輸入來源，CSV／Excel 留在次要分頁，保留既有檔案預覽與欄位表頭下載。

## 使用方式

- 貼上資料：貼上單一 resource 或 Bundle，JSON／XML 自動辨識。
- 上傳多個檔案：一次選取最多 20 份 UTF-8 檔案，總大小最多 10 MB。依內容辨識，不依副檔名判定。可把 Patient、Encounter、Observation 等分放不同檔案；預覽前先合併。同一 resourceType/id 的相同資料去重，內容或 fullUrl 衝突時拒絕整批。
- FHIR REST API：輸入完整 GET URL，例如 https://trusted.example/fhir/Patient/example/$everything 或搜尋 URL；需要時輸入 Bearer access token。讀取 JSON／XML、跟隨同來源 next 分頁，最多 10 頁、1000 個資源、總大小 10 MB。逾限或任一頁失敗會拒絕整次讀取，不會暗中截斷。

所有來源先點「預覽」，確認摘要再點「確認匯入」。確認時匯入預覽所取得的同一份資源快照，不再重新抓取遠端資料。修改資料、檔案或來源會使預覽失效。預覽只解析結構及來源衝突，不寫入病人資料；完整 relational mapping 檢查仍在既有匯入服務執行，部分資源失敗沿用 HTTP 207 與錯誤清單。

一般 Patient 搜尋只提供人口學資料，不會自動取得全部健檢。需來源支援 Patient/$everything、含所需 Observation／Condition／QuestionnaireResponse 的 Bundle，或先匯出完整相關資源後多檔上傳。此功能是手動 GET 匯入，不是持續同步、SMART OAuth 授權流程或向遠端 POST 寫入。

匯入與預覽均要求 health_screening.import_clinical_records。查看／計算匯入病人的風險仍須病人關係或明確風險權限；匯入不會自動提高權限。

## REST 來源設定

後端環境變數 FHIR_IMPORT_ALLOWED_ORIGINS 為允許連線的精確 origin，包含 scheme、hostname 與 port，多個來源以逗號分隔。例：

    FHIR_IMPORT_ALLOWED_ORIGINS=https://trusted.example,https://second.example:8443

本地 DEBUG 預設允許 http://localhost:8000 與 http://127.0.0.1:8000，正式環境預設不允許任何來源。外部服務須由部署者填入實際可信來源後重新啟動後端。URL 不可含帳密或 fragment；HTTP redirect 與跨來源分頁均拒絕，不會把 token 轉送到另一來源。外部 bearer token 必須透過 HTTPS；本地 loopback 開發例外允許 HTTP。

Access token 僅在此次預覽的 request body 與後端記憶體使用，不寫入資料庫、localStorage 或 sessionStorage；完成或失敗後清除輸入框。後端不自動使用使用者的系統 JWT 存取遠端；填入的是來源服務核發的 token。

匯入仍使用伺服器控制的 FHIR_DEFAULT_ORIGIN_NAMESPACE（本地預設 allcare365:local-ui-import:v1），各來源資料視為同一個受控匯入 inbox。同 ID 來源衝突由既有 ownership 檢查拒絕；本功能不提供多醫院來源命名空間切換。

## API

POST /api/health-screening/fhir-preview/ 接受下列任一輸入：

- JSON body：fhir_data 為 FHIR object 或文字，format 為 auto/json/xml。
- multipart：重複 files 欄位（亦相容 file），UTF-8 JSON／XML。
- JSON body：url、可選 access_token，執行遠端 GET 與分頁。

預覽回傳 fhir_data（正規化 collection Bundle）、totalResources 與 byType。
POST /api/health-screening/fhir-import/ 接受相同來源形式；前端使用預覽回傳的 fhir_data 確认匯入。

## 測試與限制

JSON/XML golden patient 放在 artifacts/golden_patient/golden_patient.fhir.json 與 golden_patient.fhir.xml；可選取其中一份，或同時選取兩份測試去重。兩份均為合成測試資料。

XML 轉換依既有 fhirclient R4 欄位定義保留 singleton arrays、boolean、integer、decimal、資源 wrapper 與 primitive extensions；拒絕未知欄位、錯誤 namespace、DTD、ENTITY 與過深巢狀內容。未宣稱通過完整 HL7 Validator、US Core 或完整術語驗證。

後端測試覆蓋預覽無寫入、多檔跨資源參照、JSON/XML 等價、錯誤檔阻止匯入、權限及 REST 分頁／redirect／跨來源阻擋。遠端讀取使用模擬 HTTP 回應；尚未對實際外部 FHIR 服務做連線驗收。

官方規格：[FHIR R4 XML](https://hl7.org/fhir/R4/xml.html)、[RESTful API](https://hl7.org/fhir/R4/http.html)、[Search](https://hl7.org/fhir/R4/search.html)。
