vi.mock('../hooks/useAuth', () => ({ useAuth: () => ({ userInfo: { role: 'manager' } }) }));
import React from 'react';
import { vi } from 'vitest';
import { act, render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom';
import PatientChart from './PatientChart';
import PatientManagement from './PatientManagement';
import { api } from '../config/api';
vi.mock('../config/api', () => ({ default: { ENDPOINTS: { PATIENTS: '/api/patients/' } }, api: { get: vi.fn(), post: vi.fn() }, parseApiResponse: response => Promise.resolve(response.payload) }));
const patient = { id: 7, full_name: 'Synthetic Test Patient', medical_record_number: 'TEST-007', status: 'inactive' };
const response = payload => ({ ok: true, payload });
const mount = () => render(<MemoryRouter><PatientManagement /></MemoryRouter>);
beforeEach(() => { api.get.mockReset(); api.post.mockReset(); });
test('uses backend count and enables pagination with accessible chart links', async () => {
 api.get.mockResolvedValueOnce(response({ count: 26, results: [patient], next: '/api/patients/?page=2' })).mockResolvedValueOnce(response({ count:26, results:[], next:null }));
 mount();
 expect(await screen.findByText('共 26 位病患')).toBeInTheDocument();
 expect(screen.getByRole('link',{name:patient.full_name})).toHaveAttribute('href','/patients/7');
 expect(screen.getByText('已停用')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'下一頁'}));
 await waitFor(() => expect(api.get).toHaveBeenLastCalledWith('/api/patients/?page=2',expect.any(Object)));
 expect(await screen.findByText('第 2 頁 · 本頁 0 位')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'下一頁'})).toBeDisabled();
});
test('a response from an earlier search cannot replace newer results', async () => {
 let resolveOld;
 api.get.mockReturnValueOnce(new Promise(resolve => { resolveOld = resolve; })).mockResolvedValueOnce(response({count:1,results:[patient],next:null}));
 mount();
 await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
 const firstSignal = api.get.mock.calls[0][1].signal;
 fireEvent.change(screen.getByLabelText('搜尋姓名或 MRN'),{target:{value:'TEST'}});
 expect(firstSignal.aborted).toBe(true);
 expect(await screen.findByRole('link',{name:patient.full_name})).toBeInTheDocument();
 await act(async () => { resolveOld(response({ count:1,results:[{id:99,full_name:'Obsolete Search Result'}] })); });
 await waitFor(() => expect(screen.getByRole('table')).toHaveAttribute('aria-busy','false'));
 expect(screen.queryByText('Obsolete Search Result')).not.toBeInTheDocument();
});
test('error clears old records, offers retry and does not imply an empty dataset', async () => {
 api.get.mockResolvedValueOnce(response({count:1,results:[patient]})).mockResolvedValueOnce({ok:false,payload:{detail:'Permission denied'}}).mockResolvedValueOnce(response({count:0,results:[]}));
 mount();
 await screen.findByRole('link',{name:patient.full_name});
 fireEvent.click(screen.getByRole('button',{name:'重新整理'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Permission denied');
 expect(screen.queryByRole('link',{name:patient.full_name})).not.toBeInTheDocument();
 expect(screen.queryByText('從第一位病患開始')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'重新載入清單'}));
 expect(await screen.findByText('從第一位病患開始')).toBeInTheDocument();
});
test('create errors remain visible inside the named dialog with entered values', async () => {
 api.get.mockResolvedValue(response({count:0,results:[]}));
 api.post.mockResolvedValue({ok:false,payload:{detail:'Unable to create patient'}});
 mount();
 fireEvent.click(screen.getByRole('button',{name:'新增病患'}));
 const dialog=screen.getByRole('dialog',{name:'新增病患',exact:true});
 expect(dialog).toHaveAccessibleDescription('建立基本資料，開始累積照護紀錄。標示 * 的欄位為必填。');
 expect(within(dialog).getByLabelText(/^名/)).toHaveFocus();
 fireEvent.mouseDown(within(dialog).getByRole('combobox',{name:'性別'}));
 fireEvent.click(screen.getByRole('option',{name:'其他',exact:true}));
 fireEvent.change(within(dialog).getByLabelText(/^名/),{target:{value:'Test'}});
 fireEvent.change(within(dialog).getByLabelText(/^姓/),{target:{value:'Synthetic'}});
 fireEvent.change(within(dialog).getByLabelText(/^出生日期/),{target:{value:'2000-01-01'}});
 fireEvent.submit(dialog.querySelector('form'));
 expect(await within(dialog).findByRole('alert')).toHaveTextContent('Unable to create patient');
 expect(api.post).toHaveBeenCalledWith('/api/patients/',expect.objectContaining({sex:'O'}));
 expect(within(dialog).getByLabelText(/^名/)).toHaveValue('Test');
 expect(within(dialog).getByRole('button',{name:'取消'})).toBeEnabled();
});

test('pending creation freezes entered data and ignores repeated submit events', async () => {
 let finish;
 api.get.mockResolvedValue(response({count:0,results:[]}));
 api.post.mockReturnValue(new Promise(resolve => { finish=resolve; }));
 mount();
 fireEvent.click(screen.getByRole('button',{name:'新增病患'}));
 const dialog=screen.getByRole('dialog',{name:/新增病患/});
 fireEvent.change(within(dialog).getByLabelText(/^名/),{target:{value:'Test'}});
 fireEvent.change(within(dialog).getByLabelText(/^姓/),{target:{value:'Synthetic'}});
 fireEvent.change(within(dialog).getByLabelText(/^出生日期/),{target:{value:'2000-01-01'}});
 const form=dialog.querySelector('form');
 fireEvent.submit(form);
 fireEvent.submit(form);
 expect(api.post).toHaveBeenCalledTimes(1);
 expect(form).toHaveAttribute('aria-busy','true');
 for (const input of form.querySelectorAll('input')) expect(input).toBeDisabled();
 expect(within(dialog).getByRole('button',{name:'取消'})).toBeDisabled();
 fireEvent.keyDown(dialog,{key:'Escape'});
 expect(screen.getByRole('dialog')).toBeInTheDocument();
 await act(async () => finish({ok:false,payload:{detail:'Synthetic save failure'}}));
 expect(await within(dialog).findByRole('alert')).toHaveTextContent('Synthetic save failure');
 expect(form).toHaveAttribute('aria-busy','false');
 expect(within(dialog).getByLabelText(/^名/)).toBeEnabled();
 expect(within(dialog).getByLabelText(/^名/)).toHaveValue('Test');
});

test('creation success survives return from page two even when list refresh fails', async () => {
 api.get.mockResolvedValueOnce(response({count:26,results:[patient],next:'/api/patients/?page=2'}))
 .mockResolvedValueOnce(response({count:26,results:[patient],next:null}))
 .mockResolvedValueOnce({ok:false,payload:{detail:'Synthetic list refresh failure'}});
 api.post.mockResolvedValue(response({id:8}));
 mount();
 await screen.findByText('共 26 位病患');
 fireEvent.click(screen.getByRole('button',{name:'下一頁'}));
 await screen.findByText('第 2 頁 · 本頁 1 位');
 fireEvent.click(screen.getByRole('button',{name:'新增病患'}));
 const dialog=screen.getByRole('dialog',{name:/新增病患/});
 fireEvent.change(within(dialog).getByLabelText(/^名/),{target:{value:'Test'}});
 fireEvent.change(within(dialog).getByLabelText(/^姓/),{target:{value:'Synthetic'}});
 fireEvent.change(within(dialog).getByLabelText(/^出生日期/),{target:{value:'2000-01-01'}});
 fireEvent.submit(dialog.querySelector('form'));
 expect(await screen.findByText('病患已新增')).toBeInTheDocument();
 expect(await screen.findByRole('alert')).toHaveTextContent('Synthetic list refresh failure');
 expect(screen.getByText('病患已新增').closest('[role="status"]')).toBeInTheDocument();
 expect(api.get).toHaveBeenLastCalledWith('/api/patients/?page=1',expect.any(Object));
 expect(api.post).toHaveBeenCalledTimes(1);
});

function RegistryJourney() {
 const navigate=useNavigate();
 return <><button onClick={()=>navigate(-1)}>Test browser back</button><Routes><Route path="/patients" element={<PatientManagement/>}/><Route path="/patients/:patientId" element={<PatientChart/>}/></Routes></>;
}
test.each(['chart return','browser back'])('restores search and page after %s',async(returnMethod)=>{
 api.get.mockImplementation(url=>Promise.resolve(url==='/api/patients/7/' ? response({...patient,allergies:[]}) : response({count:26,results:[patient],next:'/api/patients/?page=2'})));
 render(<MemoryRouter initialEntries={['/patients']}><RegistryJourney/></MemoryRouter>);
 await screen.findByRole('link',{name:patient.full_name});
 fireEvent.change(screen.getByLabelText('搜尋姓名或 MRN'),{target:{value:'TEST-007'}});
 await waitFor(()=>expect(api.get).toHaveBeenLastCalledWith('/api/patients/?page=1&search=TEST-007',expect.any(Object)));
 await screen.findByRole('link',{name:patient.full_name});
 fireEvent.click(screen.getByRole('button',{name:'下一頁'}));
 await screen.findByText('第 2 頁 · 本頁 1 位');
 fireEvent.click(screen.getByRole('link',{name:patient.full_name}));
 await screen.findByRole('heading',{name:patient.full_name});
 if(returnMethod==='chart return') fireEvent.click(screen.getByRole('link',{name:'返回病患清單'}));
 else fireEvent.click(screen.getByRole('button',{name:'Test browser back'}));
 expect(await screen.findByLabelText('搜尋姓名或 MRN')).toHaveValue('TEST-007');
 await screen.findByText('第 2 頁 · 本頁 1 位');
 expect(api.get).toHaveBeenLastCalledWith('/api/patients/?page=2&search=TEST-007',expect.any(Object));
});
