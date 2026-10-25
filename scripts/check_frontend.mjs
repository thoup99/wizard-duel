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
