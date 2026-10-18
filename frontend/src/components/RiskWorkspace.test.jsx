import React from 'react';
import { vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom';
import RiskAnalysis from './RiskAnalysis';
import RouteExperience from './RouteExperience';
import { api } from '../config/api';
vi.mock('../config/api',()=>({default:{ENDPOINTS:{PATIENTS:'/patients/',RISK_ALGORITHMS:'/catalog/',RISK_ANALYSIS:'/risk/'}},api:{get:vi.fn(),post:vi.fn()},parseApiResponse:r=>Promise.resolve(r.payload)}));
const patient={id:73,full_name:'Synthetic Risk Patient',medical_record_number:'TEST-73',age:42};
const second={id:74,full_name:'Second Synthetic Patient',medical_record_number:'TEST-74'};
const response=payload=>({ok:true,payload});
function Harness(){const navigate=useNavigate();return <><button onClick={()=>navigate('/risk-analysis?patient_id=74')}>Switch risk route</button><RiskAnalysis/></>;}
const mount=(path='/risk-analysis?patient_id=73')=>render(<MemoryRouter initialEntries={[path]}><Harness/></MemoryRouter>);
beforeEach(()=>{vi.spyOn(window,'scrollTo').mockImplementation(()=>{});api.get.mockReset();api.post.mockReset();api.get.mockImplementation(endpoint=>Promise.resolve(endpoint==='/catalog/'?response({counts:{executable_models:0},systems:[]}):endpoint==='/patients/73/'?response(patient):endpoint==='/patients/74/'?response(second):response({results:[patient,second]})));});
test('resolves a chart-selected patient beyond the initial list page',async()=>{
 api.get.mockImplementation(endpoint=>Promise.resolve(endpoint==='/catalog/'?response({systems:[]}):endpoint==='/patients/73/'?response(patient):response({results:[]})));
 mount();await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());expect(api.get).toHaveBeenCalledWith('/patients/73/',expect.any(Object));expect(screen.getByText('Synthetic Risk Patient')).toBeInTheDocument();
});
test('selecting another patient clears previous result and identity',async()=>{
 api.post.mockResolvedValue(response({disease_risk_results:[],execution_summary:{resolved_models:0,executable_models:1}}));mount();await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'執行分析'}));await screen.findByText('分析已完成，可探索各領域結果與共同資料因子。');expect(screen.getByRole('heading',{name:'模型結果總覽'})).toBeInTheDocument();expect(screen.getByRole('link',{name:'核對病患資料'})).toHaveAttribute('href','/patients/73');
 fireEvent.mouseDown(screen.getByRole('combobox',{name:'分析病患'}));fireEvent.click(screen.getByRole('option',{name:'Second Synthetic Patient · TEST-74'}));expect(screen.queryByRole('heading',{name:'模型結果總覽'})).not.toBeInTheDocument();expect(screen.queryByRole('link',{name:'核對病患資料'})).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled();
});
test('changing the route aborts in-flight analysis and ignores its late result',async()=>{
 let resolveAnalysis;api.post.mockReturnValue(new Promise(resolve=>{resolveAnalysis=resolve;}));mount();await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'執行分析'}));await waitFor(()=>expect(api.post).toHaveBeenCalled());const signal=api.post.mock.calls[0][2].signal;
 fireEvent.click(screen.getByRole('button',{name:'Switch risk route'}));expect(signal.aborted).toBe(true);await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());await act(async()=>{resolveAnalysis(response({disease_risk_results:[],data_summary:{data:{age:999}}}));});expect(screen.queryByText('分析已完成，可探索各領域結果與共同資料因子。')).not.toBeInTheDocument();expect(screen.queryByRole('heading',{name:'模型結果總覽'})).not.toBeInTheDocument();
});

