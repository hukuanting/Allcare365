import React, { useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import Brand from './Brand';
import { useAuth } from '../hooks/useAuth';
import { hasAnyRole, CLINICAL_WRITE_ROLES, RESEARCH_ACCESS_ROLES } from '../utils/roles';

const workflows = [
  { number: '01', label: '臨床照護', title: '每一次照護，都有完整脈絡。', text: '將病患資料與歷次健檢整合於同一個工作空間，從紀錄回到人，讓每一次判斷都有依據。', rows: ['病患資料與病歷摘要', '歷次健檢與檢驗紀錄', '個人健康風險分析'], action: '進入臨床工作台', path: '/patients' },
  { number: '02', label: '資料整合', title: '從分散的紀錄，到清楚的輪廓。', text: '透過批次匯入與手動建檔整理健康資料，保留來源與時間脈絡，讓團隊把心力留給照護。', rows: ['健檢檔案批次匯入', '單筆健康資料建檔', '資料品質與完整性檢視'], action: '開始整理資料', path: '/bulk-import', allowedRoles: CLINICAL_WRITE_ROLES },
  { number: '03', label: '研究探索', title: '好的研究，始於可信的資料。', text: '以群體摘要探索研究族群，透過報告申請與審核流程，讓資料使用有清楚的界線。', rows: ['研究族群條件篩選', '群體資料品質摘要', '研究報告申請與審核'], action: '探索研究工作台', path: '/research-cohorts', allowedRoles: RESEARCH_ACCESS_ROLES },
];

export default function LandingPage() {
  const [selected, setSelected] = useState(0);
  const workflowId = useId();
  const workflowTabs = useRef([]);
  const { isAuthenticated, userInfo } = useAuth();
  const availableWorkflows = workflows.filter(item => !isAuthenticated || hasAnyRole(userInfo, item.allowedRoles));
  const activeIndex = Math.min(selected, availableWorkflows.length - 1);
  const flow = availableWorkflows[activeIndex];
  return <div className="atlas-home">
    <section className="atlas-hero" aria-labelledby="hero-title">
      <div className="atlas-eyebrow"><span /> HEALTH, IN CONTEXT</div>
      <div className="atlas-hero-grid">
        <div className="atlas-hero-copy">
          <h1 id="hero-title">看見完整的健康，<br />讓照護<span className="atlas-emphasis">更有方向。</span></h1>
          <p>串起臨床紀錄、健康風險與研究洞察。<br />AllCare365，為每一位專業工作者，<br className="mobile-break" />也為每一個被照護的人。</p>
          <div className="atlas-actions"><Link className="atlas-button" to={isAuthenticated ? "/dashboard" : "/login"}>{isAuthenticated ? "返回工作空間" : "登入工作空間"} <ArrowForwardIcon fontSize="small" /></Link><a className="atlas-text-link" href="#workflows">探索工作流程 <span>↘</span></a></div>
          <div className="atlas-hero-note"><span className="atlas-small-cross">+</span> 臨床照護 · 資料整合 · 研究探索</div>
        </div>
        <div className="atlas-diagram" role="img" aria-label="以人為中心，串連臨床紀錄、健康風險與研究探索。產品流程示意，非真實病患資料。">
          <div className="atlas-diagram-top"><span>THE CARE CONTINUUM</span><span>FIG. 01</span></div>
          <div className="atlas-orbit"><div className="atlas-orbit-inner" /><div className="atlas-orbit-core"><Brand compact /><span>以人為中心</span></div><span className="orbit-point point-a">臨床紀錄<small>Clinical records</small></span><span className="orbit-point point-b">健康風險<small>Health insights</small></span><span className="orbit-point point-c">研究探索<small>Research</small></span></div>
          <div className="atlas-diagram-bottom"><span className="atlas-coordinate">01 — 02 — 03</span><span>讓資料形成照護的脈絡</span></div>
        </div>
      </div>
      <div className="atlas-foundation"><span>為專業工作而設計</span><div><b>FHIR R4</b><span>資料互通</span></div><div><b>Role-aware</b><span>依角色存取</span></div><div><b>Longitudinal</b><span>連續健康紀錄</span></div></div>
    </section>
    <section id="workflows" className="atlas-workflows" aria-labelledby="workflow-title">
      <div className="atlas-section-heading"><div className="atlas-eyebrow">ONE WORKSPACE. A CLEARER PICTURE.</div><h2 id="workflow-title">專注當下的工作。<br /><span>連結更完整的視野。</span></h2><p>從第一筆紀錄到下一個發現，<br />在同一個空間，找到下一步。</p></div>
      <div className="atlas-workflow-layout"><div role="tablist" aria-label="工作流程" className="atlas-flow-tabs">{availableWorkflows.map((item,index)=><button key={item.number} ref={element => { workflowTabs.current[index] = element; }} id={workflowId+'-tab-'+index} role="tab" aria-selected={activeIndex===index} aria-controls={workflowId+'-panel'} tabIndex={activeIndex===index?0:-1} onClick={()=>setSelected(index)} onKeyDown={event=>{if(event.ctrlKey||event.altKey||event.metaKey)return;if(['ArrowDown','ArrowRight','ArrowUp','ArrowLeft','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?availableWorkflows.length-1:(index+(['ArrowUp','ArrowLeft'].includes(event.key)?availableWorkflows.length-1:1))%availableWorkflows.length;setSelected(next);workflowTabs.current[next]?.focus();}}}><span>{item.number}</span>{item.label}<span className="flow-arrow">↗</span></button>)}</div>
      <div id={workflowId+'-panel'} role="tabpanel" aria-labelledby={workflowId+'-tab-'+activeIndex} tabIndex={0} className="atlas-flow-panel"><span className="atlas-eyebrow">{flow.number} / ALLCARE365</span><h3>{flow.title}</h3><p>{flow.text}</p><ul>{flow.rows.map(row=><li key={row}><span>+</span>{row}</li>)}</ul><Link to={flow.path} className="atlas-text-link">{flow.action} <ArrowForwardIcon fontSize="small" /></Link></div></div>
    </section>
    <section className="atlas-closing"><span className="atlas-eyebrow">CARE STARTS WITH CLARITY</span><h2>讓下一次照護，<br />從更清楚的理解開始。</h2><Link to={isAuthenticated ? "/dashboard" : "/register"} className="atlas-button atlas-button-light">{isAuthenticated ? "返回工作空間" : "申請帳號"} <ArrowForwardIcon fontSize="small" /></Link></section>
    <footer className="atlas-footer"><Brand /><span>Clinical care. Connected.</span><span>AllCare365 · 健康資料工作空間</span></footer>
  </div>;
}
