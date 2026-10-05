from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# 1. File paths
ML_DIR = Path(__file__).resolve().parent
DATA_PATH = ML_DIR / "Hospital_ER_Data_Cleaned.csv"
MODEL_PATH = ML_DIR / "smarter_waittime_model.joblib"


# 2. Load dataset
df = pd.read_csv(DATA_PATH)

print("Dataset loaded:", df.shape)


# 3. Prepare data
df["patient_admission_date"] = pd.to_datetime(
    df["patient_admission_date"],
    errors="coerce"
)

df["patient_waittime"] = pd.to_numeric(
    df["patient_waittime"],
    errors="coerce"
)

df = df.dropna(
    subset=["patient_admission_date", "patient_waittime"]
).copy()


# 4. Sort chronologically
df = df.sort_values(
    "patient_admission_date"
).reset_index(drop=True)


# 5. Create time features
df["hour"] = df["patient_admission_date"].dt.hour
df["day_of_week"] = df["patient_admission_date"].dt.dayofweek
df["month"] = df["patient_admission_date"].dt.month
df["is_weekend"] = (
    df["day_of_week"] >= 5
).astype(int)


# 6. Features
categorical_features = [
    "patient_gender",
    "patient_race",
    "department_referral",
]

numeric_features = [
    "patient_age",
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
]

features = categorical_features + numeric_features

X = df[features]
y = df["patient_waittime"]


# 7. Chronological 80/20 split
split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

print("Training records:", len(X_train))
print("Testing records:", len(X_test))


# 8. Preprocessing
preprocessor = ColumnTransformer([
    (
        "categorical",
        Pipeline([
            (
                "imputer",
                SimpleImputer(strategy="most_frequent")
            ),
            (
                "encoder",
                OneHotEncoder(handle_unknown="ignore")
            ),
        ]),
        categorical_features,
    ),
    (
        "numeric",
        SimpleImputer(strategy="median"),
        numeric_features,
    ),
])


# 9. Random Forest model
model = Pipeline([
    ("preprocessor", preprocessor),
    (
        "regressor",
        RandomForestRegressor(
            n_estimators=100,
            random_state=42,
            n_jobs=-1,
        ),
    ),
])


# 10. Train model
print("\nTraining Random Forest...")

model.fit(X_train, y_train)


# 11. Evaluate model
predictions = model.predict(X_test)

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = np.sqrt(
    mean_squared_error(
        y_test,
        predictions
    )
)

r2 = r2_score(
    y_test,
    predictions
)


print("\n========== MODEL EVALUATION ==========")
print(f"MAE  : {mae:.2f} minutes")
print(f"RMSE : {rmse:.2f} minutes")
print(f"R²   : {r2:.3f}")
print("======================================")


# 12. Save model
joblib.dump(model, MODEL_PATH)

print("\nModel training completed successfully!")
print("Saved model:", MODEL_PATH)