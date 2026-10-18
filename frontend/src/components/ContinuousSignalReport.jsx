import React, { useEffect, useMemo, useRef, useState } from 'react';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import DatabaseRoundedIcon from '@mui/icons-material/StorageRounded';
import ScienceRoundedIcon from '@mui/icons-material/ScienceRounded';
import TimelineRoundedIcon from '@mui/icons-material/TimelineRounded';
import VerifiedUserRoundedIcon from '@mui/icons-material/VerifiedUserRounded';
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage } from '../utils/apiData';
import { countValue, numericValue, percentageValue } from '../utils/numericDisplay';
import './ContinuousSignalReport.css';

const signalLabels = {
  SCG: 'SCG 胸壁微震',
  ECG_II: 'ECG II 心電圖',
  IR_PPG: 'IR PPG 脈搏波',
  RED_PPG: 'Red PPG 脈搏波',
  ACC_ECG: '胸前動作感測',
  IP: '呼吸波形',
  HR: '心率',
  SPO2: '血氧',
  RR: '呼吸率',
  CNIBP_SYS: '連續收縮壓',
  CNIBP_DIA: '連續舒張壓',
  TEMP: '皮膚溫度',
  PR: '脈搏率',
};

const findingLabels = {
  numeric_validity_below_90_pct: '部分數值有效率低於 90%',
  continuous_waveform_coverage_below_80_pct: '連續波形覆蓋率低於 80%',
  duplicate_waveform_timestamps: '發現重複時間戳',
  poor_calibration_event: '發現較差的校正事件',
  nonfinite_waveform_values: '波形包含非有限值',
};

const sourceNotes = {
  'The high-frequency waveform values remain in the source Parquet archive; only coverage metadata is imported.': '高頻波形保留於來源 Parquet 檔案；系統匯入波形覆蓋資訊。',
  'Rows marked invalid by the source are summarized but excluded from clinical Observation records.': '來源標記為無效的資料列納入品質摘要，並從臨床 Observation 紀錄中排除。',
  'This report is technical data-quality analysis, not disease-risk estimation or diagnosis.': '本報告呈現技術資料品質分析；疾病風險估算與診斷結果另行評估。',
};

const importStatusLabels = { completed: '已完成', pending: '等待處理', running: '處理中', failed: '匯入失敗' };

const standardStatus = {
  mapped: '已對應',
  partial: '部分對應',
  evaluation: '評估中',
};

const formatValidity = value => {
  const percentage = percentageValue(value);
  return percentage === null ? '有效率未提供' : formatNumber(percentage, 1) + '% 有效';
};

const formatNumber = (value, maximumFractionDigits = 0) => {
  const numeric = numericValue(value);
  if (numeric === null) return '—';
  return new Intl.NumberFormat('zh-TW', { maximumFractionDigits }).format(numeric);
};

const unitLabel = (unit) => ({
  '{beats}/min': 'bpm',
  '{breaths}/min': '次/分',
  'mm[Hg]': 'mmHg',
  Cel: '°C',
}[unit] || unit || '');

function Metric({ eyebrow, value, unit, note }) {
  return (
    <Box className="signal-metric">
      <Typography className="signal-eyebrow">{eyebrow}</Typography>
      <Box className="signal-metric-value">
        <span>{value}</span>
        {unit && <small>{unit}</small>}
      </Box>
      <Typography className="signal-metric-note">{note}</Typography>
    </Box>
  );
}

