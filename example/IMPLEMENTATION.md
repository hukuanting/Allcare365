# Coding／FHIR 實作規格

## 模組介面

建議每個演算法暴露同一介面：

```text
calculate(input, context) -> {
  algorithm_id,
  algorithm_version,
  value,
  unit,
  interpretation,
  input_snapshot,
  warnings,
  calculated_at
}
```

不要把 Excel cell 名稱帶進 domain model。Cell 只作 provenance；正式輸入名稱以 `algorithms.json` 為準。

## 數值規則

- `ln` 必須是自然對數；`log10` 必須明確使用十進位對數。
- 禁止自動把 `mg/dL` 當成 `mmol/L`。轉換應是獨立、可測試且記錄原始單位的步驟。
- Logistic probability 建議用數值穩定的 sigmoid；大型正負 predictor 不可直接造成 overflow。
- 分數內部保留 double precision，只在顯示層 round。
- 缺值不得默認成 0；只有演算法明確規定的 indicator reference 才能是 0。
- enum／boolean 編碼集中管理，不可散落在公式字串。
- 輸入超出 derivation domain 時回傳 structured warning 或拒算，不可靜默外推。

## 測試層級

每個演算法至少需要：

- `verification_cases.json` golden case。
- 邊界值測試，例如剛好落在 `<30`、`30`、`36`。
- 單位誤用測試。
- 0、負值、缺值及除以 0 測試。
- enum one-hot mutual exclusivity 測試。
- 公式版本升級的 regression test。

## FHIR R4 建模

依 allcare-365 規範：

- 事件風險／疾病機率使用 `RiskAssessment`。
- BMI、FIB-4、FLI、量表總分等衍生指標可使用 `Observation`。
- 原始量測維持各自的 `Observation`；風險計算不得覆寫來源量測。
- `RiskAssessment.basis`／`Observation.derivedFrom` 指向實際輸入資源。
- `method` 或 extension 保存演算法 canonical URL、`algorithm_id` 及版本。
- 使用 `Provenance` 記錄計算服務、時間、輸入與公式版本。
- 保存 `source_manifest.json` 的來源 SHA-256 或相應 release artifact hash，以支援稽核。

建議 canonical：

```text
https://<your-domain>/fhir/algorithm/<algorithm_id>|<semantic-version>
```

## 安全與產品限制

- `blocked_source_conflict` 完全排除於 runtime、API 與 UI；不得只靠 `enabled=false` 留在 production catalog。待醫院人工審核來源後，以新版本重新走完整 onboarding。
- 風險結果必須顯示模型適用族群及「風險估計不等於診斷」。
- 臨床門檻、患者文字及建議行動不應硬寫在計算函式；使用版本化 policy layer。
- 每次修改係數、單位、編碼、baseline survival 或門檻都必須升版。
- 不要把族群校正係數（例如某些工作簿內的華人修正值）套用到其他模型，除非有明確版本與臨床核准。
