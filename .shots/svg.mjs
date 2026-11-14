import { chromium } from '@playwright/test'
const b = await chromium.launch({ channel: 'chrome' }); const p = await b.newPage({ viewport: { width: 1536, height: 1024 } })
await p.goto('file:///D:/Travelly/Frontend/public/images/travelly/landing-scenes-2026-11-07/home/card-vehicle-hire-route.svg'); await p.screenshot({ path: 'D:/Travelly/.shots/svg.png' }); await b.close()
