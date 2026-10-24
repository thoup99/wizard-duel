import {$,api,store} from './common.js';
let joining=false;
$('#name').value=store.get('mage-name')||'';
const incoming=new URLSearchParams(location.search).get('room');
function tab(join){joining=join;$('#codeField').hidden=!join;$('#code').required=join;$('#createTab').classList.toggle('active',!join);$('#joinTab').classList.toggle('active',join);$('#createTab').setAttribute('aria-selected',String(!join));$('#joinTab').setAttribute('aria-selected',String(join));$('#submit').textContent=join?'Join room ↗':'Create room ↗';}
$('#createTab').onclick=()=>tab(false);$('#joinTab').onclick=()=>tab(true);
if(incoming){tab(true);$('#code').value=incoming.toUpperCase();}
$('#code').oninput=()=>$('#code').value=$('#code').value.toUpperCase().replace(/[^A-Z]/g,'');
$('#roomForm').onsubmit=async e=>{e.preventDefault();const name=$('#name').value.trim();if(!name)return;$('#submit').disabled=true;$('#formStatus').textContent='Opening the portal…';try{store.set('mage-name',name);let code;if(joining){code=$('#code').value.trim().toUpperCase();await api('/api/rooms/'+code);}else{({code}=await api('/api/rooms',{method:'POST'}));}location.href='/phone?room='+encodeURIComponent(code);}catch(err){$('#formStatus').textContent=err.message;$('#submit').disabled=false;}};
