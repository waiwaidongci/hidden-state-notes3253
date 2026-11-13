from datetime import datetime,date
from sqlalchemy import inspect
def row(obj):
 values={c.key:(getattr(obj,c.key).isoformat() if isinstance(getattr(obj,c.key),(datetime,date)) else getattr(obj,c.key)) for c in inspect(obj).mapper.column_attrs if c.key!='password_hash'}
 # Legacy observations upgraded in place have no moment hypotheses; the API always exposes an array.
 if 'constraints' in values and values['constraints'] is None:values['constraints']=[]
 return values
