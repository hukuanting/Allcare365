# 疾病風險平台擴充架構

狀態：正式 runtime 架構契約  
更新日期：2026-07-21

## 1. 目的

疾病風險功能是一套可追溯的確定性臨床規則平台，不是以畫面卡片為中心的公式集合。任何新演算法都必須使用相同的輸入契約、版本規則、臨床審核閘門、FHIR 投影與驗證流程。

## 2. 不可妥協原則

1. 臨床原始值只來自已持久化的 `Patient`、`Encounter`、`Observation`、`Condition` 與 `QuestionnaireResponse`；不得由 production API 產生 mock 值或以預設值補缺值。
2. 缺值必須明確回傳為資料不足，不得轉成 `0`、`false` 或平均值。
3. 演算法是純函式；資料選取、單位轉換、公式計算、結果持久化與 FHIR 投影必須分層。
4. 同一臨床概念只有一個 canonical variable key。Excel cell、醫院欄位名稱與 FHIR code 只能作為來源 alias，不得進入公式 domain model。
5. 每一筆衍生結果都要保存演算法 ID、版本、輸入快照、輸入來源、計算時間與 `Provenance`。
6. `blocked_source_conflict` 不得載入 runtime registry、不得計算、不得出現在臨床 API 或 UI。來源經醫院人工確認後，必須以新的審核版本重新走完整 onboarding，不能直接解除隱藏。
7. `candidate_after_clinical_validation` 只是待審候選，不等於可在 production 啟用。

## 2.1 目前模型盤點

- 正式 runtime catalog：42 項，皆為 `runtime_approved + runtime_enabled`。
- `example/algorithms.json` 保留作來源審核紀錄；`blocked_source_conflict` 不得進入 runtime、API 或 UI。
- `GET /api/health-screening/risk-algorithms/` 回傳依器官系統分類的 42 項正式目錄與計數，但不公開公式內容。
- Golden Patient 可解析全部 42 項：39 項產生分數，3 項依既定族群條件標示 `not_applicable`，且不得有任何資料缺失。

## 3. 分層

```text
FHIR / hospital import / manual entry
  -> canonical clinical persistence
  -> latest-valid-value selection
  -> canonical input + unit normalization
  -> governed algorithm catalog
  -> approved-only deterministic execution plan
  -> result persistence + audit
  -> Observation or RiskAssessment + Provenance
  -> organ-system presentation
```

各層責任如下：

- Ingestion：驗證並保存來源內容，不計算風險。
- Repository：逐欄選取最新有效資料並保留來源，不知道公式係數。
- Input contract：統一變數名稱、型別、單位、LOINC/問卷 alias 與合理範圍。
- Registry：保存產品 catalog 的分類、版本、輸入、輸出與治理狀態；只有 `runtime_approved + runtime_enabled` 能進執行計畫。待審模型可作為不計分的治理卡片呈現，但公式不得被呼叫。
- Formula catalog：`services/disease_risk_engine/formula_catalog.py` 是唯一可執行公式來源；無資料庫、API、FHIR 存取或隱藏 fallback，相同輸入永遠產生相同輸出。
- Runtime calculator：只依公式目錄的顯式 execution plan 執行，並驗證與 registry 的順序、數量及 ID 完全一致。
- Orchestrator：執行適用模型、保存結果、AuditLog 與醫師覆核狀態。
- FHIR projection：指標型結果使用 `Observation`；疾病事件機率使用 `RiskAssessment`；兩者都以 `Provenance` 指向輸入與方法版本。
- Frontend：病患風險結果區只呈現 API 真實執行的 `runtime_approved` 結果並依 `clinical_system` 分區；待審項目放在獨立、預設收合的模型導入清單，不得混成病患缺值或未完成結果。

FHIR 匯入另有獨立來源所有權契約：

- `(resource_type, resource_id)` 是全站唯一 canonical FHIR identity。
- 每筆 `FHIRResource` 必須有 stable `origin_namespace`；不得由單次 Bundle identifier 推測來源醫院。
- 每個 Bundle 在寫入 Patient 前完成整包 ownership preflight，任一碰撞即整批 rollback。
- Patient 識別合併使用 `(identifier.system, identifier.value, origin_namespace)`，禁止裸 MRN 猜測合併。

