# 醫院核定風險模型正式導入稽核（2026-07）

## 決策與範圍

- `example/algorithms.json` 中 22 項 `candidate_after_clinical_validation` 已依醫院核定授權，升級為版本化、可執行 runtime models。
- 3 項 `blocked_source_conflict`（`new_zealand_dcs_cvd`、`hunt_lung_cancer_6y`、`china_nonobese_nafld_1y`）仍不載入、不執行，等待另外一次醫院人工審核。
- 舊 `nafld_fibrosis` 是不同量尺的無來源平均值，正式退役，由 HSI、LFS、FLI、FIB-4、APRI、RPR、NFS 個別結果取代。
- 舊 `framingham_fatty_liver` 與核定的 `incident_hepatic_steatosis_model_2` 重複，正式以後者作為唯一 ID，避免同一病患產生重複結果。
- 2026-07-21 公式目錄更新後，正式 runtime catalog 擴充為 42 項；新增的 Reynolds（男女）、PCE、CMI、LAP、GPR、IPAG、MCI-to-AD、ANU-ADRI、Brock、VA、CAIDE 與 BDSI 均已完成 canonical input、FHIR output 與版本接線。舊 `vascular_caide` 退役，由有明確臨床量表版本的 `caide_dementia_20y` 取代。

## 已確認並修正的人因錯誤

| 模型 | 整理檔/工作簿問題 | 正式實作 | 核對依據 |
|---|---|---|---|
| HSI | AST/ALT 顛倒，且 BMI 被錯誤乘上指示變數 | `8 × ALT/AST + BMI + 2(女性) + 2(糖尿病)` | Lee 2010, DOI `10.1016/j.dld.2009.08.002` |
| FLI | 分母的 `ln(GGT)` 誤抄為 `0.178` | 分子與分母皆使用 `0.718` | Bedogni 2006, PMID 17081293 |
| APRI | 漏掉 AST 實驗室 ULN 與乘 100 | `((AST/AST_ULN)×100)/platelets` | WHO 2024 hepatitis B guideline |
| QUICKI | Excel `LOG` 容易被誤解為自然對數 | 明確使用 `log10` | Katz 2000, DOI `10.1210/jcem.85.7.6661` |
| NAFLD-LFS | 糖尿病編碼易被誤改為 0/1 | 保留有=2、無=0，AST/ALT 前為負號 | Kotronen 2009, PMID 19524579 |
| NAFLD-CV | 糖尿病編碼看似反常 | 保留有=1、無=2 | Abeles 2019, PMID 30836450 |
| THIN DRS | 誤寫為 `-0.13199×antihypertensive` | 修正為 `+0.13199×has_hypertension` | Walters 2016 與公開模型公式 |
| NOMAS GVRS | 容易漏掉交互作用 | 保留 `activity × male` 的 `-1.01324` | Sacco 2009, PMCID PMC2812026 |
| Mayo SPN | 癌症時間方向容易顛倒 | 胸外癌需為距今至少 5 年；直徑 4–30 mm | PMCID PMC2882437 |
| Christianson | 前段 scratch IF 與後段點數表衝突 | 依醫院核定的最終點數表；不採 scratch IF | 醫院核定表；公開檢索未找到足以取代該表的原始全文 |

## 公式與單位契約

| 群組 | 正式模型 | 關鍵單位/運算 |
|---|---|---|
| 代謝 | BMI、TyG、HOMA-IR、QUICKI、Cambridge | 身高 cm、體重 kg、血糖/TG mg/dL、insulin uIU/mL；TyG 用 ln、QUICKI 用 log10 |
| 肝臟 | HSI、LFS、FLI、FIB-4、APRI、RPR、NFS、incident steatosis | AST/ALT/GGT U/L、platelet 10^9/L、albumin g/dL、RDW % |
| 心血管 | NAFLD-CV、Framingham lipid/BMI、Framingham HTN、NOMAS、Christianson | BP mmHg、MPV fL、cholesterol mg/dL；機率模型保留 0–1 |
| 神經 | THIN DRS | 僅 60–79 歲模型；使用評估日的 calendar year，不使用伺服器當日猜值 |
| 呼吸 | Mayo SPN | 結節最大徑 mm；吸菸史與影像特徵必須有明確來源 |
| 心理 | GAD-7 | 7 題各 0–3，總分 0–21；不得標示為診斷 |

## FHIR 與追溯契約

- 42 項正式模型依 registry 契約輸出 20 個 `Observation` 與 22 個 `RiskAssessment`；輸出型別不得由前端或公式名稱推測。
- 每項結果都有 `Provenance`，target 指向實際輸出 resource；輸入來源分別使用 `Observation`、`QuestionnaireResponse`、`Condition` 或 `Patient` reference。
- 資料缺失不補零、不插補、不以 Golden Patient 代替真實病患資料。

## Golden Patient 驗證

固定評估日為 2026-07-15。Golden Patient 以正式 FHIR ingestion 寫入 31 項 Observation、1 項 QuestionnaireResponse、Patient/Encounter/Condition 及完整 mapping；42/42 模型均由持久化資料完成解析（39 項有分數、3 項族群不適用、0 項缺資料），產生 22 個 RiskAssessment、20 個結果 Observation、42 個 Provenance。

## 尚需在產品中持續揭露的限制

- BMI、TyG、HOMA-IR、QUICKI、FIB-4、APRI、RPR 的臨床門檻會隨族群、疾病與用途變動；公式可正式執行，不代表存在單一全球門檻。
- NOMAS 的種族/族裔係數源自 Northern Manhattan cohort，臺灣族群需做在地校準；目前結果必須附來源族群限制。
- Christianson 的公開 primary-source 可識別性不足；目前版本是「醫院核定點數表」的明確版本，任何日後來源更新都必須改 model version 並重跑 Golden vectors。
- 所有分數是臨床決策支援，不得單獨作為診斷或治療指令。
