# Allcare 365 臨床資料與演算法平台重構計畫

狀態：架構決策草案與分階段實作基線
盤點日期：2026-08-29（Asia/Taipei）
適用範圍：臨床資料、FHIR/SMART API、疾病風險演算法、未來 AI inference、前後端整合
非範圍：本文件不宣稱 ONC 認證，不把目前資料用於真實臨床決策

## 1. 結論

目前系統不適合直接在既有中央 registry 與多套資料表上持續堆疊模型，也不需要一次重寫。建議保留現有良好的輸入驗證、runtime 核准閘門、結果稽核與 FHIR 投影能力，逐步收斂成以下五個穩定邊界：

1. 一條可版本化、可追溯的 canonical clinical write path。
2. 由 canonical data 衍生的 relational read models，供搜尋與大量運算，不允許各模型直接查任意資料表。
3. Feature Resolver，依 FHIR/terminology/time/unit 契約產生不可變輸入快照。
4. Governed Module Platform，以 manifest + adapter + test vectors 個別加入公式或 AI 模型。
5. 同一套結果帳本投影為 FHIR `Observation`、`RiskAssessment`、`DiagnosticReport` 與 `Provenance`，再供內部 UI 與外部 SMART/FHIR API 使用。

先完成護欄與 shadow migration，再逐項搬移 42 個既有模型；禁止直接切換整個資料庫或一次重寫所有 FHIR endpoint。

## 2. 本次故障與立即修正

### 2.1 `風險模型目錄讀取失敗`

故障鏈如下：

```text
GET /api/health-screening/risk-algorithms/
  -> public_algorithm_catalog()
  -> registry_with_review_candidates()
  -> 讀取已移除的 example/algorithms.json + algorithm.schema.json
  -> CatalogSchemaValidationError
  -> HTTP 500
  -> 前端顯示「風險模型目錄讀取失敗」
```

正式產品目錄實際已有 42 個 `runtime_approved + runtime_enabled` 模型；舊 review catalog 沒有提供額外可執行模型。因此已將產品 API 改為只讀取 `runtime_registry()`。離線待審目錄仍可由治理工具顯式載入，但它遺失、封存或暫時格式錯誤時，不再使臨床頁面失效。

驗收基線：

- 已登入請求 `GET /api/health-screening/risk-algorithms/` 回傳 HTTP 200。
- `runtime_catalog_models=42`、`executable_models=42`、`review_candidate_models=0`。
- runtime 目錄測試覆蓋「離線 review loader 故障時產品目錄仍可用」。

### 2.2 OIDC signing key

盤點發現 tracked settings 曾含 RSA private key。已改成由 `OIDC_RSA_PRIVATE_KEY` 注入；development/test 缺值時使用 process-local ephemeral key，production 缺值直接拒絕啟動。舊 key 應視為已暴露並完成撤銷、輪替與部署端 JWKS/consumer 檢查。

### 2.3 認證文字

README 已正確標示 demo，但舊架構文件與公開 API 文件仍使用「ONC-certified」。已改為 `not_certified` 的 certification candidate，避免把開發與測試紀錄誤當第三方認證證據。

## 3. 現況判斷

### 3.1 應保留的能力

| 能力 | 現況價值 | 重構原則 |
| --- | --- | --- |
| Runtime governance | metadata 與 executable formula 分離；enabled 模型必須 approved；42 個模型有完整性檢查 | 搬入 module manifest/schema，不移除核准閘門 |
| Clinical input repository | 有有效時間、來源、單位與缺值處理，不捏造預設值 | 收斂為 Feature Resolver 的資料存取實作 |
| Risk orchestration | transaction 內保存輸入快照、版本、結果、稽核狀態 | 改為 durable job/result ledger 與 idempotency |
| FHIR outputs | 指標可投影 `Observation`，事件機率可投影 `RiskAssessment`，並建立 `Provenance` | 從同一 result ledger 產生，不另建平行結果真相 |
| SMART/OAuth2/OIDC | 已有 patient context、scope、revocation/introspection 等基礎 | 加強 token browser storage、部署金鑰與完整 Inferno 證據 |

### 3.2 主要架構債

