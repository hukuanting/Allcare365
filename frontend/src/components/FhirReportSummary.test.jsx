import React from 'react';
import {render,screen} from '@testing-library/react';
import FhirReportSummary from './FhirReportSummary';
const ns='https://allcare365.local/fhir/research/StructureDefinition/';
test('retains zero values and hides suppressed population and metrics',()=>{
 const data={resourceType:'MeasureReport',status:'complete',group:[{population:[{code:{coding:[{code:'initial-population'}]},count:0}],extension:[{url:ns+'numeric-feature-summary',extension:[{url:'code',valueCode:'sbp'},{url:'mean',valueDecimal:0},{url:'count',valueInteger:0}]}]}]};
 const {rerender}=render(<FhirReportSummary data={data}/>);expect(screen.getByText('平均 0 · 樣本 0')).toBeInTheDocument();
 data.group[0].population[0].extension=[{url:ns+'privacy-suppressed',valueBoolean:true}];data.group[0].extension[0].extension.push({url:'suppressed',valueBoolean:true});
 rerender(<FhirReportSummary data={data}/>);expect(screen.getAllByText('已遮蔽')).toHaveLength(2);expect(screen.queryByText('平均 0 · 樣本 0')).not.toBeInTheDocument();
});

test('multiple populations are named and absent groups are explicit',()=>{const {rerender}=render(<FhirReportSummary data={{resourceType:'MeasureReport',group:[{code:{text:'Synthetic first cohort'}},{code:{coding:[{display:'Synthetic second cohort'}]}},{}]}}/>);expect(screen.getByRole('heading',{name:'Synthetic first cohort'})).toBeInTheDocument();expect(screen.getByRole('heading',{name:'Synthetic second cohort'})).toBeInTheDocument();expect(screen.getByRole('heading',{name:'族群 3'})).toBeInTheDocument();rerender(<FhirReportSummary data={{resourceType:'MeasureReport'}}/>);expect(screen.getByText('本份報告未提供族群摘要。')).toBeInTheDocument();expect(screen.queryByText(/族群人數/)).not.toBeInTheDocument();});
