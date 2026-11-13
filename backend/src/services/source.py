from sqlalchemy import select
from fastapi import HTTPException
from src.models import SequenceStudy,ObservationTrace
from src.utils.serialize import row
from .validation import validate_traces,validate_constraints,MAX_STATES
from .audit import record

def create_study(db,data,actor):
 if db.scalar(select(SequenceStudy).where(SequenceStudy.name==data.name)):raise HTTPException(409,'研究名已存在')
 traces=[t.model_dump() for t in data.traces]
 try:validate_traces(data.symbols,traces)
 except ValueError as error:raise HTTPException(422,str(error))
 study=SequenceStudy(**data.model_dump(exclude={'traces'}));db.add(study);db.flush()
 for trace in traces:db.add(ObservationTrace(study_id=study.id,**trace))
 db.commit();record(db,actor,'study.imported',{'study_id':study.id,'traces':len(traces),'constraint_steps':sum(len(t['constraints']) for t in traces)})
 return row(study)

def edit_trace(db,id,data,actor):
 trace=db.get(ObservationTrace,id)
 if not trace:raise HTTPException(404,'轨迹不存在')
 study=db.get(SequenceStudy,trace.study_id)
 # PATCH keeps an untouched field; clearing constraints explicitly requires [].
 tokens=data.tokens if data.tokens is not None else trace.tokens
 constraints=[c.model_dump() for c in data.constraints] if data.constraints is not None else (trace.constraints or [])
 try:
  validate_traces(study.symbols,[dict(row(trace),tokens=tokens,constraints=constraints)])
  validate_constraints(constraints,len(tokens),MAX_STATES)
 except ValueError as error:raise HTTPException(422,str(error))
 changed=[]
 if data.tokens is not None:trace.tokens=tokens;changed.append('tokens')
 if data.constraints is not None:trace.constraints=constraints;changed.append('constraints')
 if not changed:raise HTTPException(422,'PATCH须至少包含tokens或constraints')
 db.commit();record(db,actor,'trace.revised',{'trace_id':id,'fields':changed,'constraint_steps':len(trace.constraints or [])});return row(trace)
