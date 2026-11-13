"""小序列穷举核对：把逐时刻隐态约束的前向后向、条件后验、条件Viterbi与冲突定位
直接和全部路径枚举对比。仅依赖 numpy/scipy，不连数据库。

运行：python -m scripts.verify_constrained  （在 backend 目录，已安装 requirements）
"""
import itertools,math,random,sys

import numpy as np

from src.services.hmm import ImpossibleSequence,infer_sequence
from src.services.parameters import normalize_parameters


def _normalized(pi,A,B):
 norm=normalize_parameters(pi,A,B)
 return np.array(norm['pi']),np.array(norm['transition']),np.array(norm['emission'])


def _path_scores(pi,A,B,obs,marks):
 p,AA,BB=_normalized(pi,A,B);K=len(p);scores={}
 for path in itertools.product(range(K),repeat=len(obs)):
  if any(marks[t] is not None and path[t] not in marks[t] for t in range(len(obs))):continue
  value=p[path[0]]*BB[path[0],obs[0]]
  for t in range(1,len(obs)):value*=AA[path[t-1],path[t]]*BB[path[t],obs[t]]
  scores[path]=value
 return scores


def _prefix_feasible(pi,A,B,obs,marks,prefix,use_emission):
 p,AA,BB=_normalized(pi,A,B)
 for path in itertools.product(range(len(p)),repeat=prefix):
  if any(marks[t] is not None and path[t] not in marks[t] for t in range(prefix)):continue
  value=1.0 if use_emission else 1.0
  value=p[path[0]]*(BB[path[0],obs[0]] if use_emission else 1.0)
  for t in range(1,prefix):value*=AA[path[t-1],path[t]]*(BB[path[t],obs[t]] if use_emission else 1.0)
  if value>0:return True
 return False


def _first_infeasible(pi,A,B,obs,marks,use_emission):
 for step in range(1,len(obs)+1):
  if not _prefix_feasible(pi,A,B,obs,marks,step,use_emission):return step
 return None


def check_case(pi,A,B,obs,marks,tolerance=1e-9):
 constraints=[{'step':t+1,'allowed_states':sorted(marks[t])} for t in range(len(obs)) if marks[t] is not None]
 result=infer_sequence(obs,pi,A,B,constraints)
 if not constraints:
  assert result['constraint_mode']=='unconstrained' and result['constraint_status']=='unconstrained'
  return 'unconstrained'
 full=_path_scores(pi,A,B,obs,[None]*len(obs));masked=_path_scores(pi,A,B,obs,marks)
 unl=math.fsum(full.values());cond=math.fsum(masked.values())
 if cond==0:
  assert result['constraint_status']=='conflict',result['constraint_status']
  expected_first=_first_infeasible(pi,A,B,obs,marks,True)
  model_first=_first_infeasible(pi,A,B,obs,marks,False)
  assert result['constraint_conflict']['first_infeasible_step']==expected_first,(result['constraint_conflict'],expected_first)
  assert result['constraint_conflict']['stage']==('model' if model_first==expected_first else 'observation'),result['constraint_conflict']
  assert result['constraint_probability']==0.0 and result['constraint_probability_is_true_zero'] is True
  return 'conflict'
 assert result['constraint_status']=='satisfied',result['constraint_status']
 assert abs(math.exp(result['log_likelihood'])-unl)<=tolerance
 assert abs(math.exp(result['conditional_log_likelihood'])-cond)<=tolerance
 assert abs(math.exp(result['constraint_log_probability'])-cond/unl)<=tolerance
 posterior=np.array(result['conditional_posterior'])
 for t in range(len(obs)):
  for s in range(len(pi)):
   expected=math.fsum(v for path,v in masked.items() if path[t]==s)/cond
   assert abs(posterior[t][s]-expected)<tolerance,(t,s,posterior[t][s],expected)
  assert abs(posterior[t].sum()-1)<tolerance
 best=max(masked.values());ties=[path for path,v in masked.items() if v==best]
 assert tuple(result['conditional_viterbi_path'])==min(ties),(result['conditional_viterbi_path'],min(ties))
 assert abs(math.exp(result['conditional_viterbi_log_joint'])-best)<=tolerance
 marginal=result['conditional_marginal_path'];legal=all(marks[t] is None or marginal[t] in marks[t] for t in range(len(obs)))
 assert legal==result['conditional_marginal_path_is_legal']
 assert result['constraint_probability_is_true_zero'] is False
 return 'ok'


def random_case(rng):
 K=rng.choice([2,3]);T=rng.randint(1,4);M=rng.randint(2,3)
 pi=[rng.random() for _ in range(K)];pi=[v/sum(pi) for v in pi]
 A=[[rng.random() for _ in range(K)] for _ in range(K)];A=[[v/sum(row) for v in row] for row in A]
 B=[[rng.random() for _ in range(M)] for _ in range(K)];B=[[v/sum(row) for v in row] for row in B]
 for i in range(K):
  if rng.random()<0.4:
   j=rng.randrange(M);B[i][j]=0.0;B[i]=[v/sum(B[i]) for v in B[i]]
 obs=[rng.randrange(M) for _ in range(T)]
 marks=[set(rng.sample(range(K),rng.randint(1,K))) if rng.random()<0.5 else None for _ in range(T)]
 return pi,A,B,obs,marks


def main(trials=300,seed=7):
 rng=random.Random(seed);counts={}
 for _ in range(trials):
  pi,A,B,obs,marks=random_case(rng)
  try:status=check_case(pi,A,B,obs,marks)
  except ImpossibleSequence:status='unconstrained-impossible'
  counts[status]=counts.get(status,0)+1
 print(counts)
 ok=sum(counts.get(status,0) for status in ('ok','conflict','unconstrained','unconstrained-impossible'))
 if ok!=trials:raise SystemExit(f'exhaustive mismatch: {counts}')
 print('exhaustive cross-check passed')

if __name__=='__main__':main(*(int(a) for a in sys.argv[1:]))
