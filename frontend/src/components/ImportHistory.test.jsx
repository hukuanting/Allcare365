import React from 'react';
import { vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import BulkHealthDataImport from './BulkHealthDataImport';
import HistoryRecords from './HistoryRecords';
import { api } from '../config/api';
vi.mock('../config/api',()=>({default:{ENDPOINTS:{PARSE_FILE:'/parse/',BULK_IMPORT:'/import/',FHIR_IMPORT:'/fhir-import/',FHIR_PREVIEW:'/fhir-preview/',HEALTH_SCREENINGS:'/screenings/'}},api:{get:vi.fn(),post:vi.fn(),upload:vi.fn()},parseApiResponse:r=>Promise.resolve(r.payload)}));
const mount=Component=>render(<MemoryRouter><Component/></MemoryRouter>);
beforeEach(()=>{api.get.mockReset();api.post.mockReset();api.upload.mockReset();});
test('file requires preview, imports only once and renders partial errors',async()=>{
 const errors=Array.from({length:7},(_,i)=>({row:i+1,error:'Test error '+(i+1)}));
 api.upload.mockResolvedValueOnce({ok:true,payload:{row_count:8,headers:['ID'],sample_data:[{ID:'TEST-1'}]}}).mockResolvedValueOnce({ok:false,status:207,payload:{success_count:1,error_count:7,total_count:8,errors}});
 mount(BulkHealthDataImport);fireEvent.click(screen.getByRole('button',{name:'CSV / Excel'}));const file=new File(['ID\nTEST-1'],'synthetic.csv',{type:'text/csv'});fireEvent.change(screen.getByLabelText('選擇匯入檔案'),{target:{files:[file]}});
 expect(screen.getByRole('button',{name:'確認匯入'})).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'預覽'}));await screen.findByRole('table',{name:'匯入檔案樣本'});expect(screen.getByRole('button',{name:'確認匯入'})).toBeEnabled();
 fireEvent.click(screen.getByRole('button',{name:'確認匯入'}));await screen.findByText('匯入結果');expect(screen.getByRole('button',{name:'確認匯入'})).toBeDisabled();
 expect(screen.getByRole('link',{name:'前往風險分析'})).toHaveAttribute('href','/risk-analysis');
 expect(screen.queryByText(/Test error 7/)).not.toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'查看全部 7 筆錯誤'}));expect(screen.getByText(/Test error 7/)).toBeInTheDocument();expect(api.upload).toHaveBeenCalledTimes(2);
});
const fhirData = {resourceType:'Bundle',type:'collection',entry:[{resource:{resourceType:'Patient',id:'synthetic'}}]};
const fhirPreview = {fhir_data:fhirData,totalResources:1,byType:{Patient:1}};
test('FHIR is primary; edits invalidate preview and processing locks all source controls',async()=>{
 let resolveImport;
 api.post.mockResolvedValueOnce({ok:true,payload:fhirPreview}).mockResolvedValueOnce({ok:false,payload:{detail:'請提供具有 resourceType 的 FHIR resource 或 Bundle。'}}).mockResolvedValueOnce({ok:true,payload:fhirPreview}).mockImplementationOnce(()=>new Promise(resolve=>{resolveImport=resolve;}));
 mount(BulkHealthDataImport);
 expect(screen.getByRole('button',{name:'FHIR（主要）'})).toHaveAttribute('aria-pressed','true');
 const input=screen.getByLabelText('FHIR JSON / XML 資料');
 fireEvent.change(input,{target:{value:JSON.stringify({resourceType:'Patient',id:'synthetic'})}});
 fireEvent.click(screen.getByRole('button',{name:'預覽'}));await screen.findByText('FHIR 預覽');expect(screen.getByRole('button',{name:'確認匯入'})).toBeEnabled();
 fireEvent.change(input,{target:{value:'{}'}});expect(screen.getByRole('button',{name:'確認匯入'})).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'預覽'}));expect(await screen.findByRole('alert')).toHaveTextContent('resourceType');
 fireEvent.change(input,{target:{value:JSON.stringify({resourceType:'Patient',id:'synthetic'})}});fireEvent.click(screen.getByRole('button',{name:'預覽'}));await screen.findByText('FHIR 預覽');fireEvent.click(screen.getByRole('button',{name:'確認匯入'}));expect(input).toBeDisabled();expect(screen.getByRole('button',{name:'CSV / Excel'})).toBeDisabled();expect(screen.getByRole('button',{name:'FHIR REST API'})).toBeDisabled();
 resolveImport({ok:true,payload:{success_count:1,error_count:0,total_count:1,primary_patient_id:73}});await screen.findByText('匯入結果');
 expect(screen.getByRole('link',{name:'分析這位病患的風險'})).toHaveAttribute('href','/risk-analysis?patient_id=73');
 expect(api.post).toHaveBeenLastCalledWith('/fhir-import/',{fhir_data:fhirData,format:'json'});
});
test('FHIR malformed entry preview cannot unlock import',async()=>{
 api.post.mockResolvedValue({ok:false,payload:{detail:'每個 entry 都必須包含 resource 與 resourceType。'}});
 mount(BulkHealthDataImport);fireEvent.change(screen.getByLabelText('FHIR JSON / XML 資料'),{target:{value:JSON.stringify({resourceType:'Bundle',entry:[{}]})}});fireEvent.click(screen.getByRole('button',{name:'預覽'}));expect(await screen.findByRole('alert')).toHaveTextContent('resourceType');expect(screen.getByRole('button',{name:'確認匯入'})).toBeDisabled();
});
test('multiple FHIR files use one multipart preview and import the same normalized snapshot',async()=>{
 api.upload.mockResolvedValue({ok:true,payload:fhirPreview});api.post.mockResolvedValue({ok:true,payload:{success_count:1,error_count:0,total_count:1}});
 mount(BulkHealthDataImport);fireEvent.click(screen.getByRole('button',{name:'上傳多個檔案'}));const input=screen.getByLabelText('選擇多個 FHIR 檔案');expect(input).toHaveAttribute('multiple');
 const files=[new File(['{}'],'golden_patient.fhir.json'),new File(['<Patient/>'],'patient.xml')];fireEvent.change(input,{target:{files}});expect(screen.getByText(/golden_patient.fhir.json/)).toBeInTheDocument();expect(screen.getByRole('button',{name:'確認匯入'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'預覽'}));await screen.findByText('FHIR 預覽');expect(screen.getByRole('heading',{name:'FHIR 預覽',level:2})).toHaveFocus();expect(screen.getByRole('table',{name:'FHIR 資源摘要'})).toBeInTheDocument();expect(api.upload.mock.calls[0][1].getAll('files')).toEqual(files);
 fireEvent.click(screen.getByRole('button',{name:'確認匯入'}));await screen.findByText('匯入結果');expect(screen.getByRole('heading',{name:'匯入結果',level:2})).toHaveFocus();expect(api.post).toHaveBeenCalledWith('/fhir-import/',{fhir_data:fhirData,format:'json'});
 fireEvent.change(input,{target:{files:[files[0]]}});expect(screen.queryByText('FHIR 預覽')).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'確認匯入'})).toBeDisabled();
});
test('XML paste is sent for auto detection and API token is cleared after fetch',async()=>{
 api.post.mockResolvedValue({ok:true,payload:fhirPreview});mount(BulkHealthDataImport);
 const xml='<Patient xmlns="http://hl7.org/fhir"><id value="synthetic"/></Patient>';
 fireEvent.change(screen.getByLabelText('FHIR JSON / XML 資料'),{target:{value:xml}});fireEvent.click(screen.getByRole('button',{name:'預覽'}));await screen.findByText('FHIR 預覽');expect(api.post).toHaveBeenCalledWith('/fhir-preview/',{fhir_data:xml,format:'auto'});
 fireEvent.click(screen.getByRole('button',{name:'FHIR REST API'}));expect(screen.queryByText('FHIR 預覽')).not.toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('FHIR API URL'),{target:{value:'https://trusted.example/fhir/Patient/synthetic/$everything'}});fireEvent.change(screen.getByLabelText('API Access token（如需要）'),{target:{value:'synthetic-token'}});
 fireEvent.click(screen.getByRole('button',{name:'預覽'}));await screen.findByText('FHIR 預覽');expect(api.post).toHaveBeenLastCalledWith('/fhir-preview/',{url:'https://trusted.example/fhir/Patient/synthetic/$everything',access_token:'synthetic-token'});expect(screen.getByLabelText('API Access token（如需要）')).toHaveValue('');
});
test('history uses total count, sourced fields, patient links and page navigation',async()=>{
 api.get.mockResolvedValueOnce({ok:true,payload:{count:26,next:'/screenings/?page=2',results:[{id:1,patient:73,patient_name:'Synthetic History Patient',screening_date:'2026-10-09',encounter_type:'annual_physical'}]}}).mockResolvedValueOnce({ok:true,payload:{count:26,next:null,results:[]}});
 mount(HistoryRecords);expect(await screen.findByText('共 26 筆紀錄')).toBeInTheDocument();expect(screen.getByRole('region',{name:'健檢紀錄表格捲動區'})).toHaveAttribute('tabindex','0');expect(screen.getByRole('link',{name:'Synthetic History Patient'})).toHaveAttribute('href','/patients/73');expect(screen.getByRole('link',{name:'開啟 Synthetic History Patient 的病患風險分析'})).toHaveAttribute('href','/risk-analysis?patient_id=73');
 fireEvent.click(screen.getByRole('button',{name:'下一頁'}));await waitFor(()=>expect(api.get).toHaveBeenLastCalledWith('/screenings/?page=2',expect.any(Object)));expect(await screen.findByText('第 2 頁 · 本頁 0 筆')).toBeInTheDocument();expect(screen.getByRole('heading',{name:'本頁沒有健檢紀錄'})).toBeInTheDocument();expect(screen.queryByRole('heading',{name:'尚無健檢紀錄'})).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'上一頁'})).toBeEnabled();
});
test('history failure does not masquerade as an empty dataset and can retry',async()=>{
 api.get.mockResolvedValueOnce({ok:false,payload:{detail:'Test unavailable'}}).mockResolvedValueOnce({ok:true,payload:{count:0,results:[]}});mount(HistoryRecords);const historyError=await screen.findByRole('alert');expect(historyError).toHaveTextContent('Test unavailable');await waitFor(()=>expect(historyError).toHaveFocus());expect(screen.queryByText('尚無健檢紀錄')).not.toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'重試'}));expect(await screen.findByText('尚無健檢紀錄')).toBeInTheDocument();
});

