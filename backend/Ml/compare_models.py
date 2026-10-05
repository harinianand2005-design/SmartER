import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline

from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ==========================================
# 1. LOAD DATASET
# ==========================================

df = pd.read_csv("backend/ML/Hospital_ER_Data_Cleaned.csv")


# ==========================================
# 2. CONVERT DATE
# ==========================================

df["patient_admission_date"] = pd.to_datetime(
    df["patient_admission_date"],
    dayfirst=False
)


# ==========================================
# 3. CREATE TIME FEATURES
# ==========================================

df["hour"] = df["patient_admission_date"].dt.hour
df["day_of_week"] = df["patient_admission_date"].dt.dayofweek
df["month"] = df["patient_admission_date"].dt.month
df["is_weekend"] = df["day_of_week"] >= 5


# ==========================================
# 4. FEATURES AND TARGET
# ==========================================

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


# ==========================================
# 5. PREPROCESSING
# ==========================================

categorical_features = [
    "patient_gender",
    "patient_race",
    "department_referral"
]

numerical_features = [
    "patient_age",
    "hour",
    "day_of_week",
    "month",
    "is_weekend"
]

preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features
        ),
        (
            "numerical",
            "passthrough",
            numerical_features
        )
    ]
)


# ==========================================
# 6. TRAIN-TEST SPLIT
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)


# ==========================================
# 7. MODELS
# ==========================================

models = {

    "Linear Regression": LinearRegression(),

    "Decision Tree": DecisionTreeRegressor(
        random_state=42,
        max_depth=10
    ),

    "Random Forest": RandomForestRegressor(
        n_estimators=200,
        random_state=42
    )
}


# ==========================================
# 8. MODEL COMPARISON
# ==========================================

results = []

for name, model in models.items():

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model)
        ]
    )

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)

    rmse = mean_squared_error(
        y_test,
        y_pred
    ) ** 0.5

    r2 = r2_score(
        y_test,
        y_pred
    )

    results.append({
        "Model": name,
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2
    })


# ==========================================
# 9. DISPLAY RESULTS
# ==========================================

results_df = pd.DataFrame(results)

print("\n========== MODEL COMPARISON ==========\n")

print(
    results_df.to_string(
        index=False,
        formatters={
            "MAE": "{:.2f}".format,
            "RMSE": "{:.2f}".format,
            "R2": "{:.3f}".format
        }
    )
)

print("\n======================================")