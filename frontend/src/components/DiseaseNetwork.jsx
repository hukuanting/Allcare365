import React, {useEffect,useId,useMemo,useRef,useState} from 'react';
import {Link} from 'react-router-dom';
import {buildDiseaseNetwork} from '../utils/diseaseNetwork';
import './DiseaseNetwork.css';
function NetworkActions({ patientId }) {
 return <nav className="network-actions" aria-label="病患資料與分析"><Link className="network-action" to={'/patients/'+encodeURIComponent(patientId)}>核對病患資料 →</Link><Link className="network-action" to={'/risk-analysis?patient_id='+encodeURIComponent(patientId)}>查看完整模型結果 →</Link></nav>;
}

export default function DiseaseNetwork({groups,catalog,snapshot,labels,patientId,patientName,formatValue = (key,value) => value === true ? '是' : value === false ? '否' : String(value)}) {
 const graph=useMemo(()=>buildDiseaseNetwork(groups,catalog,snapshot),[groups,catalog,snapshot]);
 const [selected,setSelected]=useState(null);
 const detailId=useId();
 const detailHeading=useRef(null);
 const focusDetail=useRef(false);
 useEffect(()=>{
  if(!focusDetail.current) return;
  focusDetail.current=false;
  detailHeading.current?.focus({preventScroll:true});
  detailHeading.current?.scrollIntoView?.({behavior:"instant",block:"start"});
 },[selected]);
 const exploreConnection=key=>{focusDetail.current=true;setSelected(key);};
 const node=graph.nodes.find(n=>n.key===selected)||graph.nodes[0];
 const positions=Object.fromEntries(graph.nodes.map((n,i)=>{const angle=-Math.PI/2+i*2*Math.PI/graph.nodes.length;return [n.key,{x:380+280*Math.cos(angle),y:325+270*Math.sin(angle)}];}));
 const connections=graph.edges.filter(e=>e.source===node?.key||e.target===node?.key).sort((a,b)=>b.observed.length-a.observed.length);
 if(!node) return <section className="disease-network" aria-label="病患疾病網絡"><div className="network-intro"><div><span className="atlas-eyebrow">CONNECTED HEALTH</span><h2>目前沒有可建立網絡的模型結果</h2><p>{patientName}</p><p>可核對病患資料，或返回模型清單查看本次分析摘要。</p></div></div><NetworkActions patientId={patientId} /></section>;
 return <section className="disease-network" aria-label="病患疾病網絡">
  <div className="network-intro"><div><span className="atlas-eyebrow">CONNECTED HEALTH</span><h2>從一個線索，看見健康全貌</h2><p>選擇領域，探索共同資料因子與可補充的評估。</p></div><span className="network-count">{graph.nodes.length} 個領域 · {graph.edges.length} 條資料關聯</span></div>
  <div className="network-layout"><div className="network-map">
   <div className="network-diagram" role="region" aria-label="健康領域關聯圖捲動區" tabIndex={0}><svg viewBox="0 0 760 650" role="group" aria-label="互動健康領域圖，使用 Tab 選擇節點">
    <ellipse cx="380" cy="325" rx="280" ry="270" className="network-orbit"/>
    {graph.edges.map(e=>{const a=positions[e.source],b=positions[e.target];const active=e.source===node.key||e.target===node.key;return <path key={e.source+e.target} d={'M'+a.x+','+a.y+' Q380,325 '+b.x+','+b.y} className={'network-edge'+(active?' active':'')+(e.observed.length?' observed':' pending')} strokeDasharray={e.observed.length?undefined:'5 7'} strokeWidth={active?2:1}><title>{e.shared.map(f=>labels[f]||f).join('、')} · 共同模型輸入</title></path>;})}
    <circle cx="380" cy="325" r="65" className="network-centre"/>
    <text x="380" y="319" textAnchor="middle" className="network-centre-label">個人健康圖譜</text><text x="380" y="343" textAnchor="middle" className="network-centre-count">{groups.reduce((n,g)=>n+g.cards.length,0)} 項模型</text>
    {graph.nodes.map(n=>{const pos=positions[n.key];return <g key={n.key} role="button" tabIndex="0" aria-controls={detailId} aria-pressed={n.key===node.key} aria-label={n.title+'，已計算 '+n.calculated+' 項，需關注 '+n.attention+' 項'} onClick={()=>setSelected(n.key)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSelected(n.key);}}} className={'network-node'+(n.key===node.key?' selected':'')} transform={'translate('+pos.x+','+pos.y+')'}>
     <rect x="-94" y="-35" width="188" height="70" rx="3"/>
     <text textAnchor="middle" y="-7" className="network-node-title">{n.title}</text>
     <text textAnchor="middle" y="17" className="network-node-count">{n.calculated}/{n.cards.length} 已計算{n.attention?' · '+n.attention+' 需關注':''}</text>
     <circle cx="-81" cy="-24" r="3" fill={n.attention?'#b94c3f':n.calculated?'#39715c':'#a2aaa6'}/>
    </g>;})}
   </svg></div><p className="network-pan-hint">左右滑動查看關聯圖；鍵盤可聚焦圖區後使用左右方向鍵，或使用領域按鈕切換。</p><p className="network-legend">實線：已有共同資料 · 虛線：共同資料待補 · 節點：模型結果</p>
   <div className="network-node-list" aria-label="健康領域清單">{graph.nodes.map(n=><button key={n.key} type="button" aria-controls={detailId} aria-pressed={n.key===node.key} onClick={()=>setSelected(n.key)}>{n.title}</button>)}</div>
  </div><aside id={detailId} className="network-detail" aria-label="領域探索詳情"><span className="atlas-eyebrow">EXPLORE / {node.code}</span><h3 ref={detailHeading} tabIndex={-1}>{node.title}</h3><p>{patientName}</p>
   <div className="network-totals"><span><b>{node.calculated}</b>已計算</span><span><b>{node.attention}</b>需關注</span><span><b>{node.cards.filter(c=>c.level==='missing').length}</b>待補資料</span>{node.cards.some(c=>c.applicability==='not_applicable')&&<span><b>{node.cards.filter(c=>c.applicability==='not_applicable').length}</b>不適用</span>}</div>
   <details className="network-disclosure" key={node.key+"-evidence"}><summary>本次可用的連結資料 <span>{new Set(connections.flatMap(e=>e.observed)).size} 項</span></summary>
   <dl className="network-evidence">{[...new Set(connections.flatMap(e=>e.observed))].map(field=><div key={field}><dt>{labels[field]||field}</dt><dd>{formatValue(field,snapshot[field])}</dd></div>)}</dl>
   {!connections.some(e=>e.observed.length)&&<p>補充共同因子的資料後，這裡會呈現病患的實際數值。</p>}
   </details><h4>延伸探索</h4>{connections.length?connections.map(e=>{const other=graph.nodes.find(n=>n.key===(e.source===node.key?e.target:e.source));return <div className="network-connection" key={other.key}><button type="button" aria-controls={detailId} onClick={()=>exploreConnection(other.key)}>{other.title} ↗</button><p>共同因子：{e.shared.map(f=>labels[f]||f).join('、')}</p><small>共同資料 {e.observed.length}/{e.shared.length} 項 · {other.calculated}/{other.cards.length} 項模型已計算</small></div>;}):<p>目前模型沒有共用的連結因子。</p>}
   <details className="network-disclosure" key={node.key+"-models"}><summary>這個領域的模型 <span>{node.cards.length} 項</span></summary><ul className="network-models">{node.cards.map(c=><li key={c.id}><div className="network-model-name"><span>{c.title}</span>{(c.levelLabel||["high","moderate_high"].includes(c.level))&&<small className={["high","moderate_high"].includes(c.level)?"network-model-status attention":"network-model-status"}>{c.levelLabel||"需關注"}</small>}{c.applicability==='not_applicable'&&c.recommendation&&<p className="network-model-reason">{c.recommendation}</p>}</div><strong>{c.value}</strong></li>)}</ul>
   </details>{node.missing.length>0&&<><h4>補充資料，展開更多評估</h4><ul className="network-next">{node.cards.filter(c=>c.level==='missing').sort((a,b)=>a.missing.length-b.missing.length).slice(0,3).map(c=><li key={c.id}><strong>{c.title}</strong><span>補充 {c.missing.join('、')}</span></li>)}</ul></>}
   <NetworkActions patientId={patientId} />
  </aside></div>
 </section>;
}
