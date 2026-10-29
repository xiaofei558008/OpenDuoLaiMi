/* OpenDoremi optional account + sync (web). Playback never depends on this file. */
(function(){
var API='https://openduolaimi.com/api/v1',LS=window.localStorage,EN=window.EN_UI;
var M=EN?{acct:'Account',login:'Log in',reg:'Sign up',email:'Email',pw:'Password (8+ chars)',out:'Log out',del:'Delete account',delc:'Delete this account and ALL its synced data on the server? This cannot be undone. Your local data on this browser is kept.',delpw:'Enter your password to confirm deletion:',synced:'Synced',syncing:'Syncing…',offline:'Sync service unavailable — your data is saved in this browser.',opt:'Logging in is optional. Without it, favorites, history and resume are saved in this browser only. Log in to sync across the app and web.',e401:'Wrong email or password.',e409:'This email is already registered.',e423:'Too many attempts, account temporarily locked.',e429:'Too many attempts, try again later.',ew:'Password too weak (at least 8 characters).',err:'Request failed: ',fav:'Favorites',rec:'Recently played',mine:'Mine',deld:'Account deleted.',tier:'Plan: '}
:{acct:'账号',login:'登录',reg:'注册',email:'邮箱',pw:'密码（至少 8 位）',out:'退出登录',del:'注销账号',delc:'确定注销账号并删除服务器上的全部同步数据吗？此操作不可恢复。本浏览器里的本地数据会保留。',delpw:'请输入密码确认注销：',synced:'已同步',syncing:'同步中…',offline:'同步服务暂不可用，数据已保存在本浏览器。',opt:'登录是可选的。不登录时，收藏、最近播放和续播只保存在本浏览器；登录后可与 App 和网页跨端同步。',e401:'邮箱或密码错误。',e409:'该邮箱已注册。',e423:'尝试次数过多，账号暂时锁定。',e429:'尝试过于频繁，请稍后再试。',ew:'密码太弱（至少 8 位）。',err:'请求失败：',fav:'我的收藏',rec:'最近播放',mine:'我的',deld:'账号已注销。',tier:'会员等级：'};
function J(k,d){try{var v=LS.getItem(k);return v?JSON.parse(v):d}catch(e){return d}}
function W(k,v){try{LS.setItem(k,JSON.stringify(v))}catch(e){}}
function uuid(){if(window.crypto&&crypto.randomUUID)return crypto.randomUUID();return'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0;return(c=='x'?r:(r&3|8)).toString(16)})}
function now(){return new Date().toISOString()}
var dev=J('od_dev',null);if(!dev){dev=uuid();W('od_dev',dev)}
var fav=J('od_fav',{});      // track_id -> {updated_at,deleted,p}
var hist=J('od_hist',[]);    // [{id,track_id,played_at,position_ms,duration_ms,updated_at,deleted,p}]
var resume=J('od_resume',null);
var access=null,user=null,busy=null,state='';
function save(){W('od_fav',fav);W('od_hist',hist);W('od_resume',resume)}
function trim(){hist.sort(function(a,b){return a.played_at<b.played_at?1:-1});if(hist.length>500)hist.length=500}
function client(){return{platform:'web',device_id:dev,device_name:(navigator.platform||'web').slice(0,64),app_version:'web-1.0'}}
function call(path,o,noAuth){o=o||{};var h={'Content-Type':'application/json'};if(o.idem)h['Idempotency-Key']=o.idem;if(access&&!noAuth)h.Authorization='Bearer '+access;
 var ac=window.AbortController?new AbortController():null,t=setTimeout(function(){ac&&ac.abort()},10000);
 return fetch(API+path,{method:o.method||'GET',headers:h,body:o.body?JSON.stringify(o.body):undefined,signal:ac&&ac.signal}).then(function(r){clearTimeout(t);
  if(r.status==401&&!noAuth&&!o.retried&&J('od_rt',null))return refresh().then(function(ok){if(!ok)throw{status:401};o.retried=1;return call(path,o)});
  return r.text().then(function(x){var d=null;try{d=x?JSON.parse(x):null}catch(e){}if(!r.ok&&r.status!=409)throw{status:r.status,data:d};return{status:r.status,data:d}})})}
var rf=null;
function refresh(){if(rf)return rf;var rt=J('od_rt',null);if(!rt)return Promise.resolve(false);
 rf=call('/auth/refresh',{method:'POST',body:{refresh_token:rt}},true).then(function(r){access=r.data.access_token;W('od_rt',r.data.refresh_token);return true}).catch(function(e){if(e&&e.status==401){LS.removeItem('od_rt');access=null;user=null}return false}).then(function(v){rf=null;ui();return v});return rf}
function markAll(){for(var k in fav)fav[k].p=1;hist.forEach(function(h){h.p=1});if(resume)resume.p=1;LS.removeItem('od_cf');LS.removeItem('od_ch');save()}
function onAuth(d){access=d.access_token;W('od_rt',d.refresh_token);user=d.user;if(J('od_uid',null)!==user.id){markAll();W('od_uid',user.id)}ui();return sync()}
function push(path,items,keyf,apply){var ch=[];for(var i=0;i<items.length;i+=500)ch.push(items.slice(i,i+500));
 return ch.reduce(function(p,c){return p.then(function(){return call(path,{method:'POST',idem:uuid(),body:{changes:c.map(function(x){var y={};for(var k in x)if(k!='p')y[k]=x[k];return y})}}).then(function(r){(r.data&&r.data.results||[]).forEach(function(z){apply(z)})})})},Promise.resolve())}
function pull(path,ck,each){var go=function(){var c=J(ck,null);return call(path+'?limit=500'+(c?'&cursor='+encodeURIComponent(c):'')).then(function(r){r.data.items.forEach(each);W(ck,r.data.next_cursor);if(r.data.has_more)return go()}).catch(function(e){if(e&&e.status==410){LS.removeItem(ck);return go()}throw e})};return go()}
function lww(a,b){return!a||a.updated_at<=b.updated_at}
function sync(){if(!access)return Promise.resolve();if(busy)return busy;state='syncing';ui();
 var pf=Object.keys(fav).filter(function(k){return fav[k].p}).map(function(k){return{track_id:k,updated_at:fav[k].updated_at,deleted:!!fav[k].deleted}});
 var ph=hist.filter(function(h){return h.p});
 busy=push('/sync/favorites',pf,0,function(z){if(z.status=='applied'&&fav[z.key])delete fav[z.key].p;else if(z.status=='ignored_older'&&z.current){fav[z.key]={updated_at:z.current.updated_at,deleted:z.current.deleted}}else if(fav[z.key])delete fav[z.key].p})
 .then(function(){return push('/sync/history',ph,0,function(z){hist.forEach(function(h){if(h.id==z.key)delete h.p})})})
 .then(function(){return pull('/sync/favorites','od_cf',function(x){if(lww(fav[x.track_id],x)&&!(fav[x.track_id]&&fav[x.track_id].p))fav[x.track_id]={updated_at:x.updated_at,deleted:x.deleted}})})
 .then(function(){return pull('/sync/history','od_ch',function(x){var f=null;hist.forEach(function(h){if(h.id==x.id)f=h});if(f){if(lww(f,x)&&!f.p)for(var k in x)f[k]=x[k]}else hist.push(x)})})
 .then(function(){hist=hist.filter(function(h){return!h.deleted||h.p});trim();return syncResume()})
 .then(function(){state='ok';save()},function(){state='off';save()}).then(function(){busy=null;ui();OD.onchange&&OD.onchange()});return busy}
function syncResume(){return call('/sync/resume').then(function(r){var s=r.data;if(s&&s.track_id&&(!resume||s.updated_at>resume.updated_at)){resume={track_id:s.track_id,position_ms:s.position_ms,updated_at:s.updated_at};OD.onresume&&OD.onresume(resume)}else if(resume&&resume.p)return putResume()}).catch(function(e){if(e&&e.status==404&&resume)return putResume();throw e})}
function putResume(){if(!access||!resume)return Promise.resolve();return call('/sync/resume',{method:'PUT',body:{track_id:resume.track_id,position_ms:resume.position_ms,device_id:dev,updated_at:resume.updated_at,deleted:false}}).then(function(){if(resume)delete resume.p;save()}).catch(function(){})}
var st=null;function soon(){clearTimeout(st);st=setTimeout(function(){sync()},1500)}
var lastRP=0;
window.OD={
 isFav:function(id){return!!(fav[id]&&!fav[id].deleted)},
 favs:function(){return Object.keys(fav).filter(function(k){return!fav[k].deleted}).sort(function(a,b){return fav[a].updated_at<fav[b].updated_at?1:-1})},
 toggleFav:function(id){var on=!this.isFav(id);fav[id]={updated_at:now(),deleted:!on,p:1};save();if(access)soon();return on},
 recent:function(){var seen={},o=[];hist.filter(function(h){return!h.deleted}).sort(function(a,b){return a.played_at<b.played_at?1:-1}).forEach(function(h){if(!seen[h.track_id]){seen[h.track_id]=1;o.push(h.track_id)}});return o},
 played:function(id,dur){var h={id:uuid(),track_id:id,played_at:now(),position_ms:0,duration_ms:Math.round((dur||0)*1000),platform:'web',updated_at:now(),deleted:false,p:1};hist.push(h);trim();save();if(access)soon();return h.id},
 progress:function(hid,id,sec,push){hist.forEach(function(h){if(h.id==hid){h.position_ms=Math.round(sec*1000);h.updated_at=now();h.p=1}});resume={track_id:id,position_ms:Math.round(sec*1000),updated_at:now(),p:1};save();if(access&&(push||Date.now()-lastRP>30000)){lastRP=Date.now();putResume();if(push)soon()}},
 resume:function(){return resume},
 user:function(){return user}
};
/* ---- UI ---- */
var box;function esc(s){return String(s||'').replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function ui(){var b=document.getElementById('ub');if(b){b.classList.toggle('in',!!user);b.title=user?(user.email||M.acct):M.login}
 if(!box||box.hidden)return;var h='<button class="x" id="ax">×</button><h3>'+M.acct+'</h3>';
 if(user){h+='<p><b>'+esc(user.email)+'</b></p><p class="note">'+M.tier+esc(user.membership_tier)+' · '+(state=='syncing'?M.syncing:state=='off'?M.offline:M.synced)+'</p><div class="ar"><button id="alo">'+M.out+'</button><button id="adel" class="dg">'+M.del+'</button></div>'}
 else h+='<p class="note">'+M.opt+'</p><input id="aem" type="email" autocomplete="username" placeholder="'+M.email+'"><input id="apw" type="password" autocomplete="current-password" minlength="8" placeholder="'+M.pw+'"><div class="ar"><button id="ali" class="pr">'+M.login+'</button><button id="arg">'+M.reg+'</button></div>';
 h+='<p class="am" id="amsg"></p>';box.querySelector('.ac').innerHTML=h;bind()}
function msg(t){var e=document.getElementById('amsg');if(e)e.textContent=t||''}
function emsg(e){var s=e&&e.status,c=e&&e.data&&e.data.error&&e.data.error.code;if(c=='PASSWORD_WEAK'||s==422)return M.ew;if(s==401||s==403)return M.e401;if(s==409)return M.e409;if(s==423)return M.e423;if(s==429)return M.e429;if(!s)return M.offline;return M.err+(c||s)}
function auth(path){var em=document.getElementById('aem').value.trim(),pw=document.getElementById('apw').value;msg('…');
 call(path,{method:'POST',idem:path=='/auth/register'?uuid():null,body:{email:em,password:pw,client:client()}},true).then(function(r){return onAuth(r.data)}).then(function(){msg('')}).catch(function(e){msg(emsg(e))})}
function bind(){var g=function(i){return document.getElementById(i)};g('ax').onclick=function(){box.hidden=true};
 if(g('ali')){g('ali').onclick=function(){auth('/auth/login')};g('arg').onclick=function(){auth('/auth/register')};g('apw').onkeydown=function(e){if(e.key=='Enter')auth('/auth/login')}}
 if(g('alo'))g('alo').onclick=function(){call('/auth/logout',{method:'POST',body:{}}).catch(function(){}).then(function(){LS.removeItem('od_rt');access=null;user=null;markAll();LS.removeItem('od_uid');ui()})};
 if(g('adel'))g('adel').onclick=function(){if(!confirm(M.delc))return;var pw=prompt(M.delpw);if(!pw)return;msg('…');call('/me',{method:'DELETE',body:{password:pw}}).then(function(){LS.removeItem('od_rt');LS.removeItem('od_uid');access=null;user=null;markAll();ui();msg(M.deld)}).catch(function(e){msg(emsg(e))})}}
function init(){var b=document.getElementById('ub');if(!b)return;box=document.createElement('div');box.id='acct';box.hidden=true;box.innerHTML='<div class="ac"></div>';document.body.appendChild(box);
 box.onclick=function(e){if(e.target===box)box.hidden=true};b.onclick=function(){box.hidden=!box.hidden;ui()};ui();
 if(J('od_rt',null))refresh().then(function(ok){if(!ok)return;return call('/me').then(function(r){user=r.data;ui();return sync()})}).catch(function(){state='off';ui()});
 setInterval(function(){if(access)sync()},120000);window.addEventListener('online',function(){if(access)sync()})}
OD.M=M;if(document.readyState=='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
