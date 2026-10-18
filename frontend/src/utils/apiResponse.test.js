import { parseApiResponse } from './apiResponse';

const jsonResponse = (body, contentType = 'application/json') => new Response(body, {
  headers: { 'Content-Type': contentType },
});

test.each([
  ['application/json; charset=utf-8', { count: 0 }],
  ['Application/JSON', [0, false]],
  ['application/fhir+json; charset=utf-8', { resourceType: 'MeasureReport' }],
  ['application/problem+json', { title: 'Invalid request' }],
])('parses JSON media type %s without a text wrapper', async (contentType, payload) => {
  await expect(parseApiResponse(jsonResponse(JSON.stringify(payload), contentType))).resolves.toEqual(payload);
});

test.each([0, false, null])('preserves JSON value %s', async (payload) => {
  await expect(parseApiResponse(jsonResponse(JSON.stringify(payload)))).resolves.toBe(payload);
});

test('does not treat a JSON phrase in a plain-text parameter as its media type', async () => {
  await expect(parseApiResponse(jsonResponse('plain reply', 'text/plain; note=application/json')))
    .resolves.toEqual({ detail: 'plain reply' });
});

test('keeps empty plain-text replies empty', async () => {
  await expect(parseApiResponse(new Response(''))).resolves.toEqual({});
});

test.each([204, 205])('handles HTTP %s without attempting JSON decoding', async (status) => {
  await expect(parseApiResponse(new Response(null, {
    status, headers: { 'Content-Type': 'application/json' },
  }))).resolves.toEqual({});
});

test('reports malformed JSON without exposing response body fragments', async () => {
  await expect(parseApiResponse(jsonResponse('private-response-fragment')))
    .rejects.toThrow('伺服器回應格式不正確，請稍後重試。');
});

test('preserves request cancellation', async () => {
  const abort = new DOMException('Cancelled', 'AbortError');
  const response = jsonResponse('{}');
  response.json = async () => { throw abort; };
  await expect(parseApiResponse(response)).rejects.toBe(abort);
});
