'use strict';
const $ = id => document.getElementById(id);
let state, index = 0, selection = null, dirty = false;
const labels = ['WEAPON', 'MIL_UNIT', 'MIL_ORG'];
function status(text) { $('status').textContent = text; }
function changed() { dirty = true; $('attest').checked = false; status('Modifications à enregistrer. Une nouvelle attestation sera nécessaire.'); }
async function api(path, body) {
  const options = body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-Review-Token':state.csrf}, body:JSON.stringify(body)};
  const response = await fetch(path, options); const value = await response.json();
  if (!response.ok) throw Error(value.error || 'Erreur de revue'); return value;
}
function checkedSpans() {
  const chars = Array.from(state.articles[index].text);
  const spans = [...$('annotations').children].map(row => ({start:Number(row.querySelector('.start').value),end:Number(row.querySelector('.end').value),label:row.querySelector('select').value})).sort((a,b)=>a.start-b.start);
  let previous = 0;
  for (const s of spans) { if (!Number.isInteger(s.start)||!Number.isInteger(s.end)||s.start<previous||s.start<0||s.end<=s.start||s.end>chars.length||!labels.includes(s.label)) throw Error('Corrige les positions ou les chevauchements avant d’enregistrer.'); s.text=chars.slice(s.start,s.end).join(''); previous=s.end; }
  return spans;
}
function addSpan(span) {
  const row = document.createElement('div'); row.className='annotation';
  for (const [name,label,value] of [['start','Début',span.start],['end','Fin',span.end]]) {
    const wrap=document.createElement('label'); wrap.textContent=label;
    const input=document.createElement('input');input.type='number';input.min=0;input.value=value;input.className=name;
    input.oninput=()=>{changed();refreshSurface(row);};wrap.appendChild(input);row.appendChild(wrap);
  }
  const wrap=document.createElement('label');wrap.textContent='Label';const select=document.createElement('select');
  labels.forEach(label=>{const option=document.createElement('option');option.value=label;option.textContent=label;select.appendChild(option);});select.value=span.label;select.onchange=changed;wrap.appendChild(select);row.appendChild(wrap);
  const surface=document.createElement('span');surface.className='surface';row.appendChild(surface);
  const remove=document.createElement('button');remove.className='secondary';remove.textContent='Retirer';remove.onclick=()=>{row.remove();changed();$('empty').hidden=!!$('annotations').children.length;};row.appendChild(remove);
  $('annotations').appendChild(row);refreshSurface(row);
}
function refreshSurface(row) { const chars=Array.from(state.articles[index].text);row.querySelector('.surface').textContent=chars.slice(Number(row.querySelector('.start').value),Number(row.querySelector('.end').value)).join(''); }
function show() {
  const r=state.articles[index];$('title').textContent=r.title || `Article ${r.id}`;$('source').textContent=r.text;$('url').textContent=r.url;$('url').href=r.url;
  $('identity').textContent=`Article ${r.id} · réservé au test · ${Array.from(r.text).length} caractères`;
  $('choose').value=index;
  const codexReviewed=state.articles.filter(article=>article.review_note?.startsWith('PRÉLECTURE CODEX, IA.')).length;
  $('progress').textContent=`Prélecture Codex (IA) : ${codexReviewed} / ${state.total} · attestations humaines : ${state.reviewed} / ${state.total}`;
  $('annotations').replaceChildren();r.entities.forEach(addSpan);$('empty').hidden=!!r.entities.length;
  $('note').value=r.review_note||'';if(r.reviewer)$('reviewer').value=r.reviewer;
  $('attest').checked=false;dirty=false;selection=null;
  status(r.annotation_status==='human_reviewed'?`Attestation enregistrée par ${r.reviewer}.`:'À relire ; aucune attestation humaine pour cet article.');
}
async function save(attest) {
  if(attest&&!$('attest').checked)throw Error('Confirme la lecture complète de cet article avant de l’attester.');
  const r=state.articles[index];const value=await api('/api/save',{id:r.id,text_sha256:r.text_sha256,entities:checkedSpans(),reviewer:$('reviewer').value,review_note:$('note').value,attest});
  state={...state,...value};show();status(attest?'Revue humaine enregistrée sur le volume chiffré.':'Brouillon enregistré ; cet article reste à attester.');
}
$('note').oninput=changed;$('reviewer').oninput=changed;
$('choose').onchange=()=>{if(dirty){$('choose').value=index;status('Enregistre le brouillon ou atteste cet article avant de changer.');return;}index=Number($('choose').value);show();};
$('next').onclick=()=>{if(dirty){status('Enregistre tes modifications avant de passer au suivant.');return;}index=(index+1)%state.total;show();};
document.addEventListener('selectionchange',()=>{const selected=getSelection();if(!selected.rangeCount)return;const range=selected.getRangeAt(0);if(!$('source').contains(range.commonAncestorContainer))return;const before=range.cloneRange();before.selectNodeContents($('source'));before.setEnd(range.startContainer,range.startOffset);selection={start:Array.from(before.toString()).length,end:Array.from(before.toString()+range.toString()).length};});
$('add').onclick=()=>{if(!selection||selection.end<=selection.start){status('Sélectionne un nom dans le texte.');return;}addSpan({...selection,label:$('label').value});$('empty').hidden=true;changed();};
for(const [id,attest] of [['draft',false],['validate',true]])$(''+id).onclick=async()=>{try{await save(attest);}catch(e){status(e.message);}};
$('evaluate').onclick=async()=>{if(dirty){status('Enregistre la dernière revue avant l’évaluation.');return;}$('evaluate').disabled=true;try{const result=await api('/api/evaluate',{});const number=v=>v===null?'non défini':(100*v).toFixed(2)+' %';$('result').textContent=`${result.documents} articles évalués\nPrécision : ${number(result.global.precision)}\nRappel : ${number(result.global.recall)}\nF1 : ${number(result.global.f1)}\n\nRésultat et erreurs enregistrés sur le volume chiffré. Échantillon assisté de 42 articles, sans validation de qualité globale en production.`;}catch(e){status(e.message);}finally{$('evaluate').disabled=false;}};
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
api('/api/state').then(value=>{state=value;state.articles.forEach((r,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${i+1}. Article ${r.id}`;$('choose').appendChild(o);});show();}).catch(e=>status(e.message));
