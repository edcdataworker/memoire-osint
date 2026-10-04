// Browser recipe for this local workstation. Data commands are bounded live demos.
const fs = require('fs');
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/Users/ed/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const proof = path.resolve('Preuves/Collecte_TASS');
fs.mkdirSync(proof, {recursive:true});
const scanner = fs.readFileSync('/Users/ed/.codex/skills/responsive-button-guard/scripts/audit-buttons.js','utf8');
const sleep = ms => new Promise(r=>setTimeout(r,ms));
(async()=>{
  const browser = await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
  const context = await browser.newContext({viewport:{width:1440,height:1000},recordVideo:{dir:proof,size:{width:1440,height:1000}}});
  const page = await context.newPage();
  const errors = []; page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:18743');
  await page.waitForFunction(()=>document.querySelector('#total').textContent.includes('21'));
  await page.locator('#start').fill('2026-10-03');
  await page.locator('#end').fill('2026-10-03');
  await page.locator('#limit').selectOption('5');
  await page.locator('#preview-button').click();
  const response = page.waitForResponse(r=>r.url().endsWith('/api/start') && r.request().method()==='POST');
  await page.locator('#start-button').click();
  const key = (await (await response).json()).job_id;
  const status = async()=>page.evaluate(async()=>await(await fetch('/api/status')).json());
  const until = async(predicate,seconds=90)=>{
    const deadline=Date.now()+seconds*1000;
    while(Date.now()<deadline){const s=await status();if(predicate(s))return s;await sleep(150);}
    throw Error('Timed out waiting for collection');
  };
  let s=await until(s=>s.jobs.find(j=>j.job_id===key).processed>=1);
  const running=s.jobs.find(j=>j.job_id===key);
  let pause=null;
  if(running.status==='running'){
    await page.locator(`[data-job="${key}"][data-action="stop"]`).click();
    s=await until(s=>s.jobs.find(j=>j.job_id===key).status==='paused');
    pause=s.jobs.find(j=>j.job_id===key);
    await page.screenshot({path:path.join(proof,'pause.png'),fullPage:true});
    await page.locator(`[data-job="${key}"][data-action="resume"]`).click();
  }
  s=await until(s=>['complete','empty','failed','quality_failed'].includes(s.jobs.find(j=>j.job_id===key).status));
  const collected=s.jobs.find(j=>j.job_id===key);
  if(collected.status!=='complete')throw Error('Live collection failed: '+JSON.stringify(collected));
  await page.screenshot({path:path.join(proof,'suivi.png'),fullPage:true});
  await page.locator(`[data-job="${key}"][data-action="corpus"]`).click();
  await page.locator('[data-article]').first().waitFor();
  const downloaded=await page.evaluate(async()=>await(await fetch(document.querySelector('#export-json').href)).json());
  const jsonl=await page.evaluate(async()=>await(await fetch(document.querySelector('#export-jsonl').href)).text());
  if(JSON.stringify(downloaded)!==JSON.stringify(jsonl.trim().split('\n').map(JSON.parse)))throw Error('Export formats differ');
  await page.locator('[data-article]').first().click();
  await page.locator('#article-dialog[open]').waitFor();
  await page.screenshot({path:path.join(proof,'article.png'),fullPage:true});
  await page.keyboard.press('Escape');
  if(await page.locator('#article-dialog').getAttribute('open')!==null)throw Error('Escape did not close dialog');
  const matrix=[];
  for(const width of [320,390,560,649,650,651,700,775,849,850,851,1024,1149,1150,1151,1280,1440]){
    await page.setViewportSize({width,height:900});
    for(const view of ['collecte','suivi','corpus']){
      await page.locator(`.nav-button[data-tab="${view}"]`).click();
      await sleep(70);
      for(const position of ['top','bottom']){
        await page.evaluate(p=>window.scrollTo(0,p==='top'?0:document.documentElement.scrollHeight),position);
        const audit=await page.evaluate(scanner);
        const horizontal=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
        matrix.push({width,view,position,horizontal,audit});
      }
    }
    await page.locator('[data-article]').first().click();
    await page.locator('#article-dialog[open]').waitFor();
    await page.evaluate(()=>globalThis.__buttonAuditOptions={rootSelector:'#article-dialog'});
    matrix.push({width,view:'dialog',audit:await page.evaluate(scanner)});
    await page.evaluate(()=>delete globalThis.__buttonAuditOptions);
    await page.keyboard.press('Escape');
    await page.locator('#article-dialog[open]').waitFor({state:'hidden'});
    if(width===320)await page.screenshot({path:path.join(proof,'mobile.png'),fullPage:true});
  }
  await page.setViewportSize({width:1280,height:450});
  for(const zoom of [1.25,1.5,2]){
    await page.evaluate(z=>document.body.style.zoom=z,zoom);
    for(const view of ['collecte','suivi','corpus']){
      await page.locator(`.nav-button[data-tab="${view}"]`).click();
      await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));
      matrix.push({width:1280,height:450,zoom,view,audit:await page.evaluate(scanner),horizontal:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)});
    }
  }
  await page.evaluate(()=>document.body.style.zoom='');
  await page.setViewportSize({width:1440,height:1000});
  await page.locator('.nav-button[data-tab="collecte"]').click();
  await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:path.join(proof,'collecte.png'),fullPage:true});
  // Only a completed user-chosen bounded selection is handed to the existing B2 stack.
  const csrf=await page.evaluate(async()=>(await(await fetch('/api/config')).json()).csrf);
  const result=await page.evaluate(async({csrf,key})=>{const r=await fetch('/api/ingest-b2',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({job_id:key})});return {status:r.status,body:await r.json()};},{csrf,key});
  if(result.status!==202)throw Error('B2 command refused: '+JSON.stringify(result));
  s=await until(s=>s.bridge && s.bridge.status!=='running',240);
  const video=page.video();
  const report={at:new Date().toISOString(),browser:'Google Chrome on macOS',live_job:collected,pause,export_count:downloaded.length,export_fields:Object.keys(downloaded[0]||{}),bridge:s.bridge,page_errors:errors,matrix,zoom_method:'CSS body zoom 125/150/200 percent, short 1280x450 viewport; native browser zoom and other browsers not tested'};
  fs.writeFileSync(path.join(proof,'UI_validation.json'),JSON.stringify(report,null,2));
  await context.close();await video.saveAs(path.join(proof,'Collecte_locale_TASS.webm'));await browser.close();
  console.log(JSON.stringify({job_id:key,live:collected.counts,pause:Boolean(pause),export:downloaded.length,bridge:s.bridge,page_errors:errors,matrix_cases:matrix.length,issues:matrix.filter(x=>x.horizontal||x.audit.issues?.length)},null,2));
})().catch(e=>{console.error(e);process.exit(1);});
