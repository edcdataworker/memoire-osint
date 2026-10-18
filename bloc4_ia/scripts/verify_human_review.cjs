const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const {chromium} = require('/Users/ed/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const proof=path.join(root,'Preuves/Revue_humaine');fs.mkdirSync(proof,{recursive:true});
const scanner=fs.readFileSync('/Users/ed/.codex/skills/responsive-button-guard/scripts/audit-buttons.js','utf8');
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const report={scope:'Synthetic end-to-end tests; real 42-article UI only viewed, never attested',at:new Date().toISOString(),matrix:[]};
 try{
  await page.goto('http://127.0.0.1:18767');await page.waitForFunction(()=>document.querySelector('#progress').textContent.includes('/ 3'));
  await page.locator('#evaluate').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Revue incomplète'));
  await page.locator('#reviewer').fill('Test automatique : articles fictifs uniquement');
  await page.locator('#draft').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Brouillon enregistré'));
  await page.reload();await page.waitForFunction(()=>document.querySelector('#progress').textContent.includes('0 / 3'));
  for(let i=0;i<3;i++){
   await page.locator('#choose').selectOption(String(i));await page.locator('#reviewer').fill('Test automatique : articles fictifs uniquement');
   await page.locator('#attest').check();await page.locator('#validate').click();await page.waitForFunction(n=>document.querySelector('#progress').textContent.startsWith(`${n} / 3`),i+1);
  }
  await page.locator('#evaluate').click();await page.waitForFunction(()=>document.querySelector('#result').textContent.includes('3 articles évalués'),{timeout:30000});
  assert((await page.locator('#result').textContent()).includes('F1 :'));
  await page.locator('#note').fill('Brouillon fictif modifié');await page.locator('#draft').click();await page.waitForFunction(()=>document.querySelector('#progress').textContent.startsWith('2 / 3'));
  report.synthetic_flow={incomplete_rejected:true,draft_restored:true,attestation_explicit:true,evaluation_returned:true,edited_attestation_revoked:true};
  // Actual source texts are never saved, attested or exported by this browser test.
  await page.goto('http://127.0.0.1:8767');await page.waitForFunction(()=>document.querySelector('#progress').textContent.includes('/ 42'));
  assert((await page.locator('#progress').textContent()).startsWith('0 / 42'));
  for(const width of [320,390,560,649,650,651,700,775,850,1024,1280,1440]){
   await page.setViewportSize({width,height:900});
   for(const zoom of [1,1.25,1.5,2]){
    await page.evaluate(z=>document.body.style.zoom=String(z),zoom);await page.evaluate(()=>document.fonts.ready);
    const issues=[];let checked=0;
    for(const selector of ['#progress','#add','#annotations','#draft','#evaluate']){
     await page.locator(selector).scrollIntoViewIfNeeded();const result=await page.evaluate(scanner);issues.push(...result.issues);checked+=result.checked;
    }
    const horizontal=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
    report.matrix.push({width,css_enlargement:zoom,checked,issues,horizontal_overflow:horizontal});
   }
  }
  await page.evaluate(()=>document.body.style.zoom='1');await page.setViewportSize({width:1280,height:900});await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:path.join(proof,'interface_1280.png'),fullPage:true});
  await page.setViewportSize({width:390,height:760});await page.reload();await page.waitForFunction(()=>document.querySelector('#source').textContent.length>0);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(proof,'interface_390.png'),fullPage:true});
  await page.locator('#evaluate').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('0 / 42'));
  report.real_state={articles:42,human_reviewed:0,quality_evaluation_blocked:true};
  report.errors=errors;report.issues=report.matrix.filter(r=>r.issues.length||r.horizontal_overflow);
  fs.writeFileSync(path.join(proof,'Verification_interface.json'),JSON.stringify(report,null,2));
  assert.equal(errors.length,0);assert.equal(report.issues.length,0);
  console.log(JSON.stringify({states:report.matrix.length,issues:report.issues.length,errors:errors.length,synthetic_flow:report.synthetic_flow,real_state:report.real_state}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
