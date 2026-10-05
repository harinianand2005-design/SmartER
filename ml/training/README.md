# Phase 4 training

Run `python -m ml.training.run_all` from the repository root after Phase 3 processed data exists. Model selection uses validation metrics only; the untouched test split is evaluated once after selection. Artifacts are saved under `ml/models/`, evaluation figures and JSON reports under `ml/evaluation/outputs/`, and optional SHAP summaries under `ml/explainability/outputs/`.

These artifacts are for academic decision-support experimentation. They are not medical diagnoses or autonomous clinical decisions.# ML training