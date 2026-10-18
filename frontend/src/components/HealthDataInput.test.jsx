import React from 'react';
import { vi } from 'vitest';
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, useNavigate } from 'react-router-dom';
import HealthDataInput from './HealthDataInput';
import { api } from '../config/api';
vi.mock('../config/api',()=>({default:{ENDPOINTS:{PATIENTS:'/api/patients/',HEALTH_SCREENINGS:'/api/screenings/'}},api:{get:vi.fn(),post:vi.fn()},parseApiResponse:response=>Promise.resolve(response.payload)}));
const patient={id:73,full_name:'Synthetic Intake Patient',medical_record_number:'TEST-73',age:25};
const mount=(path='/health-data-input?patient_id=73')=>render(<MemoryRouter initialEntries={[path]}><HealthDataInput/></MemoryRouter>);
const choose=(name,value)=>{fireEvent.mouseDown(screen.getByRole('combobox',{name}));fireEvent.click(screen.getByRole('option',{name:value}));};
beforeEach(()=>{api.get.mockReset();api.post.mockReset();api.get.mockResolvedValue({ok:true,payload:patient});});
test('chart context fetches the exact patient and omits unknown answers with decimal measures',async()=>{
 api.post.mockResolvedValue({ok:true,payload:{id:91}});mount();
 const save=screen.getByRole('button',{name:'儲存'});await waitFor(()=>expect(save).toBeEnabled());
 expect(api.get).toHaveBeenCalledWith('/api/patients/73/',expect.any(Object));
 expect(screen.getByRole('combobox',{name:'病患'})).toHaveAttribute('aria-disabled','true');
 const weight=screen.getByRole('spinbutton',{name:'體重'});expect(weight).toHaveAttribute('step','any');expect(weight).toHaveAccessibleDescription('kg');expect(screen.getByRole('spinbutton',{name:'空腹血糖 FPG'})).toHaveAccessibleDescription('mg/dL');fireEvent.change(weight,{target:{value:'62.5'}});
 const height=screen.getByRole('spinbutton',{name:'身高'});fireEvent.change(height,{target:{value:'170'}});expect(screen.getByLabelText('計算 BMI')).toHaveTextContent('21.6');fireEvent.change(height,{target:{value:'-170'}});expect(screen.queryByLabelText('計算 BMI')).not.toBeInTheDocument();fireEvent.change(height,{target:{value:'170'}});
 fireEvent.click(save);await waitFor(()=>expect(api.post).toHaveBeenCalled());
 const payload=api.post.mock.calls[0][1];expect(payload.patient).toBe('73');expect(payload.vital_signs.body_weight).toBe(62.5);expect(payload.hq).toEqual({});expect(payload.problems).toEqual({});
 const feedback=(await screen.findByText('健檢資料已儲存')).closest('[role="status"]');
 expect(feedback).toHaveFocus();
 expect(await screen.findByRole('link',{name:'前往風險分析'})).toHaveAttribute('href','/risk-analysis?patient_id=73');
});
test('explicit yes/no answers remain distinct and smoking flags have one source',async()=>{
 api.post.mockResolvedValue({ok:false,payload:{detail:'Save test failed'}});mount();await waitFor(()=>expect(screen.getByRole('button',{name:'儲存'})).toBeEnabled());
 choose('糖尿病家族史','否');choose('糖尿病','是');choose('吸菸狀態','曾經吸菸');fireEvent.click(screen.getByRole('button',{name:'儲存'}));await screen.findByText('Save test failed');
 const payload=api.post.mock.calls[0][1];expect(payload.hq.family_history_diabetes).toBe(false);expect(payload.problems.has_diabetes).toBe(true);expect(payload.hq.current_smoker).toBe(false);expect(payload.hq.former_smoker).toBe(true);expect(payload.hq).not.toHaveProperty('heavy_alcohol');
});
test('a failed patient fetch can retry and a mismatched patient cannot be saved',async()=>{
 api.get.mockResolvedValueOnce({ok:false,payload:{detail:'Patient unavailable'}}).mockResolvedValueOnce({ok:true,payload:{...patient,id:74}});mount();
 expect(await screen.findByText('Patient unavailable')).toBeInTheDocument();expect(screen.queryByText('目前沒有符合的病患')).not.toBeInTheDocument();expect(screen.getByRole('status')).toHaveTextContent('病患資料尚未載入');expect(screen.getByRole('button',{name:'儲存'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'重試'}));expect(await screen.findByText('病患資料不符，請返回病歷重新開啟。')).toBeInTheDocument();expect(api.post).not.toHaveBeenCalled();
});
test('general entry searches beyond the initial patient page',async()=>{
 api.get.mockResolvedValueOnce({ok:true,payload:{results:[],count:0}}).mockResolvedValueOnce({ok:true,payload:{results:[patient],count:1}});mount('/health-data-input');
 await screen.findByText('目前沒有符合的病患');fireEvent.change(screen.getByLabelText('搜尋病患姓名或 MRN'),{target:{value:'TEST-73'}});
 await waitFor(()=>expect(api.get).toHaveBeenLastCalledWith('/api/patients/?search=TEST-73',expect.any(Object)));
 await screen.findByText('請選擇本次健檢的病患');choose('病患','Synthetic Intake Patient (TEST-73)');expect(screen.getByRole('button',{name:'儲存'})).toBeEnabled();
});

