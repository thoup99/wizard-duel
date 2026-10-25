import fs from 'node:fs';
import assert from 'node:assert/strict';
import {project,integrate,angles} from '../frontend/js/projection.js';
const vectors=JSON.parse(fs.readFileSync(new URL('../tests/fixtures/projection.json',import.meta.url)));
for(const v of vectors){const actual=project(v.rows);assert.equal(actual.length,v.path.length);actual.forEach((p,i)=>p.forEach((x,j)=>assert.ok(Math.abs(x-v.path[i][j])<1e-7,`${v.name} sample ${i}`)));}
const r=integrate([[1,0,0],[0,1,0],[0,0,1]],[90,0,0],.5);assert.ok(Math.abs(angles(r)[1]-45)<1e-8);
// common.js is browser-independent until its helpers are called.
const {isLikelyPhone}=await import('../frontend/js/device.js');
function env(coarse,touch,mobile,platform='Linux'){return {navigator:{maxTouchPoints:touch,userAgentData:{mobile},platform},matchMedia:()=>({matches:coarse}),DeviceMotionEvent:class{}};}
assert.equal(isLikelyPhone(env(false,0,false)),false);
assert.equal(isLikelyPhone(env(true,5,true)),true);
assert.equal(isLikelyPhone(env(false,5,false,'MacIntel')),true);
assert.equal(isLikelyPhone(env(false,1,false)),false);
console.log('Projection parity, gyro integration and audience detection passed.');
const {stabilizeHorizontal,preview}=await import('../frontend/js/projection.js');
assert.deepEqual(stabilizeHorizontal([[0,0],[10,2],[20,-3],[30,1]]),[[0,0],[10,1.1],[20,-1.6500000000000001],[30,.55]]);
const zigzag=[[0,0],[20,0],[0,-5],[20,-5]];
assert.deepEqual(stabilizeHorizontal(zigzag),zigzag);
assert.deepEqual(preview([]),[]);
// Verify the same spell definitions drive guides in every supported mode.
globalThis.fetch=async()=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(new URL('../frontend/spells.json',import.meta.url)))});
const spellbook=await import('../frontend/js/spells.js');
assert.equal(spellbook.gestureMode,'mixed');
for(const spell of spellbook.SPELLS){
 assert.equal(spellbook.caption(spell),spell.mixed.caption);
 assert.ok(spellbook.diagram(spell.id).includes(spell.mixed.caption));
 assert.equal(spellbook.points(spell).length,spell.id==='ward'?65:spell.id==='hex'?4:2);
}
console.log('Horizontal damping and mixed spellbook diagrams passed.');
