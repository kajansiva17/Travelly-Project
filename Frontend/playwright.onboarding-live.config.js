import {defineConfig} from '@playwright/test'
export default defineConfig({testDir:'./tests/onboarding-live',workers:1,timeout:120000,expect:{timeout:20000},reporter:'list',use:{baseURL:'http://127.0.0.1:5182',channel:'chrome',trace:'retain-on-failure'},projects:[{name:'desktop',use:{viewport:{width:1366,height:900}}},{name:'mobile',use:{viewport:{width:360,height:740}}}]})
