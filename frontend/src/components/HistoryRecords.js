import React, { useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import RefreshIcon from '@mui/icons-material/Refresh';
import API_CONFIG, { api, parseApiResponse } from '../config/api';
import { apiErrorMessage, displayValue, listFromResponse } from '../utils/apiData';

function HistoryRecords() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const loadRecords = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const response = await api.get(API_CONFIG.ENDPOINTS.HEALTH_SCREENINGS);
      const data = await parseApiResponse(response);
      if (!response.ok) throw new Error(apiErrorMessage(data, '健檢紀錄讀取失敗'));
      setRecords(listFromResponse(data));
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, []);

  return (
    <Box className="page-frame">
      <Box className="page-heading">
        <Box>
          <Typography variant="overline" color="primary">健檢紀錄</Typography>
          <Typography variant="h4">健檢紀錄清單</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            資料來源為後端 Health Screening API。
          </Typography>
        </Box>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadRecords} disabled={loading}>
          重新整理
        </Button>
      </Box>

      {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}

      <TableContainer component={Paper} className="data-table">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>日期</TableCell>
              <TableCell>病患</TableCell>
              <TableCell>MRN</TableCell>
              <TableCell>Encounter type</TableCell>
              <TableCell>Vital signs</TableCell>
              <TableCell>Lab count</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {records.map((record) => (
              <TableRow key={record.id} hover>
                <TableCell>{displayValue(record.screening_date)}</TableCell>
                <TableCell>{displayValue(record.patient_name)}</TableCell>
                <TableCell>{displayValue(record.patient_medical_record_number)}</TableCell>
                <TableCell>{displayValue(record.encounter_type)}</TableCell>
                <TableCell>
                  <Chip size="small" label={record.vital_signs ? '已回傳' : '無資料'} color={record.vital_signs ? 'success' : 'default'} variant="outlined" />
                </TableCell>
                <TableCell>{record.laboratory_results?.length ?? 0}</TableCell>
              </TableRow>
            ))}
            {!loading && records.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>
                  <Box sx={{ py: 6, textAlign: 'center' }}>
                    <Typography fontWeight={900}>後端目前沒有回傳健檢紀錄</Typography>
                    <Typography variant="body2" color="text.secondary">請先新增健檢資料或匯入 H2U CVD 檔案。</Typography>
                  </Box>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

export default HistoryRecords;
