import { apiErrorMessage } from './apiData';

describe('apiErrorMessage', () => {
  test('does not render an HTML error document as user-facing text', () => {
    const html404 = '<!DOCTYPE html><html><head><title>Page not found</title></head></html>';

    expect(apiErrorMessage({ detail: html404 }, '風險模型目錄讀取失敗')).toBe(
      '風險模型目錄讀取失敗',
    );
  });

  test('keeps concise API error details', () => {
    expect(apiErrorMessage({ detail: 'Patient not found.' }, 'fallback')).toBe(
      'Patient not found.',
    );
  });
});