test('FHIR URL feedback blocks malformed and credential-bearing URLs before fetching',()=>{
 mount(BulkHealthDataImport);fireEvent.click(screen.getByRole('button',{name:'FHIR REST API'}));
 const url=screen.getByLabelText('FHIR API URL');
 fireEvent.change(url,{target:{value:'localhost:8000/fhir/Patient'}});
 expect(url).toHaveAttribute('aria-invalid','true');expect(screen.getByRole('button',{name:'預覽'})).toBeDisabled();
 fireEvent.change(url,{target:{value:'https://synthetic:secret@trusted.example/fhir/Patient'}});
 expect(screen.getByText(/請移除網址中的帳密/)).toBeInTheDocument();expect(screen.getByRole('button',{name:'預覽'})).toBeDisabled();
 fireEvent.change(url,{target:{value:'https://trusted.example/fhir/Patient'}});
 expect(url).toHaveAttribute('aria-invalid','false');expect(screen.getByRole('button',{name:'預覽'})).toBeEnabled();expect(api.post).not.toHaveBeenCalled();
});


test.each([[401,'有效 token'],[403,'讀取這份資料的權限']])('FHIR source HTTP %s explains recovery, focuses the notice and retains the URL',async(status,guidance)=>{
 api.post.mockResolvedValue({ok:false,payload:{detail:'FHIR API 讀取失敗（HTTP '+status+'），未匯入資料。'}});
 mount(BulkHealthDataImport);fireEvent.click(screen.getByRole('button',{name:'FHIR REST API'}));
 const url='https://trusted.example/fhir/Patient/synthetic';
 fireEvent.change(screen.getByLabelText('FHIR API URL'),{target:{value:url}});
 fireEvent.change(screen.getByLabelText('API Access token（如需要）'),{target:{value:'synthetic-token'}});
 fireEvent.click(screen.getByRole('button',{name:'預覽'}));
 const alert=await screen.findByRole('alert');expect(alert).toHaveTextContent(guidance);
 await waitFor(()=>expect(alert).toHaveFocus());
 expect(screen.getByLabelText('FHIR API URL')).toHaveValue(url);
 expect(screen.getByLabelText('API Access token（如需要）')).toHaveValue('');
 expect(screen.getByRole('button',{name:'確認匯入'})).toBeDisabled();
});


