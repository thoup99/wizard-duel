import {SPELLS,diagram,caption,setGestureMode,guide} from './spells.js';
import {$,api,store,isLikelyPhone} from './common.js';
async function main(){
let joining=false;
$('#name').value=store.get('mage-name')||'';
const params=new URLSearchParams(location.search);
const incoming=params.get('room');
const phone=isLikelyPhone();
if(incoming&&!phone){location.replace('/arena?room='+encodeURIComponent(incoming.toUpperCase()));return;}
const settings=await api('/api/settings');setGestureMode(settings.gesture_mode);
document.querySelector('.spell-grid').innerHTML=SPELLS.map(s=>`<article class="spell-card">${diagram(s.id)}<h3>${s.name} <span class="tiny muted">/ ${s.cost} mana</span></h3><p>${caption(s)}</p></article>`).join('');
document.querySelector('#spells').insertAdjacentHTML('beforeend',guide({includeSpells:false}));
function tab(join){joining=join;$('#codeField').hidden=!join;$('#code').required=join;$('#name').required=!(join&&!phone);$('#name').hidden=join&&!phone;document.querySelector('label[for=name]').hidden=join&&!phone;$('#createTab').classList.toggle('active',!join);$('#joinTab').classList.toggle('active',join);$('#createTab').setAttribute('aria-selected',String(!join));$('#joinTab').setAttribute('aria-selected',String(join));$('#submit').textContent=join?(!phone?'Watch room ↗':'Join room ↗'):'Create room ↗';}
$('#createTab').onclick=()=>{if(phone)tab(false);};$('#joinTab').onclick=()=>tab(true);
if(!phone){tab(true);document.querySelector('.tabs').hidden=true;document.querySelector('.panel-header h2').textContent='Watch the arena';document.querySelector('.join-note').textContent='Players join from phones or tablets. Laptops and desktops are spectators.';$('#trainingCopy').textContent='Practice casts on your phone or tablet. You can preview the 3D arena here.';}
if(incoming){tab(true);$('#code').value=incoming.toUpperCase();}
$('#code').oninput=()=>$('#code').value=$('#code').value.toUpperCase().replace(/[^A-Z]/g,'');
$('#roomForm').onsubmit=async e=>{e.preventDefault();const name=$('#name').value.trim();if(!name&&!(joining&&!phone))return;$('#submit').disabled=true;$('#formStatus').textContent='Opening the portal…';try{store.set('mage-name',name);let code;if(joining){code=$('#code').value.trim().toUpperCase();await api('/api/rooms/'+code);}else{({code}=await api('/api/rooms',{method:'POST',headers:{'X-Pocket-Mages-Mobile':phone?'1':'0'}}));}location.href=(joining&&!phone?'/arena?room=':'/phone?room=')+encodeURIComponent(code);}catch(err){$('#formStatus').textContent=err.message;$('#submit').disabled=false;}};

}
main().catch(error=>{$('#formStatus').textContent=error.message;});