test('model summaries expose all backend limitations, missing fields and review notes',async()=>{
 const longTitle='Synthetic model with a deliberately long title for wrapping';
 api.post.mockResolvedValue(response({disease_risk_results:[{
  id:'synthetic-missing',algorithm:'synthetic',display_name_zh:longTitle,display_name_en:'Synthetic Long Model',
  outcome_label:'Synthetic outcome',risk_level:'low',missing_data_labels:['Synthetic field one','Synthetic field two','Synthetic field three','Synthetic field four'],
  limitations:['Synthetic limitation one','Synthetic limitation two'],recommendation_text:'Synthetic backend recommendation',requires_doctor_review:true,
 },{
  id:'synthetic-calculated',algorithm:'synthetic-calculated',display_name_zh:'Synthetic calculated model',display_name_en:'Synthetic Calculated Model',
  outcome_label:'Synthetic calculated outcome',risk_level:'low',risk_percentage:'0%',limitations:['Synthetic calculated-model limitation'],
 }]}));
 mount();await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'執行分析'}));
 const first=await screen.findByRole('article',{name:longTitle+'，Synthetic Long Model：Synthetic outcome'});
 expect(within(first).getByRole('heading',{level:3,name:longTitle})).toBeInTheDocument();
 expect(within(first).getByText('缺少 4 項輸入資料')).toBeInTheDocument();
 expect(within(first).queryByText('後端標示：需醫師審核')).not.toBeInTheDocument();
 const disclosure=first.querySelector('details');expect(disclosure).not.toHaveAttribute('open');
 fireEvent.click(within(first).getByText('查看評估細節'));
 expect(disclosure).toHaveAttribute('open');
 expect(within(first).getByText('Synthetic field four')).toBeVisible();
 expect(within(first).getByText('Synthetic limitation two')).toBeVisible();
 expect(within(first).getByText('Synthetic backend recommendation')).toBeVisible();
 const second=screen.getByRole('article',{name:'Synthetic calculated model，Synthetic Calculated Model：Synthetic calculated outcome'});
 expect(within(second).getByText('0%')).toBeInTheDocument();
 fireEvent.click(within(second).getByText('查看評估細節'));
 expect(within(second).getByText('Synthetic calculated-model limitation')).toBeVisible();
 expect(within(second).queryByText('後端標示：需醫師審核')).not.toBeInTheDocument();
});


test('searching results preserves the overall summary and exposes model references', async () => {
 api.post.mockResolvedValue(response({
  execution_summary:{executable_models:2,resolved_models:2,calculated_models:2,all_executable_models_resolved:true},
  disease_risk_results:[
   {algorithm:'prisq',display_name_zh:'PRISQ 篩檢',display_name_en:'PRISQ',outcome_label:'篩檢積分',risk_level:'informational',risk_percentage:'18.000',
    model_version:'expert-source-2026-10-10',method_uri:'https://doi.org/10.1111/jdi.13445',evidence:{source_document:'Abbas 2021 Table 2'}},
   {algorithm:'nelson',display_name_zh:'Nelson 腎臟風險',display_name_en:'Nelson',outcome_label:'五年風險',risk_level:'high',risk_percentage:'12.00%'}
  ]
 }));
 mount();await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'執行分析'}));
 await screen.findByText('顯示 2 / 2 項');
 fireEvent.change(screen.getByRole('textbox',{name:'搜尋模型或評估項目'}),{target:{value:'PRISQ'}});
 expect(screen.getByText('顯示 1 / 2 項')).toBeInTheDocument();
 expect(screen.queryByRole('article',{name:/Nelson 腎臟風險/})).not.toBeInTheDocument();
 const article=screen.getByRole('article',{name:'PRISQ 篩檢，PRISQ：篩檢積分'});
 fireEvent.click(within(article).getByText('查看評估細節'));
 expect(within(article).getByText('Abbas 2021 Table 2')).toBeVisible();
 expect(within(article).getByRole('link',{name:'閱讀原始參考文獻 ↗'})).toHaveAttribute('href','https://doi.org/10.1111/jdi.13445');
 fireEvent.change(screen.getByRole('textbox',{name:'搜尋模型或評估項目'}),{target:{value:'no matching model'}});
 expect(screen.getByText('顯示 0 / 2 項')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'清除篩選'}));
 expect(screen.getByRole('textbox',{name:'搜尋模型或評估項目'})).toHaveFocus();
 expect(screen.getByText('顯示 2 / 2 項')).toBeInTheDocument();
 expect(screen.getByText('2/2 模型已解析 · 2 項產生分數')).toBeInTheDocument();
 fireEvent.change(screen.getByRole('textbox',{name:'搜尋模型或評估項目'}),{target:{value:'PRISQ'}});
 fireEvent.click(screen.getByRole('button',{name:'Switch risk route'}));
 await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'執行分析'}));
 await screen.findByText('顯示 2 / 2 項');
 expect(screen.getByRole('textbox',{name:'搜尋模型或評估項目'})).toHaveValue('');
});