test('FHIR identity review shows source names, identifier fallback and explicit truncation, then clears on edits',async()=>{
 const patients=[
  {resourceType:'Patient',id:'a',name:[{use:'usual',text:'Usual name'},{use:'official',text:'Official source name'}],identifier:[{value:'SYNTHETIC-A'}]},
  {resourceType:'Patient',id:'b',name:[{family:'Family',given:['Given','Second']} ]},
  {resourceType:'Patient',id:'c'},
  {resourceType:'Patient',id:'d',name:[{text:'Fourth source name'}]},
  {resourceType:'Patient',id:'e',name:[{text:'Fifth source name'}]},
  {resourceType:'Patient',id:'f',name:[{text:'Sixth source name'}]},
 ];
 const bundle={resourceType:'Bundle',entry:patients.map(resource=>({resource}))};
 api.post.mockResolvedValue({ok:true,payload:{fhir_data:bundle,totalResources:6,byType:{Patient:6}}});
 mount(BulkHealthDataImport);
 const input=screen.getByLabelText('FHIR JSON / XML 資料');
 fireEvent.change(input,{target:{value:JSON.stringify(bundle)}});
 fireEvent.click(screen.getByRole('button',{name:'預覽'}));
 const review=await screen.findByRole('region',{name:'預覽病患資料'});
 expect(within(review).getByText('Official source name')).toBeInTheDocument();
 expect(within(review).queryByText('Usual name')).not.toBeInTheDocument();
 expect(within(review).getByText('識別碼：SYNTHETIC-A')).toBeInTheDocument();
 expect(within(review).getByText('Family Given Second')).toBeInTheDocument();
 expect(within(review).getByText('資源 ID：c')).toBeInTheDocument();
 expect(within(review).queryByText('Sixth source name')).not.toBeInTheDocument();
 expect(within(review).getByText('另有 1 筆病患資料；本次合計 6 筆。')).toBeInTheDocument();
 fireEvent.change(input,{target:{value:'{"resourceType":"Patient","id":"different"}'}});
 expect(screen.queryByRole('region',{name:'預覽病患資料'})).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'確認匯入'})).toBeDisabled();
});


