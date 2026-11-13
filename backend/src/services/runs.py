from sqlalchemy import select
from fastapi import HTTPException
from src.models import ModelProfile,ObservationTrace,InferenceRun
from src.utils.serialize import row
from .validation import validate_constraints,validate_states
from .audit import record

def create_run(db,data,actor):
 profile=db.get(ModelProfile,data.profile_id)
 if not profile or profile.study_id!=data.study_id:raise HTTPException(422,'模型版本不属于该研究')
 ids=data.trace_ids
 if len(ids)!=len(set(ids)):raise HTTPException(422,'轨迹ID不能重复')
 traces=list(db.scalars(select(ObservationTrace).where(ObservationTrace.id.in_(ids),ObservationTrace.study_id==data.study_id).order_by(ObservationTrace.reference)))
 if len(traces)!=len(ids):raise HTTPException(422,'轨迹不属于该研究或不存在')
 if db.scalar(select(InferenceRun).where(InferenceRun.name==data.name)):raise HTTPException(409,'运行名已存在')
 # A mark naming a state index outside this frozen model is rejected before queueing, not as a worker failure.
 K=len(profile.parameters['pi'])
 try:
  validate_states(profile.states,K)
  for trace in traces:validate_constraints(trace.constraints or [],len(trace.tokens),K)
 except ValueError as error:raise HTTPException(422,str(error))
 # Queue freezes the profile and the selected observations together, moment hypotheses included;
 # later edits to the source trace cannot change the queued input.
 snapshot=[dict(row(t),constraints=list(t.constraints or [])) for t in traces]
 run=InferenceRun(study_id=data.study_id,profile_id=profile.id,name=data.name,profile_snapshot=row(profile),trace_snapshot=snapshot,created_by=actor);db.add(run);db.commit()
 try:
  from src.worker import analyze_run
  analyze_run.delay(run.id)
 except Exception:
  run.status='failed';run.error='队列不可用，请稍后重建';db.commit();raise HTTPException(503,run.error)
 record(db,actor,'run.queued',{'run_id':run.id,'traces':len(traces),'constrained_traces':sum(1 for t in snapshot if t['constraints']),'constraint_steps':sum(len(t['constraints']) for t in snapshot)});return row(run)
