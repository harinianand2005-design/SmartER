# SmartER

SmartER is an AI and data science decision-support platform for emergency room overcrowding prediction and resource optimization. It is designed for synthetic or anonymized operational data and does not make autonomous clinical decisions.

## Architecture

The project is organized as a modular monorepo:

- `frontend/`: React + Vite operational dashboard.
- `backend/`: FastAPI service, SQLAlchemy database layer, and versioned API.
- `ml/`: Synthetic data pipeline, preprocessing, feature engineering, trained Phase 4 models, evaluation, and explainability artifacts.
- `dataset/`: Raw and processed synthetic/anonymized data locations.
- `database/`: Database documentation and future migrations.
- `tests/`: Cross-project test organization.
- `docs/`: Architecture and project documentation.

The frontend communicates with the FastAPI backend. The backend owns configuration, persistence, and future prediction services. PostgreSQL is the local development database.

## Technology stack

- Frontend: React, TypeScript, Vite, TailwindCSS, React Router, Axios.
- Backend: Python, FastAPI, Pydantic Settings, SQLAlchemy, PostgreSQL.
- Machine learning: Pandas, NumPy, scikit-learn, XGBoost, statsmodels ARIMA benchmark, and SHAP summaries.
- Development: Docker Compose, Pytest, Ruff, ESLint, and Prettier.

## Setup requirements

- Node.js 20 or newer and npm.
- Python 3.11 or newer.
- Docker Desktop (recommended for PostgreSQL and the full local stack).

Copy `.env.example` to `.env` before running services that need environment configuration. Never commit `.env` or real patient information.

### Database initialization and demo users

With PostgreSQL running and the backend dependencies installed, initialize the schema with:

```powershell
cd backend
python -m app.db.init_db
```

Set the three `DEMO_*_PASSWORD` values in `.env` locally, then seed development users with `python -m app.db.seed`. The command creates one `ADMIN`, `TRIAGE_NURSE`, and `HEALTH_AUTHORITY` account using environment-provided passwords. Credentials are never stored in source control or printed by the application.

The development accounts use these non-personal email addresses:

- `admin@example.com` - `ADMIN`
- `triage@example.com` - `TRIAGE_NURSE`
- `authority@example.com` - `HEALTH_AUTHORITY`

Set passwords only in the local process environment. For PowerShell, use secure prompts rather than adding passwords to a file:

```powershell
$env:DEMO_ADMIN_PASSWORD = Read-Host "Admin demo password"
$env:DEMO_TRIAGE_PASSWORD = Read-Host "Triage demo password"
$env:DEMO_HEALTH_AUTHORITY_PASSWORD = Read-Host "Health authority demo password"
python -m app.db.seed
```

If these email addresses already exist but their passwords are unavailable, the seed command intentionally leaves them unchanged. To manually create missing development accounts or reset passwords without changing roles, run the guarded provisioner inside the already-configured development backend container:

```powershell
docker compose exec -e SMARTER_ALLOW_DEMO_PASSWORD_RESET=true backend python -m app.db.provision_demo_users
```

The command requires typing `RESET SMARTER DEVELOPMENT DEMO ACCOUNTS`, then prompts separately for each account password with input hidden. Passwords must be at least 14 characters, confirmations must match, existing account roles must match the expected role, and inactive accounts are not reactivated. The command refuses production `APP_ENV` values and does nothing unless `SMARTER_ALLOW_DEMO_PASSWORD_RESET=true` is explicitly set in that process. It is never run automatically by application startup or Docker Compose.

For local verification when PostgreSQL/Docker is unavailable, use an ignored SQLite development database only:

```powershell
$env:DATABASE_URL = "sqlite:///./demo_smarter.db"
python -m app.db.init_db
python -m app.db.seed
```

This SQLite override is for local development verification only. PostgreSQL remains the configured shared development database. Demo passwords are hashed with Argon2 before storage.

Authentication uses Argon2 password hashes and short-lived JWT access tokens. The frontend stores the development-session token in browser local storage and clears it on logout.

## How to run

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Health check: `GET /health`. API documentation: `http://localhost:8000/docs`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The dashboard is available at `http://localhost:5173`.

### PostgreSQL and Docker Compose

```powershell
docker compose up --build
```

This starts PostgreSQL, the backend, and the frontend. The backend container uses the database service name internally and the frontend is exposed on port 5173.

### Tests and quality checks

From the repository root, run the backend suite with `.venv\Scripts\python.exe -m pytest -q backend\tests`. Run the ML/data suite with `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe -m pytest --import-mode=importlib -q tests\test_data_pipeline.py tests\test_ml_models.py tests\ml`. Run frontend checks with `Push-Location frontend; npm run lint; npm run build; Pop-Location`.

## Current implementation status

Phases 1-7 foundations are implemented: React/FastAPI/PostgreSQL, role-aware authentication, synthetic dataset and preprocessing pipeline, persisted Phase 4 ML artifacts, authenticated prediction APIs, operational dashboard, and the Phase 7 congestion score/SHAP summary/recommendation/alert intelligence layer. Phase 8 is in progress with analytics over persisted ER metrics and model predictions.

All development data is synthetic or anonymized. The system is operational decision support, not a medical diagnosis or autonomous clinical decision system. Historical analytics only display records actually persisted by existing APIs.

Phase 8 includes authenticated operational metric ingestion using the existing `ERMetric` table. ADMIN and TRIAGE_NURSE can submit observed intervals from Live Monitoring; ADMIN and HEALTH_AUTHORITY can view those persisted intervals in Analytics. Prediction scenario requests remain separate from observed measurements.

Successful combined model assessments from `POST /api/v1/predictions/run` are also appended to `ai_assessments` with aggregate inputs, real model outputs, score/level, timestamp, ER unit, and requesting user. Authorized roles can retrieve history newest-first from `GET /api/v1/predictions/assessments/history` and view it on the Assessment History page. Initialize the additive table with `python -m app.db.init_db` for local databases, or apply `database/migrations/0001_ai_assessments.sql` to an existing PostgreSQL deployment before restarting the backend.

## Phase roadmap

1. Project foundation (complete).
2. Synthetic ER dataset generation and data validation (complete).
3. Preprocessing and feature engineering (complete).
4. Arrival forecasting and overcrowding classification (complete).
5. Prediction API integration (complete).
6. Operational dashboard (complete).
7. Congestion score, SHAP explanations, recommendations, and alerts (complete).
8. Analytics, end-to-end testing, deployment readiness, and final documentation (in progress).