const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'/Users/ed/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const proofs=path.resolve(process.env.OSINT_PROOFS||path.join(root,'Preuves_complement_20261018'));
const scanner=fs.readFileSync('/Users/ed/.codex/skills/responsive-button-guard/scripts/audit-buttons.js','utf8');
(async()=>{
 fs.mkdirSync(proofs,{recursive:true});
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const report={at:new Date().toISOString(),scope:process.env.OSINT_SCOPE||'Synthetic fixture only; loaded spaCy model; no TASS article',matrix:[]};
 try{
  await page.goto(process.env.OSINT_URL||'http://127.0.0.1:18766');
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('sélectionnés'));
  await page.locator('#prediction-text').fill('😀 NATO mentioned a Kalibr missile.');
  await page.locator('#prediction-submit').click();
  await page.waitForFunction(()=>document.querySelector('#prediction-status').textContent.includes('mentions prédites'));
  assert.equal(await page.locator('#prediction-source').textContent(),'😀 NATO mentioned a Kalibr missile.');
  assert((await page.locator('#prediction-meta').textContent()).includes('Texte non enregistré'));
  report.prediction={response_rendered:true,unicode_preserved:true,model_identity_visible:true};
  await page.locator('#prediction-text').fill('Erreur attendue');
  await page.route('**/api/predict',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Erreur synthétique de disponibilité'})}));
  await page.locator('#prediction-submit').click();
  await page.waitForFunction(()=>document.querySelector('#prediction-status').textContent.includes('Erreur synthétique'));
  assert.equal(await page.locator('#prediction-submit').isDisabled(),false);
  report.error_recovery=true;await page.unroute('**/api/predict');
  for(const width of [320,390,559,560,561,700,775,850,1024,1280,1440]){
   await page.setViewportSize({width,height:900});
   for(const enlargement of [1,1.25,1.5,2]){
    await page.evaluate(z=>document.body.style.zoom=String(z),enlargement);await page.evaluate(()=>document.fonts.ready);
    let checked=0;const issues=[];
    for(const selector of ['#prediction-submit','#filters button','#articles button:first-child']){
     await page.locator(selector).scrollIntoViewIfNeeded();const result=await page.evaluate(scanner);checked+=result.checked;issues.push(...result.issues);
    }
    report.matrix.push({width,css_enlargement:enlargement,checked,issues,horizontal_overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)});
   }
  }
  await page.evaluate(()=>document.body.style.zoom='1');await page.setViewportSize({width:700,height:390});
  await page.locator('#prediction-submit').scrollIntoViewIfNeeded();report.landscape=await page.evaluate(scanner);
  await page.setViewportSize({width:1280,height:900});await page.locator('#prediction-text').fill('NATO mentioned a Kalibr missile.');await page.locator('#prediction-submit').click();
  await page.waitForFunction(()=>document.querySelector('#prediction-status').textContent.includes('mentions prédites'));
  await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(proofs,'Interface_prediction_1280.png'),fullPage:true});
  await page.setViewportSize({width:390,height:760});await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(proofs,'Interface_prediction_390.png'),fullPage:true});
  await page.locator('#prediction-text').focus();await page.keyboard.press('Tab');
  report.keyboard_submit_reachable=await page.locator('#prediction-submit').evaluate(el=>document.activeElement===el);
  report.errors=errors;report.issues=report.matrix.filter(r=>r.issues.length||r.horizontal_overflow);
  fs.writeFileSync(path.join(proofs,'Verification_interface.json'),JSON.stringify(report,null,2));
  assert.equal(errors.length,0);assert.equal(report.issues.length,0);assert.equal(report.landscape.issues.length,0);assert(report.keyboard_submit_reachable);
  console.log(JSON.stringify({states:report.matrix.length,issues:report.issues.length,prediction:report.prediction,error_recovery:report.error_recovery}));
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
