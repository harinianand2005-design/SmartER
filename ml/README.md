# Machine Learning Workspace

Phase 3 provides the reproducible data foundation. Training, forecasting, classification, resource prediction, and SHAP explainability are intentionally not implemented yet.

From the repository root:

```powershell
C:/Users/harin/AppData/Local/Programs/Python/Python310/python.exe -m ml.data.generator
C:/Users/harin/AppData/Local/Programs/Python/Python310/python.exe -m ml.scripts.prepare_dataset
C:/Users/harin/AppData/Local/Programs/Python/Python310/python.exe -m ml.scripts.eda
```

The pipeline generates synthetic hourly data, validates it, creates past-only features and future labels, fits preprocessing values on training data only, exports chronological splits, and writes EDA figures plus a measured summary. See `docs/data_dictionary.md` for the field contract.