test.each(['fhir','csv'])('new %s preview clears prior import result and restores confirmation',async(mode)=>{
 const response={ok:true,payload:mode==='fhir'?fhirPreview:{row_count:1,headers:['ID'],sample_data:[{ID:'SYNTHETIC'}]}};
 const request=mode==='fhir'?api.post:api.upload;
 request.mockResolvedValueOnce(response).mockResolvedValueOnce({ok:true,payload:{success_count:1,error_count:0,total_count:1}}).mockResolvedValueOnce(response);
 mount(BulkHealthDataImport);
 if(mode==='fhir') fireEvent.change(screen.getByLabelText('FHIR JSON / XML 資料'),{target:{value:JSON.stringify(fhirData)}});
 else {fireEvent.click(screen.getByRole('button',{name:'CSV / Excel'}));fireEvent.change(screen.getByLabelText('選擇匯入檔案'),{target:{files:[new File(['ID\nSYNTHETIC'],'synthetic.csv')]}});}
 fireEvent.click(screen.getByRole('button',{name:'預覽'}));
 await waitFor(()=>expect(screen.getByRole('button',{name:'確認匯入'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'確認匯入'}));
 await screen.findByRole('heading',{name:'匯入結果'});
 expect(screen.getByRole('button',{name:'確認匯入'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'預覽'}));
 await waitFor(()=>expect(screen.getByRole('button',{name:'確認匯入'})).toBeEnabled());
 expect(screen.queryByRole('heading',{name:'匯入結果'})).not.toBeInTheDocument();
 await waitFor(()=>expect(screen.getByRole('heading',{name:mode==='fhir'?'FHIR 預覽':'檔案預覽'})).toHaveFocus());
 expect(request).toHaveBeenCalledTimes(3);
});

test('removing one FHIR file invalidates preview and preserves the remaining selection',async()=>{api.upload.mockResolvedValue({ok:true,payload:fhirPreview});mount(BulkHealthDataImport);fireEvent.click(screen.getByRole('button',{name:'上傳多個檔案'}));const files=[new File(['{}'],'first.fhir.json'),new File(['{}'],'second.fhir.xml')];fireEvent.change(screen.getByLabelText('選擇多個 FHIR 檔案'),{target:{files}});fireEvent.click(screen.getByRole('button',{name:'預覽'}));await screen.findByText('FHIR 預覽');await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'移除 first.fhir.json'}));});expect(screen.queryByText('FHIR 預覽')).not.toBeInTheDocument();expect(screen.getByRole('button',{name:'確認匯入'})).toBeDisabled();expect(within(screen.getByRole('list',{name:'已選 FHIR 檔案'})).getAllByRole('listitem')).toHaveLength(1);expect(screen.getByRole('button',{name:'選擇 FHIR 檔案'})).toHaveFocus();fireEvent.click(screen.getByRole('button',{name:'預覽'}));await screen.findByText('FHIR 預覽');expect(api.upload.mock.calls[1][1].getAll('files')).toEqual([files[1]]);await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'移除 second.fhir.xml'}));});expect(screen.getByRole('button',{name:'預覽'})).toBeDisabled();expect(screen.getByRole('button',{name:'確認匯入'})).toBeDisabled();expect(screen.queryByRole('list',{name:'已選 FHIR 檔案'})).not.toBeInTheDocument();expect(screen.getByText('尚未選擇 FHIR 檔案')).toBeInTheDocument();fireEvent.change(screen.getByLabelText('選擇多個 FHIR 檔案'),{target:{files:[files[1]]}});expect(screen.getByText('已選 1 個 FHIR 檔案')).toBeInTheDocument();expect(screen.getByRole('button',{name:'預覽'})).toBeEnabled();expect(api.upload).toHaveBeenCalledTimes(2);});

