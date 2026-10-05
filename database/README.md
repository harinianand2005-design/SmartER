# Database

PostgreSQL is the development database. SQLAlchemy connection and session infrastructure is available in `backend/app/db/`. Phase 2 provides an explicit `python -m app.db.init_db` initialization command. A migration tool such as Alembic should replace `create_all` before production deployment.

Assessment history adds the `ai_assessments` table. Fresh/local databases create it through `python -m app.db.init_db` because the model is registered in SQLAlchemy metadata. For an existing PostgreSQL deployment managed outside that initializer, apply the additive, idempotent SQL in `database/migrations/0001_ai_assessments.sql` before running the updated backend. The migration only creates the new table and indexes; it does not delete or rewrite existing data.

For the Compose development database, apply/verify the additive schema with `docker compose exec backend python -m app.db.init_db`. This uses SQLAlchemy `create_all(checkfirst)` and does not delete existing rows. Alternatively, a DBA may apply `database/migrations/0001_ai_assessments.sql` directly to the configured PostgreSQL database.

The authenticated combined prediction operation appends its input and actual output JSON, score/level, timestamp, ER-unit identifier, and requesting user in the same transaction as its prediction/resource rows. The history GET endpoint reads those assessment records newest-first.