test('network mode loads the real graph from patient analysis and preserves exploration controls',async()=>{
 api.post.mockResolvedValue(response({execution_summary:{resolved_models:2,executable_models:2,calculated_models:2},data_summary:{data:{systolic_bp:140}},algorithm_catalog:{systems:[{algorithms:[{algorithm_id:'synthetic-heart',required_input_keys:['systolic_bp']},{algorithm_id:'synthetic-kidney',required_input_keys:['systolic_bp','egfr']}]}]},disease_risk_results:[{algorithm:'synthetic-heart',clinical_system:'cardiovascular',display_name_zh:'Synthetic heart model',risk_level:'high',risk_percentage:'12%'},{algorithm:'synthetic-kidney',clinical_system:'renal',display_name_zh:'Synthetic kidney model',risk_level:'low',risk_percentage:'3%'}]}));
 render(<MemoryRouter initialEntries={['/disease-network?patient_id=73']}><RiskAnalysis network/></MemoryRouter>);await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'執行分析'}));
 const graph=await screen.findByRole('region',{name:'病患疾病網絡'});expect(within(graph).getByText('Synthetic Risk Patient')).toBeInTheDocument();const detail=within(graph).getByRole('complementary',{name:'領域探索詳情'});
 const nodes=within(graph).getAllByRole('button').filter(el=>el.tagName.toLowerCase()==='g');expect(nodes).toHaveLength(2);fireEvent.keyDown(nodes[1],{key:'Enter'});expect(nodes[1]).toHaveAttribute('aria-pressed','true');expect(nodes[1]).toHaveAttribute('aria-controls',detail.id);expect(within(detail).getByRole('link',{name:'查看完整模型結果 →'})).toHaveAttribute('href','/risk-analysis?patient_id=73');expect(within(graph).getByRole('region',{name:'健康領域關聯圖捲動區'})).toHaveAttribute('tabindex','0');
});

test('switching network and model routes retains the completed patient analysis',async()=>{
 api.post.mockResolvedValue(response({execution_summary:{resolved_models:1,executable_models:1,calculated_models:1},disease_risk_results:[{algorithm:'synthetic',display_name_zh:'Synthetic retained model',display_name_en:'Synthetic',clinical_system:'renal',risk_level:'low',risk_percentage:'3%'}]}));
 render(<MemoryRouter initialEntries={['/risk-analysis?patient_id=73']}><main id="main-content" tabIndex={-1}><RouteExperience><Routes><Route path="/risk-analysis" element={<RiskAnalysis/>}/><Route path="/disease-network" element={<RiskAnalysis network/>}/></Routes></RouteExperience></main></MemoryRouter>);
 await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.mouseDown(screen.getByRole('combobox',{name:'分析病患'}));fireEvent.click(screen.getByRole('option',{name:'Second Synthetic Patient · TEST-74'}));fireEvent.click(screen.getByRole('button',{name:'執行分析'}));await screen.findByText('Synthetic retained model');fireEvent.click(screen.getByRole('link',{name:'探索疾病網絡 →'}));await screen.findByRole('region',{name:'病患疾病網絡'});expect(document.title).toBe('疾病網絡 · AllCare365');expect(await within(screen.getByRole('region',{name:'病患疾病網絡'})).findByText('Second Synthetic Patient')).toBeInTheDocument();fireEvent.click(screen.getByRole('link',{name:'切換至模型清單 →'}));await screen.findByText('Synthetic retained model');expect(api.post).toHaveBeenCalledTimes(1);expect(document.title).toBe('風險分析 · AllCare365');expect(document.getElementById('main-content')).toHaveFocus();
});

afterEach(()=>vi.restoreAllMocks());

test('same-patient view change preserves an in-flight analysis until it completes',async()=>{
 let finish;api.post.mockReturnValue(new Promise(resolve=>{finish=resolve}));render(<MemoryRouter initialEntries={['/risk-analysis?patient_id=73']}><main id="main-content" tabIndex={-1}><RouteExperience><Routes><Route path="/risk-analysis" element={<RiskAnalysis/>}/><Route path="/disease-network" element={<RiskAnalysis network/>}/></Routes></RouteExperience></main></MemoryRouter>);
 await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.mouseDown(screen.getByRole('combobox',{name:'分析病患'}));fireEvent.click(screen.getByRole('option',{name:'Second Synthetic Patient · TEST-74'}));fireEvent.click(screen.getByRole('button',{name:'執行分析'}));const signal=api.post.mock.calls[0][2].signal;fireEvent.click(screen.getByRole('link',{name:'探索疾病網絡 →'}));expect(signal.aborted).toBe(false);await act(async()=>finish(response({execution_summary:{resolved_models:1,executable_models:1},disease_risk_results:[{algorithm:'synthetic',clinical_system:'renal',display_name_zh:'Pending synthetic model',risk_level:'low',risk_percentage:'3%'}]})));await screen.findByRole('region',{name:'病患疾病網絡'});expect(screen.getByRole('button',{name:'重新分析'})).toBeEnabled();expect(api.post).toHaveBeenCalledTimes(1);
});