| 優先級 | 現況證據 | 風險 | 目標 |
| --- | --- | --- | --- |
| P0 | 產品目錄曾依賴已刪除的 `example` 檔案 | 離線治理資料使線上臨床 API 500 | 線上 runtime 與離線 onboarding 完全分離（已修） |
| P0 | tracked settings 曾含 OIDC private key | token signing trust 已不可證明 | secret manager 注入、輪替、key ID 與 rotation runbook（程式已修） |
| P1 | legacy screening/lab、Encounter/Observation、FHIR JSON/mapping 並存 | 同一事實可能有多個值與不同更新順序 | 單一 canonical write + version history + outbox + derived read models |
| P1 | `BaseProjector.project_batch()` 驗證失敗只記 warning，仍回傳 resource | 可把已知不符合契約的資料交給客戶端 | certification surface fail closed；內部資料進 quarantine |
| P1 | FHIR `ModelViewSet` 搭配弱 serializer 可直接 create/update/delete | 形成未經 profile/terminology/ownership 驗證的第二寫入路徑 | g10 read surface 與 validated ingestion/transaction 分離 |
| P1 | Bulk export job 放在 process-global dictionary | restart、多 worker 或 deploy 後 job 遺失 | DB durable job + queue + object storage + owner/scope/idempotency |
| P1 | browser 將 access/refresh token 放在 `localStorage` | XSS 可讀取 bearer token | Authorization Code + PKCE；內部 UI 優先 BFF/HttpOnly session 或 memory token |
| P2 | registry、formula catalog、ingestion、FHIR views 各自為大型中央檔案 | 新增模型/資源需修改多處且衝突率高 | module package、adapter registry、application services、窄 view |
| P2 | LOINC mapping 散落於 ingestion、projector、seed 與測試 | code/display/version 漂移，難以重現 | versioned terminology package/service + mapping provenance + `$validate-code` |
| P2 | 舊 `RiskAssessment*` 與目前 `AIAnalysisJob/Result` 並存 | lifecycle 與查詢語意重複 | 建立統一 `AnalysisRun/Result`，shadow migrate 後再退役舊表 |
| P2 | capability、artifact、文件混用 US Core 7、USCDI v6 與「certified」字樣 | 無法證明到底測哪一個 conformance target | 一份 versioned `ConformanceProfile` 生成所有宣告與測試矩陣 |

本機資料庫只讀盤點顯示：968 位 Patient、962 筆 Encounter、140,840 筆新 Observation；同時仍有 963 筆 legacy screening 與 11,958 筆 legacy lab。舊風險結果表各只有 1 筆，而 `AIAnalysisJob=44`、`AIAnalysisResult=776`。這不是資料正確性的證明，但足以顯示 migration 不能假設舊表或新表可直接刪除。

## 4. 標準與合規基線

使用者所寫的「LONIC」應為 **LOINC**。FHIR、USCDI、US Core、LOINC 是不同層次，不能只在 model field 或文件寫上名稱就視為合規：

- FHIR R4 定義 resource 與 REST 語意。
- US Core 指定美國情境的 profile、Must Support 與 search 行為。
- USCDI 指定要可交換的資料類別與元素。
- LOINC 是 observation/document 等臨床概念的 terminology；版本必須隨選定 conformance target 固定。
- SMART App Launch 定義 authorization/discovery/scope 行為。
- ONC certification criteria 定義可驗收的產品能力與證據。

截至 2026-08-29，官方 g(10) test method 的基準仍列 FHIR R4.0.1、US Core 6.1.0、USCDI v3 與 Bulk Data STU1，並要求 single/multiple patient API、Must Support、基本 provenance、search、registration、SMART security 與公開文件。2026 SVAP 另外允許 g(10) 選用 USCDI v6 + US Core 9.0.0。對新的 certification target，本計畫建議明確選用後者，同時把法規基準作回歸 profile；不得在同一 CapabilityStatement 混稱 US Core 7 + USCDI v6 + 其他版本。

參考：

