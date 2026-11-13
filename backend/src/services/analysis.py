import math
from .hmm import infer_sequence,ImpossibleSequence
from .validation import validate_traces,validate_states,validate_constraints
from .fingerprint import fingerprint,CONSTRAINED_VERSION,VERSION as LEGACY_VERSION

def _trace_mode(trace):return 'conditional' if trace.get('constraints') else 'unconstrained'

def analyze(profile,traces):
 if not 1<=len(traces)<=30:raise ValueError('单次须选择1..30条轨迹')
 parameters=profile['parameters'];K=len(parameters['pi']);validate_traces(profile['symbols'],traces);validate_states(profile['states'],K)
 lookup={symbol:i for i,symbol in enumerate(profile['symbols'])};results=[]
 for trace in sorted(traces,key=lambda t:t['reference']):
  constraints=validate_constraints(trace.get('constraints'),len(trace['tokens']),K)
  try:inferred=infer_sequence([lookup[s] for s in trace['tokens']],parameters['pi'],parameters['transition'],parameters['emission'],constraints)
  except ImpossibleSequence as error:raise ImpossibleSequence(f'{trace["reference"]}：{error}') from error
  results.append({'id':trace['id'],'reference':trace['reference'],'tokens':trace['tokens'],'constraints':constraints,**inferred})
 conditional=[r for r in results if r['constraints']]
 satisfied=[r for r in conditional if r['constraint_status']=='satisfied'];conflicts=[r for r in conditional if r['constraint_status']=='conflict']
 # Task-level result stays descriptive: per-trace conditionals are retained, but no aggregate mixes them with the unconditional totals.
 return {'profile':profile,'states':profile['states'],'symbols':profile['symbols'],'trace_count':len(results),'token_count':sum(len(r['tokens']) for r in results),'total_log_likelihood':math.fsum(r['log_likelihood'] for r in results),'illegal_marginal_paths':sum(not r['marginal_path_is_legal'] for r in results),'constrained_trace_count':len(conditional),'unconstrained_trace_count':len(results)-len(conditional),'constraint_satisfied_trace_count':len(satisfied),'constraint_conflict_trace_count':len(conflicts),'conditional_total_log_likelihood':math.fsum(r['conditional_log_likelihood'] for r in satisfied) if satisfied else None,'constraint_conflict_total_log_likelihood':math.fsum(r['log_likelihood'] for r in conflicts) if conflicts else None,'constraint_conflicts':[{'id':r['id'],'reference':r['reference'],'first_infeasible_step':r['constraint_conflict']['first_infeasible_step'],'stage':r['constraint_conflict']['stage'],'reason':r['constraint_conflict']['reason']} for r in conflicts],'traces':results,'fingerprint':fingerprint(profile,traces),'fingerprint_version':CONSTRAINED_VERSION if conditional else LEGACY_VERSION,'legacy_fingerprint_version':LEGACY_VERSION,'constraint_mode':'mixed' if conditional and len(conditional)!=len(results) else ('conditional' if conditional else 'unconstrained'),'legal_marginal_paths':len(results)-sum(not r['marginal_path_is_legal'] for r in results),'interpretation':'Fixed HMM parameters, no EM or fitting. Marginal argmax can violate legal transitions; Viterbi is the full joint MAP path. Marked moment hypotheses condition only that trace\'s posterior and joint path on the same fixed π/A/B; unconstrained likelihoods and conditional masses are reported separately. States are model labels, not equipment-fault facts or online alarms.'}
