import React from 'react';
import { vi } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import ContinuousSignalReport from './ContinuousSignalReport';
import ResearchCohorts from './ResearchCohorts';
import { api } from '../config/api';
vi.mock('../config/api',()=>({default:{ENDPOINTS:{CONTINUOUS_SIGNAL_REPORT:'/signal/',DATA_QUALITY_SUMMARY:'/quality/',COHORT_SUMMARY:'/cohort/',PATIENTS_LIKE_THIS:'/similar/'}},api:{get:vi.fn()},parseApiResponse:r=>Promise.resolve(r.payload)}));
const response=payload=>({ok:true,payload});
const report={available:true,session:{duration_hours:3.5},import:{status:'pending',raw_waveform_samples:null,database_observations:0},fhir:{quality_result_traceable:false,resources:[]},ao_readiness:{outputs:1,model_runs:2,ground_truth_records:0},numeric_signals:[{signal:'PR',median:null,valid_pct:0}],waveform_signals:[],limitations:['Synthetic source limitation']};
beforeEach(()=>{api.get.mockReset();});
test('signal report reflects duration, AO outputs and pending import without inventing completion',async()=>{
 api.get.mockResolvedValue(response(report));render(<ContinuousSignalReport/>);
 expect(await screen.findByText('匯入狀態：等待處理')).toBeInTheDocument();expect(screen.getByText('FHIR 追溯：尚未建立')).toBeInTheDocument();expect(screen.getByText(/已有 AO 輸出紀錄/)).toBeInTheDocument();expect(screen.getByText(/本次 3.5 小時/)).toBeInTheDocument();expect(screen.getByText('Synthetic source limitation')).toBeInTheDocument();expect(screen.queryByText('資料庫匯入成功')).not.toBeInTheDocument();expect(screen.queryByText(/20.95/)).not.toBeInTheDocument();
 const source=screen.getByText('來源波形').closest('.signal-metric');expect(within(source).getByText('—')).toBeInTheDocument();const numeric=screen.getByText('脈搏率').closest('.numeric-card');expect(within(numeric).getByText('—')).toBeInTheDocument();expect(within(numeric).getByText('0% 有效')).toBeInTheDocument();
});
test('signal report retries an error and aborts its request on unmount',async()=>{
 api.get.mockRejectedValueOnce(new Error('Synthetic outage')).mockResolvedValueOnce(response(report));const view=render(<ContinuousSignalReport/>);await screen.findByText('Synthetic outage');fireEvent.click(screen.getByRole('button',{name:'重試'}));await screen.findByText('匯入狀態：等待處理');const signal=api.get.mock.calls[1][1].signal;view.unmount();expect(signal.aborted).toBe(true);
});
test('editing cohort criteria invalidates results and rejects late responses',async()=>{
 let complete;api.get.mockImplementation(endpoint=>endpoint==='/quality/'?Promise.resolve(response({})):new Promise(resolve=>{complete=resolve;}));render(<ResearchCohorts/>);fireEvent.click(screen.getByRole('button',{name:'查詢族群'}));expect(screen.getAllByText('查詢中…')).toHaveLength(3);const signal=api.get.mock.calls.find(call=>call[0]==='/cohort/')[1].signal;fireEvent.change(screen.getByRole('spinbutton',{name:'年齡下限'}),{target:{value:'40'}});expect(signal.aborted).toBe(true);await act(async()=>complete(response({dataset:'Stale synthetic cohort',cohort_count:9})));expect(screen.queryByText('Stale synthetic cohort')).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'查詢族群'})).toBeEnabled();
});
test('invalid cohort range is rejected before API query',async()=>{
 api.get.mockResolvedValue(response({}));render(<ResearchCohorts/>);fireEvent.change(screen.getByRole('spinbutton',{name:'年齡下限'}),{target:{value:'70'}});fireEvent.change(screen.getByRole('spinbutton',{name:'年齡上限'}),{target:{value:'30'}});fireEvent.click(screen.getByRole('button',{name:'查詢族群'}));expect(screen.getByText(/下限或起始日期不得超過/)).toBeInTheDocument();expect(screen.getAllByText('查詢未完成')).toHaveLength(3);expect(api.get.mock.calls.every(call=>call[0]==='/quality/')).toBe(true);await act(async()=>{});
});
test('zero similarity is visible and editing profile clears the prior result',async()=>{
 api.get.mockImplementation(endpoint=>Promise.resolve(response(endpoint==='/similar/'?{matched_count:12,average_similarity:0,summary:{},privacy:{}}:{})));render(<ResearchCohorts/>);fireEvent.click(screen.getByRole('button',{name:'查詢相似族群'}));expect(screen.getAllByText('比對中…')).toHaveLength(4);await screen.findByText('0%');expect(screen.getByText('未提供')).toBeInTheDocument();fireEvent.change(screen.getByRole('spinbutton',{name:'年齡'}),{target:{value:'45'}});expect(screen.queryByText('0%')).not.toBeInTheDocument();
});

