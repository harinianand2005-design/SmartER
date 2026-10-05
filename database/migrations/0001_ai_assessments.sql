-- Additive PostgreSQL migration for append-only AI assessment history.
-- Safe to run repeatedly; it does not alter or delete existing records.
CREATE TABLE IF NOT EXISTS ai_assessments (
    id SERIAL PRIMARY KEY,
    er_unit_id VARCHAR(80) NOT NULL,
    requested_by_user_id INTEGER NOT NULL REFERENCES users(id),
    assessment_timestamp TIMESTAMPTZ NOT NULL,
    input_payload JSON NOT NULL,
    prediction_payload JSON NOT NULL,
    congestion_score DOUBLE PRECISION NOT NULL,
    congestion_level VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_ai_assessments_er_unit_id ON ai_assessments (er_unit_id);
CREATE INDEX IF NOT EXISTS ix_ai_assessments_requested_by_user_id ON ai_assessments (requested_by_user_id);
CREATE INDEX IF NOT EXISTS ix_ai_assessments_assessment_timestamp ON ai_assessments (assessment_timestamp);
CREATE INDEX IF NOT EXISTS ix_ai_assessments_created_at ON ai_assessments (created_at);