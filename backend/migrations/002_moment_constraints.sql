-- 002: per-observation moment hypotheses for conditional inference.
-- Applied in place by src.config.schema.ensure_moment_constraints() on startup.
-- NULL means a legacy observation: it is viewed and inferred exactly as before (unconstrained).
ALTER TABLE observation_traces ADD COLUMN constraints JSON NULL;
