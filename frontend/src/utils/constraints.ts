// Moment marks travel with the observation and are frozen with the queue.
// Text form: `2:0,1; 4:2` — 1-based step, 0-based state indexes. Empty text means no marks.
export type MomentMark={step:number;allowed_states:number[]};
export function formatMarks(marks:MomentMark[]|null|undefined):string{
 if(!marks||!marks.length)return '';
 return marks.slice().sort((a,b)=>a.step-b.step).map(m=>`${m.step}:${m.allowed_states.join(',')}`).join('; ');
}
export function parseMarks(text:string,tokenCount:number,stateCount:number):MomentMark[]{
 const trimmed=text.trim();if(!trimmed)return [];
 const result:MomentMark[]=[];const seen=new Set<number>();
 for(const part of trimmed.split(/[;；\n]/)){
  const chunk=part.trim();if(!chunk)continue;
  const match=chunk.match(/^(\d+)\s*[:：]\s*([0-9,\s]+)$/);
  if(!match)throw Error(`无法解析“${chunk}”，应形如 2:0,1`);
  const step=Number(match[1]);
  if(!Number.isInteger(step)||step<1||step>tokenCount)throw Error(`步号须为1..${tokenCount}的整数`);
  if(seen.has(step))throw Error(`第${step}步重复标记`);
  seen.add(step);
  const states=match[2].split(/[,\s]+/).filter(Boolean).map(Number);
  if(!states.length||states.length>5)throw Error('每步须标记1..5个状态索引');
  if(states.some(s=>!Number.isInteger(s)||s<0||s>=stateCount))throw Error(`状态索引须在0..${stateCount-1}`);
  if(new Set(states).size!==states.length)throw Error('同一时刻状态索引不能重复');
  result.push({step,allowed_states:states});
 }
 return result.sort((a,b)=>a.step-b.step);
}