function PairedPatientSwitch(){const navigate=useNavigate();return <><button onClick={()=>navigate('/disease-network?patient_id=74')}>Open second patient network</button><RouteExperience><Routes><Route path="/risk-analysis" element={<RiskAnalysis/>}/><Route path="/disease-network" element={<RiskAnalysis network/>}/></Routes></RouteExperience></>;}
test('paired views clear completed data when navigation requests a different patient',async()=>{
 api.post.mockResolvedValue(response({execution_summary:{resolved_models:1,executable_models:1},disease_risk_results:[{algorithm:'synthetic',clinical_system:'renal',display_name_zh:'First patient exclusive model',risk_level:'high',risk_percentage:'12%'}]}));render(<MemoryRouter initialEntries={['/risk-analysis?patient_id=73']}><main id="main-content" tabIndex={-1}><PairedPatientSwitch/></main></MemoryRouter>);await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'執行分析'}));await screen.findByText('First patient exclusive model');fireEvent.click(screen.getByRole('button',{name:'Open second patient network'}));
 await screen.findByText('Second Synthetic Patient');await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());expect(screen.queryByText('First patient exclusive model')).not.toBeInTheDocument();expect(screen.queryByRole('region',{name:'病患疾病網絡'})).not.toBeInTheDocument();expect(screen.getByText('尚未分析')).toBeInTheDocument();expect(api.post).toHaveBeenCalledTimes(1);expect(screen.getByRole('link',{name:'切換至模型清單 →'})).toHaveAttribute('href','/risk-analysis?patient_id=74');
});

test('clearing patient search restores its focus and reloads the full list without a selection',async()=>{
 api.get.mockImplementation(url=>Promise.resolve(response(url==='/catalog/'?{systems:[]}:url==='/patients/73/'?patient:url.includes('search=missing')?{results:[]}:{results:[patient,second]})));mount('/risk-analysis?patient_id=73');await waitFor(()=>expect(screen.getByRole('combobox',{name:'分析病患'})).not.toHaveAttribute('aria-disabled','true'));const search=screen.getByRole('textbox',{name:'搜尋姓名或 MRN'});fireEvent.change(search,{target:{value:'missing'}});await waitFor(()=>expect(api.get).toHaveBeenCalledWith('/patients/?include_demo=true&search=missing',expect.any(Object)));await screen.findByText('沒有符合搜尋條件的病患。可調整姓名或 MRN，或清除搜尋。');fireEvent.click(screen.getByRole('button',{name:'清除病患搜尋'}));expect(search).toHaveFocus();expect(search).toHaveValue('');await waitFor(()=>expect(api.get).toHaveBeenLastCalledWith('/patients/?include_demo=true',expect.any(Object)));expect(screen.getByRole('button',{name:'執行分析'})).toBeDisabled();expect(api.post).not.toHaveBeenCalled();
 fireEvent.change(search,{target:{value:'next search'}});fireEvent.keyDown(search,{key:'Escape',isComposing:true});expect(search).toHaveValue('next search');fireEvent.keyDown(search,{key:'Escape'});expect(search).toHaveValue('');expect(search).toHaveFocus();expect(search).toHaveAttribute('aria-keyshortcuts','Escape');
});

test('patient-list failure is distinct from empty results and retry restores chart selection',async()=>{
 let calls=0;api.get.mockImplementation(url=>Promise.resolve(url==='/catalog/'?response({systems:[]}):++calls===1?{ok:false,payload:{detail:'Synthetic patient list unavailable'}}:response({results:[patient,second]})));mount();const alert=await screen.findByRole('alert');expect(alert).toHaveTextContent('Synthetic patient list unavailable');expect(screen.getByRole('combobox',{name:'分析病患'})).toHaveAttribute('aria-disabled','true');expect(screen.getByRole('button',{name:'執行分析'})).toBeDisabled();expect(screen.queryByText('目前沒有可供分析的病患。')).not.toBeInTheDocument();
 fireEvent.click(within(alert).getByRole('button',{name:'重試'}));await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());expect(screen.queryByText('Synthetic patient list unavailable')).not.toBeInTheDocument();expect(screen.getByRole('combobox',{name:'分析病患'})).not.toHaveAttribute('aria-disabled','true');expect(screen.getByText('Synthetic Risk Patient')).toBeInTheDocument();expect(api.post).not.toHaveBeenCalled();
});

