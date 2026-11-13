import json,hashlib
VERSION='fixed-hmm-log-fb-viterbi-v1'
CONSTRAINED_VERSION='fixed-hmm-constrained-conditional-v2'
def fingerprint(profile,traces):
 # Unconstrained payloads keep the historical v1 bytes so upgraded data and re-runs remain comparable;
 # any marked moment switches to the conditional algorithm version.
 constrained=any(t.get('constraints') for t in traces)
 version=CONSTRAINED_VERSION if constrained else VERSION
 cleaned=[]
 for t in traces:
  item=dict(t)
  if version==VERSION:item.pop('constraints',None)
  cleaned.append(item)
 payload={'version':version,'profile':profile,'traces':sorted(cleaned,key=lambda t:t['reference'])}
 return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