test('pending screening save freezes fields and ignores repeated submission, then allows retry',async()=>{
 let finish;api.post.mockReturnValueOnce(new Promise(resolve=>{finish=resolve;})).mockResolvedValueOnce({ok:false,payload:{detail:'Second synthetic failure'}});
 mount();await waitFor(()=>expect(screen.getByRole('button',{name:'儲存'})).toBeEnabled());
 const weight=screen.getByRole('spinbutton',{name:'體重'});fireEvent.change(weight,{target:{value:'62.5'}});
 const form=weight.closest('form');
 act(()=>{fireEvent.submit(form);fireEvent.submit(form);});
 expect(api.post).toHaveBeenCalledTimes(1);expect(weight).toBeDisabled();expect(screen.getByRole('button',{name:'儲存中'})).toBeDisabled();
 await act(async()=>finish({ok:false,payload:{detail:'First synthetic failure'}}));
 await screen.findByText('First synthetic failure');expect(screen.getByRole('alert')).toHaveFocus();expect(weight).toHaveValue(62.5);expect(weight).toBeEnabled();
 fireEvent.submit(form);await screen.findByText('Second synthetic failure');expect(api.post).toHaveBeenCalledTimes(2);
});

test('switching patients clears the previous draft and saved analysis destination',async()=>{
 const other={...patient,id:74,full_name:'Synthetic Second Patient',medical_record_number:'TEST-74'};
 api.get.mockResolvedValue({ok:true,payload:{results:[patient,other],count:2}});api.post.mockResolvedValue({ok:true,payload:{id:91}});mount('/health-data-input');
 await screen.findByText('請選擇本次健檢的病患');choose('病患','Synthetic Intake Patient (TEST-73)');
 fireEvent.click(screen.getByRole('button',{name:'儲存'}));await screen.findByRole('link',{name:'前往風險分析'});
 fireEvent.change(screen.getByRole('spinbutton',{name:'體重'}),{target:{value:'62.5'}});choose('糖尿病','是');
 choose('病患','Synthetic Second Patient (TEST-74)');
 expect(screen.getByRole('spinbutton',{name:'體重'})).toHaveValue(null);expect(screen.getByRole('combobox',{name:'糖尿病'})).not.toHaveTextContent('是');
 expect(screen.queryByRole('link',{name:'前往風險分析'})).not.toBeInTheDocument();expect(screen.queryByText('健檢資料已儲存')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'儲存'}));await waitFor(()=>expect(api.post).toHaveBeenCalledTimes(2));expect(api.post.mock.calls[1][1]).toMatchObject({patient:74,vital_signs:{},problems:{}});
});

function IntakeContextSwitch(){const navigate=useNavigate();return <><button onClick={()=>navigate('/health-data-input?patient_id=74')}>Switch synthetic context</button><HealthDataInput/></>;}
test.each([true,false])('late save response from a previous patient context is ignored (success=%s)',async(ok)=>{
 const other={...patient,id:74,full_name:'Synthetic Second Patient',medical_record_number:'TEST-74'};api.get.mockImplementation(url=>Promise.resolve({ok:true,payload:url.includes('/74/')?other:patient}));
 let finishOld,finishNew;api.post.mockReturnValueOnce(new Promise(resolve=>{finishOld=resolve})).mockReturnValueOnce(new Promise(resolve=>{finishNew=resolve}));
 render(<MemoryRouter initialEntries={['/health-data-input?patient_id=73']}><IntakeContextSwitch/></MemoryRouter>);
 await waitFor(()=>expect(screen.getByRole('button',{name:'儲存'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'儲存'}));
 fireEvent.click(screen.getByRole('button',{name:'Switch synthetic context'}));await screen.findByText('Synthetic Second Patient');
 await waitFor(()=>expect(screen.getByRole('button',{name:'儲存'})).toBeEnabled());const weight=screen.getByRole('spinbutton',{name:'體重'});fireEvent.change(weight,{target:{value:'71.2'}});
 fireEvent.click(screen.getByRole('button',{name:'儲存'}));expect(api.post).toHaveBeenCalledTimes(2);
 await act(async()=>finishOld({ok,payload:ok?{id:91}:{detail:'Old context failure'}}));
 expect(weight).toHaveValue(71.2);expect(weight).toBeDisabled();expect(screen.getByRole('button',{name:'儲存中'})).toBeDisabled();expect(screen.queryByRole('link',{name:'前往風險分析'})).not.toBeInTheDocument();expect(screen.queryByText('Old context failure')).not.toBeInTheDocument();expect(screen.queryByText('健檢資料已儲存')).not.toBeInTheDocument();
 await act(async()=>finishNew({ok:true,payload:{id:92}}));expect(await screen.findByRole('link',{name:'前往風險分析'})).toHaveAttribute('href','/risk-analysis?patient_id=74');expect(api.post.mock.calls[1][1]).toMatchObject({patient:'74',vital_signs:{body_weight:71.2}});
});
