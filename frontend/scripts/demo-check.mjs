import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const base=process.env.DEMO_URL || 'http://127.0.0.1:3012';
const output=process.env.SCREENSHOT_DIR || '../docs/screenshots';
const bypass=process.env.DEMO_BYPASS_TOKEN;
const authHeaders=bypass ? {'x-vercel-protection-bypass':bypass} : {};
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true});
try {
  for(const width of [1440,390]) {
    const page=await browser.newPage({viewport:{width,height:900}});
    if(bypass) await page.route('**/*',route=>route.continue({headers:{...route.request().headers(),...(new URL(route.request().url()).origin===new URL(base).origin ? authHeaders : {})}}));
    const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    page.on('response',r=>{if(r.url().startsWith(base+'/api/') && r.status()>=400)errors.push(r.status()+' '+r.url());});
    for(const route of ['/', '/discover','/saved','/applications','/insights','/sources','/profile','/about']) {
      const loaded=route==='/about' ? null : page.waitForResponse(r=>r.url().startsWith(base+'/api/analytics/market') && r.status()===200);
      const listings=['/','/discover','/saved','/applications'].includes(route) ? page.waitForResponse(r=>r.url().includes('/api/internships?') && r.status()===200) : null;
      assert.equal((await page.goto(base+route,{waitUntil:'domcontentloaded'})).status(),200);
      if(loaded) await loaded;
      if(listings) {
        await listings;
        await page.getByLabel('Loading opportunities').waitFor({state:'hidden'});
      }
      await page.waitForTimeout(300);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,route+' overflow');
      if(route!=='/about') await page.locator('.notice strong').filter({hasText:'Public Demo'}).waitFor();
      if(route==='/discover') {
        await page.locator('.job-card').first().waitFor();
        assert.equal(await page.getByRole('button',{name:'Discover new roles'}).isDisabled(),true);
        assert.equal(await page.locator('.job-card button[aria-label="Save role"]').first().isDisabled(),true);
        await page.locator('.job-card .title-button').first().click();
        await page.getByRole('dialog').waitFor();
        await page.getByText('Why this match?',{exact:true}).waitFor();
        assert.equal(await page.getByRole('button',{name:'Mark applied',exact:true}).isDisabled(),true);
        assert.equal(await page.getByLabel('Notes',{exact:true}).count(),0);
        await page.screenshot({path:output+'/details-'+width+'.png'});
        await page.keyboard.press('Escape');
        const search=page.getByLabel('Search opportunities');
        const searched=page.waitForResponse(r=>r.url().includes('/api/internships?') && new URL(r.url()).searchParams.get('q')==='Stripe' && r.status()===200);
        await search.fill('Stripe');
        await searched;
        await page.locator('.job-card').first().waitFor();
        assert.ok(await page.locator('.job-card').count()>0);
        const cleared=page.waitForResponse(r=>r.url().includes('/api/internships?') && !new URL(r.url()).searchParams.get('q') && !new URL(r.url()).searchParams.get('paid') && r.status()===200);
        await search.fill('');
        await cleared;
        await page.locator('.job-card').first().waitFor();
        const paid=page.waitForResponse(r=>r.url().includes('/api/internships?') && new URL(r.url()).searchParams.get('paid')==='true' && r.status()===200);
        await page.getByRole('button',{name:'Paid',exact:true}).click();
        await paid;
        await page.locator('.job-card').first().waitFor();
        assert.ok(await page.locator('.job-card').count()>0);
        await page.getByRole('button',{name:'All',exact:true}).click();
        const sorted=page.waitForResponse(r=>r.url().includes('/api/internships?') && new URL(r.url()).searchParams.get('sort')==='newest' && r.status()===200);
        await page.getByLabel('Sort opportunities').selectOption('newest');
        await sorted;
        await page.locator('.job-card').first().waitFor();
      }
      if(route==='/profile') assert.equal(await page.getByRole('button',{name:'Save profile'}).isDisabled(),true);
      if(['/', '/discover','/sources'].includes(route)) await page.screenshot({path:output+'/'+(route==='/'?'overview':route.slice(1))+'-'+width+'.png',fullPage:true});
    }
    assert.deepEqual(errors,[]);
    await page.close();
  }
  for(const path of ['profile','searches','discovery/run','resume/analyze','internships/id/corrections']) {
    for(const method of ['POST','PUT','PATCH','DELETE']) assert.equal((await fetch(base+'/api/'+path,{method,headers:{...authHeaders,'Content-Type':'application/json'},body:'{}'})).status,403);
  }
  for(const path of ['health','ready','internships','analytics/market','providers/health','export.csv','export.xlsx']) assert.equal((await fetch(base+'/api/'+path,{headers:authHeaders})).status,200);
  console.log('PASS: public demo desktop/mobile routes, search, detail explanations, read-only controls, mutation/API boundaries, screenshots and no runtime errors');
} finally {await browser.close();}
