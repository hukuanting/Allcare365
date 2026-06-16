# 生理訊號資料格式說明

本文件將生理訊號分為兩大類：
1. **生命徵象** — 主要生理量測數據。
2. **其他訊號** — 支援性波形或硬體感測資料。

所有欄位皆以 TEXT 型態儲存。
- 時間欄位為 ISO8601 格式（TEXT）。
- value 欄位： 
  - 若為數值型資料，value 為 integer（數值型，非字串）。
  - 若為波形資料，value 為逗號分隔的 integer 字串（TEXT）。

---

## 數值型生命徵象

| 類型    | 資料表名稱      | 說明                        | JSON 欄位                                   | 單位                | 取樣間隔      | 量測範圍（Full Scale Range） | 資料來源                        |
|---------|-----------------|-----------------------------|---------------------------------------------|---------------------|---------------|-----------------------------|-------------------------------|
| CNIBP   | numeric_full    | 連續無創血壓                | time: ISO8601 (TEXT), systolic: integer, diastolic: integer, map: integer | mmHg                | 1–3 秒/筆      | （待定）                    | Systolic/Diastolic/MAP        |
| HR      | numeric_ecg     | 心電圖心率                   | time: ISO8601 (TEXT), value: integer                 | beats/min           | 1–3 秒/筆      | （待定）                    | 心電圖心率                     |
| PR      | numeric_oxygen  | PPG 脈搏率                   | time: ISO8601 (TEXT), value: integer                 | beats/min           | 1–3 秒/筆      | （待定）                    | PPG 脈搏率                     |
| RR      | numeric_ecg     | 呼吸率                       | time: ISO8601 (TEXT), value: integer                 | breaths/min         | 1–3 秒/筆      | （待定）                    | 呼吸率                         |
| SPO2    | numeric_oxygen  | PPG 血氧                      | time: ISO8601 (TEXT), value: integer                 | %                   | 1–3 秒/筆      | （待定）                    | PPG 血氧                       |
| TEMP    | numeric_ecg     | 皮膚溫度                     | time: ISO8601 (TEXT), value: integer                 | °C                  | 1–3 秒/筆      | （待定）                    | 皮膚溫度                       |

---

## 波形型生命徵象

| 類型      | 資料表名稱            | 說明                      | JSON 欄位                                       | 單位      | 取樣率 (Hz) | 量測範圍（Full Scale Range） | 資料來源                        |
|-----------|-----------------------|---------------------------|-------------------------------------------------|-----------|-------------|-----------------------------|-------------------------------|
| ACC_ARM   | acc_waveform_arm      | 上臂三軸加速度            | time: ISO8601 (TEXT), value: x,y,z 逗號分隔 integer (TEXT) | g/m/s²   | 250         | （待定）                    | g/m/s² 樣本                    |
| ACC_ECG   | acc_waveform_ecg      | 胸前（ECG）三軸加速度      | time: ISO8601 (TEXT), value: x,y,z 逗號分隔 integer (TEXT) | g/m/s²   | 250         | （待定）                    | g/m/s² 樣本                    |
| ACC_WRT   | acc_waveform_wt       | 手腕三軸加速度            | time: ISO8601 (TEXT), value: x,y,z 逗號分隔 integer (TEXT) | g/m/s²   | 250         | （待定）                    | g/m/s² 樣本                    |
| ECG_I     | ecg_waveform_1        | 心電圖 Lead I             | time: ISO8601 (TEXT), value: 逗號分隔 integer (TEXT)      | mV        | 250         | ±1.72 mV (19000 counts=1mV) | mV 樣本                         |
| ECG_II    | ecg_waveform_2        | 心電圖 Lead II            | time: ISO8601 (TEXT), value: 逗號分隔 integer (TEXT)      | mV        | 500         | ±1.72 mV (19000 counts=1mV) | mV 樣本                         |
| ECG_III   | ecg_waveform_3        | 心電圖 Lead III           | time: ISO8601 (TEXT), value: 逗號分隔 integer (TEXT)      | mV        | 250         | ±1.72 mV (19000 counts=1mV) | mV 樣本                         |
| IP        | respiration_waveform  | 阻抗呼吸波形              | time: ISO8601 (TEXT), value: 逗號分隔 integer (TEXT)      | Ohms      | 50          | （待定）                    | 歐姆樣本                        |
| PPG       | ppg_waveform          | 紅外線 PPG                | time: ISO8601 (TEXT), value: 逗號分隔 integer (TEXT)      | Volts     | 500         | （待定）                    | 電壓樣本                        |

---

## 其他訊號

| 類型      | 說明                      | JSON 欄位                                   | 單位      | 取樣率      | 量測範圍（Full Scale Range） | 資料來源                        |
|-----------|---------------------------|---------------------------------------------|-----------|-------------|-----------------------------|-------------------------------|

---

## 備註
- 量測範圍（Full Scale Range）部分尚未定義，後續補充。
- 更新日期：2025-10-20
- 更新者：andy.ke@soterawireless.com
