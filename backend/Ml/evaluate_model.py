import pandas as pd
import joblib
import numpy as np

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# Load dataset
df = pd.read_csv(
    "backend/ML/Hospital_ER_Data_Cleaned.csv"
)


# Convert admission date
df["patient_admission_date"] = pd.to_datetime(
    df["patient_admission_date"],
    errors="coerce"
)


# Convert target
df["patient_waittime"] = pd.to_numeric(
    df["patient_waittime"],
    errors="coerce"
)


# Remove invalid records
df = df.dropna(
    subset=["patient_admission_date", "patient_waittime"]
).copy()


# IMPORTANT:
# Same chronological sorting as train_model.py
df = df.sort_values(
    "patient_admission_date"
).reset_index(drop=True)


# Create time-based features
df["hour"] = df["patient_admission_date"].dt.hour
df["day_of_week"] = df["patient_admission_date"].dt.dayofweek
df["month"] = df["patient_admission_date"].dt.month
df["is_weekend"] = (
    df["day_of_week"] >= 5
).astype(int)


# Features
features = [
    "patient_gender",
    "patient_age",
    "patient_race",
    "department_referral",
    "hour",
    "day_of_week",
    "month",
    "is_weekend"
]

X = df[features]
y = df["patient_waittime"]


# SAME chronological 80/20 split
split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]


# Load saved model
model = joblib.load(
    "backend/ML/smarter_waittime_model.joblib"
)


# Predict
y_pred = model.predict(X_test)


# Evaluation
mae = mean_absolute_error(
    y_test,
    y_pred
)

rmse = np.sqrt(
    mean_squared_error(
        y_test,
        y_pred
    )
)

r2 = r2_score(
    y_test,
    y_pred
)


print("\n========== MODEL EVALUATION ==========")
print(f"MAE  : {mae:.2f} minutes")
print(f"RMSE : {rmse:.2f} minutes")
print(f"R²   : {r2:.3f}")
print("======================================")