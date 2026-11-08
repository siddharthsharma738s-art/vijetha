'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let CSRF=$('meta[name=csrf]').content,ME,SC,PERMS={};
async function api(method,url,body){
  const o={method,headers:{'X-CSRF':CSRF},credentials:'same-origin'};
  if(body instanceof FormData)o.body=body;else if(body!==undefined){o.headers['Content-Type']='application/json';o.body=JSON.stringify(body)}
  const r=await fetch(url,o);let j={};try{j=await r.json()}catch(e){}
  if(!r.ok){const e=new Error(j.error||'Request failed');e.status=r.status;e.data=j;if(r.status===401&&$('body').dataset.mode==='app')location.reload();throw e}
  return j}
function toast(m,bad){const t=$('#toast');t.textContent=m;t.className='show'+(bad?' bad':'');clearTimeout(toast.h);toast.h=setTimeout(()=>t.className='',3200)}
const fail=e=>toast(e.message,1);
function confirmBox(msg,okText='Yes, continue'){return new Promise(res=>{const d=$('#cfm');d.innerHTML=`<h3>Please confirm</h3><p>${esc(msg)}</p><div class="acts"><button class="btn o" id="cn">Cancel</button><button class="btn red" id="cy">${esc(okText)}</button></div>`;d.showModal();$('#cn',d).onclick=()=>{d.close();res(false)};$('#cy',d).onclick=()=>{d.close();res(true)};d.oncancel=()=>res(false)})}
function modal(title,html,wide,id='dlg'){const d=$('#'+id);d.className=wide?'wide':'';d.innerHTML=`<h3>${esc(title)}</h3><div class="mb">${html}</div>`;d.showModal();return d}
const fdt=v=>v?String(v).replace('T',' ').slice(0,16):'';const fsz=n=>n>1048576?(n/1048576).toFixed(1)+' MB':Math.max(1,Math.round(n/1024))+' KB';
const isImg=u=>/\.(jpe?g|png|webp|gif|svg)$/i.test(u||'');
const can=(mod,a)=>(PERMS[mod]||'').includes(a);
const changed=()=>{if(window.refreshPv)window.refreshPv()};

/* ---------------- login page ---------------- */
if($('body').dataset.mode==='login'){
  const lf=$('#lf'),ff=$('#ff');
  $('#fg').onclick=e=>{e.preventDefault();lf.hidden=true;ff.hidden=false};$('#bk').onclick=e=>{e.preventDefault();lf.hidden=false;ff.hidden=true};
  lf.onsubmit=async e=>{e.preventDefault();try{await api('POST','/api/login',Object.fromEntries(new FormData(lf)));location.reload()}catch(x){$('#le').textContent=x.message}};
  ff.onsubmit=async e=>{e.preventDefault();try{const r=await api('POST','/api/forgot',Object.fromEntries(new FormData(ff)));$('#fm').textContent=r.msg}catch(x){$('#fm').textContent=x.message}};
} else boot();

async function boot(){
  try{const m=await api('GET','/api/me');ME=m.user;CSRF=m.csrf;PERMS=m.perms;SC=await api('GET','/api/schema')}catch(e){return}
  $('#who').textContent=`${ME.name} · ${m_role()}`;$('#out').onclick=async()=>{await api('POST','/api/logout');location.reload()};$('#mb').onclick=()=>$('#nav').classList.toggle('open');
  if(ME.must_change)$('#warn').innerHTML='<div class="w">⚠ You are using a default or reset password. <a href="#/profile" style="text-decoration:underline">Change it now</a>.</div>';
  buildNav();addEventListener('hashchange',route);route();
}
const m_role=()=>SC.role_labels[ME.role]||ME.role;

const SPECIAL=[['Overview',[['dash','Dashboard',1]]],['Homepage',[['home','Homepage builder','sections']]],['Media',[['media','Media library','media']]]];
function buildNav(){
  const groups={};Object.values(SC.res).forEach(r=>{if(r.name==='sections')return;(groups[r.group]=groups[r.group]||[]).push(r)});
  let h='<div class="brand">Vijetha Admin</div><h4>Overview</h4><a href="#/dash" data-r="dash">Dashboard</a>';
  const order=['Content','Homepage','Courses','Live','Exams','Users','Payments','Media'];
  order.forEach(g=>{let items='';
    if(g==='Homepage'&&can('sections','v'))items+='<a href="#/home" data-r="home">Homepage builder</a>';
    if(g==='Media'&&can('media','v'))items+='<a href="#/media" data-r="media">Media library</a>';
    (groups[g]||[]).forEach(r=>{if(r.hidden||g==='Media'||!can(r.mod,'v'))return;items+=`<a href="#/res/${r.name}" data-r="res/${r.name}">${esc(r.label)}</a>`});
    if(items)h+=`<h4>${g}</h4>`+items});
  h+='<h4>Site</h4>';if(can('settings','v'))h+='<a href="#/settings" data-r="settings">Website settings</a>';if(can('roles','v'))h+='<a href="#/roles" data-r="roles">Roles & permissions</a>';
  if(can('activity','v'))h+='<a href="#/activity" data-r="activity">Activity & logins</a>';h+='<a href="#/profile" data-r="profile">My profile</a>';
  $('#nav').innerHTML=h}
