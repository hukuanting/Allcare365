# Inferno Fix Record (Minimal)

日期: 2026-04-09

## 核心修正
- 建立單病人真值模型: `Patient/00000000-0000-4000-a000-000000000001`（同時相容舊別名 `onc-patient-1` 解析）。
- 強化搜尋穩定性: 投影搜尋加入 deterministic 排序、病人參數正規化、必要時 patient-only fallback，避免空回傳。
- 修正 chaining 搜尋: `DiagnosticReport?patient=...&category=laboratory` 可穩定命中實驗室報告。
- 建立 `inferno_preflight_validator.py`:
  - Failure Router 五分類
  - 單病人一致性檢查
  - 關鍵搜尋與 deterministic 檢查
  - preflight JSON 報告輸出

## 影響檔案
- `apps/integration/fhir_integration/resource_identity.py`
- `apps/integration/fhir_integration/views.py`
- `apps/integration/fhir_integration/projectors/patient.py`
- `apps/integration/fhir_integration/projectors/diagnostic_report.py`
- `inferno_preflight_validator.py`

