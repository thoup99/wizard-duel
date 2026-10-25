import assert from 'node:assert/strict';
import {Motion} from '../frontend/js/motion.js';
let now=1000,asked=0;
Object.defineProperty(globalThis,'performance',{value:{now:()=>now},configurable:true});
Object.defineProperty(globalThis,'navigator',{value:{userAgent:'iPhone',platform:'iPhone',maxTouchPoints:5},configurable:true});
const sensor={requestPermission:()=>{asked++;return Promise.resolve('granted');}};
globalThis.window={isSecureContext:true,DeviceMotionEvent:sensor,DeviceOrientationEvent:sensor,addEventListener(){},removeEventListener(){}};
const motion=new Motion();const enabling=motion.enable();assert.equal(asked,2,'Both permission requests must start in the user tap');await enabling;
for(let i=0;i<65;i++){now+=1000/60;motion.onOrientation({alpha:i*.4,beta:30,gamma:0,absolute:false});}
assert.ok(motion.available&&motion.tested);assert.ok(motion.hz>=30);assert.equal(motion.source,'orientation');
motion.begin();assert.ok(motion.buffer.length>=8,'Pre-roll missing');const before=motion.buffer.length;
now+=20;motion.onOrientation({alpha:42,beta:30,gamma:5,absolute:false});assert.equal(motion.buffer.at(-1)[1],42,'Capture should contain raw angles');assert.ok(motion.buffer.length>before);
const ending=motion.end();assert.ok(motion.capturing,'Post-roll must remain open');now+=20;motion.onOrientation({alpha:43,beta:30,gamma:5,absolute:false});const rows=await ending;assert.equal(rows.at(-1)[1],43);assert.equal(motion.capturing,false);assert.ok(rows.at(-1)[0]<=2.5);
const length=motion.history.length;motion.onOrientation({alpha:50,beta:30,gamma:0,absolute:true});assert.equal(motion.history.length,length);
const slow=new Motion();for(let i=0;i<15;i++){now+=100;slow.sample([now/1000,i*2,30,0,0,0,0]);}assert.equal(slow.tested,false,'Low-rate sensor should not pass quality gate');
window.isSecureContext=false;await assert.rejects(()=>slow.enable(),/HTTPS/);
window.isSecureContext=true;window.DeviceOrientationEvent={requestPermission:()=>Promise.resolve('denied')};await assert.rejects(()=>slow.enable(),/Permission denied/);
console.log('Sensor permission, quality gate, raw capture and pre/post-roll checks passed.');