function route(){
  const [p,qs]=(location.hash.slice(2)||'dash').split('?');const parts=p.split('/');$('#nav').classList.remove('open');
  $$('#nav a').forEach(a=>a.classList.toggle('on',a.dataset.r===(parts[0]==='res'?'res/'+parts[1]:parts[0])));
  const m=$('#main');m.innerHTML='<p class="mu">Loading…</p>';window.refreshPv=null;
  const f={dash,home,media:mediaView,settings,roles,activity,profile}[parts[0]];
  (parts[0]==='res'&&SC.res[parts[1]]?listView(parts[1],qs||'',m):f?f(m):Promise.resolve(m.textContent='Not found')).catch(e=>{m.innerHTML=`<p class="err">${esc(e.message)}</p>`})}

/* ---------------- dashboard ---------------- */
async function dash(m){
  const d=await api('GET','/api/dashboard'),st=d.storage,pc=Math.min(100,st.used/st.quota*100),R=d.revenue;
  const tb=(h,rows)=>`<div class="tw"><table><tr>${h.map(x=>`<th>${x}</th>`).join('')}</tr>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')||`<tr><td colspan="${h.length}" class="mu">Nothing yet</td></tr>`}</table></div>`;
  const mx=R?Math.max(1,...R.by_month.map(x=>x.amount)):1;
  m.innerHTML=`<h2>Dashboard</h2><div class="cards">${[['Students',d.students],['Courses',d.courses],['Posts',d.posts],['Uploaded files',st.files]].map(x=>`<div class="card stat"><b>${x[1]}</b>${x[0]}</div>`).join('')}
  ${R?`<div class="card stat"><b>${R.total.toLocaleString('en-IN')}</b>Revenue (${R.paid} paid, ${R.pending} pending)</div>`:''}</div>
  <div class="two"><div class="card"><h3>Storage</h3><div class="prog"><i style="width:${pc}%"></i></div><p class="mu">${fsz(st.used)} of ${fsz(st.quota)} used</p>
  ${R?`<h3>Revenue by month</h3><div class="bars">${R.by_month.map(x=>`<div style="height:${x.amount/mx*100}%" title="${x.amount}"><span>${esc(x.m.slice(2))}</span></div>`).join('')||'<span class="mu">No paid orders yet</span>'}</div>`:''}</div>
  <div><h3 style="margin-top:0">Upcoming live classes</h3>${tb(['Class','When','Status'],d.upcoming.map(x=>[esc(x.title),fdt(x.start),esc(x.status)]))}</div></div>
  <div class="two"><div><h3>Recent registrations</h3>${tb(['Name','Username','Joined'],d.recent.map(x=>[esc(x.name),esc(x.username),fdt(x.when)]))}</div>
  <div><h3>Recent activity</h3>${tb(['When','Who','Action'],d.activity.map(x=>[fdt(x.ts),esc(x.who),esc(x.action)]))}</div></div>
  <div class="two"><div><h3>Course statistics</h3>${tb(['Course','Enrolled'],d.course_stats.map(x=>[esc(x.title),x.enrolled]))}</div>
  <div><h3>Exam statistics</h3>${tb(['Exam','Attempts','Avg %'],d.exam_stats.map(x=>[esc(x.title),x.attempts,x.avg]))}</div></div>`}

/* ---------------- generic list / form engine ---------------- */
const ACTS={history:'History',lessons:'Lessons',enrollments:'Enrollments',questions:'Questions',results:'Results',attendance:'Attendance',endclass:'End class',cancelclass:'Cancel class',
  approve:'Approve',spam:'Spam',paid:'Mark paid',refund:'Refund',handled:'Mark handled',publish_results:'Publish results',reset:'Reset password',detail:'Details',logins:'Login history'};
function cell(R,k,it){
  const f=R.fields.find(x=>x.k===k);if(k==='_c')return fdt(it._c);if(!f)return esc(it[k]);const v=it[k];
  if(f.t==='ref')return esc(it['_'+k]||'');if(f.t==='chk')return v?'✓':'';if(f.t==='dt')return fdt(v);
  if(f.t==='media')return isImg(v)?`<img src="${esc(v)}" alt="">`:esc(v?'file':'');if(f.t==='tags')return esc((v||[]).join(', '));
  if(f.t==='html'||f.t==='area')return esc(String(v||'').replace(/<[^>]+>/g,' ').slice(0,70));
  if(k==='status'||f.t==='sel'){const g=['published','active','approved','paid','live'].includes(v),r=['spam','failed','refunded','cancelled','revoked','inactive','disabled'].includes(v);return `<span class="tag ${g?'g':r?'r':''}">${esc(v)}</span>`}
  if(k==='price'||k==='amount')return esc(v);return esc(v)}
