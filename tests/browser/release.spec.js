import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('workflow review asks for photos without requiring GitHub',async({page})=>{
  await page.goto('http://127.0.0.1:8791/#project/P193');
  await expect(page.getByLabel('How will you show your work?')).toHaveValue('screenshots');
  await expect(page.getByText('No GitHub submission is required for this review.',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'PROJECT REVIEW Check P193'}).click();
  await expect(page.getByLabel('Review prompt')).toHaveValue(/I will attach screenshots or photos/);
  await expect(page.getByLabel('Review prompt')).not.toHaveValue(/OWNER\/REPOSITORY/);
  await page.keyboard.press('Escape');
  await page.getByLabel('How will you show your work?').selectOption('github');
  await page.getByRole('button',{name:'PROJECT REVIEW Check P193'}).click();
  await expect(page.getByLabel('Review prompt')).toHaveValue(/GitHub repository/);
});

test('public curriculum is rendered without JS and keeps learner endpoints closed',async({browser,request})=>{
  const context=await browser.newContext({javaScriptEnabled:false});
  const page=await context.newPage();
  await page.goto('http://127.0.0.1:8790/');
  await expect(page.getByRole('heading',{level:1})).toContainText('AI automation');
  await page.getByRole('link',{name:'Explore the curriculum'}).click();
  await page.getByRole('link',{name:/Phase 1:/}).click();
  await expect(page.getByRole('heading',{name:"P1 · Ohm's Law Calculator",exact:true})).toBeVisible();
  expect((await request.get('http://127.0.0.1:8790/api/progress')).status()).toBe(404);
  await context.close();
});

test('public pages have no automated WCAG A/AA violations at desktop and mobile widths',async({page})=>{
  for(const width of [1280,375,320]){
    await page.setViewportSize({width,height:900});
    for(const path of ['/','/curriculum','/curriculum/phase-1','/learning-method','/about']){
      await page.goto('http://127.0.0.1:8790'+path);
      if(width===1280&&path==='/')await page.screenshot({path:'tmp/public-home.png'});
      if(width===375&&path==='/curriculum/phase-1')await page.screenshot({path:'tmp/public-phase-mobile.png'});
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
      const audit=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
      expect(audit.violations).toEqual([]);
    }
  }
});

test('local workspace routes and Coach panel remain functional',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://127.0.0.1:8791/');
  await expect(page.getByText('No GitHub repository connected').first()).toBeVisible();
  await page.getByRole('button',{name:'Projects',exact:true}).click();
  await page.getByRole('button',{name:/Ohm's Law Calculator/}).click();
  await expect(page.getByRole('heading',{level:1})).toContainText('P1');
  await page.getByRole('button',{name:'PROJECT REVIEW Check P1'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByLabel('Review prompt')).toBeFocused();
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.setViewportSize({width:375,height:850});
  await page.screenshot({path:'tmp/local-project-mobile.png'});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test('local main views pass automated accessibility checks',async({page})=>{
  for(const hash of ['#','#roadmap','#setup','#project/P1','#settings']){
    await page.goto('http://127.0.0.1:8791/'+hash);
    await page.waitForFunction(()=>!document.body.textContent.includes('Loading your workspace')&&!document.body.textContent.includes('Loading project…'));
    const audit=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
    expect(audit.violations).toEqual([]);
  }
});
