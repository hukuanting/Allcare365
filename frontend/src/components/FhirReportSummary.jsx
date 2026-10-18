import React from 'react';
const namespace = 'https://allcare365.local/fhir/research/StructureDefinition/';
const labels = {age:'年齡',sbp:'收縮壓 SBP',dbp:'舒張壓 DBP',bmi:'BMI',fpg:'空腹血糖 FPG',hba1c:'HbA1c',ldl:'LDL',hdl:'HDL',tg:'三酸甘油脂 TG',tc:'總膽固醇 TC',waist:'腰圍',height:'身高',weight:'體重',creatinine:'肌酸酐'};
const number = value => typeof value === 'number' && Number.isFinite(value) ? (Number.isInteger(value) ? String(value) : value.toFixed(2)) : '未提供';
const fields = extension => Object.fromEntries((extension.extension || []).map(item => [item.url,Object.entries(item).find(([key]) => key.startsWith('value'))?.[1]]));
export default function FhirReportSummary({data}) {
 if (data?.resourceType !== 'MeasureReport') return null;
 const groups = data.group || [];
 return <section className="fhir-report-summary" aria-label="FHIR 報告摘要">
  <h3>報告摘要</h3><p>狀態：{{complete:'已完成',pending:'處理中',error:'處理失敗'}[data.status] || data.status || '未提供'} · 日期：{data.date || '未提供'}</p>
  {groups.length === 0 && <p>本份報告未提供族群摘要。</p>}
  {groups.map((group,index) => {
   const population = (group.population || []).find(item => item.code?.coding?.some(code => code.code === 'initial-population'));
   const hidden = population?.extension?.some(item => item.url === namespace+'privacy-suppressed' && item.valueBoolean === true);
   const metrics = (group.extension || []).filter(item => item.url === namespace+'numeric-feature-summary').map(fields);
   return <div key={group.id || index}>{groups.length > 1 && <h4>{group.code?.text || group.code?.coding?.find(item => item.display)?.display || '族群 ' + (index + 1)}</h4>}<p>族群人數：<strong>{hidden ? '已遮蔽' : number(population?.count)}</strong></p>
    {metrics.length > 0 && <dl className="fhir-report-metrics">{metrics.map((item,i) => <div key={item.code || i}><dt>{labels[item.code] || item.display || item.code || '未命名指標'}</dt><dd>{item.suppressed ? '已遮蔽' : <>平均 {number(item.mean)}{item.unit ? ' '+(item.unit === 'a' ? '歲' : item.unit) : ''} · 樣本 {number(item.count)}</>}</dd></div>)}</dl>}
   </div>;
  })}
 </section>;
}
