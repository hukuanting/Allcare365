// Display-only source normalization. Clinical input validation belongs to ingestion.
export const numericValue = value => {
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  if (typeof value === 'string' && !value.trim()) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

const boundedValue = (value, maximum) => {
  const numeric = numericValue(value);
  return numeric !== null && numeric >= 0 && numeric <= maximum ? numeric : null;
};

export const percentageValue = value => boundedValue(value, 100);
export const ratioValue = value => boundedValue(value, 1);

export const countValue = value => {
  const numeric = numericValue(value);
  return Number.isSafeInteger(numeric) && numeric >= 0 ? numeric : null;
};
