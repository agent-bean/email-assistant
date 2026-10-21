import { test, expect } from '@playwright/test';
import { spawn, type ChildProcess } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import net from 'node:net';

let api: ChildProcess | undefined;
const backend = fileURLToPath(new URL('../../../backend/', import.meta.url));

async function startApi() {
  api = spawn('uv', ['run', '--locked', 'uvicorn', 'email_assistant.api.main:app',
    '--host', '127.0.0.1', '--port', '8000'], {
    cwd: backend, detached: true, stdio: 'ignore',
    env: { ...process.env, APP_ENV_FILE: '', APP_ENVIRONMENT: 'local' },
  });
  await expect.poll(async () => {
    if (api?.exitCode !== null) throw new Error('Owned API exited before readiness');
    try { return (await fetch('http://127.0.0.1:8000/health')).status; }
    catch { return 0; }
  }, { timeout: 15000 }).toBe(200);
}

async function stopApi() {
  if (!api || api.exitCode !== null) return;
  const exit = once(api, 'exit');
  process.kill(-api.pid!, 'SIGTERM');
  await exit;
  api = undefined;
}

test.beforeAll(async () => {
  const server = net.createServer();
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(8000, '127.0.0.1', resolve);
  });
  await new Promise<void>(resolve => server.close(() => resolve()));
});

test.afterAll(stopApi);

test('real API proxy, loading, keyboard retry and outage recovery', async ({ page }) => {
  const retry = page.getByRole('button', { name: 'Check again' });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Email Assistant', exact: true })).toBeVisible();
  await expect(page.getByRole('status')).toContainText('API unavailable');
  await startApi();
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', {
    offline: false, latency: 600, downloadThroughput: -1, uploadThroughput: -1,
  });
  await page.keyboard.press('Tab');
  await expect(retry).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status')).toHaveText('Checking API…');
  await expect(page.getByRole('status')).toHaveText('API is running.');
  const response = await page.request.get('/api/health');
  expect(await response.json()).toEqual({ status: 'ok' });
  await stopApi();
  await retry.click();
  await expect(page.getByRole('status')).toContainText('API unavailable');
  await startApi();
  await retry.click();
  await expect(page.getByRole('status')).toHaveText('API is running.');
  await page.setViewportSize({ width: 375, height: 812 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
