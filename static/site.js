(function(){
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)],b=document.body,rm=matchMedia('(prefers-reduced-motion:reduce)').matches;
/* intro splash */
if(b.dataset.splash==='1'&&!sessionStorage.getItem('vj_seen')){const d=document.createElement('div');d.id='splash';d.innerHTML='<div><div class="lg"></div><h2></h2><p></p></div><button type="button">Skip intro</button>';
 d.querySelector('.lg').textContent=(b.dataset.name||'V')[0];d.querySelector('h2').textContent=(b.dataset.name||'').toUpperCase();d.querySelector('p').textContent=b.dataset.tag||'';b.append(d);
 const end=()=>{d.classList.add('out');sessionStorage.setItem('vj_seen','1');setTimeout(()=>d.remove(),700)};d.querySelector('button').onclick=end;setTimeout(end,2600)}
/* more sheet */
const more=$('#more');
function setMore(o){if(!more)return;more.hidden=!o;$$('[data-more]').forEach(x=>x.setAttribute('aria-expanded',o));$$('.bnav [data-nav="more"]').forEach(x=>x.classList.toggle('on',o))}
$$('[data-more]').forEach(x=>x.addEventListener('click',()=>setMore(more.hidden)));if(more)more.addEventListener('click',e=>{if(e.target.closest('a'))setMore(false)});
/* active nav */
const home=b.dataset.home==='1',links=$$('[data-nav]');
function active(k){links.forEach(a=>{if(a.dataset.nav!=='more')a.classList.toggle('on',a.dataset.nav===k)})}
if(home&&'IntersectionObserver'in window){const ids=['top','programs','admission','pride'],seen={};
 const io=new IntersectionObserver(es=>{es.forEach(e=>{seen[e.target.id]=e.isIntersecting});const k=ids.find(i=>seen[i]);if(k)active(k)},{rootMargin:'-35% 0px -55% 0px'});
 ids.forEach(i=>{const e=document.getElementById(i);if(e)io.observe(e)});active('top')}
else if(!home)$$('.bnav [data-nav="more"]').forEach(x=>x.classList.add('on'));
/* poster slider */
const tr=$('#track');
if(tr){const sl=$$('.sl',tr),dots=$('#dots');let i=0,timer,paused=false;
 sl.forEach((_,k)=>{const d=document.createElement('i');dots.append(d)});
 const mark=()=>{i=Math.round(tr.scrollLeft/tr.clientWidth);$$('i',dots).forEach((d,k)=>d.classList.toggle('on',k===i))};
 const go=k=>{i=(k+sl.length)%sl.length;tr.scrollTo({left:i*tr.clientWidth,behavior:rm?'auto':'smooth'})};
 tr.addEventListener('scroll',()=>{clearTimeout(tr._t);tr._t=setTimeout(mark,60)},{passive:true});mark();
 $('.slider .prev').onclick=()=>go(i-1);$('.slider .next').onclick=()=>go(i+1);
 tr.addEventListener('keydown',e=>{if(e.key==='ArrowLeft')go(i-1);if(e.key==='ArrowRight')go(i+1)});
 if(sl.length<2){$$('.slider .sb').forEach(x=>x.hidden=true)}
 else if(!rm){const s=()=>{clearInterval(timer);timer=setInterval(()=>{if(!paused&&!document.hidden)go(i+1)},4800)};s();
  ['pointerenter','focusin','touchstart'].forEach(ev=>tr.parentNode.addEventListener(ev,()=>paused=true,{passive:true}));['pointerleave','focusout','touchend'].forEach(ev=>tr.parentNode.addEventListener(ev,()=>paused=false,{passive:true}))}
 addEventListener('resize',()=>tr.scrollTo({left:i*tr.clientWidth}))}
/* lightbox */
const lb=$('#lb');
if(lb){let L=[],k=0;const img=$('#lbi'),cap=$('#lbc');
 const show=n=>{k=(n+L.length)%L.length;img.src=L[k].dataset.full;img.alt=L[k].dataset.cap||'';cap.textContent=L[k].dataset.cap||''};
 const open=el=>{L=$$('[data-full]');show(L.indexOf(el));lb.hidden=false;b.classList.add('lock');$('.lb-x',lb).focus()};
 const close=()=>{lb.hidden=true;img.src='';if($('.ov:not([hidden])')==null)b.classList.remove('lock')};
 document.addEventListener('click',e=>{const t=e.target.closest('[data-full]');if(t){e.preventDefault();open(t)}});
 $('[data-lbc]',lb).onclick=close;$('[data-lbp]',lb).onclick=()=>show(k-1);$('[data-lbn]',lb).onclick=()=>show(k+1);lb.addEventListener('click',e=>{if(e.target===lb)close()});
 let x0=null;lb.addEventListener('touchstart',e=>x0=e.touches[0].clientX,{passive:true});lb.addEventListener('touchend',e=>{if(x0==null)return;const d=e.changedTouches[0].clientX-x0;if(Math.abs(d)>50)show(k+(d<0?1:-1));x0=null});
 addEventListener('keydown',e=>{if(lb.hidden)return;if(e.key==='Escape')close();if(e.key==='ArrowLeft')show(k-1);if(e.key==='ArrowRight')show(k+1)});lb._close=close}
