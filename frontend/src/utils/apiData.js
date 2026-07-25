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
  const candidate = typeof payload === 'string'
    ? payload
    : (payload.detail || payload.error);
  if (typeof candidate !== 'string') return fallback;

  const message = candidate.trim();
  if (!message || /<!doctype\s+html|<html\b|<head\b|<body\b/i.test(message)) {
    return fallback;
  }
  return message.length > 500 ? `${message.slice(0, 500)}…` : message;
};

export const displayValue = (value, emptyText = '無資料') => (
  value === null || value === undefined || value === '' ? emptyText : value
);
