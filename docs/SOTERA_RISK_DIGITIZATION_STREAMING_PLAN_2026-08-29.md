# Sotera、疾病風險公式數位化與連續資料架構計畫

狀態：已實作第一階段底層切片；即時臨床警報仍屬設計與治理階段
盤點日期：2026-08-29（Asia/Taipei）
範圍：Sotera ViSi Mobile、教授演算法資料、逐欄最新值、連續資料、公式／AI module、FHIR/ONC/USCDI/LOINC
安全界線：本文件不宣稱 ONC 認證、醫療器材許可延伸、疾病診斷或模型臨床效能

## 1. 結論

1. Sotera 最適合成為 Allcare 365 的「院內連續生理資料來源與原生 primary alarm」，Allcare 365 則負責長期病史結合、研究資料品質、衍生特徵、受治理的疾病風險／AI module、FHIR 追溯與跨時間整合。不要重做或取代 ViSi Mobile 已有的 bedside alarm。
2. 教授資料應視為珍貴的 `source evidence archive`，不是可直接執行的程式碼。90 份檔案已全部建立 SHA-256 與可重現清冊；現有 42 個 runtime 模型維持可用，其餘逐一經來源、版本、單位、族群、測試向量與臨床簽核後才升級，證據不足者保持待審。
3. 使用者提出的 a／b／c 邏輯已落實：在評估時間 `T`，每個欄位各自選擇 `effective_at <= T` 的最新合法值。a 取今年、b 仍可取十年前、c 取三年前；同時回傳每個值距 `T` 的年齡，讓各模型自行套用經核准的 freshness/coherence 規則。
4. 資料庫需要分層調整，但不需要現在整庫重寫。一般臨床事實與低頻數值保留在 relational/FHIR read model；高頻 waveform 放受控 object storage/Parquet；另加 current-value projection、事件 outbox、window feature、AnalysisRun 與 AlertEpisode。
5. 「即時跳動」不等於每個 sample 重跑全部 42 個長期模型。應依欄位反向依賴，只刷新受影響 module，再以 debounce、window、quality gate、hysteresis 與 cooldown 控制。短時間警報應是獨立 module 類型，不應把十年風險公式硬改成即時警報。

## 2. Sotera：事實、推論與尚待合作方確認事項

### 2.1 官方已確認的事實

