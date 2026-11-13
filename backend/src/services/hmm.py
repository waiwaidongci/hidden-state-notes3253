import numpy as np
from scipy.special import logsumexp
from .parameters import normalize_parameters
from .validation import validate_constraints

class ImpossibleSequence(ValueError):pass

def log_probabilities(a):
 a=np.asarray(a,dtype=float);out=np.full(a.shape,-np.inf);positive=a>0;out[positive]=np.log(a[positive]);return out

def json_logs(a):return [[float(v) if np.isfinite(v) else None for v in row] for row in a]

def _codes(observations,n_symbols):
 obs=np.asarray(observations)
 if obs.ndim!=1 or not 1<=len(obs)<=200 or not np.issubdtype(obs.dtype,np.integer) or np.issubdtype(obs.dtype,np.bool_) or (obs<0).any() or (obs>=n_symbols).any():raise ValueError('观测须1..200个合法整数码索引')
 return obs.astype(int)

def _masks(constraints,T,K):
 allowed=np.ones((T,K),dtype=bool)
 for item in constraints:
  row=allowed[item['step']-1];row[:]=False;row[item['allowed_states']]=True
 return allowed

def _linear(logv):
 # A real zero has log=-inf; a finite log that exponentiates to 0 is numeric underflow, not an impossibility.
 if logv is None or not np.isfinite(logv):return None,False,True
 with np.errstate(under='ignore'):value=float(np.exp(logv))
 if value>0:return value,False,False
 return None,True,False

def _joint(path,lp,lA,lB,obs):
 value=lp[path[0]]+lB[path[0],obs[0]]
 for t in range(1,len(obs)):value+=lA[path[t-1],path[t]]+lB[path[t],obs[t]]
 return float(value)

def _forward(lp,lA,lB,obs,masks,use_emission=True):
 T=len(obs);K=lA.shape[0];alpha=np.full((T,K),-np.inf);alpha[0]=lp.copy() if not use_emission else lp+lB[:,obs[0]];alpha[0][~masks[0]]=-np.inf
 if not np.isfinite(alpha[0]).any():return alpha,0
 for t in range(1,T):
  row=logsumexp(alpha[t-1,:,None]+lA,axis=0)
  if use_emission:row=row+lB[:,obs[t]]
  row[~masks[t]]=-np.inf;alpha[t]=row
  if not np.isfinite(row).any():return alpha,t
 return alpha,None

def _backward(lA,lB,obs,masks,use_emission=True):
 T=len(obs);K=lA.shape[0];beta=np.zeros((T,K))
 for t in range(T-2,-1,-1):
  candidates=lA.copy()
  if use_emission:candidates+=lB[:,obs[t+1]][None,:]
  candidates+=beta[t+1][None,:];candidates[:,~masks[t+1]]=-np.inf;beta[t]=logsumexp(candidates,axis=1)
 return beta

def _posterior(alpha,beta,likelihood):
 with np.errstate(under='ignore'):posterior=np.exp(alpha+beta-likelihood)
 posterior/=posterior.sum(axis=1,keepdims=True)
 return posterior

def _viterbi(lp,lA,lB,obs,masks):
 T=len(obs);K=lA.shape[0]
 # Exact log-score ties keep the lexicographically smallest full state-index path; masked states never participate.
 score=lp+lB[:,obs[0]];score[~masks[0]]=-np.inf
 paths=[(j,) if np.isfinite(score[j]) else None for j in range(K)]
 for t in range(1,T):
  nextscore=np.full(K,-np.inf);nextpaths=[None]*K
  for j in range(K):
   if not masks[t,j]:continue
   candidates=score+lA[:,j]+lB[j,obs[t]];best=float(candidates.max())
   if not np.isfinite(best):continue
   tied=[i for i in range(K) if candidates[i]==best and paths[i] is not None]
   previous=min(tied,key=lambda i:paths[i]);nextscore[j]=best;nextpaths[j]=paths[previous]+(j,)
  score=nextscore;paths=nextpaths
 best=float(score.max())
 if not np.isfinite(best):return None,-np.inf
 terminal=min((j for j in range(K) if score[j]==best),key=lambda j:paths[j]);return list(paths[terminal]),best

