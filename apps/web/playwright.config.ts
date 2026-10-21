import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e', workers: 1, timeout: 45000,
  use: { baseURL: 'http://127.0.0.1:5173', headless: true },
  webServer: {
    command: 'npm run dev', url: 'http://127.0.0.1:5173',
    reuseExistingServer: false, timeout: 30000,
  },
});
