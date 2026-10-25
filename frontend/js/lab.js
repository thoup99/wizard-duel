import {$,api,toast,spellGuide} from './common.js';
import {Motion} from './motion.js';
import {StrokeControl} from './training.js';
import {setGestureMode,SPELLS,caption} from './spells.js';
const settings=await api('/api/settings');setGestureMode(settings.gesture_mode);
for(const s of SPELLS) document.querySelector(`#label option[value="${s.id}"]`).textContent=s.name+" · "+caption(s);
let history=[],record=null,lastDraw=0;
const motion=new Motion(row=>{history.push(row);history=history.slice(-200);$('#sensorStatus').textContent=motion.status();if(performance.now()-lastDraw>50){draw('acceleration',1,360);draw('rotation',4,240);lastDraw=performance.now();}});
$('#enable').onclick=async()=>{try{await motion.enable();$('#sensorStatus').textContent='Permission granted. Waiting for orientation data…';setTimeout(()=>$('#sensorStatus').textContent=motion.status(),1800);}catch(e){toast(e.message);}};
function draw(id,offset,scale){const canvas=$('#'+id),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);ctx.strokeStyle='#34414a';for(let i=1;i<4;i++){ctx.beginPath();ctx.moveTo(0,h*i/4);ctx.lineTo(w,h*i/4);ctx.stroke();}['#ec9d9b','#8dd6bd','#8bbce3'].forEach((color,axis)=>{ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();history.forEach((r,i)=>{const x=i*w/200,y=h/2-r[offset+axis]*h/(scale*2);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.stroke();});}
let label;
new StrokeControl($('#capture'),motion,payload=>{record={...payload,label,mode:settings.gesture_mode};$('#recordStatus').textContent=`Captured ${record.samples.length} orientation samples over ${record.samples.at(-1)[0].toFixed(2)} seconds.`;$('#download').disabled=$('#save').disabled=false;},()=>{label=$('#label').value;record=null;$('#download').disabled=$('#save').disabled=true;$('#recordStatus').textContent='Recording orientation…';});
$('#download').onclick=()=>{if(!record)return;const url=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`${record.label}-${record.platform}-${Date.now()}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('#save').onclick=async()=>{try{const r=await api('/api/samples',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+$('#admin').value},body:JSON.stringify(record)});toast('Saved '+r.filename);}catch(e){toast(e.message);}};
$('#reload').onclick=async()=>{try{await api('/api/gestures/reload',{method:'POST',headers:{Authorization:'Bearer '+$('#admin').value}});toast('Thresholds reloaded. Refresh pages if you changed shape/flick mode.');}catch(e){toast(e.message);}};
$('#guide').innerHTML=spellGuide();