def _satisfies(path,masks):
 return path is not None and all(bool(masks[t,path[t]]) for t in range(len(path)))

def _conflict(step,masks,obs,lB,stage,unconstrained_likelihood,prior_log,prior_probability,prior_under,prior_true_zero):
 allowed=[int(s) for s in np.flatnonzero(masks[step])];detail={'step':step+1,'allowed_states':allowed,'observation_index':int(obs[step])}
 emission_impossible=not any(np.isfinite(lB[s,obs[step]]) for s in allowed)
 if stage=='model':detail['reason']='constraint_excludes_model_path'
 elif emission_impossible:detail['reason']='emission_zero_at_marked_step'
 else:detail['reason']='no_legal_transition_into_marked_step'
 conflict={'first_infeasible_step':step+1,'stage':stage,'reason':detail['reason'],'detail':detail,
  'unconstrained_log_likelihood':unconstrained_likelihood,'constraint_prior_log_probability':prior_log,'constraint_prior_probability':prior_probability,
  'constraint_prior_probability_underflows':prior_under,'constraint_prior_probability_is_true_zero':prior_true_zero,
  'constraint_probability':0.0,'constraint_probability_is_true_zero':True,'constraint_probability_underflows':False}
 return conflict

def infer_sequence(observations,pi,transition,emission,constraints=None):
 normalized=normalize_parameters(pi,transition,emission);p=np.asarray(normalized['pi']);A=np.asarray(normalized['transition']);B=np.asarray(normalized['emission']);K=len(p)
 obs=_codes(observations,B.shape[1]);T=len(obs);lp=log_probabilities(p);lA=log_probabilities(A);lB=log_probabilities(B)
 constraints=validate_constraints(constraints,T,K);allowed=_masks(constraints,T,K);everything=np.ones((T,K),dtype=bool)
 # The unconstrained reference is always computed on the complete path set, regardless of any marks on this trace.
 alpha=np.full((T,K),-np.inf);alpha[0]=lp+lB[:,obs[0]]
 if not np.isfinite(alpha[0]).any():raise ImpossibleSequence('不可能序列：第1码在固定模型下概率为0')
 for t in range(1,T):
  alpha[t]=logsumexp(alpha[t-1,:,None]+lA,axis=0)+lB[:,obs[t]]
  if not np.isfinite(alpha[t]).any():raise ImpossibleSequence(f'不可能序列：到第{t+1}码所有路径概率为0')
 likelihood=float(logsumexp(alpha[-1]));beta=_backward(lA,lB,obs,everything);posterior=_posterior(alpha,beta,likelihood)
 marginal=np.argmax(posterior,axis=1).astype(int).tolist();viterbi,best=_viterbi(lp,lA,lB,obs,everything);marginal_joint=_joint(marginal,lp,lA,lB,obs)
 linear_probability,linear_underflow,_=_linear(likelihood)
 result={'log_likelihood':likelihood,'likelihood_if_representable':linear_probability,'linear_likelihood_underflows':linear_underflow,'posterior':posterior.tolist(),
  'marginal_path':marginal,'marginal_path_is_legal':bool(np.isfinite(marginal_joint)),'marginal_log_joint':marginal_joint if np.isfinite(marginal_joint) else None,
  'viterbi_path':viterbi,'viterbi_log_joint':best,'log_forward':json_logs(alpha),'log_backward':json_logs(beta),
  'null_log_meaning':'null in log arrays means exact zero probability (-infinity), not missing data',
  'tie_rule':'Exact floating log-score ties choose lexicographically smallest full state-index path; marginal ties choose smallest state index.',
  'normalization':normalized['normalization'],'constraints':constraints,'constraint_mode':'conditional' if constraints else 'unconstrained',
  'constraint_status':'satisfied' if constraints else 'unconstrained','constraint_conflict':None,
  'constraint_prior_log_probability':None,'constraint_prior_probability':None,'constraint_prior_probability_underflows':False,'constraint_prior_probability_is_true_zero':None,
  'constraint_log_probability':None,'constraint_probability':None,'constraint_probability_underflows':False,'constraint_probability_is_true_zero':None,
  'conditional_log_likelihood':None,'conditional_likelihood_if_representable':None,'conditional_likelihood_underflows':False,
  'conditional_posterior':None,'conditional_marginal_path':None,'conditional_marginal_path_is_legal':None,'conditional_marginal_log_joint':None,
  'conditional_viterbi_path':None,'conditional_viterbi_log_joint':None,'conditional_log_forward':None,'conditional_log_backward':None,
  'constraint_interpretation':'No moment hypotheses are marked; probabilities above use the complete fixed-model path set.'}
 if not constraints:return result
 # Conditional forward failure is the first step with no feasible path under the fixed model *and* observations.
 # The π/A-only forward ignores emissions: if it dies at the same step, the model itself excludes the marks.
 conditional_alpha,conditional_failure=_forward(lp,lA,lB,obs,allowed,use_emission=True)
 prior_alpha,prior_failure=_forward(lp,lA,lB,obs,allowed,use_emission=False)
 prior_log=float(logsumexp(prior_alpha[-1])) if prior_failure is None else None
 if prior_log is not None:prior_probability,prior_underflow,prior_true_zero=_linear(prior_log)
 else:prior_probability,prior_underflow,prior_true_zero=0.0,False,True
 result.update({'constraint_prior_log_probability':prior_log,'constraint_prior_probability':prior_probability,
  'constraint_prior_probability_underflows':prior_underflow,'constraint_prior_probability_is_true_zero':prior_true_zero})
 if conditional_failure is not None:
  stage='model' if prior_failure==conditional_failure else 'observation'
  result.update({'constraint_status':'conflict','constraint_conflict':_conflict(conditional_failure,allowed,obs,lB,stage,likelihood,prior_log,prior_probability,prior_underflow,prior_true_zero),
   'constraint_probability':0.0,'constraint_probability_is_true_zero':True,'constraint_probability_underflows':False})
  return result
 # Posterior, marginal and Viterbi below all live inside the marked path set; their masses are conditional, not rescaled unconstrained values.
 conditional_likelihood=float(logsumexp(conditional_alpha[-1]));conditional_beta=_backward(lA,lB,obs,allowed);conditional_posterior=_posterior(conditional_alpha,conditional_beta,conditional_likelihood)
 conditional_marginal=np.argmax(conditional_posterior,axis=1).astype(int).tolist();conditional_viterbi,conditional_best=_viterbi(lp,lA,lB,obs,allowed)
 conditional_marginal_joint=_joint(conditional_marginal,lp,lA,lB,obs);conditional_marginal_legal=bool(np.isfinite(conditional_marginal_joint) and _satisfies(conditional_marginal,allowed))
 constraint_log=conditional_likelihood-likelihood;constraint_probability,constraint_underflow,constraint_true_zero=_linear(constraint_log)
 conditional_probability,conditional_underflow,_=_linear(conditional_likelihood)
 result.update({'constraint_log_probability':constraint_log,'constraint_probability':constraint_probability,'constraint_probability_underflows':constraint_underflow,'constraint_probability_is_true_zero':constraint_true_zero,
  'conditional_log_likelihood':conditional_likelihood,'conditional_likelihood_if_representable':conditional_probability,'conditional_likelihood_underflows':conditional_underflow,
  'conditional_posterior':conditional_posterior.tolist(),'conditional_marginal_path':conditional_marginal,'conditional_marginal_path_is_legal':conditional_marginal_legal,
  'conditional_marginal_log_joint':conditional_marginal_joint if np.isfinite(conditional_marginal_joint) else None,
  'conditional_viterbi_path':conditional_viterbi,'conditional_viterbi_log_joint':conditional_best,
  'conditional_log_forward':json_logs(conditional_alpha),'conditional_log_backward':json_logs(conditional_beta),
  'conditional_interpretation':'Conditional posterior sums paths that satisfy the marked moment hypotheses at those steps; conditional Viterbi is the joint MAP inside the same constrained path set. Unconstrained likelihood and paths are kept for comparison, and constraint_probability is P(marked hypothesis | observations).'})
 return result
