import React from 'react';
import { vi } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from './Dashboard';
import { api } from '../config/api';
const auth=vi.hoisted(()=>({userInfo:{username:'Synthetic user',role:'clinician'}}));
vi.mock('../hooks/useAuth',()=>({useAuth:()=>auth}));
vi.mock('../config/api',()=>({default:{ENDPOINTS:{PATIENTS:'/patients/',HEALTH_SCREENINGS:'/screenings/',DATA_QUALITY_SUMMARY:'/quality/',RESEARCH_REPORTS:'/reports/'}},api:{get:vi.fn()},parseApiResponse:r=>Promise.resolve(r.payload)}));
const response=payload=>({ok:true,payload});
const mount=()=>render(<MemoryRouter><Dashboard/></MemoryRouter>);
beforeEach(()=>{api.get.mockReset();auth.userInfo={username:'Synthetic user',role:'clinician'};});
test('task links stay available during load and abort requests on unmount',()=>{
 api.get.mockReturnValue(new Promise(()=>{}));const view=mount();expect(screen.getByRole('link',{name:'病患管理'})).toHaveAttribute('href','/patients');expect(screen.getByRole('status')).toHaveTextContent('讀取資料概況');expect(screen.getByRole('button',{name:'整理中…'})).toBeDisabled();const signal=api.get.mock.calls[0][1].signal;view.unmount();expect(signal.aborted).toBe(true);
});
test('nonresearch account does not request or expose restricted research summaries',async()=>{
 auth.userInfo={username:'Synthetic basic',role:'patient'};api.get.mockResolvedValue(response({count:17,results:[]}));mount();await screen.findByRole('button',{name:'重新整理'});expect(api.get.mock.calls.map(call=>call[0])).toEqual(['/patients/?page_size=1','/screenings/?page_size=1']);expect(screen.queryByText('待審研究報告')).not.toBeInTheDocument();expect(screen.queryByRole('heading',{name:'資料品質摘要'})).not.toBeInTheDocument();expect(screen.queryByRole('link',{name:'研究報告'})).not.toBeInTheDocument();
});
test('partial failure preserves successful totals, marks missing values and can refresh',async()=>{
 api.get.mockImplementation(endpoint=>endpoint==='/quality/'?Promise.reject(new Error('Synthetic outage')):Promise.resolve(response({count:0,results:[]})));mount();await screen.findByText(/資料品質讀取失敗/);const metric=screen.getByText('病患數').closest('.dashboard-metric');expect(within(metric).getByText('0')).toBeInTheDocument();expect(screen.getByText('未提供')).toBeInTheDocument();
 api.get.mockResolvedValue(response({count:42,results:[]}));fireEvent.click(screen.getByRole('button',{name:'重新整理'}));await screen.findByRole('button',{name:'重新整理'});expect(within(metric).getByText('42')).toBeInTheDocument();expect(screen.queryByText(/資料品質讀取失敗/)).not.toBeInTheDocument();
});
test('a role change invalidates an earlier pending research response',async()=>{
 const pending=[];api.get.mockImplementation(()=>new Promise(resolve=>pending.push(resolve)));const view=mount();const oldSignal=api.get.mock.calls[0][1].signal;auth.userInfo={username:'Synthetic basic',role:'patient'};api.get.mockResolvedValue(response({count:2,results:[]}));view.rerender(<MemoryRouter><Dashboard/></MemoryRouter>);expect(oldSignal.aborted).toBe(true);await screen.findByRole('button',{name:'重新整理'});await act(async()=>pending.forEach(resolve=>resolve(response({count:999,results:[]}))));expect(screen.queryByText('999')).not.toBeInTheDocument();
});

test('capped report arrays show a loaded count with its limit beside the metric',async()=>{
 api.get.mockImplementation(endpoint=>Promise.resolve(response(endpoint==='/reports/?status=requested'
  ? Array.from({length:100},(_,index)=>({id:index+1,status:'requested'})) : {count:0,results:[]})));
 mount();await screen.findByRole('button',{name:'重新整理'});
 const metric=screen.getByText('待審研究報告').closest('.dashboard-metric');
 expect(within(metric).getByText('100')).toBeInTheDocument();
 expect(within(metric).getByText('本次載入已達 100 份上限，可能未包含更早申請。')).toBeInTheDocument();
 expect(within(metric).queryByText('符合條件的待審申請總數。')).not.toBeInTheDocument();
});

test('an explicit report total is distinguished from the current response length',async()=>{
 api.get.mockImplementation(endpoint=>Promise.resolve(response(endpoint==='/reports/?status=requested'
  ? {count:321,results:[{id:1,status:'requested'}],next:'/reports/?page=2'} : {count:0,results:[]})));
 mount();await screen.findByRole('button',{name:'重新整理'});
 const metric=screen.getByText('待審研究報告').closest('.dashboard-metric');
 expect(within(metric).getByText('321')).toBeInTheDocument();
 expect(within(metric).getByText('符合條件的待審申請總數。')).toBeInTheDocument();
});

test('a failed report request does not look like zero pending reports or a loaded snapshot',async()=>{
 api.get.mockImplementation(endpoint=>endpoint==='/reports/?status=requested'
  ? Promise.reject(new Error('Synthetic report outage')) : Promise.resolve(response({count:0,results:[]})));
 mount();await screen.findByText(/研究報告讀取失敗/);
 const metric=screen.getByText('待審研究報告').closest('.dashboard-metric');
 expect(within(metric).getByText('無資料')).toBeInTheDocument();
 expect(within(metric).queryByText('0')).not.toBeInTheDocument();
 expect(within(metric).queryByText(/本次載入/)).not.toBeInTheDocument();
});
