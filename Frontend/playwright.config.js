import { defineConfig, devices } from '@playwright/test'
export default defineConfig({
  testDir: './tests/browser', fullyParallel: false, workers: 1,
  timeout: 30000, reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:5180', channel: 'chrome', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1366, height: 900 } } },
    { name: 'mobile', use: { ...devices['Pixel 5'], viewport: { width: 360, height: 640 }, defaultBrowserType: 'chromium', channel: 'chrome' } },
  ],
  webServer: { command: 'npm run dev -- --port 5180 --strictPort', url: 'http://127.0.0.1:5180', reuseExistingServer: true },
})
