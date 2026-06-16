# FHIR Search Engine

宣告式搜尋系統 — 將 FHIR 查詢參數轉換為 Django ORM 查詢。

## 模組 (Modules)

### `search_params.py` — 參數定義

宣告式配置：每個 resource type 支援哪些搜尋參數。

```python
get_params_for("Observation")
# → {"patient": "reference", "category": "token", "code": "token", "date": "date", ...}
```

新增搜尋參數：只需在 `_SEARCH_PARAMS` dict 加一行。

### `search_parser.py` — 解析器

將 HTTP query string 解析成結構化 `ParsedSearch` 物件。

```python
parsed = SearchParser.parse("Observation", request.GET)
parsed.params        # {"patient": "xxx", "category": "vital-signs"}
parsed.includes      # {"MedicationRequest:medication"}
parsed.rev_includes  # {"Provenance:target"}
parsed.count         # 50
parsed.sort          # "-date"
```

### `query_translator.py` — ORM 轉換

FHIR 搜尋參數 → Django Q 物件 工具函式。

```python
from .query_translator import token_filter, date_filter
qs = qs.filter(token_filter("status_field", params.get("status")))
```

### `include_resolver.py` — Lazy Include

防止遞迴爆炸的 `_include` 解析器。

```
Projector 階段:  context.include_tracker.add("Medication", med_id)
Bundle 階段:     IncludeResolver.resolve(tracker, ctx)  →  [FHIR dicts]
```

## 資料流

```
HTTP ?patient=xxx&category=vital-signs&_revinclude=Provenance:target
    │
    ▼
SearchParser.parse("Observation", query_dict)
    │
    ▼
ParsedSearch(params={patient, category}, rev_includes={Provenance:target})
    │
    ▼
projector.query(patient_id, params, context)   ← 各 projector 自行翻譯
    │
    ▼
QuerySet → project_batch() → FHIR resources
```