- ViSi Mobile 是病患穿戴式、無線連續監測平台；可取得 ECG/heart rate、SpO2/pulse rate、respiration rate、skin temperature、NIBP/cNIBP，以及 posture 與基本心律不整分析。Sotera 官方也說明 cNIBP 值每 3 秒更新，且存在首次與至少每 24 小時等重新校正情境。[Sotera FAQ](https://soteradigitalhealth.com/faqs)
- 標準架構是 monitor 經醫院 802.11 連到 ViSi Mobile Appliance/System software，再分送到 Remote Viewing Display。[Sotera FAQ](https://soteradigitalhealth.com/faqs)
- 官方列出的互通能力包括 inbound ADT patient demographics、HL7 ORU vital-sign results、HL7 distributed alarms，以及 raw waveform 傳送；已有 Epic、Cerner、Meditech、HMS/Medhost 或 Capsule 等整合經驗。[Sotera FAQ](https://soteradigitalhealth.com/faqs)
- FDA K180472 的適用範圍是 18 歲以上、醫院型場域（一般內外科、intermediate care、ED）。文件明載 cNIBP 未在 ambulation 中評估；自動心律分析是臨床評估的輔助，治療前需由 clinician review；InSight 是 secondary notification，primary alarm 仍源自 ViSi 裝置。[FDA K180472](https://www.accessdata.fda.gov/cdrh_docs/pdf18/K180472.pdf)

### 2.2 對本系統的合理設計推論

| 使用情境 | Sotera 負責 | Allcare 365 負責 | 優先級 |
| --- | --- | --- | --- |
| 院內連續監測 | 感測、patient-device association、primary alarm、RVD | 收資料、病史結合、二級分析、趨勢與 FHIR lineage | P0 |
| 研究資料／AO | ECG/SCG/PPG 等來源資料 | 去識別、品質檢查、waveform catalog、ground truth/model run 評估 | P0 |
| 長期疾病風險 | 提供近期 vital input | 與 lab、Condition、Questionnaire 等合併後執行受治理模型 | P1 |
| 短時間惡化偵測 | 原生 device alarm 不被取代 | 另建 windowed rule/AI，作 research 或 secondary decision support | P1 |
| 居家醫療 | 目前官方資料不足以證明 K180472 涵蓋 | 只能先規劃研究／其他合格裝置 adapter，不宣稱 ViSi 已獲居家使用許可 | 待法規確認 |

### 2.3 與 Sotera 開會必問的 integration contract

1. HL7 版本、profile、ADT event 範圍與 ORU/OBX 範例；病患建立、轉床、出院、device swap、pause/restart 的狀態機。
2. 傳輸方式與安全：MLLP/TLS、VPN/SecureLink、來源 IP、憑證、ACK、retry、ordering、斷線補送與 idempotency key。
3. numerics 的實際輸出頻率、時間戳精度／時區／NTP、quality flag、missing/null、alarm state 與 calibration event 定義。
4. raw waveform 的介面、授權、格式、channel、sample rate、scale/units、chunk 邊界、clock drift、壓縮與歷史補抓方式。官方只說「能傳送」，不能自行假設即時協定細節。
5. device identity：UDI/serial/firmware、monitor/sensor/cuff 身分、patient-device association 與 de-association 的穩定 identifier。
6. alarm 的 threshold、delay、severity、acknowledgement、silence、cleared/cancelled 語意；Allcare secondary alert 不得造成雙重 primary alarm。
7. non-production appliance/RVD、測試資料、SOW、UAT、升級相容性、support boundary 與 disaster recovery。
8. BAA/DPA、資料權利、保留／刪除、跨境、研究使用、資安通報、遠端維護與完整資安文件。
9. 若合作包含 AO：模型 artifact、pre/post-processing、ground truth 定義、標註者與一致性、適用波形、版本、驗證集、license 及臨床 intended use。

## 3. 目前已完成的 Sotera 基礎

系統已有一條安全的 confidential research import 路徑：來源 identifier 單向 pseudonymize、ZIP CRC/SHA-256、schema/quality 檢查、同 archive idempotency、有效低頻 numerics 落 relational `Observation`，高頻 waveform 保留 Parquet 並只存 coverage metadata，技術品質輸出 `Observation + Provenance`。

目前一個 pilot session 的可檢查結果：

- duration 20.951 小時；
- source numeric rows 129,534；
- imported database observations 124,320；
- raw waveform samples 118,318,932，未逐 sample 寫入一般資料表；
- AO model run / output / ground truth 均為 0，因此目前只能說「資料可分析」，不能說 AO 已驗證。

實作與操作說明：

- `apps/clinical/health_screening/sotera_research.py`
- `apps/clinical/health_screening/sotera_report_service.py`
- `apps/clinical/health_screening/management/commands/import_sotera_session.py`
- `docs/SOTERA_RESEARCH_IMPORT.md`
- `docs/SOTERA_PROFESSOR_EMAIL_REPORT_zh-TW.md`

這條路徑目前是 batch research import，不是已完成的 production real-time interface。

## 4. 教授演算法資料的數位化現況

### 4.1 已建立不可混淆的兩層目錄

- `source evidence manifest`：只盤點來源與可抽取證據，永遠不能直接執行。
- `runtime algorithm catalog`：只有已核准、已測試的 Python formula/module 才能執行。

目前清冊結果：

| 項目 | 數量／狀態 |
| --- | --- |
| 全部檔案 | 90/90 已雜湊，10,519,984 bytes |
| `.xlsx` | 37；其中 30 份抽出 formula cells、7 份無 formula cell |
| Excel formula cells | 6,937；這是儲存格數，不等於 6,937 個獨立疾病模型 |
| `.docx` | 31，已索引文字／表格／math/image/link，仍需逐公式人工核對 |
| legacy `.xls` / `.doc` | 12 / 2，需 lossless conversion 後再審 |
| `.pdf` / `.png` / `.pptx` | 3 / 1 / 1，需視覺與文字交叉審核 |
| 現行 runtime 模型 | 42，皆經 runtime governance gate |
| runtime 缺 method URI | 8，應列為 metadata 補強工作，不代表公式一定錯誤 |
| archive digest | `1b78c1198abc1626416949ea003d753d160a9baffecb0cae1ee1007ba5b8644b` |

產物：

- `services/disease_risk_engine/source_asset_inventory.py`
- `scripts/build_risk_source_manifest.py`
- `docs/risk_model_source_manifest.json`
- `docs/SOURCE_ASSET_ARCHIVE.md`（原始證據檔案留在受控的本機 archive，不進 Git）

原始 Word/Excel/PDF 未被修改。三份 PDF 因本機缺少可用的 PDF rendering/text toolchain，本輪保持 `pdf_requires_text_and_visual_review`，沒有猜測公式。

### 4.2 每一個公式的升級流程

```text
原始檔 SHA-256 + paper DOI/version
  -> 人工確認 outcome、population、horizon、exclusion
  -> 每個 input 對 canonical key + FHIR selector + LOINC/SNOMED + UCUM
  -> 公式、係數、rounding、missing/applicability 的純 Python 實作
  -> paper/example test vector + boundary + unit + missing + not-applicable tests
  -> 獨立 reviewer 重算
  -> clinical owner sign-off
  -> runtime registry promotion
  -> shadow run + FHIR output/Provenance 驗證
```

不能把 Excel 的 cached output 當 ground truth，也不能把 Excel formula 字串自動翻成 Python 後直接上線。需要保存 Excel 版本、工作表／cell、paper 版本與轉譯決策，才能知道 Python 到底對應哪一個來源。

### 4.3 明確保持待審、不可硬加的項目

- Gail breast cancer：缺完整 competing mortality、race/ethnicity table 與 BCRAT 積分流程。
- UKPDS stroke：Version 1/2 與近似檔案互相衝突，需先選官方版本與 test vectors。
- `GFR,45.docx`：方程、outcome 與 subgroup 對應不清。
- NZ Diabetes Cohort：categorical encoding 與 calibration 決策未完整。
- LOAD：race points 不完整且混入其他 dementia index。
- China non-obese NAFLD：equation 截斷／排版有歧義。
- ESCC、FHD Stroke、QRISK/QKidney：缺完整係數或 lookup table。
- Chinese-LAP、部分 VAI/CVAI、肝癌文件：outcome、單位、族群或原始來源仍不足。

這些保留在 evidence/review 層，正是「完整一點，但不勉強強加」的安全做法。

## 5. 逐欄最新值：已實作的精確語意

定義：對 canonical feature `f` 與評估時間 `T`，從病患可見且未失效的候選中，先排除 `effective_at > T`、空值與不可合法換算單位，再選擇最大的 `effective_at`；同時間以來源優先級打破平手。

使用者範例：

| 欄位 | 可用資料 | 選擇 | 額外輸出 |
| --- | --- | --- | --- |
| a | 每年都有 | 今年最新值 | `age_at_evaluation_days` 接近 0 |
| b | 只有十年前 | 十年前那筆 | age 約 3650 天；不偷偷補值 |
| c | 十、五、三年前 | 三年前那筆 | age 約 1095 天 |

重要區分：

- Repository 的責任是忠實選出「當時最新合法值」。因此 b 仍會被選出。
- 是否太舊，要由各 module 的已核准契約決定，例如 `max_age`、`max_input_span`、`same_panel/encounter`、quality minimum 或 source preference；不能用一個全站任意 cutoff 取代論文與臨床判斷。
- 比值與衍生值現在會留下 oldest/newest input age 與 temporal span，避免拿相隔很久的兩個數字卻看不出來。
- 對歷史回放而言，Observation/Questionnaire 已能排除未來資料；但現行 `Problem` table 沒有完整 bitemporal status history，過去某一天的 active/resolved 狀態仍無法完全重建，需在 canonical ledger 階段補強。

已實作位置：

- `services/disease_risk_engine/repository.py`
- `apps/clinical/health_screening/migrations/0011_observation_temporal_lookup_indexes.py`
- `tests/test_risk_repository_temporal_selection.py`

新增 `(patient, code, effective_at DESC)` 與 `(patient, observation_type, effective_at DESC)` 索引；正常 fast path 對每個 exact alias 只檢查最近 64 筆候選。若這批資料全因單位等問題無效，才針對該異常欄位向後分頁，保留「最新合法值」語意。對本機已匯入、含 124,320 筆 Observation 的 Sotera 病患，snapshot 由修改前約 7.46 秒降至約 0.32–0.37 秒；此為本機資料與硬體的觀察值，不是跨環境 SLA。

## 6. 連續資料與即時運算的目標資料流

```text
Sotera appliance / HL7 v2 / waveform receiver
                 |
       ingress validation + identity + idempotency
                 |
      canonical event + transactional outbox
        |                         |
low-rate clinical projection   immutable waveform chunks
(Observation/Condition etc.)   (Parquet/object store + SHA-256)
        |                         |
CurrentClinicalValue         SignalChunk catalog
        |                         |
        +------ window/feature quality pipeline ------+
                              |
                   canonical feature-changed event
                              |
                 reverse module dependency index
                              |
             debounce/coalesce + freshness/applicability
                              |
            governed formula/AI module execution
                              |
        immutable AnalysisRun/Result + AlertEpisode
                  |                         |
      FHIR output + Provenance        UI/WebSocket/approved notification
```

已新增 `services/disease_risk_engine/trigger_planner.py`：輸入變更的 canonical fields，依 42 個 runtime model 的 `required_inputs` 建立 immutable reverse index，只回傳受影響 model，未知 channel 會明確列為 unmapped，不會靜默排程。

尚未直接接上自動 dispatch，原因不是技術做不到，而是 production 需要先具備：

- transactional outbox 與 stable event/idempotency key；
- patient-device association 與 tenant/patient authorization；
- debounce/coalesce 與每個 module 的最小重跑間隔；
- raw quality、calibration、clock drift、missingness 與 out-of-order 處理；
- alert hysteresis、cooldown、acknowledgement、escalation 與 clinical owner；
- primary/secondary alarm 的明確責任與 Sotera UAT。

## 7. 資料庫是否要改：建議分階段新增，不做破壞式重寫

### 7.1 現有資料表可保留的角色

- `Observation`：病患可查詢的低頻／彙整數值與一般臨床事實；不放每個 waveform sample。
- `AIAnalysisJob/Result`：短期保留為現行風險執行 ledger，未來 shadow migrate 到統一 `AnalysisRun/Result`。
- FHIR mapping/resource：作交換、查詢與 provenance projection，不當高頻 time-series engine。
- Parquet archive：目前高頻 waveform 的 immutable source；正式環境移到有 IAM、encryption、retention、object lock/versioning 的 storage。

### 7.2 建議新增的實體

| 實體 | 主要 key／內容 | 用途 |
| --- | --- | --- |
| `DeviceStream` | tenant, patient, encounter, Device/UDI, channel, unit, sample rate, started/ended | patient-device-channel 身分與 session lifecycle |
| `SignalChunk` | stream, start/end, object URI, SHA-256, rows/samples, codec, min/max, quality | 不載入 raw sample 即可定位波形 |
| `CurrentClinicalValue` | patient + canonical feature + context/source preference | O(1) 讀目前值；由 outbox projection 更新，可重建 |
| `FeatureWindow` | patient, feature definition/version, window start/end, statistics, quality | 短時 AI/rule 的受版本控管輸入 |
| `AnalysisRun/Result` | module/artifact version, snapshot hash, idempotency, output, provenance | 統一公式與 AI 的不可變執行帳本 |
| `AlertEpisode` | rule/model, onset, active/ack/cleared, severity, evidence, cooldown | 防止每個 sample 產生新警報 |
| `ClinicalEventOutbox` | aggregate, event type, payload hash, published/checkpoint | DB commit 與事件發送一致性 |

正式 production 應使用 PostgreSQL。當 Observation／numeric stream 量持續成長，再依查詢與保留政策採時間分區；PostgreSQL 原生 declarative partitioning 可先滿足多數需求，是否採 TimescaleDB 應經實際 benchmark 與維運能力決定。[PostgreSQL partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)

## 8. 短時警報與長期風險必須分開

| 類型 | 典型輸入 | 執行節奏 | 必要控制 | 輸出 |
| --- | --- | --- | --- | --- |
| 長期疾病風險 | age、Condition、lab、近期待遇／vital | 相關欄位改變後 debounce；不是每秒 | model-specific freshness、population、horizon | `RiskAssessment` 或 index `Observation` |
| 短時惡化 rule | 近 1–30 分鐘 HR/RR/SpO2/BP trend | sliding/tumbling window | signal quality、hysteresis、cooldown、primary alarm boundary | internal alert episode + governed projection |
| waveform AI | ECG/SCG/PPG chunks | chunk/window 完成後 | artifact digest、sampling/preprocess version、OOD/quality | `AnalysisRun` + derived finding |
| device technical alert | sensor off、network、calibration | event-driven | device semantics、ack/clear state | technical alert，不偽裝疾病風險 |

短時 module 要獨立宣告 `window`、`minimum coverage`、`maximum latency`、`quality`、`threshold`、`hysteresis`、`cooldown` 與 escalation policy。原來的十年／二十年模型不應因接到每秒 heart rate 就每秒重算。

## 9. FHIR、LOINC、USCDI 與 ONC 的正確分工

- FHIR R4 `Observation` 可表達一般 vital/lab/device measurement，並引用 `Device/DeviceMetric`；`valueSampledData` 可表達高頻 device series，但它在 R4 仍是 Trial Use，且不表示一定要把整個原始檔內嵌進資料庫。[FHIR R4 Observation](https://hl7.org/fhir/R4/observation.html)、[FHIR R4 SampledData](https://hl7.org/fhir/R4/datatypes.html)
- `Provenance` 保存產生結果涉及的 entity、process 與 agent，是公式版本、輸入版本與裝置來源可重現的基礎。[FHIR R4 Provenance](https://hl7.org/fhir/R4/provenance.html)
- LOINC `82611-5 Wearable device external physiologic monitoring panel` 可作 wearable vital mapping 的參考，成員包含 HR、temperature、position、activity、respiratory waveform amplitude、HRV、SBP、DBP；仍應依 Sotera channel 真實語意逐項決定 code 與 UCUM，不以 panel 名稱取代測量方法。[LOINC 82611-5](https://loinc.org/82611-5)
- USCDI 是全國交換的資料類別／元素集合，不是 database schema，也不代表 raw waveform 全部都是 USCDI core。版本要和選定的 US Core／SVAP conformance profile 綁定。[USCDI](https://isp.healthit.gov/united-states-core-data-interoperability-uscdi)
- ONC §170.315(g)(10) 聚焦標準化 single/multiple-patient API、FHIR/US Core、SMART 與 Bulk Data 等可測能力；它不替系統決定內部 time-series storage，也不等於即時警報已獲臨床核准。[ONC g(10) test method](https://healthit.gov/test-method/standardized-api-for-patient-and-population-services-acb-atl/)
- FHIR R4 `Subscription` 可做受控的外部 notification，但規格本身是 Trial Use，且要求安全考量；內部高頻 pipeline 應使用可靠 queue/outbox，UI 再用 WebSocket/SSE，不把 Subscription 當 message broker。[FHIR R4 Subscription](https://hl7.org/fhir/R4/subscription.html)

## 10. 分階段執行與停止條件

### Phase A — 已完成的安全底座

- [x] 逐欄在 `T` 以前取最新合法值，排除未來 Observation/Questionnaire。
- [x] 每筆來源回傳 age；衍生值回傳 input temporal span。
- [x] 對 code/type/latest-time 新增索引，連續資料查詢改成 bounded candidates。
- [x] 90/90 教授資產 SHA-256、格式清冊、6,937 個 formula cell evidence。
- [x] runtime/evidence 分離，含糊模型不進臨床執行。
- [x] 欄位到 runtime model 的 reverse dependency planner。
- [x] Sotera research import、quality report、FHIR Observation/Provenance 與前端報告基礎。

停止證據：完整後端測試 `246 passed`；`manage.py check` 無錯誤；`makemigrations --check --dry-run` 無未建立 migration；`git diff --check` 無 whitespace error。

### Phase B — Sotera non-production interface

1. 取得正式 HL7/raw-waveform interface spec 與 sample messages。
2. 建立 `DeviceStream/SignalChunk/outbox` schema 與 adapter contract。
3. 用 synthetic/non-PHI stream 驗證 association、out-of-order、duplicate、disconnect、replay、clock drift 與 calibration。
4. numerics 同時產生 canonical event、current projection 與適當 FHIR Observation；waveform 只產 chunk catalog/reference。
5. 與 ViSi primary alarm 做 UAT，確認 Allcare 不影響裝置原生 alarm。

停止條件：可重播、無重複、無錯病患、斷線可補、來源 hash 可追、延遲與 loss 有量測；未取得 Sotera spec 前不得宣稱 real-time production integration 完成。

### Phase C — 模組化刷新與短時分析

1. module manifest 增加 freshness、coherence、window、quality 與 cadence contract。
2. outbox consumer 使用 reverse dependency planner，只排受影響 module。
3. 實作 debounce/coalesce、idempotent AnalysisRun 與 CurrentClinicalValue projection。
4. 先 shadow-run 一個簡單長期公式與一個無臨床通知的 technical short-window rule。
5. clinical owner 審核 alert episode lifecycle 後，才考慮通知。

停止條件：相同 event replay 不產生重複 run/alert；缺值、舊值、低品質、not-applicable、timeout 各有不同狀態；shadow output 可解釋且有人工簽核。

### Phase D — 教授資料逐模型擴充

每次只處理一個可驗證模型。`method_uri`、適用族群、time horizon、所有係數／lookup、input units、test vectors 與雙人審核缺一不可。證據不足的檔案不以「覆蓋率」為理由強行實作。

停止條件：不是 Python 能跑，而是來源可重建、測試向量通過、臨床 owner 核准、shadow/FHIR/Provenance 全鏈路通過。

## 11. 可重現命令

```powershell
.\venv\Scripts\python.exe scripts\build_risk_source_manifest.py

.\venv\Scripts\python.exe -m pytest `
  tests\test_risk_repository_temporal_selection.py `
  tests\test_risk_trigger_planner.py `
  tests\test_risk_source_asset_inventory.py `
  tests\test_sotera_research_import.py -q

.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

清冊命令只讀教授來源檔並重建 JSON evidence manifest；它不把任何待審公式提升為 runtime model。
