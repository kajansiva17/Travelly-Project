import { defineConfig, devices } from '@playwright/test'
export default defineConfig({
  testDir: './tests/auth-live', workers: 1, fullyParallel: false, timeout: 60000, reporter: 'list',
  outputDir: 'test-results/auth-live',
  use: { baseURL: 'http://127.0.0.1:5181', channel: 'chrome', trace: 'off' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1366, height: 900 } } },
    { name: 'mobile', use: { ...devices['Pixel 5'], viewport: { width: 360, height: 640 }, channel: 'chrome' } },
  ],
})
