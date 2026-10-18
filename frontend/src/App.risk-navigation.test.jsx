import React from 'react';
import {vi} from 'vitest';
import {act,render,screen,fireEvent,waitFor,within} from '@testing-library/react';
import App from './App';
import {api} from './config/api';
const auth=vi.hoisted(()=>({value:{isAuthenticated:true,userInfo:{role:'manager',username:'Synthetic manager'},loading:false}}));
vi.mock('./utils/auth',()=>({checkAuthStatus:()=>auth.value}));
vi.mock('./hooks/useAuth',()=>({useAuth:()=>({...auth.value,logout:vi.fn()})}));
vi.mock('./utils/sessionManager',()=>({default:{init:vi.fn(),cleanup:vi.fn()}}));
vi.mock('./config/api',()=>({default:{ENDPOINTS:{PATIENTS:'/patients/',RISK_ALGORITHMS:'/catalog/',RISK_ANALYSIS:'/risk/'}},api:{get:vi.fn(),post:vi.fn()},parseApiResponse:r=>Promise.resolve(r.payload)}));
// This test verifies route/state integration, not cold module transform latency.
// Keep real components and React.lazy boundaries; preload their module code.
beforeAll(async()=>{await Promise.all([import('./components/ProtectedRoute'),import('./components/RiskAnalysis'),import('./components/Login')]);});
test('actual protected App routes retain paired analysis and remove it when authentication ends',async()=>{
 const scroll=vi.spyOn(window,'scrollTo').mockImplementation(()=>{});auth.value={isAuthenticated:true,userInfo:{role:'manager',username:'Synthetic manager'},loading:false};window.history.replaceState({},'', '/risk-analysis?patient_id=73');
 api.get.mockImplementation(url=>Promise.resolve({ok:true,payload:url==='/catalog/'?{systems:[]}:{results:[{id:73,full_name:'Synthetic App Patient',medical_record_number:'TEST-73'}]}}));api.post.mockResolvedValue({ok:true,payload:{execution_summary:{executable_models:1,resolved_models:1},disease_risk_results:[{algorithm:'synthetic',clinical_system:'renal',display_name_zh:'Synthetic App Model',risk_level:'low',risk_percentage:'3%'}]}});
 try{render(<App/>);await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'執行分析'}));await screen.findByText('Synthetic App Model');fireEvent.click(screen.getByRole('link',{name:'探索疾病網絡 →'}));const graph=await screen.findByRole('region',{name:'病患疾病網絡'});expect(within(graph).getByText('Synthetic App Patient')).toBeInTheDocument();expect(window.location.pathname).toBe('/disease-network');fireEvent.click(screen.getByRole('link',{name:'切換至模型清單 →'}));await screen.findByText('Synthetic App Model');expect(api.post).toHaveBeenCalledTimes(1);expect(window.location.pathname).toBe('/risk-analysis');
 await act(async()=>{auth.value={isAuthenticated:false,userInfo:null,loading:false};window.dispatchEvent(new CustomEvent('auth-change',{detail:auth.value}));});await screen.findByRole('heading',{name:'登入工作空間'});expect(screen.queryByText('Synthetic App Model')).not.toBeInTheDocument();expect(screen.queryByText('Synthetic App Patient')).not.toBeInTheDocument();
 }finally{scroll.mockRestore();window.history.replaceState({},'','/')}
});
