import {enableSound,spellSound} from './sound.js';
import {$,api,toast,spellGuide} from './common.js';
import {Motion} from './motion.js';
import {setGestureMode} from './spells.js';
import {Training,trainingHTML} from './training.js';
const settings=await api('/api/settings');setGestureMode(settings.gesture_mode);$('#training').innerHTML=trainingHTML();$('#guide').innerHTML=spellGuide();let lastDraw=0;
const motion=new Motion(()=>{$('#quality').textContent=motion.status();if(performance.now()-lastDraw>50){training.live();lastDraw=performance.now();}});
const training=new Training($('#training'),motion,async payload=>{const r=await api('/api/practice',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'practice_cast',...payload})});training.result(r);spellSound(r.spell,r.outcome);});
$('#enable').onclick=async()=>{try{const permission=motion.enable();enableSound();await permission;setTimeout(()=>$('#quality').textContent=motion.status(),1800);}catch(e){toast(e.message);}};
