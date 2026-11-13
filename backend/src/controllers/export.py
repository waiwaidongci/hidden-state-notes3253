from fastapi import HTTPException
from src.models import InterpretationNote
from src.utils.csv_export import csv_response
from src.services.audit import record

def export_note(db,id,actor):
 note=db.get(InterpretationNote,id)
 if not note:raise HTTPException(404,'说明不存在')
 if note.status!='approved':raise HTTPException(409,'仅批准说明可导出')
 r=note.result_snapshot;rows=[]
 # Frozen runs from before moment hypotheses lack the conditional fields; they export exactly as they were recorded.
 for trace in r['traces']:
  constraints={c['step']:c['allowed_states'] for c in (trace.get('constraints') or [])}
  conditional=trace.get('conditional_posterior')
  for t,token in enumerate(trace['tokens']):
   allowed=constraints.get(t+1)
   step_state=trace['viterbi_path'][t]
   step_marginal=trace['marginal_path'][t]
   rows.append([note.name,r['profile']['name'],r['profile']['version'],r['fingerprint'],trace['reference'],t+1,token,r['states'][step_state],r['states'][step_marginal],str(trace['posterior'][t]),trace['log_likelihood'],trace['viterbi_log_joint'],trace['marginal_path_is_legal'],
    ('约束'+'/'.join(str(s) for s in allowed)) if allowed is not None else '无约束',
    r['states'][trace['conditional_viterbi_path'][t]] if conditional else '—',
    r['states'][trace['conditional_marginal_path'][t]] if conditional else '—',
    str(conditional[t]) if conditional else '—',
    trace['conditional_log_likelihood'] if conditional else '—',
    trace['constraint_probability'] if (conditional and trace.get('constraint_probability') is not None) else ('真实0' if conditional else '—'),
    '满足' if (conditional and trace.get('constraint_status')=='satisfied') else ('冲突/首个无可行步'+str(trace['constraint_conflict']['first_infeasible_step']) if trace.get('constraint_status')=='conflict' else ('无约束' if not conditional else '—')),
    note.interpretation,note.next_step,note.review_note])
 record(db,actor,'note.exported',{'note_id':id});return csv_response(f'hmm-note-{id}.csv',rows,['核对说明','固定模型','版本','指纹','轨迹','步号','观测码','Viterbi联合MAP','单点最高态','边际后验向量','序列logL','Viterbi联合logP','边际路径合法','本步隐态约束','条件联合MAP','条件单点最高态','条件边际后验向量','条件logL','约束成立概率','约束状态','人工解释','下一步','审核意见'])
