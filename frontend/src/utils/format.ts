export const fmt=(n:number,d=5)=>Number.isFinite(n)?n.toLocaleString('zh-CN',{maximumFractionDigits:d}):'—';export const clock=(v:string)=>new Date(v).toLocaleString('zh-CN',{hour12:false});
// True zero, numeric underflow and ordinary probability stay visibly distinct in the UI.
export const prob=(value:number|null|undefined,options:{underflows?:boolean;trueZero?:boolean|null}={})=>{
 if(options.trueZero)return '真实0（无可行路径）';
 if(options.underflows)return '数值下溢（log域有限）';
 if(value===null||value===undefined||!Number.isFinite(value))return '—';
 const abs=Math.abs(value);
 if(abs===0)return '0';
 if(abs<1e-4||abs>=1e6)return value.toExponential(6);
 return value.toLocaleString('zh-CN',{maximumFractionDigits:6});
};
export const constraintReason=(reason:string)=>CONSTRAINT_REASONS[reason]||reason;
export const CONSTRAINT_REASONS:Record<string,string>={constraint_excludes_model_path:'固定π/A下该时刻无可行状态路径（模型层面）',emission_zero_at_marked_step:'被标记状态在该步发射观测码的真实概率为0',no_legal_transition_into_marked_step:'观测与标记共同排除进入该步的全部合法转移'};