test('file pickers use native buttons and activate their respective file inputs',async()=>{mount(BulkHealthDataImport);fireEvent.click(screen.getByRole('button',{name:'CSV / Excel'}));const csv=screen.getByLabelText('選擇匯入檔案');const csvClick=vi.spyOn(csv,'click').mockImplementation(()=>{});try{const picker=screen.getByRole('button',{name:'選擇檔案'});expect(picker.tagName).toBe('BUTTON');expect(picker).toHaveAttribute('type','button');fireEvent.click(picker);expect(csvClick).toHaveBeenCalledTimes(1);}finally{csvClick.mockRestore()}fireEvent.click(screen.getByRole('button',{name:'FHIR（主要）'}));fireEvent.click(screen.getByRole('button',{name:'上傳多個檔案'}));const fhir=screen.getByLabelText('選擇多個 FHIR 檔案');const fhirClick=vi.spyOn(fhir,'click').mockImplementation(()=>{});try{const picker=screen.getByRole('button',{name:'選擇 FHIR 檔案'});expect(picker.tagName).toBe('BUTTON');fireEvent.click(picker);expect(fhirClick).toHaveBeenCalledTimes(1);}finally{fhirClick.mockRestore()}expect(api.upload).not.toHaveBeenCalled();});

test.each(['file','fhir'])('batched %s confirmation sends one import and failure permits retry',async(mode)=>{let finish;const pending=new Promise(resolve=>{finish=resolve});const transport=mode==='file'?api.upload:api.post;transport.mockResolvedValueOnce({ok:true,payload:mode==='file'?{row_count:1,headers:['ID'],sample_data:[{ID:'TEST'}]}:fhirPreview}).mockReturnValue(pending);mount(BulkHealthDataImport);if(mode==='file'){fireEvent.click(screen.getByRole('button',{name:'CSV / Excel'}));fireEvent.change(screen.getByLabelText('選擇匯入檔案'),{target:{files:[new File(['ID\nTEST'],'synthetic.csv')]}})}else fireEvent.change(screen.getByLabelText('FHIR JSON / XML 資料'),{target:{value:JSON.stringify(fhirData)}});fireEvent.click(screen.getByRole('button',{name:'預覽'}));await screen.findByText(mode==='file'?'檔案預覽':'FHIR 預覽');const confirm=screen.getByRole('button',{name:'確認匯入'});act(()=>{fireEvent.click(confirm);fireEvent.click(confirm)});expect(transport).toHaveBeenCalledTimes(2);await act(async()=>finish({ok:false,payload:{detail:'Synthetic import unavailable'}}));await screen.findByText('Synthetic import unavailable');expect(screen.getByRole('button',{name:'確認匯入'})).toBeEnabled();transport.mockResolvedValueOnce({ok:true,payload:{success_count:1,error_count:0,total_count:1}});fireEvent.click(screen.getByRole('button',{name:'確認匯入'}));await screen.findByText('匯入結果');expect(transport).toHaveBeenCalledTimes(3);});

