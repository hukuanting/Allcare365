// Connections describe shared model inputs, never a new predicted probability.
const CONNECTORS = new Set(['systolic_bp','diastolic_bp','has_hypertension','has_diabetes','fasting_glucose','hba1c','bmi','waist_circumference','total_cholesterol','hdl_cholesterol','triglycerides','is_smoker','ever_smoker','egfr','cvd_history','apoe_e4']);
export function buildDiseaseNetwork(groups, catalog, snapshot = {}) {
  const metadata = new Map((catalog?.systems || []).flatMap(s => s.algorithms || []).map(a => [a.algorithm_id,a]));
  const nodes = groups.map(group => {
    const fields = new Set(group.cards.flatMap(card => metadata.get(card.algorithm)?.required_input_keys || []));
    const missing = [...new Set(group.cards.flatMap(card => card.missing || []))];
    return {...group, fields, missing, calculated:group.cards.filter(c=>c.level!=='missing' && c.applicability!=='not_applicable').length,
      attention:group.cards.filter(c=>['high','moderate_high'].includes(c.level)).length};
  });
  const edges = [];
  nodes.forEach((a,i)=>nodes.slice(i+1).forEach(b=>{
    const shared = [...a.fields].filter(f=>CONNECTORS.has(f) && b.fields.has(f));
    if(shared.length) edges.push({source:a.key,target:b.key,shared,observed:shared.filter(f=>snapshot[f]!==null && snapshot[f]!==undefined && snapshot[f]!=='')});
  }));
  return {nodes,edges};
}
