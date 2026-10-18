export const parseApiResponse = async (response) => {
  if (response.status === 204 || response.status === 205) return {};

  const mediaType = (response.headers.get('content-type') || '').split(';', 1)[0].trim().toLowerCase();
  const isJson = mediaType === 'application/json' || /^[^\s/]+\/[^\s/]+\+json$/.test(mediaType);

  if (!isJson) {
    const text = await response.text();
    return text ? { detail: text } : {};
  }

  try {
    return await response.json();
  } catch (error) {
    if (error?.name === 'SyntaxError') {
      throw new Error('伺服器回應格式不正確，請稍後重試。');
    }
    throw error;
  }
};
