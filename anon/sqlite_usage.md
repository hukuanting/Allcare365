# 生理訊號 SQLite 使用說明

本文件說明如何使用 SQLite 儲存、瀏覽、匯出生理訊號資料。資料表結構請參考 `data_sheet.md`。

---

## 1. 什麼是 SQLite？
SQLite 是一種輕量級、檔案型的關聯式資料庫，適合嵌入式及桌面應用，不需要額外的伺服器。

---

## 2. 如何開啟 SQLite 資料庫

- **圖形介面工具：**
  - [DB Browser for SQLite](https://sqlitebrowser.org/)（Windows/macOS/Linux）
  - [DBeaver](https://dbeaver.io/)（Windows/macOS/Linux）

---

## 3. 資料表結構範例

每種生理訊號建議獨立一個資料表。以下為連續血壓範例：

```sql
CREATE TABLE numeric_full (
    mrn TEXT,
    sample_time TEXT, -- ISO8601
    systolic INTEGER,
    diastolic INTEGER,
    map INTEGER
);
```

其他資料表請依 `data_sheet.md` 內容設計。

---

## 4. 如何瀏覽資料

- 列出所有資料表：
  ```sql
  SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
  ```
- 顯示某表前 10 筆資料：
  ```sql
  SELECT * FROM numeric_full LIMIT 10;
  ```
- 依病人查詢：
  ```sql
  SELECT * FROM numeric_full WHERE mrn = '2189347';
  ```

---

## 5. 如何匯出資料

- 匯出為 CSV：
  在 DBeaver 或 DB Browser for SQLite，先查詢：
  ```sql
  SELECT * FROM numeric_full;
  ```
  然後用工具內建的「匯出」或「Export」功能將查詢結果另存為 CSV。
  
  另外，DBeaver 也支援直接複製查詢結果（Copy），可選擇複製成 CSV 格式。

---

## 6. 如何用 DBeaver/DB Browser for SQLite 瀏覽與匯出

你可以直接用 DBeaver 或 DB Browser for SQLite 開啟 .db 檔案，瀏覽及匯出資料。

### DBeaver 匯出 CSV
1. 開啟 DBeaver，新增 SQLite 連線。
2. 指定你的資料庫檔案（如 your_database.db）。
3. 在資料表上右鍵，選擇「Export Data」。
4. 選擇「CSV」格式，依指示完成匯出。

### DB Browser for SQLite 匯出 CSV
1. 開啟 DB Browser for SQLite。
2. 選擇「Open Database」，載入你的 .db 檔案。
3. 切換到「Browse Data」分頁，選擇資料表。
4. 點選「Export」按鈕，選擇「CSV」格式。

---

## 7. 小技巧
- 時間欄位建議使用 ISO8601 格式。
- 建議對 mrn 等常用查詢欄位建立索引。

---

## 參考資源
- [SQLite 官方文件](https://sqlite.org/docs.html)
- [DB Browser for SQLite](https://sqlitebrowser.org/)
- [DBeaver](https://dbeaver.io/)

---

更新日期：2025-10-19
作者：andy.ke@soterawireless.com
