import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const username = process.env.CAPTURE_USERNAME;
const password = process.env.CAPTURE_PASSWORD;
if (!username || !password) {
  throw new Error('CAPTURE_USERNAME and CAPTURE_PASSWORD are required.');
}

const chromePath = process.env.CHROME_PATH
  || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const reportUrl = process.env.CAPTURE_URL
  || 'http://localhost:3000/research-continuous-signals';
const outputPath = path.resolve(
  process.env.CAPTURE_PATH
    || 'docs/assets/sotera-continuous-signal-report.png',
);
const debugPort = 9333;
const profileDir = fs.mkdtempSync(path.join(os.tmpdir(), 'allcare365-capture-'));

const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function waitForDebugger(timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json/list`);
      if (response.ok) {
        const targets = await response.json();
        const page = targets.find(
          (target) => target.type === 'page' && target.url.startsWith('http://localhost:3000'),
        );
        if (page?.webSocketDebuggerUrl) return page.webSocketDebuggerUrl;
      }
    } catch (_error) {
      // Chrome may still be starting.
    }
    await delay(200);
  }
  throw new Error('Chrome DevTools endpoint did not become ready.');
}

async function connectCdp(webSocketUrl) {
  const socket = new WebSocket(webSocketUrl);
  const pending = new Map();
  let sequence = 0;

  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true });
    socket.addEventListener('error', reject, { once: true });
  });

  socket.addEventListener('message', async (event) => {
    const raw = typeof event.data === 'string'
      ? event.data
      : event.data instanceof ArrayBuffer
        ? Buffer.from(event.data).toString('utf8')
        : await event.data.text();
    const message = JSON.parse(raw);
    if (!message.id || !pending.has(message.id)) return;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result || {});
  });
  socket.addEventListener('close', (event) => {
    for (const { reject } of pending.values()) {
      reject(new Error(`Chrome DevTools socket closed (${event.code}).`));
    }
    pending.clear();
  });
  socket.addEventListener('error', () => {
    for (const { reject } of pending.values()) {
      reject(new Error('Chrome DevTools socket failed.'));
    }
    pending.clear();
  });

  return {
    socket,
    send(method, params = {}) {
      sequence += 1;
      return new Promise((resolve, reject) => {
        if (socket.readyState !== WebSocket.OPEN) {
          reject(new Error('Chrome DevTools socket is not open.'));
          return;
        }
        pending.set(sequence, { resolve, reject });
        socket.send(JSON.stringify({ id: sequence, method, params }));
      });
    },
  };
}

async function waitForPage(send, expression, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const result = await send('Runtime.evaluate', {
      expression,
      returnByValue: true,
    });
    if (result.result?.value) return;
    await delay(250);
  }
  throw new Error('The report page did not finish rendering.');
}

const chrome = spawn(chromePath, [
  '--headless=new',
  '--disable-gpu',
  '--no-sandbox',
  '--disable-gpu-sandbox',
  '--disable-dev-shm-usage',
  '--enable-logging=stderr',
  '--hide-scrollbars',
  '--no-first-run',
  '--no-default-browser-check',
  '--remote-allow-origins=*',
  `--remote-debugging-port=${debugPort}`,
  `--user-data-dir=${profileDir}`,
  '--window-size=1680,1200',
  'http://localhost:3000/login',
], {
  stdio: ['ignore', 'ignore', 'pipe'],
  windowsHide: true,
});
let chromeStderr = '';
chrome.stderr.on('data', (chunk) => {
  chromeStderr = `${chromeStderr}${chunk.toString('utf8')}`.slice(-8000);
});

let cdp;
try {
  const webSocketUrl = await waitForDebugger();
  cdp = await connectCdp(webSocketUrl);
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Page.navigate', { url: 'http://localhost:3000/login' });
  await waitForPage(
    cdp.send,
    "location.origin === 'http://localhost:3000' && document.readyState !== 'loading'",
  );

  const loginExpression = `
    (async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/auth/login/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: ${JSON.stringify(username)},
            password: ${JSON.stringify(password)}
          })
        });
        if (!response.ok) {
          return { ok: false, error: 'Capture login failed: ' + response.status, body: await response.text() };
        }
        const data = await response.json();
        const user = data.user || {};
        const role = user.role || user.product_role || user.legacy_role || user.user_type || 'patient';
        const roles = Array.isArray(user.roles) ? user.roles : [role];
        localStorage.setItem('access_token', data.access || '');
        localStorage.setItem('refresh_token', data.refresh || '');
        localStorage.setItem('user_info', JSON.stringify({
          id: user.id,
          username: user.username || 'capture-user',
          first_name: user.first_name || '',
          last_name: user.last_name || '',
          role,
          roles,
          product_role: user.product_role || '',
          legacy_role: user.legacy_role || '',
          email: user.email || ''
        }));
        window.location.replace(${JSON.stringify(reportUrl)});
        return { ok: true };
      } catch (error) {
        return { ok: false, error: String(error), stack: error?.stack || '' };
      }
    })()
  `;
  const loginResult = await cdp.send('Runtime.evaluate', {
    expression: loginExpression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (loginResult.exceptionDetails) {
    throw new Error(loginResult.exceptionDetails.text || 'Capture login failed.');
  }
  if (!loginResult.result?.value?.ok) {
    throw new Error(JSON.stringify(loginResult.result?.value || { error: 'Capture login failed.' }));
  }

  await waitForPage(
    cdp.send,
    "Boolean(document.querySelector('.continuous-report .signal-hero')) && document.body.innerText.includes('資料庫匯入成功')",
  );
  await delay(700);

  const metrics = await cdp.send('Page.getLayoutMetrics');
  const content = metrics.cssContentSize || metrics.contentSize;
  const screenshot = await cdp.send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: true,
    fromSurface: true,
    clip: {
      x: 0,
      y: 0,
      width: Math.ceil(content.width),
      height: Math.ceil(content.height),
      scale: 1,
    },
  });
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, Buffer.from(screenshot.data, 'base64'));
  process.stdout.write(`${outputPath}\n`);
} catch (error) {
  await delay(200);
  if (chromeStderr) process.stderr.write(chromeStderr);
  throw error;
} finally {
  if (cdp) {
    try {
      await cdp.send('Browser.close');
    } catch (_error) {
      // The browser may already be closing.
    }
    cdp.socket.close();
  }
  if (!chrome.killed) chrome.kill();
  await delay(300);
  const tempRoot = path.resolve(os.tmpdir());
  const resolvedProfile = path.resolve(profileDir);
  if (resolvedProfile.startsWith(`${tempRoot}${path.sep}`)) {
    try {
      fs.rmSync(resolvedProfile, { recursive: true, force: true });
    } catch (_error) {
      if (chromeStderr) process.stderr.write(chromeStderr);
    }
  }
}
