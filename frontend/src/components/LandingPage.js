import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import BiotechIcon from '@mui/icons-material/Biotech';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import UploadFileIcon from '@mui/icons-material/UploadFile';

const implementedFlows = [
  { icon: <UploadFileIcon />, title: 'H2U CVD 匯入', text: 'CSV 或 Excel 匯入會交由後端解析，建立病患、健檢與檢驗資料。' },
  { icon: <BiotechIcon />, title: '研究 Cohort', text: '使用後端 aggregate API 查詢 cohort summary、data quality 與 patients-like-this。' },
  { icon: <AssignmentTurnedInIcon />, title: '研究報告審核', text: '研究輸出需經申請、審核與 artifact 讀取流程，避免直接暴露 row-level data。' },
];

function LandingPage() {
  const navigate = useNavigate();

  return (
    <>
      <Box className="hero-shell">
        <Box className="hero-inner">
          <Box className="hero-copy">
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Chip size="small" label="FHIR R4" color="primary" variant="outlined" />
              <Chip size="small" label="PostgreSQL" color="secondary" variant="outlined" />
              <Chip size="small" label="Aggregate Research" color="success" variant="outlined" />
            </Stack>

            <Box>
              <Typography variant="h1" sx={{ fontSize: { xs: 44, md: 64 }, lineHeight: 1.02 }}>
                AllCare365
              </Typography>
              <Typography variant="h5" color="text.secondary" sx={{ mt: 2, maxWidth: 680, lineHeight: 1.7 }}>
                連接臨床資料匯入、FHIR 對應、風險分析、研究 cohort 與 aggregate report governance 的工作系統。
              </Typography>
            </Box>

            <Box className="hero-actions">
              <Button variant="contained" size="large" startIcon={<MonitorHeartIcon />} onClick={() => navigate('/login')}>
                登入系統
              </Button>
              <Button variant="outlined" size="large" startIcon={<HealthAndSafetyIcon />} onClick={() => navigate('/register')}>
                建立帳號
              </Button>
            </Box>
          </Box>
        </Box>
      </Box>

      <Box className="section-band">
        <Box className="section-inner">
          <Stack spacing={4}>
            <Box>
              <Typography variant="overline" color="primary">目前已掛接後端</Typography>
              <Typography variant="h4">可用工作流程</Typography>
            </Box>
            <Box className="workflow-grid">
              {implementedFlows.map((item) => (
                <Paper key={item.title} className="quick-card" sx={{ p: 2.5 }}>
                  <Box sx={{ color: 'primary.main', mb: 1 }}>{item.icon}</Box>
                  <Typography variant="h6">{item.title}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{item.text}</Typography>
                </Paper>
              ))}
            </Box>
          </Stack>
        </Box>
      </Box>
    </>
  );
}

export default LandingPage;
