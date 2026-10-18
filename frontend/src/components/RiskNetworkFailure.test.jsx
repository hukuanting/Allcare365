import React from 'react';
import {vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import RiskAnalysis from './RiskAnalysis';
import {api} from '../config/api';
const graphState=vi.hoisted(()=>({fail:true}));
vi.mock('./DiseaseNetwork',async importOriginal=>{const real=await importOriginal();return {default:props=>{if(graphState.fail)throw new Error('Synthetic graph render failure');return React.createElement(real.default,props);}}});
vi.mock('../config/api',()=>({default:{ENDPOINTS:{PATIENTS:'/patients/',RISK_ALGORITHMS:'/catalog/',RISK_ANALYSIS:'/risk/'}},api:{get:vi.fn(url=>Promise.resolve({ok:true,payload:url==='/catalog/'?{systems:[]}:url==='/patients/73/'?{id:73,full_name:'Synthetic retained patient'}:{results:[]}})),post:vi.fn(()=>Promise.resolve({ok:true,payload:{execution_summary:{executable_models:1,resolved_models:1,calculated_models:1},disease_risk_results:[{algorithm:'synthetic',display_name_zh:'Synthetic model',clinical_system:'renal',risk_level:'low',risk_percentage:'3%'}]}}))},parseApiResponse:r=>Promise.resolve(r.payload)}));
test('graph failure retains the analysis workspace and offers a patient-scoped recovery link',async()=>{
 const errors=vi.spyOn(console,'error').mockImplementation(()=>{});try{render(<MemoryRouter initialEntries={['/disease-network?patient_id=73']}><RiskAnalysis network/></MemoryRouter>);await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'執行分析'}));expect(await screen.findByText('疾病網絡無法載入。您仍可查看本次分析摘要與模型結果。')).toBeInTheDocument();expect(screen.getByText('Synthetic retained patient')).toBeInTheDocument();expect(screen.getByRole('button',{name:'重新分析'})).toBeEnabled();expect(screen.getByRole('link',{name:'查看模型清單'})).toHaveAttribute('href','/risk-analysis?patient_id=73');expect(screen.getByRole('button',{name:'重新載入頁面'})).toBeEnabled();expect(screen.getByText('重新載入後需再次執行分析。')).toBeInTheDocument();expect(screen.queryByText('頁面無法載入')).not.toBeInTheDocument();expect(screen.queryByText('Synthetic graph render failure')).not.toBeInTheDocument();}finally{errors.mockRestore()}
});

beforeEach(()=>{graphState.fail=true;api.post.mockClear();});

test('a new analysis remounts the graph boundary and can recover from a prior graph error',async()=>{const errors=vi.spyOn(console,'error').mockImplementation(()=>{});try{render(<MemoryRouter initialEntries={['/disease-network?patient_id=73']}><RiskAnalysis network/></MemoryRouter>);await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'執行分析'}));await screen.findByText('疾病網絡無法載入。您仍可查看本次分析摘要與模型結果。');graphState.fail=false;fireEvent.click(screen.getByRole('button',{name:'重新分析'}));await screen.findByRole('region',{name:'病患疾病網絡'});expect(screen.queryByText('疾病網絡無法載入。您仍可查看本次分析摘要與模型結果。')).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'重新分析'})).toBeEnabled();expect(api.post).toHaveBeenCalledTimes(2);}finally{errors.mockRestore()}});
