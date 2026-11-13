from sqlalchemy import inspect,text
from src.config.database import engine
from src.models import ObservationTrace

MOMENT_SQL="ALTER TABLE observation_traces ADD COLUMN constraints JSON NULL"

def ensure_moment_constraints():
 # create_all only creates missing tables; upgraded databases need the nullable JSON column added in place.
 # Existing rows stay NULL = no moment hypotheses, so old observations view and infer unconstrained until marked.
 table='observation_traces'
 columns={c['name'] for c in inspect(engine).get_columns(table)}
 if 'constraints' in columns:return False
 with engine.begin() as connection:connection.execute(text(MOMENT_SQL))
 return True
