import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Brand from './Brand';

export default function AuthFrame({ title, description, mode = 'login', children }) {
  const registration = mode === 'register';
  return <div className="atlas-auth">
    <aside className="auth-context" aria-label="工作空間介紹">
      <RouterLink to="/" className="atlas-brand-link" aria-label="AllCare365 首頁"><Brand /></RouterLink>
      <div className="auth-context-copy"><span className="atlas-eyebrow">CARE · DATA · RESEARCH</span><h2>讓每一筆資料，<br/>回到照護的脈絡。</h2><p>病患紀錄、健檢與研究資料，在同一個工作空間中連結。</p></div>
      <ol className="auth-context-steps" aria-label={registration ? '帳號申請流程' : '登入流程'}>
        {(registration ? [['01','建立帳號','設定帳號與密碼'],['02','Viewer 權限','註冊後即可登入'],['03','需要更多功能','由管理員授予額外權限']] : [['01','帳號與密碼','使用您的個人帳號'],['02','身分驗證','依帳號要求提供驗證器代碼'],['03','進入工作空間','接續病患與資料工作']]).map(([number,label,note])=><li key={number}><span>{number}</span><div><strong>{label}</strong><small>{note}</small></div></li>)}
      </ol>
      <RouterLink to="/" className="auth-back">← 回到首頁</RouterLink>
    </aside>
    <section className="auth-form-panel" aria-labelledby="auth-title"><header><span className="atlas-eyebrow">{registration ? 'CREATE ACCOUNT' : 'WORKSPACE ACCESS'}</span><h1 id="auth-title">{title}</h1><p>{description}</p></header>{children}</section>
  </div>;
}
