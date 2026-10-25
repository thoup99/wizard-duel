import * as THREE from '../vendor/three.module.min.js';
import {ArenaEvents} from './arena-events.js';
const TEAM=[0xe9c879,0xc4afe8],SPELL={bolt:0xffcc65,ward:0x6edada,empower:0xffe9a0,hex:0xb986ff};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export class ArenaScene {
 constructor(host,{onFailure=()=>{}}={}){
  this.host=host;this.onFailure=onFailure;this.mages=new Map();this.effects=[];this.events=new ArenaEvents();this.state=null;this.disposed=false;this.paused=matchMedia('(prefers-reduced-motion: reduce)').matches;this.connected=true;this.time=0;this.last=performance.now();
  this.scene=new THREE.Scene();this.scene.background=new THREE.Color(0x101827);this.scene.fog=new THREE.Fog(0x101827,20,42);
  this.camera=new THREE.PerspectiveCamera(39,1,.1,70);this.camera.position.set(10,9,13);this.camera.lookAt(0,.7,0);
  this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'low-power'});this.renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.5));this.renderer.outputColorSpace=THREE.SRGBColorSpace;this.renderer.shadowMap.enabled=true;this.renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  this.renderer.domElement.setAttribute('aria-label','Live 3D arena: four cartoon mages casting spells');this.renderer.domElement.setAttribute('role','img');host.append(this.renderer.domElement);
  this.labels=document.createElement('div');this.labels.className='mage-labels';host.append(this.labels);
  this.scene.add(new THREE.HemisphereLight(0xbddffa,0x32253e,2.7));const sun=new THREE.DirectionalLight(0xffe1b9,3.3);sun.position.set(-3,9,5);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);Object.assign(sun.shadow.camera,{left:-9,right:9,top:9,bottom:-9});sun.shadow.normalBias=.04;this.scene.add(sun);
  this.floor();this.resize=new ResizeObserver(()=>this.size());this.resize.observe(host);this.size();
  this.contextLost=e=>{e.preventDefault();this.fail('3D graphics paused. Reload to restore the arena; live scores remain available.');};this.renderer.domElement.addEventListener('webglcontextlost',this.contextLost);
  this.visibility=()=>{this.clearEffects();this.last=performance.now();};document.addEventListener('visibilitychange',this.visibility);
  this.frame=this.frame.bind(this);this.raf=requestAnimationFrame(this.frame);
 }
 material(color,extra={}){return new THREE.MeshStandardMaterial({color,roughness:.85,flatShading:true,...extra});}
 mesh(parent,geometry,color,position=[0,0,0],scale=[1,1,1],extra={}){const m=new THREE.Mesh(geometry,this.material(color,extra));m.position.set(...position);m.scale.set(...scale);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;}
 ring(parent,radius,color,y=0,width=.025){const m=this.mesh(parent,new THREE.TorusGeometry(radius,width,6,64),color,[0,y,0]);m.rotation.x=Math.PI/2;return m;}
 floor(){
  const g=new THREE.Group();this.scene.add(g);
  this.mesh(g,new THREE.CylinderGeometry(6.6,6.1,.65,12),0x334457,[0,-.4,0]);this.mesh(g,new THREE.CylinderGeometry(6.3,6.3,.1,64),0x233445,[0,-.03,0]);
  this.ring(g,5.8,0x51707e,.04,.035);this.ring(g,4.8,0x3b5364,.04,.018);this.ring(g,1.25,0x77918f,.04,.035);this.ring(g,1.05,0x425b6c,.045,.012);
  for(let i=0;i<8;i++){const a=i*Math.PI/4;const m=this.mesh(g,new THREE.BoxGeometry(.035,.02,.65),0x77918f,[Math.sin(a)*1.65,.03,Math.cos(a)*1.65]);m.rotation.y=a;}
  for(const [i,x] of [-3.1,3.1].entries()){const team=new THREE.Group();team.position.x=x;g.add(team);this.ring(team,1.55,TEAM[i],.045,.035);}
  for(let i=0;i<10;i++){const a=i*Math.PI*2/10;const x=Math.cos(a)*6.1,z=Math.sin(a)*6.1;const c=this.mesh(g,new THREE.ConeGeometry(.16,.65,5),i%2?0x82b7bd:0xc2abe4,[x,.38,z]);c.material.emissive.setHex(i%2?0x365b65:0x4c3265);}
  const ground=this.mesh(g,new THREE.PlaneGeometry(160,160),0x101827,[0,-1.3,0]);ground.rotation.x=-Math.PI/2;
  for(let i=0;i<16;i++){const a=i*2.399,rad=10+(i%4)*2;const stone=this.mesh(g,new THREE.IcosahedronGeometry(.5+(i%3)*.3,0),0x243246,[Math.sin(a)*rad,-.6+(i%4)*.65,Math.cos(a)*rad]);stone.rotation.set(i,.3*i,.5*i);}
 }
 mage(player,slot){
  const root=new THREE.Group(),body=new THREE.Group();root.add(body);this.scene.add(root);const team=player.team,color=TEAM[team],base=new THREE.Vector3(team?3.1:-3.1,0,slot%2?1.65:-1.65);root.position.copy(base);body.rotation.y=team?-Math.PI/2:Math.PI/2;
  const robe=this.mesh(body,new THREE.CylinderGeometry(.35,.65,1.05,9),team?0x795ba5:0x498e87,[0,.88,0]);
  this.mesh(body,new THREE.CylinderGeometry(.38,.63,.12,9),color,[0,.39,0]);this.mesh(body,new THREE.SphereGeometry(.43,14,10),[0xf1c8a2,0xbd8c6b,0xe4ad85,0x925f48][slot%4],[0,1.67,.06],[1,1.05,1]);
  this.mesh(body,new THREE.SphereGeometry(.12,10,8),0xe1aa83,[0,1.64,.46],[.8,.8,1.25]);
  for(const x of [-.17,.17]){this.mesh(body,new THREE.SphereGeometry(.085,10,8),0xfff7e6,[x,1.77,.425],[1,1.2,.5]);this.mesh(body,new THREE.SphereGeometry(.042,8,6),0x1c2435,[x,1.77,.47],[1,1.2,.5]);}
  this.mesh(body,new THREE.ConeGeometry(.27,.52,7),0xe9e1cf,[0,1.37,.34]).rotation.z=Math.PI;
  this.mesh(body,new THREE.CylinderGeometry(.65,.65,.09,14),color,[0,2.02,0]);const hat=this.mesh(body,new THREE.ConeGeometry(.44,.85,9),team?0x9575c9:0x69b7a5,[.04,2.43,0]);hat.rotation.z=-.15;
  const tip=this.mesh(body,new THREE.ConeGeometry(.16,.40,7),color,[.02,2.91,0]);tip.rotation.z=.4;
  this.mesh(body,new THREE.SphereGeometry(.09,8,6),color,[0,1.18,.48]);
  const legs=[];for(const x of [-.25,.25]){const leg=new THREE.Group();leg.position.set(x,.4,0);body.add(leg);this.mesh(leg,new THREE.SphereGeometry(.22,10,8),0x273040,[0,-.22,.12],[.8,.65,1.45]);legs.push(leg);}
  const arms=[];for(const x of [-.48,.48]){const arm=new THREE.Group();arm.position.set(x,1.32,0);body.add(arm);this.mesh(arm,new THREE.CylinderGeometry(.16,.21,.48,8),team?0x795ba5:0x498e87,[0,-.2,0]);this.mesh(arm,new THREE.SphereGeometry(.15,10,8),0xe1aa83,[0,-.45,.06]);arms.push(arm);}
  this.mesh(arms[1],new THREE.CylinderGeometry(.035,.05,1.1,7),0x704b3d,[0,-.05,.22]);const wandTip=this.mesh(arms[1],new THREE.IcosahedronGeometry(.14,0),color,[0,.53,.22],[1,1.3,1],{emissive:color,emissiveIntensity:.6});
  const shield=this.mesh(root,new THREE.SphereGeometry(1.04,20,12),0x6edada,[0,1.28,0],[1,1.3,1],{transparent:true,opacity:.16,depthWrite:false,roughness:.2});shield.visible=false;shield.castShadow=false;
  const shieldRing=this.ring(root,.94,0x86ece4,1.15,.025);shieldRing.rotation.x=0;shieldRing.visible=false;
  const halo=this.ring(root,.64,0xffdc77,3.15,.035);halo.visible=false;
  const curse=new THREE.Group();root.add(curse);for(let i=0;i<3;i++){const a=i*2*Math.PI/3;this.mesh(curse,new THREE.OctahedronGeometry(.12),0xc594ff,[Math.cos(a)*.65,2.7,Math.sin(a)*.65],undefined,{emissive:0x663c99,emissiveIntensity:.8});}curse.visible=false;
  const label=document.createElement('div');label.className='mage-label';label.dataset.team=team;const name=document.createElement('strong'),health=document.createElement('span');label.append(name,health);this.labels.append(label);
  const mage={root,body,base,arms,legs,wandTip,shield,shieldRing,halo,curse,label,name,health,player,slot,castAt:-99,hitAt:-99,castSpell:'bolt'};this.mages.set(player.id,mage);return mage;
 }
 update(state){
  if(this.disposed)return;const previous=this.state;this.state=state;
  if(previous&&(state.round!==previous.round||state.phase==='LOBBY'&&previous.phase!=='LOBBY'))this.clearEffects();
  const present=new Set(state.players.map(p=>p.id));for(const [id,m] of this.mages)if(!present.has(id)){this.disposeObject(m.root);m.label.remove();this.mages.delete(id);}
  const slots=[0,0];for(const p of state.players){const slot=slots[p.team]++ + p.team*2;let m=this.mages.get(p.id);if(m&&m.player.team!==p.team){this.disposeObject(m.root);m.label.remove();this.mages.delete(p.id);m=null;}m=m||this.mage(p,slot);m.player=p;m.slot=slot;m.base.set(p.team?3.1:-3.1,0,slot%2?1.65:-1.65);m.name.textContent=p.name;m.health.textContent=p.hp<=0?'Knocked out':`${Math.ceil(p.hp)} HP · ${Math.floor(p.mana)} mana`;m.label.classList.toggle('is-out',p.hp<=0);}
  for(const event of this.events.consume(state))if(!this.paused&&this.connected&&!document.hidden)this.event(event);
  this.draw(0);
 }
 setConnected(connected){this.connected=connected;if(!connected){this.events.reset();this.clearEffects();}this.draw(0);}
 setPaused(paused){this.paused=paused;this.clearEffects();this.draw(0);}
 event(e){
  const source=this.mages.get(e.caster),target=this.mages.get(e.target);
  if(e.type==='spell_result'&&e.outcome==='cast'&&source){source.castAt=this.time;source.castSpell=e.spell;
   if(e.spell==='bolt'&&target)this.addEffect('bolt',source,target,.4,SPELL.bolt);
   else if(e.spell==='hex'&&target)this.addEffect('hex',source,target,.55,SPELL.hex);
   else if(e.spell==='ward'&&target)this.burst(target,SPELL.ward,10);
   else if(e.spell==='empower')for(const m of this.mages.values())if(m.player.team===source.player.team&&m.player.hp>0)this.burst(m,SPELL.empower,12);
  }
  if(e.type==='spell_result'&&['hit','blocked'].includes(e.outcome)&&target){target.hitAt=this.time;this.effects=this.effects.filter(f=>{if(f.kind==='bolt'&&f.source===source&&f.target===target){this.disposeObject(f.object);return false;}return true;});this.burst(target,e.outcome==='blocked'?SPELL.ward:SPELL.bolt,8);}
  if(e.type==='spell_result'&&e.outcome==='fizzle'&&source)this.burst(source,0x84929f,4);
 }
 addEffect(kind,source,target,duration,color){
  if(this.effects.length>=120)return;const object=new THREE.Group();const orb=this.mesh(object,new THREE.IcosahedronGeometry(kind==='bolt'?.16:.12,1),color,undefined,undefined,{emissive:color,emissiveIntensity:2});for(let i=1;i<4;i++)this.mesh(object,new THREE.SphereGeometry(.1/i,6,6),color,[0,0,-i*.16],undefined,{emissive:color,emissiveIntensity:1});this.scene.add(object);this.effects.push({kind,source,target,duration,color,object,at:this.time,orb});
 }
 burst(mage,color,count){for(let i=0;i<count&&this.effects.length<120;i++){const a=i*Math.PI*2/count;const object=this.mesh(this.scene,new THREE.IcosahedronGeometry(.06+(i%3)*.025),color,[mage.root.position.x,1.4,mage.root.position.z],undefined,{emissive:color,emissiveIntensity:1});this.effects.push({kind:'spark',object,at:this.time,duration:.65,origin:object.position.clone(),velocity:new THREE.Vector3(Math.cos(a)*1.5,.4+(i%4)*.45,Math.sin(a)*1.5)});}}
 frame(now){if(this.disposed)return;const dt=Math.min(.05,(now-this.last)/1000);this.last=now;if(!document.hidden&&!this.paused&&this.connected){this.time+=dt;this.draw(dt);}this.raf=requestAnimationFrame(this.frame);}
 draw(dt){
  if(this.disposed)return;const t=this.time,active=this.connected&&!this.paused;
  for(const m of this.mages.values()){
   const p=m.player,alive=p.hp>0,duel=this.state?.phase==='DUEL'&&alive,cast=active?clamp(1-(t-m.castAt)/.7,0,1):0,hit=active?clamp(1-(t-m.hitAt)/.35,0,1):0;
   const walk=active&&duel ? .14 : 0;const desired=m.base.clone();desired.x+=Math.sin(t*.65+m.slot)*walk+(p.team?-1:1)*Math.sin(cast*Math.PI)*.42;desired.z+=Math.sin(t*.9+m.slot*2)*walk*2;
   m.root.position.lerp(desired,dt?1-Math.exp(-dt*8):1);m.body.position.y=active&&alive?Math.sin(t*2.2+m.slot)*.035:0;m.body.rotation.z=alive?(p.team?-1:1)*hit*.2:1.25;m.body.position.y+=alive?0:-.12;
   m.arms[1].rotation.x=-cast*1.3;m.arms[0].rotation.x=-cast*.4;
   m.legs.forEach((leg,i)=>leg.rotation.x=walk?Math.sin(t*2.5+i*Math.PI)*.15:0);
   if(active&&alive&&this.state?.phase==='MATCH_END'&&this.state.winner===p.team)m.body.position.y+=Math.abs(Math.sin(t*4))*.25;
   const effects=p.effects||{};m.shield.visible=alive&&!!effects.ward;m.shieldRing.visible=m.shield.visible;m.halo.visible=alive&&!!effects.empower;m.curse.visible=alive&&!!effects.hex;m.shield.material.opacity=.13+hit*.17;m.halo.rotation.z=active?Math.sin(t*2)*.1:0;m.curse.rotation.y=t*1.6;
   const projected=m.root.position.clone().add(new THREE.Vector3(0,m.slot%2?3.35:3.95,0)).project(this.camera);m.label.style.transform=`translate(-50%,-100%) translate(${(projected.x*.5+.5)*this.width}px,${(-projected.y*.5+.5)*this.height}px)`;
  }
  for(let i=this.effects.length-1;i>=0;i--){const f=this.effects[i],age=t-f.at,u=age/f.duration;if(u>=1){this.disposeObject(f.object);this.effects.splice(i,1);continue;}
   if(f.kind==='spark'){f.object.position.copy(f.origin).addScaledVector(f.velocity,age);f.object.position.y-=age*age*.5;f.object.scale.setScalar(Math.max(.05,1-u));}
   else{const start=f.source.wandTip.getWorldPosition(new THREE.Vector3()),end=f.target.root.position.clone().add(new THREE.Vector3(0,1.4,0));f.object.position.lerpVectors(start,end,u);f.object.position.y+=Math.sin(u*Math.PI)*(f.kind==='hex'?.8:.2);f.object.lookAt(end);}
  }
  this.renderer.render(this.scene,this.camera);
 }
 size(){if(this.disposed)return;this.width=Math.max(1,this.host.clientWidth);this.height=Math.max(1,this.host.clientHeight);this.camera.aspect=this.width/this.height;this.camera.fov=this.width<650?55:36;this.camera.position.set(...(this.width<650?[10,11,16]:[9,8,12]));this.camera.lookAt(0,.8,0);this.camera.updateProjectionMatrix();this.renderer.setSize(this.width,this.height,false);this.draw(0);}
 disposeObject(object){object.removeFromParent();object.traverse(o=>{o.geometry?.dispose();for(const m of Array.isArray(o.material)?o.material:[o.material])m?.dispose();});}
 clearEffects(){for(const f of this.effects)this.disposeObject(f.object);this.effects=[];}
 fail(message){this.onFailure(message);this.dispose();}
 dispose(){if(this.disposed)return;this.disposed=true;cancelAnimationFrame(this.raf);this.resize?.disconnect();document.removeEventListener('visibilitychange',this.visibility);this.renderer.domElement.removeEventListener('webglcontextlost',this.contextLost);this.clearEffects();this.disposeObject(this.scene);this.renderer.dispose();this.renderer.domElement.remove();this.labels.remove();}
}