async function listView(name,qs,m,embed){
  const R=SC.res[name],P=PERMS[R.mod]||'',params=new URLSearchParams(qs),filt={};params.forEach((v,k)=>{if(k!=='q')filt[k]=v});
  const data=await api('GET',`/api/${name}?`+params),items=data.items;
  const fl=Object.keys(filt).length?` <span class="tag">filtered</span> <a href="#/res/${name}" class="mu">clear</a>`:'';
  m.innerHTML=(embed?'':`<h2>${esc(R.label)}${fl}</h2>`)+`<div class="bar"><input type="search" placeholder="Search…" value="${esc(params.get('q')||'')}" id="q_${name}" aria-label="Search">
    ${P.includes('c')&&!R.nocreate?`<button class="btn" id="nw">+ New</button>`:''}${R.export||['attempts','orders','enrollments','students'].includes(name)?`<a class="btn o" href="/api/export/${name}?${params}">Export CSV</a>`:''}${R.drag?'<span class="mu">Drag ⋮⋮ rows to reorder</span>':''}</div>
    <div class="tw"><table><thead><tr>${R.drag?'<th></th>':''}${R.cols.map(c=>`<th>${esc(c==='_c'?'Created':(R.fields.find(f=>f.k===c)||{}).l||c)}</th>`).join('')}<th></th></tr></thead><tbody>${
    items.map(it=>`<tr data-id="${it.id}" ${R.drag&&!params.get('q')?'draggable="true"':''}>${R.drag?'<td class="hd">⋮⋮</td>':''}${R.cols.map(c=>`<td>${cell(R,c,it)}</td>`).join('')}<td class="ac">${rowBtns(R,P,it)}</td></tr>`).join('')||`<tr><td colspan="${R.cols.length+2}" class="mu">Nothing here yet.</td></tr>`}</tbody></table></div>`;
  const reload=()=>{changed();listView(name,qs,m,embed).catch(fail)};
  let t;$(`#q_${name}`,m).oninput=e=>{clearTimeout(t);t=setTimeout(()=>{if(embed)return;const p=new URLSearchParams(qs);e.target.value?p.set('q',e.target.value):p.delete('q');history.replaceState(0,'','#/res/'+name+'?'+p);listView(name,p.toString(),m).then(()=>{const i=$(`#q_${name}`);i.focus();i.setSelectionRange(99,99)})},350)};
  const nw=$('#nw',m);if(nw)nw.onclick=()=>openForm(name,null,filt,reload);
  if(R.drag&&!params.get('q')){let dr;$$('tr[draggable]',m).forEach(tr=>{tr.ondragstart=e=>{dr=tr;tr.classList.add('drag');e.dataTransfer.effectAllowed='move'};tr.ondragend=()=>{tr.classList.remove('drag');if(P.includes('e'))api('POST',`/api/${name}/reorder`,{ids:$$('tr[data-id]',m).map(x=>x.dataset.id)}).then(()=>{toast('Order saved');changed()}).catch(e=>{fail(e);reload()})};
    tr.ondragover=e=>{e.preventDefault();if(!dr||dr===tr)return;const b=tr.getBoundingClientRect();tr.parentNode.insertBefore(dr,e.clientY>b.top+b.height/2?tr.nextSibling:tr)}})}
  m.onclick=async e=>{const b=e.target.closest('button[data-a]');if(!b)return;const it=items.find(x=>x.id===b.closest('tr').dataset.id),a=b.dataset.a;
    try{
      if(a==='edit')return openForm(name,it,filt,reload);
      if(a==='del'){if(await confirmBox(`Delete "${it.title||it.name||it.code||'this item'}"? This cannot be undone.`,'Delete')){await api('DELETE',`/api/${name}/${it.id}`);toast('Deleted');reload()}return}
      if(a==='pv')return window.open(R.preview.replace('{slug}',it.slug)+'?preview=1','_blank');
      if(['publish','unpublish','pin','unpin','feature','unfeature'].includes(a)){await api('POST',`/api/${name}/${it.id}/${a}`);toast('Done');return reload()}
      await actionFor(a,name,it,reload)
    }catch(x){fail(x)}}}
function rowBtns(R,P,it){
  const b=(a,l,c='o')=>`<button class="btn sm ${c}" data-a="${a}">${l}</button> `;let h='';
  if(P.includes('e')&&!R.noedit)h+=b('edit','Edit','');if(R.preview)h+=b('pv','Preview');
  if(R.pub&&P.includes('p')){const live=['published','live'].includes(it.status);h+=b(live?'unpublish':'publish',live?'Unpublish':'Publish')}
  if(R.pin&&P.includes('e'))h+=b(it.pin?'unpin':'pin',it.pin?'Unpin':'Pin');if(R.feat&&P.includes('e')&&!R.fields.some(f=>f.k==='feat'))h+=b(it.feat?'unfeature':'feature',it.feat?'Unfeature':'Feature');
  (R.acts||[]).forEach(a=>{const need=['approve','spam','paid','refund','handled','reset','endclass','cancelclass','attendance','publish_results'].includes(a)?'e':'v';if(!P.includes(need))return;
    if(a==='paid'&&it.status!=='pending')return;if(a==='refund'&&it.status!=='paid')return;if(a==='handled'&&it.handled)return;
    if(a==='publish_results'){h+=b(it.results_published?'hide_results':'publish_results',it.results_published?'Hide results':'Publish results');return}
    h+=b(a,ACTS[a])});
  if(P.includes('d'))h+=b('del','Delete','red o');return h}
