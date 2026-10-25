// Consume each live event once. Joining/reconnecting starts with current state.
export class ArenaEvents {
 constructor(){this.last=null;}
 reset(){this.last=null;}
 consume(state){
  if(this.last===null||state.seq<this.last){this.last=state.seq;return [];}
  const events=(state.events||[]).filter(e=>e.seq>this.last).sort((a,b)=>a.seq-b.seq);
  this.last=Math.max(this.last,state.seq);return events;
 }
}
