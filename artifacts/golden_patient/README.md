# Golden patient 匯入試用

本資料全部合成，不是真實病人。個案為 65 歲男性，既有糖尿病及高血壓、已戒菸；病歷號為 SYNTHETIC-GOLDEN-20261010-001，姓名 Golden Synthetic (TEST ONLY)。健檢時間為 2026-10-10。

## 試用

1. 使用更新後的後端啟動系統（若伺服器未自動重新載入，重啟後端）。
2. 登入具備 health_screening.import_clinical_records 的帳號，進入健檢資料匯入的 FHIR 分頁（貼上資料或上傳多個檔案）。
3. 開啟同目錄 golden_patient.fhir.json，複製整份 JSON 貼入，或上傳 golden_patient.fhir.json／golden_patient.fhir.xml；先預覽再確認匯入；不可貼 verification.json。
4. 由匯入成功提示進入風險分析，或搜尋病歷號 SYNTHETIC-GOLDEN-20261010-001，選取此病人後執行風險分析。
5. 預期 42 個模型全部得到可判讀狀態：39 個有分數、3 個不適用，缺資料模型 0 個。分數、指數、量表與預測機率的意義不同，請依各模型輸出類型閱讀。

Viewer 不具匯入權限。Manager / Admanager 的匯入授權也不代表可查看任意病人的風險：風險 API 仍要求合法病人關係或明確的 patients.run_all_patient_risk_assessments 權限，合成 Bundle 不會自動授權。驗收測試明確授予匯入與全病人風險測試權限。

## 內容與來源

FHIR R4 collection Bundle，共 35 個資源：1 Patient、1 Encounter、31 Observation（含血壓組件）、1 Condition、1 QuestionnaireResponse。涵蓋目前模型需要的 116 個快照欄位，包括人口學、人體測量、代謝與肝腎檢驗、血球、用藥、病史、生活習慣、認知與 GAD-7 問卷、肺結節及基因相關輸入。這是完整引擎測試資料；一般健檢未必包含所有這些項目。

以專案現有 build_golden_patient_bundle 為基礎，另建獨立資源 ID、UUID 與病歷號，避免碰撞既有保留的 conformance patient。統一為曾吸菸、目前不吸菸、已戒菸 8 年；保留 18 pack-years。AST ULN、GGT ULN 與肺結節直徑採本系統自訂碼，未假冒 LOINC。AST ULN 新增明確 allcare365-ast-uln 映射；既有 1916-6 相容路徑未在此任務移除，但該碼實際是 AST/ALT 比值，不應用於新資料。

FHIR 結構參考：https://hl7.org/fhir/R4/bundle.html 、https://hl7.org/fhir/R4/observation.html 、https://hl7.org/fhir/R4/questionnaireresponse.html 。LOINC 碼查證：https://loinc.org/1916-6/ 。此驗收使用 fhirclient strict 資源結構解析；未宣稱通過完整 HL7 Validator、術語服務或 US Core profile 驗證。問卷 canonical URL 為本系統輸入契約，不是公開可下載的標準問卷。

## 匯入設定

medical_system/settings.py 現在讀取 FHIR_DEFAULT_ORIGIN_NAMESPACE。DEBUG 開發模式預設為 allcare365:local-ui-import:v1；正式環境預設空白，須由部署者設定穩定可信來源。來源由伺服器決定，Bundle 不會指定或覆寫。不要任意變動同一來源的 namespace。

## 驗收與重現

verification.json 包含交付檔 SHA-256、來源程式 SHA-256、模型版本、116 欄位快照、42 個模型實際輸出與狀態。全部經隔離測試資料庫的公開 FHIR 匯入與風險 API 產生，未寫入本地開發資料庫，未完成瀏覽器人工驗收，也沒有預先塞入風險結果。3 個不適用模型為 framingham_diabetes、ausdrisk_diabetes（既有糖尿病）及 reynolds_risk_score_women_10y（男性）。單一自洽病人不能同時適用所有互斥族群模型。

在專案根目錄重新生成輸入（不寫入資料庫）：

    venv\Scripts\python.exe artifacts\golden_patient\build_bundle.py

驗收（使用獨立 security test DB）：

    venv\Scripts\python.exe -m pytest tests/test_trial_golden_patient_import.py --ds=medical_system.settings_security_tests --reuse-db -q

設定環境變數 EXPORT_TRIAL_GOLDEN_REPORT=1 後執行測試，可重新輸出 verification.json。年齡依實際運算日期計算；未來日期、模型或輸入版本改變，分數可能改變，請對照驗收記錄。無隨機資料生成；ID 由 UUIDv5 決定。
