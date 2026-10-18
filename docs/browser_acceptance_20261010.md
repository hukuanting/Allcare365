# Chrome 實際驗收（2026-10-10）

- Chrome 擴充功能已連線；使用授權開發帳號，未保存密碼。
- 登入成功，跨頁與重新載入後仍維持登入；手動登出及再次登入成功。
- 閒置逾時在長時間檔案選擇流程中發生；不是立即登入登出。15 分鐘邊界另由 sessionManager 測試確認。
- Golden Patient JSON 上傳、44 個資源預覽及匯入成功（44 成功，0 錯誤）。
- 匯入後病患 ID 跨頁保留；風險分析 82/82 解析，77 分數、5 不適用、0 資料不足。
- 疾病網絡 8 領域、15 關聯，肝臟與心血管節點切換及共同因子呈現成功。關聯來自共同模型輸入，不等同新增疾病預測。
- JSON/XML 多檔選取成功；兩份同一 Bundle 預覽拒絕衝突 fullUrl；XML 單檔瀏覽器解析未完成。
- Chrome 上傳需擴充功能 Allow access to file URLs；使用者已啟用。檔案選擇工具仍有異常延遲，未宣稱全部上傳模式已驗收。
- 移除分析完成提示中的防禦性措辭，改為直接描述可操作功能。
- npm test -- src/utils/sessionManager.test.js src/components/AuthLifecycle.test.jsx src/components/DiseaseNetwork.test.jsx src/components/RiskWorkspace.test.jsx：4 files / 21 tests passed。

範圍：此輪完成登入、FHIR JSON 匯入與 Golden Patient 網絡流程驗收；尚未遍歷全部工作空間頁面或完成所有來源風險模組。
