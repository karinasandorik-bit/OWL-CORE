import { defineConfig } from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'*.spec.mjs',reporter:[['list'],['html',{open:'never',outputFolder:'playwright-report'}]],use:{browserName:'chromium'},retries:0});
