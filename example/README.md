# 疾病風險演算法整理報告

版本：`1.0.0-draft`  
用途：提供 coding AI agent 建立可追溯、可測試的風險計算模組。  
重要限制：本報告是來源整理與工程規格，不等於臨床核准。所有模型上線前仍需由臨床、法規與產品負責人選定版本、適用族群、門檻與顯示文字。

## 交付內容

- `algorithms.json`：已整理的公式、變數、單位、編碼、適用族群、來源與疑義。
- `algorithm.schema.json`：`algorithms.json` 的 JSON Schema。
- `verification_cases.json`：由原始工作簿範例建立的 regression/golden cases。
- `source_manifest.json`：88 個頂層來源檔案的 SHA-256、大小、推定主題與擷取狀態。
- `duplicate_groups.json`：依正規化公式 fingerprint 找到的 6 組完全相同公式群組。
- `raw/`：86 個 Office／PDF 檔案的逐檔唯讀擷取結果；Excel 保留 sheet、cell 與公式。
- `IMPLEMENTATION.md`：coding agent 的實作與 FHIR 建模要求。
- `KNOWN_ISSUES.md`：不能直接照抄到正式系統的公式與資料問題。

原始檔均未修改。`raw/` 與本報告是新增的衍生資料。

## 整理結果摘要

來源資料共 88 檔：49 個 Excel、33 個 Word、3 個 PDF、1 個 PowerPoint、1 個 PNG，以及 1 個無副檔名檔案。86 個可解析的 Office／PDF 檔均已建立 JSON 擷取檔；PNG 與無副檔名檔只列入 manifest。

`algorithms.json` 的狀態只有以下三種：

- `candidate_after_clinical_validation`：公式與必要變數已足以建立程式及測試，但臨床上線前仍須核准。
- `blocked_source_conflict`：已能描述模型，但來源有缺漏、版本差異或轉錄衝突，禁止直接上線。
- `reference_only`：只有名稱、敘述或不完整表格；目前不足以實作。

沒有任何項目被標成「production ready」，這是刻意的安全設計。

## 優先實作建議

第一批適合建立純函式與單元測試：

1. BMI、TyG、HOMA-IR、QUICKI。
2. FIB-4、RPR、NAFLD Fibrosis Score。
3. 修正後的 HSI、FLI、APRI；必須保留 `correction_reason`。
4. Framingham General CVD 10-year lipid/BMI models。
5. Framingham near-term hypertension model。
6. Cambridge Diabetes Risk Score。
7. UK THIN Dementia Risk Score。
8. NOMAS Global Vascular Risk Score。
9. Mayo solitary pulmonary nodule model。
10. GAD-7。

第二批在補齊原始論文／附錄後再做：

- HUNT Lung Cancer Model：本地 DOCX 遺漏 `log(x+1)` 的 `+1` 以及 logistic probability transform。
- New Zealand DCS：本地 DOCX 在 albuminuria 變數定義處中斷。
- Chinese non-obese NAFLD model：4 年 incidence polynomial 的科學記號已損壞。
- NAFLD CV score：公式完整，但 `DM present=1, absent=2` 是不尋常而且容易被誤改的編碼。

## 尚未升級為結構化演算法的候選

下列來源已完整保留於 `raw/`，但本輪未將它們宣告為可實作模型：

- ACC/AHA ASCVD/Pooled Cohort：`ASCVD-Optimal.xlsx` 有失效外部連結，且 `ASCVDtesting.xlsx` 與整合工作簿版本不完全相同。
- Reynolds Risk Score：男女公式與 baseline survival 分散於 Word/Excel，部分括號位置有錯。
- UKPDS CHD/Stroke：共有四個版本，包含複雜事件率、存活函數及版本差異，需要指定唯一權威版本。
- Framingham 10-year stroke：目前主要是點數表，需將男女、SBP 治療與風險換算表完整正規化。
- Framingham 30-year CVD：`FHS-CVD-30.xls` 有超過 24,000 個公式及大型查表，不宜只從單一輸出 cell 逆推。
- Korea CVD models：`Asia-Korea CVD risk.xlsx` 與 `EastKorea CVD risk.xlsx` 需確認地區、終點及原始論文版本。
- CAIDE、LOAD、BDSI、MCI：資料散落於問卷、Word 表格及整合工作簿，應分別建立獨立量表版本。
- COPD 澳洲風險、Gail 乳癌、Brock 肺結節、QKidney、代謝症候群四種標準：有問卷或規則，但來源版本或公式不足以安全定版。
- GPR、FibroIndex、PLALA、PAAR、Modified NAFIC：工作簿中可見計算草稿，但存在單位或係數疑義。
- 肺功能預測值、理想體重、體脂率及基礎代謝率：屬衍生量測或健康工具，不應和疾病事件風險使用同一輸出語意。

候選清單本身可在 `HRA (清單勾選).xlsx` 的原始擷取檔中查閱；清單上有名稱不表示資料夾內一定含可實作公式。

## Coding agent 使用順序

1. 驗證 `algorithms.json` 符合 `algorithm.schema.json`。
2. 只產生 catalog 中列出的 `id`，不要從檔名自行推測新的公式。
3. 每個演算法實作為 deterministic pure function；輸入先做 unit normalization 和 domain validation。
4. 先讓 `verification_cases.json` 全部通過。
5. 對 `blocked_source_conflict` 不建立模組、不載入 registry，也不加入 API／臨床 UI；待醫院人工審核來源後，以新版本重新走完整 onboarding。
6. 保存 `algorithm_id`、版本、輸入引用、計算時間、輸出及 Provenance。
7. 由臨床負責人簽核適用族群、排除條件、門檻與患者顯示文字後才能 enable。

## 來源交叉核對

關鍵公式已和原始或權威文獻頁交叉核對，包括：

- FLI、HSI、FIB-4、APRI。
- Framingham General CVD 及 hypertension 模型。
- Cambridge Diabetes Risk Score。
- UK THIN Dementia Risk Score。
- NOMAS GVRS。
- New Zealand Diabetes Cohort Study equation。
- Mayo pulmonary nodule model。
- HUNT Lung Cancer Model。
- NAFLD CV Risk Score。

文獻識別資訊保存在各演算法的 `literature` 欄位；引用連結與核對結論列於 `KNOWN_ISSUES.md`。