async function actionFor(a,name,it,reload){
  const post=async(act,body)=>{const r=await api('POST',`/api/${name}/${it.id}/${act}`,body);toast(r.msg||'Done');reload()};
  const q=(k,v)=>location.hash=`#/res/${k}?${v}=${it.id}`;
  switch(a){
    case'lessons':return q('lessons','course');case'enrollments':return q('enrollments',name==='students'?'student':'course');case'questions':return q('questions','exam');case'results':return q('attempts','exam');
    case'approve':case'spam':case'handled':case'publish_results':case'hide_results':return post(a);
    case'endclass':case'cancelclass':if(await confirmBox(`${ACTS[a]} "${it.title}"?`))return post(a);return;
    case'refund':if(await confirmBox('Record a refund for this order? Course access will be revoked.','Refund'))return post('refund');return;
    case'paid':{const d=modal('Mark as paid',`<label>Transaction reference<input id="tx" value="${esc(it.txn||'')}"></label><div class="acts"><button class="btn o" id="c">Cancel</button><button class="btn" id="s">Confirm payment</button></div>`);$('#c',d).onclick=()=>d.close();$('#s',d).onclick=async()=>{try{await post('paid',{txn:$('#tx',d).value});d.close()}catch(x){fail(x)}};return}
    case'reset':{const d=modal('Reset password',`<p class="mu">Set a new password for ${esc(it.name)}. Share it securely; the user can change it afterwards.</p><label>New password<input type="password" id="pw" autocomplete="new-password"></label><div class="acts"><button class="btn o" id="c">Cancel</button><button class="btn" id="s">Set password</button></div>`);$('#c',d).onclick=()=>d.close();$('#s',d).onclick=async()=>{try{await post('reset',{password:$('#pw',d).value});d.close()}catch(x){fail(x)}};return}
    case'history':{const v=(await api('GET',`/api/${name}/${it.id}/versions`)).items,d=modal('Version history',`<div class="tw"><table><tr><th>Saved</th><th>By</th><th></th></tr>${v.map(x=>`<tr><td>${fdt(x.ts)}</td><td>${esc(x.author)}</td><td><button class="btn sm" data-v="${x.id}">Restore</button></td></tr>`).join('')||'<tr><td colspan="3" class="mu">No earlier versions yet.</td></tr>'}</table></div><div class="acts"><button class="btn o" id="c">Close</button></div>`);
      $('#c',d).onclick=()=>d.close();d.onclick=async e=>{const b=e.target.closest('[data-v]');if(b&&await confirmBox('Restore this version? The current content is saved in history first.','Restore')){try{await api('POST',`/api/${name}/${it.id}/restore/${b.dataset.v}`);d.close();toast('Version restored');reload()}catch(x){fail(x)}}};return}
    case'attendance':{const L=(await api('GET',`/api/live/${it.id}/attendance`)).items,d=modal('Attendance – '+it.title,`${L.map(s=>`<label class="ck"><input type="checkbox" value="${s.id}" ${s.present?'checked':''}> ${esc(s.name)}</label>`).join('')||'<p class="mu">No enrolled students.</p>'}<div class="acts"><button class="btn o" id="c">Cancel</button><button class="btn" id="s">Save attendance</button></div>`);
      $('#c',d).onclick=()=>d.close();$('#s',d).onclick=async()=>{try{await api('POST',`/api/live/${it.id}/attendance`,{present:$$('input:checked',d).map(x=>x.value)});d.close();toast('Attendance saved')}catch(x){fail(x)}};return}
    case'detail':{const r=await api('GET',`/api/students/${it.id}/detail`),t=(h,rows)=>`<div class="tw"><table><tr>${h.map(x=>`<th>${x}</th>`).join('')}</tr>${rows.map(r=>`<tr>${r.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('')||`<tr><td colspan="${h.length}" class="mu">None</td></tr>`}</table></div>`;
      modal(r.student.name,`<h3>Enrolled courses</h3>${t(['Course','Access','Until'],r.enrollments.map(e=>[e._course,e.status,fdt(e.expires_at)]))}<h3>Orders</h3>${t(['Item','Amount','Status'],r.orders.map(o=>[o.title,o.amount,o.status]))}<h3>Exam attempts</h3>${t(['Exam','Score'],r.attempts.map(a=>[a._exam,a.score+'/'+a.total]))}<h3>Recent activity</h3>${t(['When','Action'],r.activity.map(a=>[fdt(a.ts),a.action]))}<h3>Logins</h3>${t(['When','IP','OK'],r.logins.map(a=>[fdt(a.ts),a.ip,a.ok?'yes':'failed']))}<div class="acts"><button class="btn o" onclick="this.closest('dialog').close()">Close</button></div>`,1);return}
    case'logins':{const r=await api('GET',`/api/admins/${it.id}/logins`);modal('Login history – '+it.username,`<div class="tw"><table><tr><th>When</th><th>IP</th><th>Result</th></tr>${r.logins.map(a=>`<tr><td>${fdt(a.ts)}</td><td>${esc(a.ip)}</td><td>${a.ok?'OK':'Failed'}</td></tr>`).join('')}</table></div><div class="acts"><button class="btn o" onclick="this.closest('dialog').close()">Close</button></div>`);return}
  }}

/* ---------------- form builder ---------------- */
const refCache={};
async function refOpts(res){const r=await api('GET',`/api/${res}`);return r.items.map(x=>[x.id,x.title||x.name||x.code])}
function widget(f,v,isNew){
  const k=f.k,id='f_'+k,req=f.req?' required':'',h=f.help?` <span class="help">${esc(f.help)}</span>`:'';
  const L=`<label for="${id}">${esc(f.l)}${f.req?' *':''}${h}</label>`;
  switch(f.t){
    case'chk':return `<label class="ck"><input type="checkbox" id="${id}" data-k="${k}" ${v?'checked':''}> ${esc(f.l)}</label>`;
    case'area':return L+`<textarea id="${id}" data-k="${k}" rows="4"${req}>${esc(v)}</textarea>`;
    case'sel':return L+`<select id="${id}" data-k="${k}">${f.opts.map(o=>`<option ${o===v?'selected':''}>${esc(o)}</option>`).join('')}</select>`;
    case'ref':return L+`<select id="${id}" data-k="${k}" data-ref="${f.ref}" data-v="${esc(v||'')}"><option value="">—</option></select>`;
    case'num':return L+`<input type="number" step="any" id="${id}" data-k="${k}" value="${esc(v)}"${req}>`;
    case'dt':return L+`<input type="datetime-local" id="${id}" data-k="${k}" value="${esc(v)}">`;
    case'color':return L+`<input type="color" id="${id}" data-k="${k}" value="${esc(v||'#6C35C9')}">`;
    case'tags':return L+`<input id="${id}" data-k="${k}" value="${esc((v||[]).join(', '))}" placeholder="comma, separated">`;
    case'pass':return f.create_only&&!isNew?'':L+`<input type="password" id="${id}" data-k="${k}" autocomplete="new-password"${req}>`;
    case'html':return L+`<div class="ed" data-k="${k}"><div class="tb">${[['bold','B'],['italic','I'],['formatBlock:h2','H2'],['formatBlock:h3','H3'],['insertUnorderedList','• List'],['insertOrderedList','1. List'],['link','Link'],['image','Image'],['removeFormat','Clear']].map(b=>`<button type="button" data-c="${b[0]}">${b[1]}</button>`).join('')}</div><div class="ced" contenteditable="true" role="textbox" aria-label="${esc(f.l)}">${v||''}</div></div>`;
    case'media':return L+`<div class="mw" data-k="${k}" data-v="${esc(v||'')}"><div class="thumbs"></div><button type="button" class="btn sm o" data-m="pick">Choose / upload</button> <button type="button" class="btn sm red o" data-m="clr">Remove</button></div>`;
    case'medias':return L+`<div class="mw" data-k="${k}" data-multi="1" data-v='${esc(JSON.stringify(v||[]))}'><div class="thumbs"></div><button type="button" class="btn sm o" data-m="add">Add images</button></div>`;
    default:return L+`<input id="${id}" data-k="${k}" type="${f.t==='email'?'email':f.t==='url'?'url':'text'}" value="${esc(v)}"${req}>`}}
function drawMedia(w){const multi=w.dataset.multi,v=multi?JSON.parse(w.dataset.v||'[]'):(w.dataset.v?[w.dataset.v]:[]);
  $('.thumbs',w).innerHTML=v.map((u,i)=>`<div class="t">${isImg(u)?`<img src="${esc(u)}" alt="">`:`<span class="tag">${esc(u.split('/').pop())}</span>`}${multi?`<button type="button" class="x" data-x="${i}" aria-label="Remove">×</button>`:''}</div>`).join('')}
function wire(d,fields,item){
  $$('select[data-ref]',d).forEach(async s=>{try{(refCache[s.dataset.ref]=refCache[s.dataset.ref]||await refOpts(s.dataset.ref));s.innerHTML='<option value="">—</option>'+refCache[s.dataset.ref].map(o=>`<option value="${o[0]}" ${o[0]===s.dataset.v?'selected':''}>${esc(o[1])}</option>`).join('')}catch(e){}});
  $$('.mw',d).forEach(w=>{drawMedia(w);w.onclick=async e=>{const b=e.target.closest('button');if(!b)return;const multi=w.dataset.multi;
    if(b.dataset.x!==undefined){const v=JSON.parse(w.dataset.v);v.splice(+b.dataset.x,1);w.dataset.v=JSON.stringify(v)}
    else if(b.dataset.m==='clr')w.dataset.v='';
    else{const u=await pickMedia(!!multi);if(!u||!u.length)return;w.dataset.v=multi?JSON.stringify([...JSON.parse(w.dataset.v),...u]):u[0]}
    drawMedia(w)}});
  $$('.ed',d).forEach(ed=>{const ce=$('.ced',ed);ed.onclick=async e=>{const b=e.target.closest('[data-c]');if(!b)return;ce.focus();const c=b.dataset.c;
    if(c==='link'){const u=prompt('Link URL (https://…)');if(u)document.execCommand('createLink',false,u)}
    else if(c==='image'){const u=await pickMedia(false,true);if(u&&u[0])document.execCommand('insertImage',false,u[0])}
    else if(c.startsWith('formatBlock'))document.execCommand('formatBlock',false,c.split(':')[1]);else document.execCommand(c)}})}
function collect(d,fields){const o={};fields.forEach(f=>{const k=f.k;
  if(f.t==='html')o[k]=$(`.ed[data-k=${k}] .ced`,d).innerHTML;else if(f.t==='media')o[k]=$(`.mw[data-k=${k}]`,d).dataset.v;else if(f.t==='medias')o[k]=JSON.parse($(`.mw[data-k=${k}]`,d).dataset.v);
  else{const e=$(`[data-k=${k}]`,d);if(!e)return;o[k]=f.t==='chk'?e.checked:e.value}});return o}
async function openForm(name,item,pref,done){
  const R=SC.res[name],isNew=!item,v=item||{...Object.fromEntries(R.fields.map(f=>[f.k,f.default??(f.t==='chk'?false:f.t==='tags'||f.t==='medias'?[]:'')])),...pref};
  const d=modal((isNew?'New ':'Edit ')+R.label.replace(/s$/,''),`<form id="rf">${R.fields.map(f=>widget(f,v[f.k],isNew)).join('')}<div class="acts"><button type="button" class="btn o" id="cx">Cancel</button>${R.preview&&!isNew?'<button type="button" class="btn o" id="sp">Save & preview</button>':''}<button class="btn">Save</button></div></form>`,1);
  wire(d,R.fields,item);$('#cx',d).onclick=()=>d.close();
  const save=async()=>{const body=collect(d,R.fields);const r=isNew?await api('POST',`/api/${name}`,body):await api('PUT',`/api/${name}/${item.id}`,body);toast('Saved');return r};
  $('#rf',d).onsubmit=async e=>{e.preventDefault();try{await save();d.close();done()}catch(x){fail(x)}};
  const sp=$('#sp',d);if(sp)sp.onclick=async()=>{const w=window.open('about:blank','_blank');try{await save();w.location=R.preview.replace('{slug}',collect(d,R.fields).slug||item.slug)+'?preview=1';done()}catch(x){w.close();fail(x)}}}

/* ---------------- media ---------------- */
async function pickMedia(multi,imgOnly){return new Promise(async res=>{
  const d=modal('Select media','<div id="pk"></div>',1,'dlg2');let sel=[];
  const draw=async(q='',fo='*')=>{const r=await api('GET',`/api/media?q=${encodeURIComponent(q)}&folder=${encodeURIComponent(fo)}`);let L=r.items;if(imgOnly)L=L.filter(x=>isImg(x.url));
    $('#pk',d).innerHTML=`<div class="bar"><input id="pq" placeholder="Search files…" value="${esc(q)}"><select id="pf"><option value="*">All folders</option><option value="">Root</option>${r.folders.map(f=>`<option ${f===fo?'selected':''}>${esc(f)}</option>`).join('')}</select><label class="btn sm" style="margin:0">Upload<input type="file" id="pu" multiple hidden></label></div>
    <div class="mg">${L.map(x=>`<div class="mi ${sel.includes(x.url)?'sel':''}" data-u="${esc(x.url)}"><div class="pv">${isImg(x.url)?`<img src="${esc(x.url)}" alt="">`:esc(x.ext.toUpperCase())}</div><div class="nm">${esc(x.name)}</div></div>`).join('')||'<p class="mu">No files. Upload one.</p>'}</div>
    <div class="acts"><button class="btn o" id="pc">Cancel</button><button class="btn" id="po">Use selected</button></div>`;
    $('#pq',d).onchange=e=>draw(e.target.value,$('#pf',d).value);$('#pf',d).onchange=e=>draw($('#pq',d).value,e.target.value);
    $('#pu',d).onchange=async e=>{try{await upload(e.target.files,fo==='*'?'':fo);draw()}catch(x){fail(x)}};
    $$('.mi',d).forEach(c=>c.onclick=()=>{const u=c.dataset.u;if(multi)sel=sel.includes(u)?sel.filter(x=>x!==u):[...sel,u];else sel=[u];$$('.mi',d).forEach(z=>z.classList.toggle('sel',sel.includes(z.dataset.u)))});
    $('#pc',d).onclick=()=>{d.close();res(null)};$('#po',d).onclick=()=>{d.close();res(sel)}};
  d.oncancel=()=>res(null);try{await draw()}catch(x){fail(x);d.close();res(null)}})}
async function upload(files,folder){const fd=new FormData();[...files].forEach(f=>fd.append('files',f));fd.append('folder',folder||'');
  const r=await api('POST','/api/media/upload',fd);if(r.errors.length)toast(r.errors.join(' • '),1);else toast(`${r.ok.length} file(s) uploaded`);return r}
async function mediaView(m){
  let q='',fo='*';
  const draw=async()=>{const r=await api('GET',`/api/media?q=${encodeURIComponent(q)}&folder=${encodeURIComponent(fo)}`),st=r.storage,P=PERMS.media||'';
    m.innerHTML=`<h2>Media library</h2><div class="card" style="margin-bottom:1rem"><div class="prog"><i style="width:${Math.min(100,st.used/st.quota*100)}%"></i></div><span class="mu">${fsz(st.used)} of ${fsz(st.quota)} · ${st.files} files</span></div>
    <div class="bar"><input id="mq" placeholder="Search files…" value="${esc(q)}"><select id="mf"><option value="*">All folders</option><option value="" ${fo===''?'selected':''}>Root</option>${r.folders.map(f=>`<option ${f===fo?'selected':''}>${esc(f)}</option>`).join('')}</select>
    ${P.includes('c')?'<button class="btn o" id="nf">+ Folder</button>':''}${P.includes('d')&&fo&&fo!=='*'?'<button class="btn red o" id="df">Delete folder</button>':''}</div>
    ${P.includes('c')?'<div class="drop" id="dz">Drop files here or <label style="display:inline;color:var(--p);cursor:pointer;text-decoration:underline">browse<input type="file" id="mu" multiple hidden></label><br><span class="help">JPG, PNG, WEBP, GIF, SVG, MP4, PDF, ZIP, PPT/PPTX, DOC/DOCX – validated on the server</span></div>':''}
    <div class="mg">${r.items.map(x=>`<div class="mi" data-id="${x.id}"><div class="pv" data-a="view">${isImg(x.url)?`<img src="${esc(x.url)}" alt="">`:x.ext==='mp4'?`<video src="${esc(x.url)}" preload="metadata" muted></video>`:esc(x.ext.toUpperCase())}</div><div class="nm">${esc(x.name)}</div><div class="mt">${fsz(x.size)}${x.folder?' · '+esc(x.folder):''}</div>
      <div class="ab">${P.includes('e')?'<button class="btn sm o" data-a="ren">Rename</button><button class="btn sm o" data-a="rep">Replace</button>':''}<button class="btn sm o" data-a="cp">Copy URL</button>${P.includes('d')?'<button class="btn sm red o" data-a="del">Delete</button>':''}</div></div>`).join('')||'<p class="mu">No files yet.</p>'}</div>`;
    $('#mq').onchange=e=>{q=e.target.value;draw()};$('#mf').onchange=e=>{fo=e.target.value;draw()};
    const up=async fs=>{try{await upload(fs,fo==='*'?'':fo);draw()}catch(x){fail(x)}};const mu=$('#mu');if(mu)mu.onchange=e=>up(e.target.files);
    const dz=$('#dz');if(dz){dz.ondragover=e=>{e.preventDefault();dz.classList.add('over')};dz.ondragleave=()=>dz.classList.remove('over');dz.ondrop=e=>{e.preventDefault();dz.classList.remove('over');up(e.dataTransfer.files)}}
    const nf=$('#nf');if(nf)nf.onclick=()=>{const n=prompt('Folder name');if(n)api('POST','/api/folders',{name:n}).then(draw).catch(fail)};
    const df=$('#df');if(df)df.onclick=async()=>{if(!await confirmBox(`Delete folder "${fo}"? Files inside move to the root.`,'Delete folder'))return;try{const fl=(await api('GET','/api/folders')).items.find(x=>x.name===fo);for(const x of r.items.filter(i=>i.folder===fo))await api('PUT','/api/media/'+x.id,{folder:''});if(fl)await api('DELETE','/api/folders/'+fl.id);fo='*';draw()}catch(x){fail(x)}};
    m.onclick=async e=>{const b=e.target.closest('[data-a]');if(!b)return;const it=r.items.find(x=>x.id===b.closest('.mi').dataset.id),a=b.dataset.a;
      try{if(a==='view')window.open(it.url,'_blank');
      else if(a==='cp'){await navigator.clipboard.writeText(location.origin+it.url);toast('URL copied')}
      else if(a==='ren'){const d=modal('Rename / move',`<label>File name<input id="rn" value="${esc(it.name)}"></label><label>Folder<select id="rf2"><option value="">Root</option>${r.folders.map(f=>`<option ${f===it.folder?'selected':''}>${esc(f)}</option>`).join('')}</select></label><div class="acts"><button class="btn o" id="c">Cancel</button><button class="btn" id="s">Save</button></div>`);$('#c',d).onclick=()=>d.close();$('#s',d).onclick=async()=>{try{await api('PUT','/api/media/'+it.id,{name:$('#rn',d).value,folder:$('#rf2',d).value});d.close();draw()}catch(x){fail(x)}}}
      else if(a==='rep'){const i=document.createElement('input');i.type='file';i.accept='.'+it.ext;i.onchange=async()=>{const fd=new FormData();fd.append('file',i.files[0]);try{await api('POST',`/api/media/${it.id}/replace`,fd);toast('File replaced');draw()}catch(x){fail(x)}};i.click()}
      else if(a==='del'){if(await confirmBox(`Delete "${it.name}"?`,'Delete')){try{await api('DELETE','/api/media/'+it.id)}catch(x){if(x.status===409&&await confirmBox(x.message,'Delete anyway'))await api('DELETE','/api/media/'+it.id+'?force=1');else if(x.status!==409)throw x}draw()}}}catch(x){fail(x)}}};
  await draw()}

/* ---------------- homepage builder ---------------- */
async function home(m){
  m.innerHTML=`<h2>Homepage builder</h2><div class="bar"><a class="btn o" href="#/res/sliders">Sliders</a><a class="btn o" href="#/res/banners">Promo banners</a><a class="btn o" href="#/res/testimonials">Testimonials</a><a class="btn o" href="#/res/courses">Featured courses</a><a class="btn o" href="#/res/posts">Latest posts</a><a class="btn o" href="#/res/notices">Notices</a><a class="btn o" href="#/settings">Heading, subtitle, About & Contact text</a></div>
  <p class="mu">Drag sections to change their order on the public homepage; edit a section to change its text or number of items; untick “Visible” to hide it.</p><div id="sl"></div><h3>Live preview (includes drafts)</h3><div class="bar"><button class="btn sm o" id="rp">Refresh preview</button></div><iframe class="pvf" id="pvf" src="/?preview=1" title="Homepage preview"></iframe>`;
  window.refreshPv=()=>{const f=$('#pvf');if(f)f.src='/?preview=1&t='+Date.now()};$('#rp').onclick=window.refreshPv;await listView('sections','',$('#sl'),true)}

/* ---------------- settings ---------------- */
async function settings(m){
  const r=await api('GET','/api/settings'),V=r.values,groups=[...new Set(SC.settings.map(f=>f.g))];if(SC.sup)groups.push('Backup & restore');let cur=groups[0];
  const draw=()=>{const fs=SC.settings.filter(f=>f.g===cur&&(!f.sup||SC.sup)&&(cur!=='Maintenance'||SC.sup));
    m.innerHTML=`<h2>Website settings</h2><div class="tabs">${groups.map(g=>`<button class="${g===cur?'on':''}" data-g="${esc(g)}">${esc(g)}</button>`).join('')}</div>`+(cur==='Backup & restore'?`<div class="card"><p>Download a full backup (database + uploaded files) or restore from one. Restoring <b>replaces all current content</b> and signs everyone out.</p><p><a class="btn" href="/api/backup">Download backup</a></p><label>Restore from backup (.zip)<input type="file" id="rs" accept=".zip"></label><p><button class="btn red" id="rb">Restore</button></p></div>`
      :`<form class="card" id="sf" style="max-width:760px">${fs.map(f=>widget(f,V[f.k],0)).join('')}<div class="acts"><button class="btn" ${can('settings','e')?'':'disabled'}>Save settings</button></div></form><h3>Version history</h3><div class="tw"><table><tr><th>Saved</th><th>By</th><th></th></tr>${r.versions.map(v=>`<tr><td>${fdt(v.ts)}</td><td>${esc(v.author)}</td><td><button class="btn sm" data-v="${v.id}">Restore</button></td></tr>`).join('')||'<tr><td colspan="3" class="mu">None yet</td></tr>'}</table></div>`);
    $$('.tabs button',m).forEach(b=>b.onclick=()=>{cur=b.dataset.g;draw()});
    const sf=$('#sf');if(sf){wire(sf,fs);sf.onsubmit=async e=>{e.preventDefault();try{const body=collect(sf,fs);await api('PUT','/api/settings',body);Object.assign(V,body);toast('Settings saved – live on the website');}catch(x){fail(x)}};
      m.onclick=async e=>{const b=e.target.closest('[data-v]');if(b&&await confirmBox('Restore these settings?','Restore')){try{await api('POST','/api/settings/restore/'+b.dataset.v);toast('Restored');settings(m)}catch(x){fail(x)}}}}
    const rb=$('#rb');if(rb)rb.onclick=async()=>{const f=$('#rs').files[0];if(!f)return toast('Choose a backup file',1);if(!await confirmBox('Replace ALL content with this backup?','Restore'))return;const fd=new FormData();fd.append('file',f);try{const x=await api('POST','/api/restore',fd);alert(x.msg);location.reload()}catch(x){fail(x)}}};
  draw()}

/* ---------------- roles, activity, profile ---------------- */
async function roles(m){
  const r=await api('GET','/api/roles'),R=r.roles,names=Object.keys(R),ed=SC.sup,L=[['v','View'],['c','Create'],['e','Edit'],['p','Publish'],['d','Delete']];let cur=names[0];
  const draw=()=>{m.innerHTML=`<h2>Roles & permissions</h2><p class="mu">Super Admin always has full access. ${ed?'':'Only the Super Admin can edit permissions.'}</p><div class="tabs">${names.map(n=>`<button class="${n===cur?'on':''}" data-r="${n}">${esc(r.labels[n])}</button>`).join('')}</div>
    <div class="tw"><table><tr><th>Module</th>${L.map(x=>`<th>${x[1]}</th>`).join('')}</tr>${r.mods.map(mod=>`<tr><td>${esc(mod)}</td>${L.map(x=>`<td><input type="checkbox" data-m="${mod}" data-l="${x[0]}" ${(R[cur][mod]||'').includes(x[0])?'checked':''} ${ed?'':'disabled'}></td>`).join('')}</tr>`).join('')}</table></div>${ed?'<div class="acts"><button class="btn" id="sv">Save permissions</button></div>':''}`;
    $$('.tabs button',m).forEach(b=>b.onclick=()=>{cur=b.dataset.r;draw()});
    $$('input[data-m]',m).forEach(c=>c.onchange=()=>{const s=new Set((R[cur][c.dataset.m]||'').split(''));c.checked?s.add(c.dataset.l):s.delete(c.dataset.l);R[cur][c.dataset.m]=[...s].join('')});
    const sv=$('#sv');if(sv)sv.onclick=async()=>{try{await api('PUT','/api/roles',{roles:R});toast('Permissions saved')}catch(x){fail(x)}}};draw()}
async function activity(m){
  const draw=async q=>{const r=await api('GET','/api/logs?q='+encodeURIComponent(q||''));
    m.innerHTML=`<h2>Activity & login history</h2><div class="bar"><input id="aq" placeholder="Search activity…" value="${esc(q||'')}"></div><div class="tw"><table><tr><th>When</th><th>User</th><th>Action</th></tr>${r.items.map(x=>`<tr><td>${fdt(x.ts)}</td><td>${esc(x.who)}</td><td>${esc(x.action)}</td></tr>`).join('')||'<tr><td colspan="3" class="mu">No activity</td></tr>'}</table></div>
    <h3>Recent login attempts</h3><div class="tw"><table><tr><th>When</th><th>Username</th><th>IP</th><th>Result</th></tr>${r.logins.map(x=>`<tr><td>${fdt(x.ts)}</td><td>${esc(x.usr)}</td><td>${esc(x.ip)}</td><td><span class="tag ${x.ok?'g':'r'}">${x.ok?'OK':'Failed'}</span></td></tr>`).join('')}</table></div>`;
    $('#aq').onchange=e=>draw(e.target.value)};await draw()}
async function profile(m){
  const f=[{k:'name',l:'Display name',t:'text',req:1},{k:'username',l:'Username',t:'text',req:1},{k:'email',l:'Email',t:'email'},{k:'photo',l:'Profile picture',t:'media'}];
  m.innerHTML=`<h2>My profile</h2><form class="card" id="pf" style="max-width:560px">${f.map(x=>widget(x,ME[x.k],0)).join('')}<h3>Change password</h3><label>Current password<input type="password" id="cp" autocomplete="current-password"></label><label>New password (min 8)<input type="password" id="np" autocomplete="new-password"></label><div class="acts"><button class="btn">Save profile</button></div></form>`;
  wire($('#pf'),f);$('#pf').onsubmit=async e=>{e.preventDefault();const b=collect($('#pf'),f);b.current_password=$('#cp').value;b.new_password=$('#np').value;try{await api('PUT','/api/me',b);toast('Profile saved');const me=await api('GET','/api/me');ME=me.user;$('#who').textContent=`${ME.name} · ${m_role()}`;if(!ME.must_change)$('#warn').innerHTML=''}catch(x){fail(x)}}}
