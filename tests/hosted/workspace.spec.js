import {test,expect} from '@playwright/test';

test('browser snapshots survive reload, keep prior evidence on failure and remain isolated',async({page,browser,request})=>{
  const empty = await (await request.get('/api/browser-bootstrap')).json();
  const snapshot = {...empty, repository:'learner/practice',root:'projects',completed:1,percent:0,activity:[{id:'a'.repeat(40),sha:'a'.repeat(40),source:'manual',created_at:'2026-09-09T00:00:00Z'}]};
  snapshot.last_sync=snapshot.activity[0];
  snapshot.projects=snapshot.projects.map(p=>({...p,repository:snapshot.repository,sha:snapshot.last_sync.sha}));
  let failed=false;
  await page.route('**/api/browser-sync',route=>route.fulfill({status:failed?429:200,json:failed?{detail:'GitHub rate limit reached. Your saved progress was kept.'}:snapshot}));
  await page.goto('/');
  await page.getByPlaceholder('owner/repository or GitHub URL').fill('learner/practice');
  await page.getByRole('button',{name:'Connect and load'}).click();
  await expect(page.getByText('Repository connected. Curriculum and GitHub evidence are up to date.',{exact:true})).toBeVisible();
  await page.reload();
  await expect(page.getByPlaceholder('owner/repository or GitHub URL')).toHaveValue('learner/practice');
  failed=true;
  await page.getByRole('button',{name:'Sync repository',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('saved progress was kept');
  await page.goto('/#project/P1');
  await expect(page.getByRole('heading',{name:'What you type'})).toBeVisible();
  const other=await browser.newContext(); const isolated=await other.newPage();
  await isolated.goto('http://127.0.0.1:8792/');
  await expect(isolated.getByPlaceholder('owner/repository or GitHub URL')).toHaveValue('');
  await other.close();
});