/* program pages (full-screen) */
const ovs=$$('.ov');let pushed=false,opener=null;
function hideAll(){ovs.forEach(o=>o.hidden=true);if(!lb||lb.hidden)b.classList.remove('lock')}
function openProg(k,push){const o=document.getElementById('ov-'+k);if(!o)return;hideAll();setMore(false);o.hidden=false;o.scrollTop=0;b.classList.add('lock');if(push){history.pushState({prog:k},'','#program-'+k);pushed=true}$('[data-close]',o).focus()}
function closeProg(){if(pushed){pushed=false;history.back()}else{hideAll();if(location.hash.startsWith('#program-'))history.replaceState(null,'',location.pathname+'#programs')}}
$$('[data-prog]').forEach(c=>c.addEventListener('click',()=>{opener=c;openProg(c.dataset.prog,true)}));
ovs.forEach(o=>o.addEventListener('click',e=>{const c=e.target.closest('[data-close]');if(c){const a=c.closest('a');if(a){hideAll();pushed=false}else{e.preventDefault();closeProg()}}}));
addEventListener('popstate',()=>{const m=location.hash.match(/^#program-(\w+)/);if(m)openProg(m[1],false);else{hideAll();if(opener)opener.focus()}});
addEventListener('keydown',e=>{if(e.key==='Escape'){if(lb&&!lb.hidden)return;if(!more.hidden)setMore(false);else if($('.ov:not([hidden])'))closeProg()}});
{const m=location.hash.match(/^#program-(\w+)/);if(m)openProg(m[1],false)}
/* lazy video players */
document.addEventListener('click',e=>{const p=e.target.closest('.vplay[data-yt]');if(!p)return;const f=document.createElement('iframe');f.src='https://www.youtube-nocookie.com/embed/'+encodeURIComponent(p.dataset.yt)+'?autoplay=1&rel=0';f.allow='autoplay; encrypted-media; picture-in-picture; fullscreen';f.allowFullscreen=true;f.title='Academy video';p.replaceWith(f)});
/* admission form → existing /contact enquiry endpoint (shown in Admin → Enquiries) */
const af=$('#admForm');
if(af){const err=$('#a_e'),ok=$('#a_ok');af.addEventListener('submit',async e=>{e.preventDefault();err.textContent='';ok.textContent='';
 const father=$('#a_f').value.trim(),stu=$('#a_s').value.trim(),mob=$('#a_m').value.replace(/\s/g,''),cl=(af.querySelector('input[name=a_c]:checked')||{}).value;
 if(!father||!stu)return err.textContent="Please enter the father's and the student's names.";
 if(!/^[0-9]{10}$/.test(mob))return err.textContent='Enter a valid 10-digit mobile number.';if(!cl)return err.textContent='Please choose the class: 4th or 5th.';
 const btn=af.querySelector('button[type=submit]');btn.disabled=true;
 const fd=new FormData();fd.append('csrf',af.dataset.csrf);fd.append('name',stu);fd.append('contact',mob);fd.append('msg',`ADMISSION APPLICATION | Student: ${stu} | Father: ${father} | Class: ${cl} | Mobile: ${mob}`);
 try{const r=await fetch('/contact',{method:'POST',body:fd,credentials:'same-origin'});if(!r.ok)throw 0;ok.textContent='Thank you! Your application is received. We will call you soon.';af.reset()}
 catch(x){err.textContent='Could not submit. Please check your connection and try again, or call us.'}finally{btn.disabled=false}})}
/* online exam timer (unchanged behaviour) */
const t=$('#timer'),f=$('#exf');
if(t&&f){let left=Math.round(parseFloat(t.dataset.min)*60);const tick=()=>{const m=Math.floor(left/60),s=left%60;t.textContent=m+':'+String(s).padStart(2,'0');if(left--<=0){clearInterval(h);f.submit()}};const h=setInterval(tick,1000);tick();f.addEventListener('submit',()=>clearInterval(h))}
})();