test('analysis failure focuses its feedback and retries the same selected patient',async()=>{api.post.mockResolvedValueOnce({ok:false,payload:{detail:'Synthetic analysis unavailable'}}).mockResolvedValueOnce(response({disease_risk_results:[],execution_summary:{resolved_models:0,executable_models:0}}));mount();await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'執行分析'}));const feedback=await screen.findByRole('alert');expect(feedback).toHaveTextContent('Synthetic analysis unavailable');await waitFor(()=>expect(feedback).toHaveFocus());expect(screen.getByText('Synthetic Risk Patient')).toBeInTheDocument();expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled();fireEvent.click(screen.getByRole('button',{name:'執行分析'}));await screen.findByText('分析已完成，可探索各領域結果與共同資料因子。');expect(screen.queryByText('Synthetic analysis unavailable')).not.toBeInTheDocument();expect(api.post).toHaveBeenCalledTimes(2);expect(api.post.mock.calls[1][1]).toEqual({patient_id:'73'});});

test('rapid analysis clicks send one pending request and failure permits retry',async()=>{let finish;api.post.mockReturnValue(new Promise(resolve=>{finish=resolve}));mount();await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());const button=screen.getByRole('button',{name:'執行分析'});act(()=>{fireEvent.click(button);fireEvent.click(button)});expect(api.post).toHaveBeenCalledTimes(1);expect(api.post.mock.calls[0][2].signal.aborted).toBe(false);await act(async()=>finish({ok:false,payload:{detail:'Synthetic pending analysis failure'}}));await screen.findByText('Synthetic pending analysis failure');expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled();fireEvent.click(screen.getByRole('button',{name:'執行分析'}));await waitFor(()=>expect(api.post).toHaveBeenCalledTimes(2));});


test('invalid execution counters stay unknown instead of fabricating completed models',async()=>{api.post.mockResolvedValue(response({disease_risk_results:[],execution_summary:{executable_models:true,resolved_models:' ',calculated_models:'invalid',all_executable_models_resolved:true}}));mount();await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'執行分析'}));await screen.findByText('分析已完成，可探索各領域結果與共同資料因子。');expect(screen.getByText('未提供 / 未提供')).toBeInTheDocument();expect(screen.getByText('解析比例未提供')).toBeInTheDocument();expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();expect(screen.queryByText(/項產生分數/)).not.toBeInTheDocument();});


test('numeric-string execution counts preserve zero scored models and valid resolved completion',async()=>{api.post.mockResolvedValue(response({disease_risk_results:[],execution_summary:{executable_models:'2',resolved_models:'2',calculated_models:'0',not_applicable_models:'2',all_executable_models_resolved:true}}));mount();await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'執行分析'}));await screen.findByText('分析已完成，可探索各領域結果與共同資料因子。');expect(screen.getByText('2 / 2')).toBeInTheDocument();expect(screen.getByText('模型已解析 · 100%')).toBeInTheDocument();expect(screen.getByText('2/2 模型已解析 · 0 項產生分數，2 項不適用')).toBeInTheDocument();});


test('an explicit different-patient route clears the previous search before resolving its patient',async()=>{api.get.mockImplementation(endpoint=>Promise.resolve(endpoint==='/catalog/'?response({counts:{executable_models:0},systems:[]}):endpoint.includes('search=')?response({results:[patient]}):response({results:[patient,second]})));mount();await waitFor(()=>expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled());const search=screen.getByRole('textbox',{name:'搜尋姓名或 MRN'});fireEvent.change(search,{target:{value:'Only first'}});await waitFor(()=>expect(api.get).toHaveBeenCalledWith('/patients/?include_demo=true&search=Only+first',expect.any(Object)));fireEvent.click(screen.getByRole('button',{name:'Switch risk route'}));await waitFor(()=>expect(search).toHaveValue(''));await screen.findByText('Second Synthetic Patient');expect(screen.getByRole('button',{name:'執行分析'})).toBeEnabled();expect(api.post).not.toHaveBeenCalled();});