test('starting an import immediately prevents a batched format change',async()=>{let finish;api.post.mockResolvedValueOnce({ok:true,payload:fhirPreview}).mockReturnValueOnce(new Promise(resolve=>{finish=resolve}));mount(BulkHealthDataImport);fireEvent.change(screen.getByLabelText('FHIR JSON / XML 資料'),{target:{value:JSON.stringify(fhirData)}});fireEvent.click(screen.getByRole('button',{name:'預覽'}));await screen.findByText('FHIR 預覽');const confirm=screen.getByRole('button',{name:'確認匯入'}),csv=screen.getByRole('button',{name:'CSV / Excel'});act(()=>{fireEvent.click(confirm);fireEvent.click(csv)});expect(screen.getByRole('region',{name:'FHIR 資料匯入'})).toBeInTheDocument();expect(screen.queryByRole('region',{name:'CSV 或 Excel 資料匯入'})).not.toBeInTheDocument();expect(api.post).toHaveBeenCalledTimes(2);await act(async()=>finish({ok:false,payload:{detail:'Synthetic interrupted import'}}));await screen.findByText('Synthetic interrupted import');fireEvent.click(screen.getByRole('button',{name:'CSV / Excel'}));expect(screen.getByRole('region',{name:'CSV 或 Excel 資料匯入'})).toBeInTheDocument();expect(screen.queryByText('FHIR 預覽')).not.toBeInTheDocument();});
