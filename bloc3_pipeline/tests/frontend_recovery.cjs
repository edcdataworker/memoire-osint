// Exercise the actual UI script with a synthetic DOM and transport. No live jobs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const source = fs.readFileSync(path.join(__dirname,'../pipeline/collection/static/app.js'),'utf8');
const tick = () => new Promise(resolve=>setImmediate(resolve));
async function fixture(initiallyOffline=false){
  const fields=new Map(), requests=[];
  const transport={offline:initiallyOffline,token:'initial',failPost:false};
  function field(selector){
    if(!fields.has(selector))fields.set(selector,{value:selector.endsWith('section')?'defense':selector.endsWith('limit')?'20':selector.endsWith('start')||selector.endsWith('end')?'2025-10-26':'',textContent:'',hidden:true,dataset:{},classList:{toggle(){}},addEventListener(){},replaceChildren(){this.value='';this.options=[];},add(option){(this.options??=[]).push(option);if(!this.value)this.value=option.value;}});
    return fields.get(selector);
  }
  const context=vm.createContext({Intl,URLSearchParams,console,Option:function(text,value){this.text=text;this.value=value;},document:{querySelector:field,querySelectorAll:()=>[],activeElement:null,addEventListener(){}},setInterval:()=>1,setTimeout:()=>1,clearTimeout(){},fetch:async(url,options={})=>{
    requests.push({url,options});
    if(transport.offline||(transport.failPost&&options.method==='POST'))throw new TypeError('Failed to fetch');
    const data=url==='/api/config'?{csrf:transport.token,sections:{defense:'Défense',world:'Monde'}}:url==='/api/status'?{articles:21681,active:null,jobs:[],events:[],bridge:null,read_only:Boolean(transport.readOnly),backend:transport.readOnly?"mirror":"primary",mirror_at:"2026-10-04T12:00:00Z"}:url.startsWith('/api/corpus')?{total:3}:{job_id:'synthetic'};
    return {ok:true,json:async()=>data};
  }});
  vm.runInContext(source,context);
  for(let i=0;i<8;i++)await tick();
  return {context,field,transport,requests,run:code=>vm.runInContext(code,context)};
}
test('a temporary status failure clears on recovery, without clearing validation errors',async()=>{
  const f=await fixture();
  f.transport.offline=true;await f.run('refresh()');
  assert.equal(f.field('#global-state').textContent,'Indisponible');
  assert.equal(f.field('#start-button').disabled,true);
  assert.match(f.field('#notice').textContent,/Connexion au service local interrompue/);
  f.transport.offline=false;await f.run('refresh()');
  assert.equal(f.field('#notice').hidden,true);
  assert.equal(f.field('#global-state').textContent,'Prêt');
  f.run('notice("Choisissez une période valide.",true)');await f.run('refresh()');
  assert.equal(f.field('#notice').hidden,false);
  assert.equal(f.field('#notice').textContent,'Choisissez une période valide.');
});
test('initial service outage can recover through the next periodic refresh',async()=>{
  const f=await fixture(true);
  assert.equal(f.field('#global-state').textContent,'Indisponible');
  f.transport.offline=false;await f.run('refresh()');
  assert.equal(f.field('#notice').hidden,true);
  assert.equal(f.field('#section').options.length,2);
  assert.equal(f.field('#existing').textContent,'3');
});
test('commands obtain the current session token and a failed mutation is never replayed',async()=>{
  const f=await fixture();f.transport.token='restarted-session';
  await f.run('api("/api/start",{section:"defense"})');
  const posts=()=>f.requests.filter(r=>r.options.method==='POST');
  assert.equal(posts()[0].options.headers['X-CSRF-Token'],'restarted-session');
  f.transport.failPost=true;
  await assert.rejects(()=>f.run('api("/api/start",{section:"defense"})'),/Connexion au service local interrompue/);
  assert.equal(posts().length,2);
});

test('degraded storage keeps reads available and blocks collection until restored',async()=>{
 const f=await fixture();f.transport.readOnly=true;await f.run('refresh()');
 assert.equal(f.field('#global-state').textContent,'Secours en lecture');
 assert.equal(f.field('#start-button').disabled,true);
 assert.equal(f.field('#notice').dataset.scope,'storage');
 assert.match(f.field('#notice').textContent,/Collecte et import suspendus/);
 f.transport.readOnly=false;await f.run('refresh()');
 assert.equal(f.field('#start-button').disabled,false);
 assert.equal(f.field('#notice').hidden,true);
});
