import React from 'react';
import { vi } from 'vitest';
import { act, fireEvent, render, screen, within, waitFor } from '@testing-library/react';
import ResearchReports from './ResearchReports';
import { api } from '../config/api';
import { useAuth } from '../hooks/useAuth';
vi.mock('../hooks/useAuth',()=>({useAuth:vi.fn()}));
vi.mock('../config/api',()=>({default:{ENDPOINTS:{RESEARCH_REPORTS:'/reports/'}},api:{get:vi.fn(),post:vi.fn()},parseApiResponse:r=>Promise.resolve(r.payload)}));
const report={id:1,title:'Synthetic Research Report',status:'requested',report_type:'cohort_summary',privacy_json:{},artifact_available:false};
beforeEach(()=>{api.get.mockReset();api.post.mockReset();useAuth.mockReturnValue({userInfo:{role:'clinician'}});});
test('queue count is scoped, privacy is unknown and pages use backend totals',async()=>{
 api.get.mockResolvedValueOnce({ok:true,payload:{count:26,next:'/reports/?page=2',results:[report]}}).mockResolvedValueOnce({ok:true,payload:{count:26,next:null,results:[]}});render(<ResearchReports/>);
 expect(await screen.findByText('符合條件共 26 份報告')).toBeInTheDocument();expect(screen.getByText('本頁待審核 1')).toBeInTheDocument();expect(screen.getByText(/未提供遮蔽狀態/)).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'下一頁'}));expect(await screen.findByText('第 2 頁 · 本頁 0 份')).toBeInTheDocument();expect(api.get).toHaveBeenLastCalledWith('/reports/?page=2&status=requested',expect.any(Object));
});
test('approval failure is visible within the dialog and keeps its note',async()=>{
 api.get.mockResolvedValue({ok:true,payload:{results:[report],count:1}});api.post.mockResolvedValue({ok:false,payload:{detail:'Test approval unavailable'}});render(<ResearchReports/>);await screen.findByText(report.title);expect(screen.getByRole('button',{name:'核准'})).toHaveAccessibleDescription(report.title);expect(screen.getByRole('button',{name:'拒絕'})).toHaveAccessibleDescription(report.title);fireEvent.click(screen.getByRole('button',{name:'核准'}));const dialog=screen.getByRole('dialog',{name:'核准研究報告'});expect(dialog).toHaveAccessibleDescription(report.title);
 fireEvent.change(within(dialog).getByLabelText('審核備註'),{target:{value:'Synthetic review note'}});fireEvent.click(within(dialog).getByRole('button',{name:'核准'}));expect(await within(dialog).findByRole('alert')).toHaveTextContent('Test approval unavailable');await waitFor(()=>expect(within(dialog).getByRole('alert')).toHaveFocus());expect(within(dialog).getByLabelText('審核備註')).toHaveValue('Synthetic review note');
});
test('researcher cannot see review actions and failure does not look like an empty queue',async()=>{
 useAuth.mockReturnValue({userInfo:{role:'researcher'}});api.get.mockResolvedValueOnce({ok:false,payload:{detail:'Test queue unavailable'}}).mockResolvedValueOnce({ok:true,payload:{results:[report],count:1}});render(<ResearchReports/>);expect(await screen.findByRole('alert')).toHaveTextContent('Test queue unavailable');expect(screen.queryByText('目前沒有符合條件的研究報告。')).not.toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'重新整理'}));await screen.findByText(report.title);expect(screen.queryByRole('button',{name:'核准'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'拒絕'})).not.toBeInTheDocument();
});

test('array snapshots are described as loaded records rather than backend totals',async()=>{
 api.get.mockResolvedValue({ok:true,payload:[report]});render(<ResearchReports/>);
 expect(await screen.findByText('本次載入 1 份報告')).toBeInTheDocument();
 expect(screen.queryByText(/符合條件共/)).not.toBeInTheDocument();
 expect(screen.getByText('本次清單 · 1 份')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'下一頁'})).toBeDisabled();
});

test('a capped array snapshot explains that earlier reports may not be included',async()=>{
 useAuth.mockReturnValue({userInfo:{role:'researcher'}});
 api.get.mockResolvedValue({ok:true,payload:Array.from({length:100},(_,index)=>({...report,id:index+1,title:'Synthetic report '+index}))});
 render(<ResearchReports/>);
 expect(await screen.findByText('本次載入 100 份報告')).toBeInTheDocument();
 expect(screen.getByText(/本次清單已達 100 份上限/)).toBeInTheDocument();
 expect(screen.queryByText(/符合條件共/)).not.toBeInTheDocument();
});

