# 已知疑義與禁止直接照抄項目

## 高風險公式差異

1. `fatty liver.xlsx` 的 HSI 使用 `8*AST/ALT`，且把 BMI 乘上 indicator sum。文獻公式是 `8*ALT/AST + BMI + 2(if diabetes) + 2(if female)`。
2. 同一檔案的 FLI 分子使用 `0.718*ln(GGT)`，分母卻使用 `0.178*ln(GGT)`。正規公式兩處均為 `0.718`。
3. `Liver fibrosis.xlsx` 的 APRI 只有 `AST/platelet`；標準式需要 AST laboratory ULN 與 `*100`。
4. 同檔 GPR 寫成 `GGT/(platelet*100)`，很可能把 `(GGT/GGT_ULN)*100/platelet` 的乘除位置弄反。
5. 同檔 FibroIndex 使用 `0.05*AST`，需要回原始論文核對是否應為 `0.005*AST` 以及 platelet 單位。
6. `metabolic syndrome.xlsx` 的 WHO 腰臀比條件拿腰圍 cell 與 `0.9/0.85` 比較，應使用 waist/hip ratio；另有 `O2`、治療欄位引用錯位等問題。
7. `Dementia Risk Score (DRS) .xlsx` 只有不可執行的 symbolic Excel 字串；完整係數在 `dementia drs2 uk.docx`。
8. `CLIDE.xlsx` 與 `UKPDS DM-STROKE.xlsx` 有 `AND(score>=12,score>=15)`，第二個條件看起來應為上界，但禁止未查來源就自行改成 `<=15`。
9. `ASCVD-Optimal.xlsx` 引用不存在的 `[1]A1 KEY IN` 外部工作簿。
10. `Reynolds.docx` 的部分 Excel 式括號錯置，且 baseline survival 的百分比括號可能造成錯誤運算順序。
11. HUNT 本地文件把 linear predictor 稱為 risk，並遺漏 log1p 與 sigmoid；目前 catalog 因此標為 blocked。
12. Chinese NAFLD 4-year incidence 科學記號轉錄為 `-7e-(08*points^3)` 等破損文字，不可實作。

## 重複與版本風險

- `CORE 20220414.xlsx`、`CORE 20220415.xlsx` 與 `CORE.xlsx` 不是單純相同檔名副本，sheet 數和公式數不同。
- UKPDS Stroke/CHD 有至少四個版本；輸出與中間公式數不同。
- FHS CVD BMI／lipid workbooks 有多個近似副本，且部分輸入直接連到已不存在的本機絕對路徑。
- 三份 `Fatty-Liver-Risk-Score-Calculator-Excel-*.xls` 目前看似同一模型版本，但仍應以 SHA-256 和公式 fingerprint 判定 release。

## 文獻核對連結

- [WHO FIB-4/APRI formulas](https://www.ncbi.nlm.nih.gov/books/NBK614988/box/ch4.box1/?report=objectonly)
- [Framingham General CVD primary paper](https://pubmed.ncbi.nlm.nih.gov/18212285/)
- [Cambridge Diabetes Risk Score primary paper](https://onlinelibrary.wiley.com/doi/abs/10.1002/1520-7560%28200005/06%2916%3A3%3C164%3A%3AAID-DMRR103%3E3.0.CO%3B2-R)
- [UK THIN Dementia Risk Score paper record](https://discovery.ucl.ac.uk/id/eprint/1476027/)
- [NOMAS Global Vascular Risk Score primary paper](https://www.jacc.org/doi/10.1016/j.jacc.2009.07.047)
- [New Zealand Diabetes Cohort Study equation](https://pmc.ncbi.nlm.nih.gov/articles/PMC2875452/)
- [Mayo pulmonary nodule model validation/equation](https://pmc.ncbi.nlm.nih.gov/articles/PMC2882437/)
- [HUNT Lung Cancer Model primary paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6013755/)
- [NAFLD CV Risk Score paper](https://pubmed.ncbi.nlm.nih.gov/30836450/)

