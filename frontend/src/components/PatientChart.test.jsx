vi.mock('../hooks/useAuth', () => ({ useAuth: () => ({ userInfo: { role: 'manager' } }) }));
import React from 'react';
import { vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom';
import PatientChart from './PatientChart';
import { api } from '../config/api';
vi.mock('../config/api', () => ({default:{ENDPOINTS:{PATIENTS:'/api/patients/'}},api:{get:vi.fn()},parseApiResponse:r=>Promise.resolve(r.payload)}));
const base={id:7,full_name:'Synthetic Chart Patient',age:null,status:'inactive',allergies:[],medications:[],care_team:[],clinical_notes:[],medical_orders:[]};
const response=patient=>({ok:true,payload:patient});
function Harness(){const navigate=useNavigate();return <><button onClick={()=>navigate('/patients/8')}>Switch test patient</button><Routes><Route path="/patients/:patientId" element={<PatientChart/>}/></Routes></>;}
const mount=()=>render(<MemoryRouter initialEntries={['/patients/7']}><Harness/></MemoryRouter>);
beforeEach(()=>api.get.mockReset());
test('exposes sourced allergies, linked tabs, document content and patient-specific risk action',async()=>{
 api.get.mockResolvedValue(response({...base,allergies:[{id:1,substance:'Synthetic allergen',reaction:'Test reaction',severity:'Test severity'}],clinical_notes:[{id:2,note_type:'progress',content:'Synthetic note line 1\nLine 2',document_date:'2026-10-09'}]}));
 mount();await screen.findByRole('heading',{name:base.full_name});
 expect(screen.getByRole('link',{name:'風險分析'})).toHaveAttribute('href','/risk-analysis?patient_id=7');
 expect(screen.getByText('年齡未提供')).toBeInTheDocument();expect(screen.getByText('已停用')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('tab',{name:'過敏 1'}));
 const allergyPanel=screen.getByRole('tabpanel',{name:'過敏 1'});
 expect(allergyPanel).toHaveAttribute('id','chart-panel-allergies');expect(allergyPanel).toHaveTextContent('Test severity');
 fireEvent.click(screen.getByRole('tab',{name:'文件 1'}));expect(screen.getByRole('tabpanel',{name:'文件 1'})).toHaveTextContent('Synthetic note line 1');
});
test('no recorded allergies does not claim absence of allergies',async()=>{
 api.get.mockResolvedValue(response(base));mount();await screen.findByRole('heading',{name:base.full_name});
 expect(screen.getByText(/過敏狀態待補充/)).toBeInTheDocument();fireEvent.click(screen.getByRole('tab',{name:'過敏 0'}));
 expect(screen.getByRole('tabpanel',{name:'過敏 0'})).toHaveTextContent('尚無過敏紀錄');
 expect(screen.getByRole('tabpanel')).toHaveTextContent('補充過敏物質與反應');
});
test('failed chart can retry with clear loading status',async()=>{
 api.get.mockResolvedValueOnce({ok:false,payload:{detail:'Access unavailable'}}).mockResolvedValueOnce(response(base));mount();
 expect(await screen.findByRole('alert')).toHaveTextContent('Access unavailable');
 fireEvent.click(screen.getByRole('button',{name:'重新載入病歷'}));
 expect(await screen.findByRole('heading',{name:base.full_name})).toBeInTheDocument();expect(api.get).toHaveBeenCalledTimes(2);
});
test('patient switch cancels old request and does not render late patient records',async()=>{
 let resolveOld;api.get.mockReturnValueOnce(new Promise(resolve=>{resolveOld=resolve;})).mockResolvedValueOnce(response({...base,id:8,full_name:'Second Synthetic Patient'}));
 mount();await waitFor(()=>expect(api.get).toHaveBeenCalledTimes(1));const signal=api.get.mock.calls[0][1].signal;
 fireEvent.click(screen.getByRole('button',{name:'Switch test patient'}));expect(signal.aborted).toBe(true);
 await screen.findByRole('heading',{name:'Second Synthetic Patient'});await act(async()=>{resolveOld(response(base));});
 expect(screen.queryByRole('heading',{name:base.full_name})).not.toBeInTheDocument();
});
test('wrong-patient response is rejected before any identifying record is displayed',async()=>{
 api.get.mockResolvedValue(response({...base,id:8,full_name:'Wrong Synthetic Patient'}));mount();
 expect(await screen.findByRole('alert')).toHaveTextContent('病歷資料格式不完整');expect(screen.queryByText('Wrong Synthetic Patient')).not.toBeInTheDocument();
});
