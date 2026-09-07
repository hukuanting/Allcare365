import React, { useEffect, useMemo, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import DatabaseRoundedIcon from '@mui/icons-material/StorageRounded';
import ScienceRoundedIcon from '@mui/icons-material/ScienceRounded';
import TimelineRoundedIcon from '@mui/icons-material/TimelineRounded';
import VerifiedUserRoundedIcon from '@mui/icons-material/VerifiedUserRounded';
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage } from '../utils/apiData';
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
  duplicate_waveform_timestamps: '發現少量重複時間戳',
  poor_calibration_event: '有一筆較差的校正事件',
  nonfinite_waveform_values: '波形包含非有限值',
};

const standardStatus = {
  mapped: '已對應',
  partial: '部分對應',
  evaluation: '評估中',
};

const formatNumber = (value, maximumFractionDigits = 0) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';
  return new Intl.NumberFormat('zh-TW', { maximumFractionDigits }).format(numeric);
};

const unitLabel = (unit) => ({
  '{beats}/min': 'bpm',
  '{breaths}/min': '次/分',
  'mm[Hg]': 'mmHg',
  Cel: '°C',
}[unit] || unit || '');

function Metric({ eyebrow, value, unit, note, accent = 'blue' }) {
  return (
    <Box className={`signal-metric signal-metric-${accent}`}>
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

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const response = await api.get(API_CONFIG.ENDPOINTS.CONTINUOUS_SIGNAL_REPORT);
        const payload = await parseApiResponse(response);
        if (!response.ok) throw new Error(apiErrorMessage(payload, '無法讀取連續訊號報告'));
        if (active) setReport(payload);
      } catch (requestError) {
        if (active) setError(requestError.message || '無法讀取連續訊號報告');
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => { active = false; };
  }, []);

  const scg = useMemo(
    () => report?.waveform_signals?.find((item) => item.signal === 'SCG'),
    [report],
  );
  const numericSignals = report?.numeric_signals || [];
  const waveformSignals = report?.waveform_signals || [];
  const findings = report?.quality?.findings || [];
  const fhirResources = report?.fhir?.resources || [];

  if (loading) {
    return (
      <Box className="continuous-report-state">
        <CircularProgress size={34} />
        <Typography>正在讀取資料庫分析結果…</Typography>
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!report?.available) {
    return <Alert severity="info">目前尚未匯入 Sotera 連續生理資料。</Alert>;
  }

  return (
    <Box className="page-frame continuous-report">
      <section className="signal-hero signal-surface">
        <Box className="signal-hero-copy">
          <Box className="signal-kicker">
            <span className="signal-live-dot" />
            RESEARCH INGESTION · SESSION 01
          </Box>
          <Typography component="h1">連續生理資料<br />匯入與可分析性報告</Typography>
          <Typography className="signal-lead">
            已把一個長時間監測 session 的可查詢數值、事件與波形索引載入 AllCare365，
            並完成技術品質分析與 FHIR 追溯紀錄。
          </Typography>
          <Box className="signal-status-row">
            <span className="signal-pill signal-pill-success"><CheckCircleRoundedIcon />資料庫匯入成功</span>
            <span className="signal-pill signal-pill-success"><VerifiedUserRoundedIcon />FHIR 可追溯</span>
            <span className="signal-pill signal-pill-warning"><WarningAmberRoundedIcon />AO 尚未執行</span>
          </Box>
        </Box>
        <Box className="signal-hero-stamp" aria-label="technical quality partial coverage">
          <span>TECHNICAL QUALITY</span>
          <strong>PARTIAL</strong>
          <small>部分訊號覆蓋</small>
        </Box>
      </section>

      <section className="signal-metrics">
        <Metric eyebrow="監測時間" value={formatNumber(report.session?.duration_hours, 2)} unit="小時" note="單一去識別化 session" accent="navy" />
        <Metric eyebrow="來源波形" value={formatNumber(report.import?.raw_waveform_samples)} unit="samples" note="原始高頻資料保留於 Parquet" accent="teal" />
        <Metric eyebrow="資料庫紀錄" value={formatNumber(report.import?.database_observations)} unit="Observations" note="數值、事件與波形索引" accent="green" />
        <Metric eyebrow="SCG 可用覆蓋" value={formatNumber(scg?.coverage_pct, 1)} unit="%" note={`${formatNumber(scg?.fs_nominal_hz)} Hz · ${formatNumber(scg?.n_channels)} channels`} accent="amber" />
      </section>

      <section className="signal-route signal-surface">
        <Box className="signal-section-heading">
          <Box>
            <Typography className="signal-eyebrow">DATA ROUTE</Typography>
            <Typography component="h2">這批資料如何進入系統</Typography>
          </Box>
          <DatabaseRoundedIcon />
        </Box>
        <Box className="signal-route-grid">
          <Box className="route-node route-node-done"><span>01</span><strong>Parquet 原始檔</strong><small>完整波形來源</small></Box>
          <Box className="route-arrow">→</Box>
          <Box className="route-node route-node-done"><span>02</span><strong>資料品質檢查</strong><small>格式、時間、缺值、覆蓋</small></Box>
          <Box className="route-arrow">→</Box>
          <Box className="route-node route-node-done"><span>03</span><strong>Clinical DB</strong><small>數值、事件、索引</small></Box>
          <Box className="route-arrow">→</Box>
          <Box className="route-node route-node-done"><span>04</span><strong>FHIR R4</strong><small>Observation + Provenance</small></Box>
          <Box className="route-arrow route-arrow-pending">→</Box>
          <Box className="route-node route-node-pending"><span>05</span><strong>AO 模型</strong><small>等待模型與驗證資料</small></Box>
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
          <Typography className="signal-panel-note">百分比代表整段 20.95 小時中，實際有連續波形的時間。</Typography>
          <Box className="coverage-list">
            {waveformSignals.map((item) => (
              <Box className="coverage-row" key={item.signal}>
                <Box className="coverage-name"><strong>{signalLabels[item.signal] || item.signal}</strong><small>{formatNumber(item.fs_nominal_hz)} Hz</small></Box>
                <Box className="coverage-bar"><span style={{ width: `${Math.min(Number(item.coverage_pct) || 0, 100)}%` }} /></Box>
                <strong className="coverage-value">{formatNumber(item.coverage_pct, 1)}%</strong>
              </Box>
            ))}
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
          <Typography className="signal-panel-note">以下是資料中位數與來源有效率，只作資料檢查，不作臨床判讀。</Typography>
          <Box className="numeric-grid">
            {numericSignals.slice(0, 6).map((item) => (
              <Box className="numeric-card" key={item.signal}>
                <Box><span>{signalLabels[item.signal] || item.signal}</span><small>{formatNumber(item.valid_pct, 1)}% valid</small></Box>
                <strong>{formatNumber(item.median, 2)} <em>{unitLabel(item.unit)}</em></strong>
              </Box>
            ))}
          </Box>
        </section>
      </Box>

      <section className="ao-readiness signal-surface">
        <Box className="ao-title-block">
          <Typography className="signal-eyebrow">AORTIC OPENING READINESS</Typography>
          <Typography component="h2">AO：資料已到位，模型分析尚未開始</Typography>
          <Typography>
            目前系統已有 ECG 與三軸 SCG，可作 AO 模型輸入；但資料庫中沒有 AO 模型執行、AO 結果或 ground-truth 紀錄，
            因此不能宣稱已完成 AO 偵測。
          </Typography>
        </Box>
        <Box className="ao-checkpoints">
          <Box className="ao-check ao-check-done"><CheckCircleRoundedIcon /><span><strong>輸入訊號</strong><small>ECG + SCG 已匯入／索引</small></span></Box>
          <Box className="ao-check"><span className="ao-empty">!</span><span><strong>Ground truth</strong><small>{formatNumber(report.ao_readiness?.ground_truth_records)} 筆</small></span></Box>
          <Box className="ao-check"><span className="ao-empty">!</span><span><strong>模型執行</strong><small>{formatNumber(report.ao_readiness?.model_runs)} 次</small></span></Box>
          <Box className="ao-check"><span className="ao-empty">!</span><span><strong>AO 輸出</strong><small>{formatNumber(report.ao_readiness?.outputs)} 筆</small></span></Box>
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
            已生成 {fhirResources.map((item) => item.resource_type).join(' + ') || 'FHIR 紀錄'}；
            研究測試不等同 ONC 認證或臨床驗證。
          </Box>
        </section>

        <section className="signal-surface signal-panel">
          <Box className="signal-section-heading compact">
            <Box><Typography className="signal-eyebrow">QUALITY FLAGS</Typography><Typography component="h2">本次需要注意</Typography></Box>
            <WarningAmberRoundedIcon />
          </Box>
          <Box className="finding-list">
            {findings.map((finding) => (
              <Box className="finding-row" key={finding.code}>
                <span />
                <Box><strong>{findingLabels[finding.code] || finding.code}</strong><small>{finding.code === 'duplicate_waveform_timestamps' ? `${formatNumber(finding.count)} 筆` : '分析前應納入品質篩選'}</small></Box>
              </Box>
            ))}
          </Box>
          <Box className="report-verdict">
            <strong>結論</strong>
            <span>可進行資料工程與模型整合測試；AO 準確度需待模型／標準答案後才能評估。</span>
          </Box>
        </section>
      </Box>

      <footer className="signal-report-footer">
        <span>AllCare365 · Continuous Physiological Data Integration</span>
        <span>Technical data-quality report · Not for diagnosis</span>
      </footer>
    </Box>
  );
}

export default ContinuousSignalReport;