test('signal loading and empty states retain page identity without fabricated metrics',async()=>{
 let complete; api.get.mockImplementation(()=>new Promise(resolve=>{complete=resolve;}));
 render(<ContinuousSignalReport/>);
 expect(screen.getByRole('heading',{level:1,name:/連續生理資料/})).toBeInTheDocument();
 expect(screen.getByRole('status')).toHaveTextContent('正在讀取資料庫分析結果');
 await act(async()=>complete(response({available:false})));
 expect(screen.getByRole('heading',{level:1,name:/連續生理資料/})).toBeInTheDocument();
 expect(screen.getByRole('heading',{level:2,name:'尚無監測資料'})).toBeInTheDocument();
 expect(screen.queryByText('監測時間')).not.toBeInTheDocument();
 expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

test('cohort quality distinguishes measured zero from unavailable coverage',async()=>{api.get.mockResolvedValue(response({feature_coverage:{sbp:{coverage:0},hba1c:{coverage:null}}}));render(<ResearchCohorts/>);const meter=await screen.findByRole('meter',{name:'SBP 資料覆蓋率'});expect(meter).toHaveAttribute('aria-valuenow','0');expect(meter).toHaveAttribute('aria-valuetext','0%');expect(screen.queryByRole('meter',{name:'HBA1C 資料覆蓋率'})).not.toBeInTheDocument();expect(screen.getByText('未提供')).toBeInTheDocument();});


test('cohort demographics preserve zero and reject invalid numeric representations',async()=>{api.get.mockImplementation(endpoint=>Promise.resolve(response(endpoint==='/cohort/'?{cohort_count:12,summary:{demographics:{age:{mean:false,min:' ',max:90},sex:{F:0,M:NaN}}}}:{})));render(<ResearchCohorts/>);fireEvent.click(screen.getByRole('button',{name:'查詢族群'}));await screen.findByText('未釋出 - 90');const mean=within(document.querySelector('.cohort-demographics')).getByText('平均年齡');expect(within(mean.closest('.demographic-stat')).getByText('未釋出')).toBeInTheDocument();expect(within(screen.getByText('女性').closest('.demographic-stat')).getByText('0')).toBeInTheDocument();expect(within(screen.getByText('男性').closest('.demographic-stat')).getByText('未釋出')).toBeInTheDocument();expect(screen.getByText('未釋出 - 90')).toBeInTheDocument();});


test('research percentages reject boolean and blank source values without losing numeric-string zero',async()=>{api.get.mockImplementation(endpoint=>Promise.resolve(response(endpoint==='/quality/'?{feature_coverage:{sbp:{coverage:true},hba1c:{coverage:' '},ldl:{coverage:'0'}}}:endpoint==='/similar/'?{matched_count:12,average_similarity:false,summary:{}}:{})));render(<ResearchCohorts/>);const meter=await screen.findByRole('meter',{name:'LDL 資料覆蓋率'});expect(meter).toHaveAttribute('aria-valuenow','0');expect(screen.getAllByRole('meter')).toHaveLength(1);expect(screen.queryByRole('meter',{name:'SBP 資料覆蓋率'})).not.toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'查詢相似族群'}));await screen.findByText('12');expect(within(screen.getByText('平均相似度').closest('.similar-stat')).getByText('未釋出')).toBeInTheDocument();});
