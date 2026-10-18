import React from 'react';
import {vi} from 'vitest';
import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import ContinuousSignalReport from './ContinuousSignalReport';
import {api} from '../config/api';
vi.mock('../config/api',()=>({default:{ENDPOINTS:{CONTINUOUS_SIGNAL_REPORT:'/signals/latest/'}},api:{get:vi.fn()},parseApiResponse:async r=>r.payload}));
const response=payload=>({ok:true,payload});
beforeEach(()=>api.get.mockReset());

test('no data is distinct from an imported session with zero AO output',async()=>{
 api.get.mockResolvedValue(response({available:false}));
 render(<ContinuousSignalReport/>);
 await screen.findByRole('heading',{name:'尚無監測資料'});
 expect(screen.queryByText('AO 輸出：0 筆')).not.toBeInTheDocument();
 expect(screen.queryByRole('heading',{name:'主要波形覆蓋'})).not.toBeInTheDocument();
});

test('failed load offers retry and recovery keeps absent counts distinct from zero',async()=>{
 api.get.mockRejectedValueOnce(new Error('Synthetic unavailable')).mockResolvedValueOnce(response({available:true,ao_readiness:{outputs:0},limitations:['Unknown source note']}));
 render(<ContinuousSignalReport/>);
 const notice=await screen.findByRole('alert');
 expect(notice).toHaveTextContent('Synthetic unavailable');
 await waitFor(()=>expect(notice).toHaveFocus());
 fireEvent.click(screen.getByRole('button',{name:'重試'}));
 await screen.findByRole('heading',{name:'AO 模型執行與輸出'});
 expect(api.get).toHaveBeenCalledTimes(2);
 expect(screen.getByText('本次未提供波形覆蓋摘要。')).toBeInTheDocument();
 expect(screen.getByText('本次未提供數值訊號摘要。')).toBeInTheDocument();
 expect(screen.getByText('AO 輸出：0 筆')).toBeInTheDocument();
 const metrics=document.querySelector('.signal-metrics');
 expect(within(metrics).getAllByText('—')).toHaveLength(4);
 expect(screen.getByText('Unknown source note')).toBeInTheDocument();
 expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('leaving aborts a pending load and a late response cannot render the report',async()=>{
 let finish;
 api.get.mockReturnValue(new Promise(resolve=>{finish=resolve;}));
 const view=render(<ContinuousSignalReport/>);
 expect(screen.getByRole('status')).toHaveTextContent('正在讀取');
 const signal=api.get.mock.calls[0][1].signal;
 view.unmount();
 expect(signal.aborted).toBe(true);
 await act(async()=>finish(response({available:true,ao_readiness:{outputs:12}})));
 expect(screen.queryByText('AO 輸出：12 筆')).not.toBeInTheDocument();
});

test('zero coverage remains measured while absent coverage is unavailable',async()=>{api.get.mockResolvedValue(response({available:true,waveform_signals:[{signal:'SCG',coverage_pct:0},{signal:'ECG_II',coverage_pct:null}]}));render(<ContinuousSignalReport/>);const meter=await screen.findByRole('meter',{name:'SCG 胸壁微震覆蓋率'});expect(meter).toHaveAttribute('aria-valuenow','0');expect(meter).toHaveAttribute('aria-valuetext','0%');expect(screen.queryByRole('meter',{name:'ECG II 心電圖覆蓋率'})).not.toBeInTheDocument();expect(screen.getByText('未提供覆蓋率')).toBeInTheDocument();});


test('whitespace and boolean source values cannot masquerade as numeric measurements',async()=>{api.get.mockResolvedValue(response({available:true,session:{duration_hours:'  '},import:{raw_waveform_samples:false,database_observations:'12'},waveform_signals:[{signal:'SCG',coverage_pct:true},{signal:'ECG_II',coverage_pct:'  '},{signal:'IR_PPG',coverage_pct:'0'}]}));render(<ContinuousSignalReport/>);const meter=await screen.findByRole('meter',{name:'IR PPG 脈搏波覆蓋率'});expect(meter).toHaveAttribute('aria-valuenow','0');expect(screen.getAllByRole('meter')).toHaveLength(1);expect(screen.getAllByText('未提供覆蓋率')).toHaveLength(2);const metrics=document.querySelector('.signal-metrics');expect(within(metrics).getAllByText('—')).toHaveLength(3);expect(within(metrics).getByText('12')).toBeInTheDocument();});


test('summary and meters reject out-of-range percentages while measured zero stays valid',async()=>{api.get.mockResolvedValue(response({available:true,waveform_signals:[{signal:'SCG',coverage_pct:120}],numeric_signals:[{signal:'HR',valid_pct:-1},{signal:'SPO2',valid_pct:null},{signal:'RR',valid_pct:0}]}));render(<ContinuousSignalReport/>);await screen.findByRole('heading',{name:'主要波形覆蓋'});expect(screen.queryByRole('meter')).not.toBeInTheDocument();expect(screen.queryByText('120')).not.toBeInTheDocument();expect(screen.getAllByText('有效率未提供')).toHaveLength(2);expect(screen.getByText('0% 有效')).toBeInTheDocument();expect(within(document.querySelector('.signal-metrics')).getAllByText('—')).toHaveLength(4);});


test.each([[true,'—','目前未提供 AO 輸出數量。'],['0','0','目前沒有 AO 輸出紀錄。'],[-1,'—','目前未提供 AO 輸出數量。'],[1.5,'—','目前未提供 AO 輸出數量。']])('AO output value %s keeps count and narrative consistent',async(value,count,narrative)=>{api.get.mockResolvedValue(response({available:true,ao_readiness:{outputs:value}}));render(<ContinuousSignalReport/>);expect(await screen.findByText('AO 輸出：'+count+' 筆')).toBeInTheDocument();expect(screen.getByText(text=>text.startsWith(narrative))).toBeInTheDocument();expect(within(document.querySelector('.ao-checkpoints')).getAllByText(count+' 筆').length).toBeGreaterThan(0);expect(screen.queryByText(text=>text.startsWith('已有 AO 輸出紀錄。'))).not.toBeInTheDocument();});