test('request submission locks its input and sends one decimal-filter payload',async()=>{
 let finish;
 api.get.mockResolvedValue({ok:true,payload:[]});
 api.post.mockReturnValue(new Promise(resolve=>{finish=resolve;}));render(<ResearchReports/>);
 fireEvent.change(screen.getByLabelText(/^標題/),{target:{value:'Synthetic request'}});
 const decimal=screen.getByLabelText('HbA1c 下限');fireEvent.change(decimal,{target:{value:'6.5'}});
 expect(decimal.checkValidity()).toBe(true);
 const form=screen.getByLabelText(/^標題/).closest('form');
 fireEvent.submit(form);fireEvent.submit(form);
 expect(api.post).toHaveBeenCalledTimes(1);
 expect(api.post).toHaveBeenCalledWith('/reports/',{title:'Synthetic request',report_type:'cohort_summary',query_params:{hba1c_min:'6.5'}});
 expect(form).toHaveAttribute('aria-busy','true');
 expect(screen.getByLabelText(/^標題/)).toBeDisabled();
 expect(screen.getByRole('combobox',{name:'報告類型'})).toHaveAttribute('aria-disabled','true');
 await act(async()=>{finish({ok:false,payload:{detail:'Synthetic request unavailable'}});});
 expect(await screen.findByRole('alert')).toHaveTextContent('Synthetic request unavailable');
 await waitFor(()=>expect(screen.getByRole('alert')).toHaveFocus());
 expect(screen.getByRole('form',{name:'申請研究報告'})).toBeInTheDocument();expect(decimal).toHaveAccessibleDescription('%');
 expect(screen.getByLabelText(/^標題/)).toBeEnabled();
 expect(screen.getByLabelText(/^標題/)).toHaveValue('Synthetic request');
 expect(decimal).toHaveValue(6.5);
});

test('review failure releases the operation lock for an explicit retry',async()=>{
 api.get.mockResolvedValue({ok:true,payload:[report]});
 api.post.mockResolvedValueOnce({ok:false,payload:{detail:'Synthetic review failure'}}).mockResolvedValueOnce({ok:true,payload:{...report,status:'approved'}});
 render(<ResearchReports/>);await screen.findByText(report.title);
 fireEvent.click(screen.getByRole('button',{name:'核准'}));
 const dialog=screen.getByRole('dialog',{name:'核准研究報告'});
 fireEvent.click(within(dialog).getByRole('button',{name:'核准'}));
 await within(dialog).findByRole('alert');
 fireEvent.click(within(dialog).getByRole('button',{name:'核准'}));
 expect(await screen.findByText('研究報告已核准')).toBeInTheDocument();
 expect(api.post).toHaveBeenCalledTimes(2);
});

test('artifact failure stays in its named preview and can retry the selected report',async()=>{
 const approved={...report,status:'approved',artifact_available:true};
 api.get.mockResolvedValueOnce({ok:true,payload:[approved]})
 .mockResolvedValueOnce({ok:false,payload:{detail:'Synthetic artifact unavailable'}})
 .mockResolvedValueOnce({ok:true,payload:{synthetic_result:'complete'}});
 render(<ResearchReports/>);await screen.findByText(report.title);
 expect(screen.getByRole('button',{name:'檢視報告'})).toHaveAccessibleDescription(report.title);fireEvent.click(screen.getByRole('button',{name:'檢視報告'}));
 const dialog=screen.getByRole('dialog',{name:'研究報告預覽'});
 expect(within(dialog).getByText(report.title)).toBeInTheDocument();
 expect(await within(dialog).findByRole('alert')).toHaveTextContent('Synthetic artifact unavailable');
 expect(within(dialog).queryByLabelText('報告原始輸出')).not.toBeInTheDocument();
 fireEvent.click(within(dialog).getByRole('button',{name:'重新讀取'}));
 expect(await within(dialog).findByLabelText('報告原始輸出')).toHaveTextContent('complete');
 expect(api.get).toHaveBeenLastCalledWith('/reports/1/artifact/',expect.objectContaining({signal:expect.any(AbortSignal)}));
});

test('cancel aborts a pending preview and its late result cannot replace another report',async()=>{
 let finishOld;
 const approved={...report,status:'approved',artifact_available:true};
 const other={...approved,id:2,title:'Second Synthetic Report'};
 api.get.mockResolvedValueOnce({ok:true,payload:[approved,other]})
 .mockReturnValueOnce(new Promise(resolve=>{finishOld=resolve;}))
 .mockResolvedValueOnce({ok:true,payload:{synthetic_result:'Current preview'}});
 render(<ResearchReports/>);await screen.findByText(report.title);
 fireEvent.click(within(screen.getByText(report.title).closest('tr')).getByRole('button',{name:'檢視報告'}));
 const first=screen.getByRole('dialog',{name:'研究報告預覽'});
 expect(within(first).getByRole('status')).toHaveTextContent('正在讀取所選報告');
 const oldSignal=api.get.mock.calls[1][1].signal;
 fireEvent.click(within(first).getByRole('button',{name:'取消讀取'}));
 expect(oldSignal.aborted).toBe(true);
 fireEvent.click(await within(screen.getByText(other.title).closest('tr')).findByRole('button',{name:'檢視報告'}));
 const next=screen.getByRole('dialog',{name:'研究報告預覽'});
 expect(await within(next).findByLabelText('報告原始輸出')).toHaveTextContent('Current preview');
 await act(async()=>{finishOld({ok:true,payload:{synthetic_result:'Obsolete preview'}});});
 expect(within(next).getByText(other.title)).toBeInTheDocument();
 expect(screen.queryByText(/Obsolete preview/)).not.toBeInTheDocument();
});

test('leaving the report page aborts the active preview request',async()=>{
 let finish;
 api.get.mockResolvedValueOnce({ok:true,payload:[{...report,status:'approved',artifact_available:true}]})
 .mockReturnValueOnce(new Promise(resolve=>{finish=resolve;}));
 const view=render(<ResearchReports/>);await screen.findByText(report.title);
 fireEvent.click(screen.getByRole('button',{name:'檢視報告'}));
 const signal=api.get.mock.calls[1][1].signal;
 view.unmount();expect(signal.aborted).toBe(true);
 await act(async()=>{finish({ok:false,payload:{detail:'Synthetic obsolete failure'}});});
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
