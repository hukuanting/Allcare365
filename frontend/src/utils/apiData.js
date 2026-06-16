export const listFromResponse = (payload) => {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.results)) return payload.results;
  return [];
};

export const countFromResponse = (payload) => {
  if (typeof payload?.count === 'number') return payload.count;
  return listFromResponse(payload).length;
};

export const apiErrorMessage = (payload, fallback = '後端請求失敗') => {
  if (!payload) return fallback;
  if (typeof payload === 'string') return payload;
  if (payload.detail) return payload.detail;
  if (payload.error) return payload.error;
  return fallback;
};

export const displayValue = (value, emptyText = '無資料') => (
  value === null || value === undefined || value === '' ? emptyText : value
);
