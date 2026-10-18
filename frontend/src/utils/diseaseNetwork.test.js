import {buildDiseaseNetwork} from './diseaseNetwork';
import {describe,test,expect} from 'vitest';
describe('patient disease network',()=>{
 const groups=[{key:'cardiovascular',cards:[{algorithm:'heart',level:'high',applicability:'applicable',missing:[]}]},{key:'renal',cards:[{algorithm:'kidney',level:'missing',missing:['尿白蛋白'],applicability:'applicable'}]},{key:'mental_health',cards:[{algorithm:'mental',level:'low',applicability:'applicable',missing:[]}]}];
 const catalog={systems:[{algorithms:[{algorithm_id:'heart',required_input_keys:['age','sex','systolic_bp','has_diabetes']},{algorithm_id:'kidney',required_input_keys:['age','sex','systolic_bp','has_diabetes','egfr']},{algorithm_id:'mental',required_input_keys:['age','sex']}]}]};
 test('links shared risk inputs but never demographic-only overlap or missing scores',()=>{
  const graph=buildDiseaseNetwork(groups,catalog,{systolic_bp:138,has_diabetes:false});
  expect(graph.edges).toHaveLength(1);expect(graph.edges[0].observed).toEqual(['systolic_bp','has_diabetes']);
  expect(graph.nodes[0].attention).toBe(1);expect(graph.nodes[1].calculated).toBe(0);
  expect(graph.nodes[1].missing).toEqual(['尿白蛋白']);expect(graph.nodes[1]).not.toHaveProperty('probability');
 });
 test('patient data changes evidence counts without inventing a result',()=>{
  expect(buildDiseaseNetwork(groups,catalog,{}).edges[0].observed).toEqual([]);
  expect(buildDiseaseNetwork(groups,null,{}).edges).toEqual([]);
 });
});
