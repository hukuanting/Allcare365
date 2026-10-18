import React, { useEffect, useRef, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import LinearProgress from '@mui/material/LinearProgress';
import { authorize } from 'fhirclient/browser';
import API_CONFIG from '../config/api';

export default function Launch() {
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const authorization = useRef(null);

  useEffect(() => {
    let active = true;
    // Reuse the pending launch during StrictMode effect replay. A retry explicitly resets it.
    if (!authorization.current) {
      try {
        authorization.current = Promise.resolve(authorize({
          clientId: 'my_web_app',
          scope: 'launch patient/*.read openid fhirUser',
          redirectUri: `${window.location.origin}/dashboard`,
          iss: `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.FHIR_BASE}`,
        }));
      } catch {
        authorization.current = Promise.reject(new Error('SMART launch failed'));
      }
    }
    // Success leaves this page via SDK redirection; do not infer a local authenticated session.
    authorization.current.catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [attempt]);

  const retry = () => {
    authorization.current = null;
    setFailed(false);
    setAttempt(value => value + 1);
  };

  return <section className="atlas-launch" aria-labelledby="launch-title">
    <header><span className="atlas-eyebrow">SMART / SYSTEM CONNECTION</span><h1 id="launch-title">連接醫療系統</h1><p>透過 SMART 授權，開啟醫療系統的存取流程。</p></header>
    {failed ? <div className="launch-recovery">
      <Alert severity="error">目前無法啟動醫療系統授權。請重試，或返回登入工作空間。</Alert>
      <div className="inline-actions"><Button variant="contained" onClick={retry}>重新連接</Button><Button component={RouterLink} to="/login">返回登入</Button></div>
    </div> : <div className="launch-progress" role="status" aria-live="polite">
      <p>正在開啟授權頁面…</p>
      <LinearProgress aria-label="醫療系統授權進行中" />
      <span>接下來將前往醫療系統，依其指示完成授權。</span>
    </div>}
  </section>;
}
