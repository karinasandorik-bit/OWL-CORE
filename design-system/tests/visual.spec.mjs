import { test, expect, devices } from '@playwright/test';
import { fileURLToPath } from 'node:url';
const pageUrl = new URL('../index.html', import.meta.url).href;
const sizes = [
 {name:'desktop',viewport:{width:1440,height:900},isMobile:false},
 {name:'iphone',viewport:{width:390,height:844},isMobile:true}
];
for(const cfg of sizes) test(cfg.name+' renders without horizontal overflow', async({browser},testInfo)=>{
 const context=await browser.newContext({viewport:cfg.viewport,deviceScaleFactor:1,isMobile:cfg.isMobile,hasTouch:cfg.isMobile});
 const page=await context.newPage();
 await page.goto(pageUrl);
 await expect(page.locator('h1')).toContainText('EYES');
 await expect(page.locator('.hero-art svg')).toBeVisible();
 await expect(page.locator('text=STATUS / DESIGN PROTOTYPE, NOT PRODUCTION')).toBeVisible();
 const geometry=await page.evaluate(()=>({scrollWidth:document.documentElement.scrollWidth,viewport:window.innerWidth}));
 expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.viewport+1);
 await page.screenshot({path:testInfo.outputPath(cfg.name+'.png'),fullPage:true,animations:'disabled'});
 await context.close();
});
test('reduced-motion disables brand animations',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.goto(pageUrl);
 const animation=await page.locator('.hero-art svg').evaluate(el=>getComputedStyle(el).animationName);
 expect(animation).toBe('none');
});
test('brand SVG is importable and labelled', async({page})=>{
 const svg=new URL('../owl-mark.svg',import.meta.url).href;
 await page.goto(svg);
 await expect(page.locator('svg title')).toHaveText('OWL Nocturne geometric mark');
 await expect(page.locator('svg desc')).toContainText('Angular owl');
});