- [ONC §170.315(g)(10) Standardized API test method](https://healthit.gov/test-method/standardized-api-for-patient-and-population-services-acb-atl/)
- [ONC 2026 Standards Version Advancement Process](https://healthit.gov/certification-health-it/certification-criteria/standards-version-advancement-process-svap/)
- [USCDI v6（2025-07）](https://isp.healthit.gov/sites/default/files/2025-07/USCDI-Version-6-July-2025.pdf)
- [US Core 8.0.1 official implementation guide](https://hl7.org/fhir/us/core/STU8.0.1/)
- [LOINC FHIR terminology service](https://cdn.loinc.org/kb/api/fhir)
- [ONC g(10) Inferno test suite](https://fhir.healthit.gov/suites/g10_certification)

`RiskAssessment` 在 FHIR R4 仍是 Trial Use resource；它適合表達事件風險、prediction/probability/time horizon、basis、method 與 performer，但不能把所有衍生值都硬塞成 RiskAssessment。一般量測或 index 使用 `Observation`；完整判讀可使用 `DiagnosticReport`；模型 artifact 或說明可由 `DocumentReference` 連結。每筆衍生輸出必須以 `Provenance.target` 指向結果，並以 `entity`/`agent` 保存輸入版本與演算法/Device 身分。

參考：[FHIR R4 RiskAssessment](https://hl7.org/fhir/R4/riskassessment.html)、[FHIR R4 Provenance](https://hl7.org/fhir/R4/provenance.html)。

對 predictive AI/ML，ONC §170.315(b)(11) 不只要求「可以 inference」。產品需支援可存取及維護的 source attributes，並對 supplied Predictive DSI 建立 validity、reliability、robustness、fairness、intelligibility、safety、security、privacy 的 risk analysis、mitigation 與 governance。這些欄位和證據應成為 module governance record，不應只存在 README。

參考：[ONC Decision Support Interventions test method](https://healthit.gov/test-method/decision-support-interventions/)、[ONC DSI Resource Guide](https://www.healthit.gov/wp-content/uploads/2024/05/DSI-Criterion-Resource-Guide_508.pdf)。

## 5. 目標架構

```text
FHIR / HL7 v2 / CSV / device / manual entry
                    |
             Ingress adapters
                    |
   identity + profile + terminology + unit validation
                    |
       Versioned Clinical Resource Ledger
          |             |              |
   source history   transactional    raw waveform/artifact
   + validation       outbox          object storage + hash
                        |
          Relational read models / search index
                        |
                 Feature Resolver
       (FHIR selectors + effective time + UCUM)
                        |
             Immutable FeatureSnapshot
                        |
            Governed Module Registry
                        |
       Formula worker / ONNX worker / container worker
                        |
          Immutable AnalysisRun + Result ledger
              |                    |
  Observation/RiskAssessment/      Audit, DSI feedback,
  DiagnosticReport + Provenance    monitoring and review
              |
     FHIR R4 + SMART API / internal application API
              |
          React clinical workflow
```

### 5.1 Canonical clinical data

`Versioned Clinical Resource Ledger` 是唯一臨床寫入權威，至少保存：tenant、patient、resource type/id/version、origin namespace、source identifier、effective time、recorded time、FHIR payload 或無損 source payload、profile validation result、terminology version、content hash、supersedes/deleted state。

演算法不直接掃描 JSON ledger，也不直接依賴 legacy tables。Outbox consumer 產生適合查詢的 typed projections，例如 Patient、Encounter、Observation/Condition read model。任何 projection 可重建；ledger 與 hash/version reference 才能重現輸入。若組織最後決定 relational domain model 是權威，也必須維持相同的「單一寫入 + immutable history + lossless source + derived FHIR」契約，不能繼續雙向互寫。

高頻 waveform 不宜逐 sample 存成一般 relational row。原始檔放 object storage，保存 SHA-256、格式、取樣率、裝置、時間範圍與 access policy；FHIR 以 `Observation.valueSampledData`、`Media` 或 `DocumentReference` 表達可交換的 metadata/reference，依 use case 選擇。

### 5.2 Feature Resolver

每個 module 只宣告需要的 clinical concepts，不知道 Django model、SQL table 或 HTTP endpoint。Resolver 負責：

- resource/profile 與 terminology selector；
- patient/encounter/tenant boundary；
- effective-time、lookback window、latest/mean/min/max 等 aggregation；
- UCUM unit conversion、range 與 data-quality flag；
- missingness/applicability，不以 `0` 或平均值補值；
- 回傳 source resource version/reference 與 immutable snapshot hash。

輸入快照建議 schema：

```json
{
  "snapshot_id": "sha256:...",
  "patient_ref": "Patient/123",
  "as_of": "2026-08-29T10:00:00Z",
  "features": {
    "systolic_bp": {
      "value": 128,
      "unit": "mm[Hg]",
      "source": "Observation/abc/_history/4",
      "effective": "2026-08-28T03:00:00Z"
    }
  }
}
```

### 5.3 演算法／AI module contract

每一個 module 是獨立 package 或 artifact，不再把所有 metadata 與公式追加到單一 Python tuple：

```text
risk_modules/<module-id>/
  manifest.yaml
  adapter.py
  tests/test_vectors.json
  README.md
```

AI 權重通常存 model registry/object storage；repository 只保存 immutable URI、digest、signature、license、SBOM 與 validation evidence，不提交大型或機敏權重。

`manifest.yaml` 至少包含：

| 區塊 | 必要內容 |
| --- | --- |
| Identity | immutable ID、semantic version、kind（formula/python/onnx/container）、artifact digest |
| Governance | draft/validated/clinical-approved/enabled/retired、owner、reviewers、approval/effective/retirement dates |
| Intended use | clinical purpose、population、exclusions、contraindications、care setting、使用者與禁止用途 |
| Inputs | FHIR profile/resource、code system/code/version、unit、range、lookback、aggregation、missingness |
| Outputs | name/type/unit/range、FHIR output resource/profile、interpretation/category |
| Evidence | bibliography、developer/funder、training data description、external/local validation、limitations |
| Predictive DSI | validity、reliability、robustness、fairness、intelligibility、safety、security、privacy evidence/status |
| Runtime | adapter ABI、timeout、CPU/memory、network policy、determinism/seed、supported platform |
| Monitoring | calibration/drift thresholds、review cadence、rollback version、feedback channel |

統一介面：

```python
class AnalysisModule(Protocol):
    def applicability(self, snapshot: FeatureSnapshot) -> Applicability: ...
    def execute(self, snapshot: FeatureSnapshot, context: RunContext) -> ModuleResult: ...
    def explain(self, result: ModuleResult) -> Explanation: ...
```

限制：

- module 不得直接連 DB、FHIR API 或任意 network；只接收 snapshot。
- deterministic formula 必須純函式；AI worker 必須固定 artifact digest、runtime image、pre/post-processing version 與可設定 seed。
- `clinical-approved + enabled` 才能進 production execution plan。
- timeout、OOM、invalid output、missing input 與 not-applicable 是不同狀態，不能都變成「計算失敗」。
- module 的測試向量包含正常、boundary、missing、unit-conversion、not-applicable 與 literature/reference case。

### 5.4 執行與結果

所有公式與 AI 都建立 durable `AnalysisRun`，建議 idempotency key 為：

```text
tenant + patient + module_id + module_version + feature_snapshot_hash + requested_use
```

快速公式可以在 request 內完成，但仍寫同一種 job/run record；較慢 AI 由 queue worker 執行。結果 immutable，覆核或更正以新 version/supersedes 表達，不覆寫原始輸入。每個 run 保存：requester/purpose、module/artifact/runtime version、snapshot、timestamps、status/error taxonomy、output、explanation、review、FHIR target 與 Provenance ID。

### 5.5 API 邊界

- 外部 USCDI/患者存取：FHIR R4 + SMART scopes，依選定 US Core profile 驗證。
- 內部 workflow API：可以保留 `/api/patients/` 與 `/api/health-screening/`，但必須呼叫相同 application services，不得形成第二套臨床寫入真相。
- FHIR read/search 與 transaction/ingestion 分開授權。若未正式支援 FHIR write，應停用 inherited create/update/delete。
- API output、CapabilityStatement、SMART discovery、公開文件與 Inferno fixture 必須由同一 `ConformanceProfile` 版本產生。

## 6. 分階段遷移與停止條件

### Phase 0：故障與安全止血（本次）

- [x] 線上風險目錄與離線 review catalog 解耦。
- [x] 新增缺檔 regression test，42 個 runtime 模型仍可列出。
- [x] 移除 tracked OIDC private key，production 改為 required secret。
- [x] 修正公開「已認證」文字。
- [ ] 人工完成舊 OIDC key rotation 與 consumer/JWKS 驗證。

停止條件：endpoint HTTP 200/42 models、後端檢查與關聯測試通過；若 key 未輪替，不得宣稱 security incident 已結案。

### Phase 1：Conformance 與 runtime guardrails

1. 建立 immutable `ConformanceProfile`（建議候選：FHIR R4.0.1、US Core 9.0.0、USCDI v6、SMART/Bulk 指定版本、terminology releases）。
2. CapabilityStatement、SMART docs、profile URL、mapping 與 test artifact 由該 profile 生成。
3. FHIR projector 改為 fail-closed/quarantine，加入 profile validator evidence。
4. FHIR generic write 改成 read-only，或導向完整 transaction validation service。
5. Bulk Data job 持久化；實作 owner/scope、restart recovery、expiry、cancel 與 object cleanup。
6. 規劃 browser token 從 `localStorage` 遷移至 BFF/HttpOnly 或 memory + PKCE。

停止條件：無混合版本宣告；invalid fixture 不會被 API 回傳；bulk job 跨 process/restart 可恢復；安全回歸測試通過。

### Phase 2：Canonical data spine

1. 建立/強化 versioned ledger、validation record、outbox 與 projection checkpoint。
2. 先遷移 Patient/Encounter，再遷移 Observation；waveform 採 metadata/reference pattern。
3. 對 legacy 與新 read model 做 shadow read，逐 patient/resource 比較 code、value、unit、time、status 與 source hash。
4. 所有寫入改走一條 service 後才停止 legacy dual-write；保留可回滾版本。
5. 依資料量規劃 Observation partition/index/retention，不用 FHIR JSON 做全表分析查詢。

停止條件：選定資料類型連續通過 reconciliation；所有 projection 可由 ledger 重建；沒有未記錄的 direct write；才可逐表標記 legacy read-only/retired。

### Phase 3：Module platform

1. 定義並驗證 manifest JSON Schema、adapter ABI、sandbox policy、module CLI 與 test-vector runner。
2. 先遷移一個簡單 deterministic module（例如 BMI）與一個複雜既有 score，確認同輸入/同版本/同輸出。
3. 若已有合格且可驗證的 AI artifact，再遷移一個 AI module；若沒有，只驗證 AI adapter，不產生假的臨床模型或結果。
4. 雙跑舊/新 engine，比較全部狀態、數值、rounding、category 與 FHIR output。
5. 逐批遷移 42 個模型，中央 tuple 僅作 compatibility adapter，完成後退役。

停止條件：golden vectors、property/boundary tests、shadow runs 與 clinical reviewer sign-off 均通過；任何 mismatch 未解釋前不得切流量。

### Phase 4：AI lifecycle 與 DSI governance

1. Model registry、artifact signature/digest、runtime image/SBOM、資料與 preprocessing lineage。
2. Local validation、calibration、subgroup fairness、drift、out-of-distribution、human override 與 rollback。
3. DSI source attributes 可由授權使用者檢視/維護，所有修改留 audit history。
4. 建立 validity、reliability、robustness、fairness、intelligibility、safety、security、privacy 的 risk register 與 mitigation evidence。

停止條件：每個 enabled predictive module 有可稽核 source attributes、risk controls、monitoring/rollback owner；缺證據的 module 保持 disabled。

### Phase 5：Certification evidence

1. 對選定 conformance profile 執行官方 Inferno suite，保存 suite/version/config、raw result、失敗與重跑證據。
2. 完成公開 API 文件、SMART client registration、accessibility、security、quality management 與 real-world testing 所需證據。
3. 由認證機構完成正式流程；取得可核對紀錄後才更新產品文字。

停止條件：不是「測試看起來會過」，而是有可查驗的正式 certification evidence。

## 7. 建議的第一個實作切片

下一個安全切片應集中在 Phase 1，而不是立刻搬資料或全部拆 module：

1. 新增單一 `ConformanceProfile` 與 version-drift tests。
2. 將 projector warning-only 改為可設定的 strict/quarantine policy，先在 certification endpoint strict。
3. 將 FHIR generic mutation 關閉或導向 validated ingestion。
4. 建立 durable BulkExportJob model 和 migration，保留現有 API contract。
5. 補 endpoint/integration tests，再開始 canonical data ADR 與 shadow migration。

這個切片的輸出可直接驗收，也不需要先破壞現有 42 個風險模型或使用者目前的資料。
