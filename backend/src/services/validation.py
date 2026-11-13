MAX_STATES=5

def validate_symbols(symbols):
 if not 2<=len(symbols)<=6 or len(set(symbols))!=len(symbols) or any(not isinstance(s,str) or not s.strip() or len(s)>80 for s in symbols):raise ValueError('声明2..6个唯一非空观测码')

def validate_traces(symbols,traces):
 validate_symbols(symbols)
 if not 1<=len(traces)<=240 or len({t['reference'] for t in traces})!=len(traces):raise ValueError('研究需1..240条唯一轨迹')
 for trace in traces:
  if not 1<=len(trace['tokens'])<=200 or any(type(s) is not str or s not in symbols for s in trace['tokens']):raise ValueError('轨迹须1..200个已声明观测码')
  # Marks are stored on the observation before any model version exists, so only the universal state cap applies here;
  # queueing then validates each mark against the frozen model's actual state count.
  validate_constraints(trace.get('constraints'),len(trace['tokens']),MAX_STATES)

def validate_constraints(constraints,token_count,state_count=None):
 # Moment hypotheses: explicit, unambiguous, inside the trace and inside the state space.
 if constraints is None:return []
 if not isinstance(constraints,list) or len(constraints)>token_count:raise ValueError('约束须为不超过步数的数组')
 if state_count is not None and not 2<=state_count<=5:raise ValueError('状态维度须为2..5')
 seen=set();normalized=[]
 for item in constraints:
  if not isinstance(item,dict):raise ValueError('每条约束须是含step与allowed_states的对象')
  if set(item)!={'step','allowed_states'}:raise ValueError('约束只接受step与allowed_states两个字段')
  step=item['step']
  if type(step) is not int or step<1 or step>token_count:raise ValueError('约束步号须为1..轨迹长度的整数')
  if step in seen:raise ValueError(f'第{step}步的约束重复')
  seen.add(step);allowed=item['allowed_states']
  if not isinstance(allowed,list) or not 1<=len(allowed)<=5:raise ValueError('allowed_states须为1..5个状态索引')
  if any(type(s) is not int for s in allowed):raise ValueError('状态索引须为整数')
  if state_count is not None and any(s<0 or s>=state_count for s in allowed):raise ValueError('状态索引超出固定模型维度')
  if len(set(allowed))!=len(allowed):raise ValueError('同一时刻状态索引不能重复')
  if any(s<0 or s>=MAX_STATES for s in allowed):raise ValueError(f'状态索引须在0..{MAX_STATES-1}')
  normalized.append({'step':step,'allowed_states':allowed})
 return normalized

def validate_states(states,K):
 if len(states)!=K or len(set(states))!=len(states) or any(not isinstance(s,str) or not s.strip() or len(s)>80 for s in states):raise ValueError('状态标签须与π维度相同且唯一非空')
