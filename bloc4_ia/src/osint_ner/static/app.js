const $=id=>document.getElementById(id);let initialized=false;
function row(target,cells){const tr=document.createElement('tr');for(const cell of cells){const td=document.createElement('td');td.textContent=String(cell);tr.append(td)}$(target).append(tr)}
async function refresh(){try{$('status').textContent='Chargement des résultats…';const p=new URLSearchParams({q:$('query').value,year:$('year').value,label:$('label').value});const response=await fetch('/api/summary?'+p);if(!response.ok)throw Error('Résultats indisponibles.');const d=await response.json();if(!initialized){for(const y of d.years){const o=document.createElement('option');o.textContent=y;o.value=y;$('year').append(o)}initialized=true}$('documents').textContent=d.documents.toLocaleString('fr');$('mentions').textContent=d.mentions.toLocaleString('fr');$('with').textContent=d.articles_with_entities.toLocaleString('fr');$('top').replaceChildren();for(const r of d.top)row('top',r);if(!d.top.length)row('top',['Aucune mention',0]);$('timeline').replaceChildren();for(const r of Object.entries(d.by_year))row('timeline',r);$('articles').replaceChildren();for(const a of d.articles){const b=document.createElement('button');b.textContent=a.title||`Article ${a.id}`;b.onclick=()=>detail(a.id);$('articles').append(b)}$('model').textContent=`Version ${d.model.model_version}. Empreinte ${d.model.model_sha256}.`;$('status').textContent=`${d.documents} articles sélectionnés sur ${d.total_documents}. Tous les tableaux utilisent les filtres ci-dessus.`;$('detail').hidden=true}catch(e){$('status').textContent=e.message}}
async function detail(id){try{const response=await fetch('/api/article?id='+encodeURIComponent(id));if(!response.ok)throw Error('Article indisponible.');const a=await response.json();$('article-title').textContent=a.title;$('source-url').href=a.url;$('article-meta').textContent=`Article ${a.id}. Texte complet. Positions en caractères Unicode. Version ${a.model_version}.`;$('article-text').replaceChildren();$('spans').replaceChildren();const chars=Array.from(a.text);let offset=0;for(const e of a.entities){$('article-text').append(document.createTextNode(chars.slice(offset,e.start).join('')));const mark=document.createElement('mark');mark.textContent=chars.slice(e.start,e.end).join('');mark.title=e.label;const label=document.createElement('span');label.className='entity-label';label.textContent=` [${e.label}]`;mark.append(label);$('article-text').append(mark);offset=e.end;row('spans',[e.text,e.label,e.start,e.end])}$('article-text').append(document.createTextNode(chars.slice(offset).join('')));$('detail').hidden=false;$('article-title').scrollIntoView({block:'start'});$('article-text').focus()}catch(e){$('status').textContent=e.message}}
$('filters').onsubmit=e=>{e.preventDefault();refresh()};refresh();

$('prediction-form').onsubmit=async event=>{
 event.preventDefault();const button=$('prediction-submit');button.disabled=true;
 $('prediction-result').hidden=true;$('prediction-status').textContent='Calcul des mentions en cours…';
 try{
  const response=await fetch('/api/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:$('prediction-text').value})});
  const result=await response.json();if(!response.ok)throw Error(result.error||'Prédiction indisponible.');
  $('prediction-source').replaceChildren();$('prediction-spans').replaceChildren();
  const chars=Array.from(result.text);let offset=0;
  for(const entity of result.entities){
   $('prediction-source').append(document.createTextNode(chars.slice(offset,entity.start).join('')));
   const mark=document.createElement('mark');mark.textContent=chars.slice(entity.start,entity.end).join('');mark.title=entity.label;
   $('prediction-source').append(mark);offset=entity.end;row('prediction-spans',[entity.text,entity.label,entity.start,entity.end]);
  }
  $('prediction-source').append(document.createTextNode(chars.slice(offset).join('')));
  if(!result.entities.length)row('prediction-spans',['Aucune mention détectée','','','']);
  $('prediction-meta').textContent=`Modèle ${result.model_version}. Empreinte ${result.model_sha256}. Calcul : ${result.duration_seconds} s. Texte non enregistré.`;
  $('prediction-result').hidden=false;$('prediction-status').textContent=`${result.entities.length} mentions prédites. Vérifiez les catégories et les passages.`;
 }catch(error){$('prediction-status').textContent=error.message}
 finally{button.disabled=false}
};