function ContinuousSignalReport() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const errorNotice = useRef(null);
  useEffect(() => {
    if (!loading && error) errorNotice.current?.focus({ preventScroll: true });
  }, [loading, error]);

  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setReport(null);
    const load = async () => {
      try {
        const response = await api.get(API_CONFIG.ENDPOINTS.CONTINUOUS_SIGNAL_REPORT, { signal: controller.signal });
        const payload = await parseApiResponse(response);
        if (!response.ok) throw new Error(apiErrorMessage(payload, '無法讀取連續訊號報告'));
        if (!controller.signal.aborted) setReport(payload);
      } catch (requestError) {
        if (!controller.signal.aborted) setError(requestError.message || '無法讀取連續訊號報告');
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    load();
    return () => controller.abort();
  }, [revision]);

  const scg = useMemo(
    () => report?.waveform_signals?.find((item) => item.signal === 'SCG'),
    [report],
  );
  const numericSignals = report?.numeric_signals || [];
  const waveformSignals = report?.waveform_signals || [];
  const findings = report?.quality?.findings || [];
  const fhirResources = report?.fhir?.resources || [];
  const aoOutputs = countValue(report?.ao_readiness?.outputs);

  if (loading || error || !report?.available) {
    return (
      <Box className="page-frame continuous-report">
        <section className="signal-hero signal-surface">
          <Box className="signal-hero-copy">
            <Box className="signal-kicker">CONTINUOUS SIGNALS</Box>
            <Typography component="h1">連續生理資料<br />匯入與可分析性報告</Typography>
            <Typography className="signal-lead">檢視監測資料的匯入紀錄、訊號覆蓋與模型輸出。</Typography>
          </Box>
        </section>
        <section className="signal-surface signal-panel" aria-labelledby="signal-state-title">
          <Typography component="h2" id="signal-state-title">{loading ? '正在讀取監測資料' : error ? '報告讀取失敗' : '尚無監測資料'}</Typography>
          {loading ? (
            <Box className="signal-state-loading" role="status">
              <CircularProgress size={24} />
              <Typography>正在讀取資料庫分析結果…</Typography>
            </Box>
          ) : error ? (
            <Alert ref={errorNotice} tabIndex={-1} severity="error" action={<Button color="inherit" onClick={() => setRevision((value) => value + 1)}>重試</Button>}>{error}</Alert>
          ) : (
            <Typography className="signal-lead">目前尚未匯入 Sotera 連續生理資料。完成資料匯入後，這裡會呈現監測時間、波形覆蓋與數值摘要。</Typography>
          )}
        </section>
      </Box>
    );
  }

  return (
    <Box className="page-frame continuous-report">
      <section className="signal-hero signal-surface">
        <Box className="signal-hero-copy">
          <Box className="signal-kicker">
            CONTINUOUS SIGNALS
          </Box>
          <Typography component="h1">連續生理資料<br />匯入與可分析性報告</Typography>
          <Typography className="signal-lead">
            檢視本次監測的匯入紀錄、訊號覆蓋與模型輸出狀態。技術品質摘要供研究資料檢查使用。
          </Typography>
          <Box className="signal-status-row">
            <span className="signal-pill">匯入狀態：{importStatusLabels[report.import?.status] || report.import?.status || '未提供'}</span>
            <span className="signal-pill">FHIR 追溯：{report.fhir?.quality_result_traceable === true ? '已建立' : report.fhir?.quality_result_traceable === false ? '尚未建立' : '未提供'}</span>
            <span className="signal-pill">AO 輸出：{formatNumber(aoOutputs)} 筆</span>
          </Box>
        </Box>

      </section>

      <section className="signal-metrics">
        <Metric eyebrow="監測時間" value={formatNumber(report.session?.duration_hours, 2)} unit="小時" note="單次去識別化監測" />
        <Metric eyebrow="來源波形" value={formatNumber(report.import?.raw_waveform_samples)} unit="個樣本" note="來源檔案樣本數" />
        <Metric eyebrow="資料庫紀錄" value={formatNumber(report.import?.database_observations)} unit="筆 Observation" note="數值、事件與波形索引" />
        <Metric eyebrow="SCG 可用覆蓋" value={formatNumber(percentageValue(scg?.coverage_pct), 1)} unit="%" note={`${formatNumber(scg?.fs_nominal_hz)} Hz · ${formatNumber(scg?.n_channels)} 通道`} />
      </section>

      <section className="signal-route signal-surface">
        <Box className="signal-section-heading">
          <Box>
            <Typography className="signal-eyebrow">DATA ROUTE</Typography>
            <Typography component="h2">資料流程概覽</Typography>
          </Box>
          <DatabaseRoundedIcon />
        </Box>
        <Box component="ol" className="signal-route-grid" aria-label="監測資料處理順序">
          <Box component="li" className="route-node"><span aria-hidden="true">01</span><strong>Parquet 原始檔</strong><small>完整波形來源</small></Box>
          <Box component="li" role="presentation" aria-hidden="true" className="route-arrow">→</Box>
          <Box component="li" className="route-node"><span aria-hidden="true">02</span><strong>資料品質檢查</strong><small>格式、時間、缺值、覆蓋</small></Box>
          <Box component="li" role="presentation" aria-hidden="true" className="route-arrow">→</Box>
          <Box component="li" className="route-node"><span aria-hidden="true">03</span><strong>臨床資料庫</strong><small>數值、事件、索引</small></Box>
          <Box component="li" role="presentation" aria-hidden="true" className="route-arrow">→</Box>
          <Box component="li" className="route-node"><span aria-hidden="true">04</span><strong>FHIR R4</strong><small>Observation + Provenance</small></Box>
          <Box component="li" role="presentation" aria-hidden="true" className="route-arrow">→</Box>
          <Box component="li" className="route-node"><span aria-hidden="true">05</span><strong>AO 模型</strong><small>執行與輸出見下方摘要</small></Box>
        </Box>
      </section>

      <Box className="signal-analysis-grid">
        <section className="signal-surface signal-panel">
          <Box className="signal-section-heading compact">
            <Box>
              <Typography className="signal-eyebrow">CONTINUITY</Typography>
              <Typography component="h2">主要波形覆蓋</Typography>
            </Box>
            <TimelineRoundedIcon />
          </Box>
          <Typography className="signal-panel-note">百分比代表本次 {formatNumber(report.session?.duration_hours, 2)} 小時監測中，實際有連續波形的時間。</Typography>
          <Box className="coverage-list">
            {waveformSignals.length === 0 && <Typography className="signal-panel-note">本次未提供波形覆蓋摘要。</Typography>}
            {waveformSignals.map((item) => {
              const coverage = percentageValue(item.coverage_pct);
              const known = coverage !== null;
              const name = signalLabels[item.signal] || item.signal;
              return <Box className="coverage-row" key={item.signal}>
                <Box className="coverage-name"><strong>{name}</strong><small>{formatNumber(item.fs_nominal_hz)} Hz</small></Box>
                {known ? <Box className="coverage-bar" role="meter" aria-label={name + '覆蓋率'} aria-valuemin={0} aria-valuemax={100} aria-valuenow={coverage} aria-valuetext={formatNumber(coverage, 1) + '%'}><span style={{ width: coverage + '%' }} /></Box> : <Typography className="signal-panel-note">未提供覆蓋率</Typography>}
                <strong className="coverage-value">{known ? formatNumber(coverage, 1) + '%' : '—'}</strong>
              </Box>;
            })}
          </Box>
        </section>

        <section className="signal-surface signal-panel">
          <Box className="signal-section-heading compact">
            <Box>
              <Typography className="signal-eyebrow">NUMERIC SUMMARY</Typography>
              <Typography component="h2">可查詢數值摘要</Typography>
            </Box>
            <ScienceRoundedIcon />
          </Box>
          <Typography className="signal-panel-note">資料中位數與來源有效率，呈現本次訊號品質。</Typography>
          <Box className="numeric-grid">
            {numericSignals.length === 0 && <Typography className="signal-panel-note">本次未提供數值訊號摘要。</Typography>}
            {numericSignals.map((item) => (
              <Box className="numeric-card" key={item.signal}>
                <Box><span>{signalLabels[item.signal] || item.signal}</span><small>{formatValidity(item.valid_pct)}</small></Box>
                <strong>{formatNumber(item.median, 2)} <em>{unitLabel(item.unit)}</em></strong>
              </Box>
            ))}
          </Box>
        </section>
      </Box>

      <section className="ao-readiness signal-surface">
        <Box className="ao-title-block">
          <Typography className="signal-eyebrow">AORTIC OPENING READINESS</Typography>
          <Typography component="h2">AO 模型執行與輸出</Typography>
          <Typography>
            {aoOutputs > 0 ? '已有 AO 輸出紀錄。' : aoOutputs === 0 ? '目前沒有 AO 輸出紀錄。' : '目前未提供 AO 輸出數量。'}
            模型執行、輸出與標準答案數量如下；這些紀錄不能單獨證明偵測準確度。
          </Typography>
        </Box>
        <Box className="ao-checkpoints">
          <Box className="ao-check"><span><strong>波形種類</strong><small>{formatNumber(waveformSignals.length)} 種來源摘要</small></span></Box>
          <Box className="ao-check"><span><strong>標準答案</strong><small>{formatNumber(report.ao_readiness?.ground_truth_records)} 筆</small></span></Box>
          <Box className="ao-check"><span><strong>模型執行</strong><small>{formatNumber(report.ao_readiness?.model_runs)} 次</small></span></Box>
          <Box className="ao-check"><span><strong>AO 輸出</strong><small>{formatNumber(aoOutputs)} 筆</small></span></Box>
        </Box>
      </section>

      <Box className="signal-bottom-grid">
        <section className="signal-surface signal-panel">
          <Box className="signal-section-heading compact">
            <Box><Typography className="signal-eyebrow">FHIR & GOVERNANCE</Typography><Typography component="h2">規範對應狀態</Typography></Box>
            <VerifiedUserRoundedIcon />
          </Box>
          <Box className="standard-list">
            {(report.standards || []).map((item) => (
              <Box className="standard-row" key={item.name}>
                <Box><strong>{item.name}</strong><small>{item.detail}</small></Box>
                <span className={`standard-status standard-${item.status}`}>{standardStatus[item.status] || item.status}</span>
              </Box>
            ))}
          </Box>
          <Box className="fhir-footnote">
            回應中的資源：{fhirResources.map((item) => item.resource_type).join(' + ') || '未提供'}；
            研究測試不等同 ONC 認證或臨床驗證。
          </Box>
        </section>

        <section className="signal-surface signal-panel">
          <Box className="signal-section-heading compact">
            <Box><Typography className="signal-eyebrow">QUALITY FLAGS</Typography><Typography component="h2">本次需要注意</Typography></Box>
            <WarningAmberRoundedIcon />
          </Box>
          <Box className="finding-list">
            {findings.length === 0 && <Typography className="signal-panel-note">本次結果未列出品質警示。</Typography>}
            {findings.map((finding) => (
              <Box className="finding-row" key={finding.code}>
                <span />
                <Box><strong>{findingLabels[finding.code] || finding.code}</strong><small>{finding.count != null ? `${formatNumber(finding.count)} 筆` : '分析前應納入品質篩選'}</small></Box>
              </Box>
            ))}
          </Box>
          <Box className="report-verdict">
            <strong>報告內容</strong>
            <span>訊號品質、模型結果與評估來源分別呈現。</span>
          </Box>
        </section>
      </Box>

      {report.limitations?.length > 0 && <section className="signal-surface signal-panel"><Typography component="h2">來源與處理方式</Typography><ul>{report.limitations.map((item, index) => <li key={index}>{sourceNotes[item] || item}</li>)}</ul></section>}
      <footer className="signal-report-footer">
        <span>AllCare365 · Continuous Physiological Data Integration</span>
        <span>連續生理資料 · 品質與可分析性摘要</span>
      </footer>
    </Box>
  );
}

export default ContinuousSignalReport;
