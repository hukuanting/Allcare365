import React from 'react';
import {test,expect} from 'vitest';
import {render,screen,fireEvent,within} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import DiseaseNetwork from './DiseaseNetwork';
test('patient graph supports keyboard exploration and shows actual model gaps',()=>{
 const groups=[{key:'cardiovascular',code:'CV',title:'心血管',cards:[{id:'a',algorithm:'a',title:'心血管模型',value:'12%',level:'high',applicability:'applicable',missing:[]}]},{key:'renal',code:'REN',title:'腎臟',cards:[{id:'b',algorithm:'b',title:'腎臟模型',value:'資料不足',level:'missing',applicability:'applicable',missing:['尿白蛋白']}] }];
 const catalog={systems:[{algorithms:[{algorithm_id:'a',required_input_keys:['systolic_bp']},{algorithm_id:'b',required_input_keys:['systolic_bp','egfr']}]}]};
 render(<MemoryRouter><DiseaseNetwork groups={groups} catalog={catalog} snapshot={{systolic_bp:140}} labels={{systolic_bp:'收縮壓'}} patientId="73" patientName="Synthetic patient"/></MemoryRouter>);
 expect(screen.getByText('Synthetic patient')).toBeInTheDocument();
 expect(screen.getByText('140')).toBeInTheDocument();
 expect(document.querySelector('.network-edge')).toHaveClass('observed');
 expect(document.querySelector('.network-edge')).not.toHaveAttribute('stroke-dasharray');
 fireEvent.keyDown(screen.getByRole('button',{name:'腎臟，已計算 0 項，需關注 0 項'}),{key:'Enter'});
 const detail=screen.getByRole('complementary',{name:'領域探索詳情'});
 expect(within(detail).getByRole('heading',{name:'腎臟'})).toBeInTheDocument();
 expect(within(detail).getByText('補充 尿白蛋白')).toBeInTheDocument();
 expect(within(detail).getByText('共同因子：收縮壓')).toBeInTheDocument();
 fireEvent.click(within(detail).getByRole('button',{name:'心血管 ↗'}));
 expect(within(detail).getByRole('heading',{name:'心血管'})).toHaveFocus();
 expect(screen.getByRole('button',{name:'心血管，已計算 1 項，需關注 1 項'})).toHaveAttribute('aria-pressed','true');
 expect(within(detail).getByRole('link',{name:'核對病患資料 →'})).toHaveAttribute('href','/patients/73');
 expect(within(detail).getByRole('link',{name:'查看完整模型結果 →'})).toHaveAttribute('href','/risk-analysis?patient_id=73');
});


test('an unmeasured shared factor is a dashed exploration connection',()=>{
 const groups=['a','b'].map(key=>({key,code:key,title:key,cards:[{id:key,algorithm:key,title:key,value:'資料不足',level:'missing',missing:['收縮壓']}]}));
 const catalog={systems:[{algorithms:['a','b'].map(key=>({algorithm_id:key,required_input_keys:['systolic_bp']}))}]};
 const {container}=render(<MemoryRouter><DiseaseNetwork groups={groups} catalog={catalog} snapshot={{}} labels={{systolic_bp:'收縮壓'}} patientId="74" patientName="Synthetic second"/></MemoryRouter>);
 expect(container.querySelector('.network-edge')).toHaveClass('pending');
 expect(container.querySelector('.network-edge')).toHaveAttribute('stroke-dasharray','5 7');
 expect(screen.getByText('共同資料 0/1 項 · 0/1 項模型已計算')).toBeInTheDocument();
});


test('empty results retain patient identity and recovery links without implying analysis was never run',()=>{render(<MemoryRouter><DiseaseNetwork groups={[]} catalog={{}} snapshot={{}} labels={{}} patientId='73' patientName='Synthetic empty patient'/></MemoryRouter>);const region=screen.getByRole('region',{name:'病患疾病網絡'});expect(within(region).getByRole('heading',{name:'目前沒有可建立網絡的模型結果'})).toBeInTheDocument();expect(within(region).getByText('Synthetic empty patient')).toBeInTheDocument();expect(within(region).getByRole('link',{name:'核對病患資料 →'})).toHaveAttribute('href','/patients/73');expect(within(region).getByRole('link',{name:'查看完整模型結果 →'})).toHaveAttribute('href','/risk-analysis?patient_id=73');expect(screen.queryByText('執行分析後建立這位病患的疾病網絡。')).not.toBeInTheDocument();});