## 4. Golden Patient 契約

Golden patient 是持久化的 conformance fixture，不是 runtime mock 或一般患者的 fallback。

- 使用固定 UUID、MRN、臨床時間及 `evaluation_as_of=2026-07-15`，確保年齡與風險向量可重現。
- 透過正式 ingestion/persistence 路徑建立 Patient、Encounter、Observation、QuestionnaireResponse 與 FHIR source resources。
- 資料須覆蓋所有 runtime catalog 模型的必填欄位；已核准模型比對凍結 score/category，runtime 治理閘門模型則驗證「未執行、無分數」。
- seed 必須可重複執行，只能更新 golden patient 自己的資料，禁止刪除或修改其他患者。
- 驗證必須涵蓋資料庫資料、canonical snapshot、全部 catalog 結果、FHIR schema、逐欄 basis reference、Provenance、來源 namespace 與 AuditLog。
- golden patient 若失敗，視為資料管線或模型契約回歸；禁止用測試特例繞過。

## 5. 演算法 onboarding

每個新模型依序完成：

1. 醫院確認來源版本、適用族群、公式、閾值及變數編碼。
2. 建立 immutable algorithm ID 與 semantic version。
3. 將每個輸入映射到 canonical variable、標準單位與 FHIR/問卷來源。
4. 實作純函式與 domain/range validation。
5. 建立來源範例 golden case、邊界案例、缺值案例、單位轉換案例。
6. 指定 `clinical_system` 與 FHIR output type。
7. 臨床簽核後才把 catalog 狀態升為 `runtime_approved`，在 `formula_catalog.py` 實作公式並加入唯一 execution plan。
8. 以 golden patient 與至少一個模型適用族群案例跑完整 DB-to-FHIR 回歸。

## 6. 前端分類契約

後端使用穩定代碼，前端負責本地化顯示：

| `clinical_system` | 顯示區域 |
| --- | --- |
| `cardiovascular` | 心臟與心血管 |
| `metabolic_endocrine` | 代謝與內分泌 |
| `hepatic` | 肝臟 |
| `renal` | 腎臟 |
| `neurocognitive` | 神經與認知 |
| `respiratory` | 呼吸系統 |
| `mental_health` | 心理健康 |
| `other` | 其他 |

畫面在尚未選擇病患時先顯示公開模型數量與治理概況；分析後，正式結果區只顯示已核准模型。完整待導入清單仍可展開並依器官系統查看，但不顯示病患分數。區域內不得遺漏任何後端回傳項目；未知分類必須落到 `other`，不能丟棄。

風險 API 必須回傳 `execution_summary`。Golden Patient 的 conformance gate 要求 `resolved_models == executable_models`、`insufficient_data_models == 0` 且 `all_executable_models_resolved=true`。`calculated` 代表產生分數，`not_applicable` 代表輸入完整但不屬於模型適用族群；兩者不得混同。

## 7. 認證與稽核

- USCDI 臨床資料以 FHIR R4 resource 表達。
- SMART on FHIR/OAuth2 scope enforcement 不因風險模組擴充而繞過。
- `patient/*` token 必須綁定持久化 launch/token patient context；沒有 context 時 fail closed，禁止使用第一位患者當預設值。
- Bulk Data 只接受具備逐 resource `system/*` read scope 的 backend-service token，job 必須綁定 OAuth client owner；Group membership 只讀取持久化 FHIR Group。
- 風險衍生資料不得覆寫來源 `Observation`。
- 每次重大資料模型或 projector 變更後重跑相關 FHIR schema、single-patient、SMART 與 Inferno baseline。
- 測試 fixture 可以是合成資料，但只能存在於明確的 seed/test 邊界，production 查詢不得自動回退到 fixture generator。
- `clinical_use_prohibited=true` 的 conformance fixture 預設不進入臨床患者清單與 FHIR 搜尋；只有明確的認證環境旗標可暴露。
