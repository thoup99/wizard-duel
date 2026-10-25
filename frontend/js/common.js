export const $ = s => document.querySelector(s);
export const escape = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const symbols = {bolt:'ϟ',ward:'◉',empower:'↟',hex:'⌁'};
export function toast(text) { let el = $('#toast'); if (!el) { el=document.createElement('div'); el.id='toast'; el.className='toast'; el.setAttribute('role','status'); document.body.append(el); } el.textContent=text; el.hidden=false; clearTimeout(toast.timer); toast.timer=setTimeout(()=>el.hidden=true,4500); }
export async function api(path, options={}) { const r = await fetch(path,options); let body; try{body=await r.json();}catch{throw new Error('The server returned an invalid response.');} if(!r.ok)throw new Error(typeof body.detail==='string'?body.detail:'Please check your input.'); return body; }
export const store = {get(k){try{return localStorage.getItem(k);}catch{return null;}},set(k,v){try{localStorage.setItem(k,v);}catch{}},remove(k){try{localStorage.removeItem(k);}catch{}}};
export {guide as spellGuide} from './spells.js';
export function teamName(state,team){return state.team_names?.[team]||['Team A','Team B'][team];}
export {isLikelyPhone} from './device.js';
