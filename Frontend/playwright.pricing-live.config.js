import { defineConfig } from '@playwright/test'
export default defineConfig({testDir:'./tests/pricing-live',workers:1,timeout:120000,reporter:'list',outputDir:'test-results/pricing-live',
  use:{baseURL:process.env.TRAVELLY_PRICING_BASE_URL || 'http://127.0.0.1:5182',channel:'chrome',trace:'off'},
  projects:[{name:'desktop',use:{viewport:{width:1366,height:900}}},{name:'mobile',use:{viewport:{width:360,height:740}}}],
})
