
from pathlib import Path
import json
import re

import joblib
import pandas as pd

from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.svm import LinearSVC
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

# =========================================================
# 1. PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = PROJECT_DIR / "datasets"

MODELS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
TEST_SIZE = 0.20

FEATURE_COLUMNS = ["career_goal", "current_skills"]
TARGET_COLUMN = "target_skill"

# Never use these columns as classifier inputs.
LEAKAGE_COLUMNS = [
    "learning_goal",
    "topic",
    "skill_gaps",
    "required_skills",
    "title",
    "calculated_skill_gaps",
    "calculated_skill_gaps_text",
]


# =========================================================
# 2. FIND AND LOAD DATASET
# =========================================================

def find_dataset():
    candidates = sorted(DATA_DIR.glob("*.csv"))

    for path in candidates:
        try:
            columns = pd.read_csv(path, nrows=0).columns
            if set(FEATURE_COLUMNS + [TARGET_COLUMN]).issubset(columns):
                return path
        except Exception:
            continue

    raise FileNotFoundError(
        f"No suitable CSV found in {DATA_DIR}. "
        "Check that your dataset is inside the datasets folder."
    )


def clean_text(series):
    return series.fillna("").astype(str).str.strip()


DATA_PATH = find_dataset()

print(f"Loading dataset: {DATA_PATH}")

df = pd.read_csv(DATA_PATH)

required_columns = [
    "career_goal",
    "current_skills",
    "target_skill",
    "resource_id",
    "title",
    "topic",
    "difficulty",
    "content_type",
    "description",
]

missing = [c for c in required_columns if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

df = df.dropna(subset=["target_skill"]).copy()

for col in FEATURE_COLUMNS + ["target_skill"]:
    df[col] = clean_text(df[col])

df = df[df["target_skill"] != ""].copy()

if df["target_skill"].nunique() < 2:
    raise ValueError("At least two target classes are required.")

print(f"Rows loaded: {len(df)}")
print(f"Target classes: {df['target_skill'].nunique()}")

print("\nTarget class distribution:")
print(df["target_skill"].value_counts().to_string())


# =========================================================
# 3. LEAKAGE AUDIT
# =========================================================

print("\n========== LEAKAGE AUDIT ==========")

for col in LEAKAGE_COLUMNS:
    if col not in df.columns:
        continue

    values = clean_text(df[col]).str.casefold()
    targets = df["target_skill"].str.casefold()

    exact_match = (values == targets).mean()

    contains_target = sum(
        bool(target) and target in value
        for value, target in zip(values, targets)
    ) / len(df)

    print(
        f"{col}: exact target match={exact_match:.1%}, "
        f"contains target text={contains_target:.1%}"
    )

print(
    "\nOnly career_goal and current_skills will be used "
    "to predict the target skill."
)


# =========================================================
# 4. PREPARE FEATURES AND SPLIT DATA
# =========================================================

# Remove exact repeated examples to reduce duplicate leakage.
before = len(df)

df = df.drop_duplicates(
    subset=FEATURE_COLUMNS + [TARGET_COLUMN]
).copy()

print(f"\nDuplicate examples removed: {before - len(df)}")

class_counts = df["target_skill"].value_counts()

if (class_counts < 2).any():
    raise ValueError(
        "Some target classes have fewer than two unique examples. "
        "Collect more examples or review those classes before training."
    )

X = (
    df["career_goal"]
    + " [CURRENT SKILLS] "
    + df["current_skills"]
)

y = df["target_skill"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y,
)


# =========================================================
# 5. COMPARE MODELS
# =========================================================

models = {
    "Majority Baseline": DummyClassifier(
        strategy="most_frequent"
    ),

    "Logistic Regression": make_pipeline(
        TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            sublinear_tf=True,
        ),
        LogisticRegression(
            max_iter=3000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
    ),

    "Linear SVM": make_pipeline(
        TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            sublinear_tf=True,
        ),
        LinearSVC(
            class_weight="balanced",
            random_state=RANDOM_STATE,
            dual="auto",
        ),
    ),
}

results = []
trained_models = {}
predictions_by_model = {}

print("\n========== MODEL COMPARISON ==========")

for name, model in models.items():
    print(f"\nTraining {name}...")

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    trained_models[name] = model
    predictions_by_model[name] = predictions

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(
        y_test, predictions,
        average="macro", zero_division=0
    )
    recall = recall_score(
        y_test, predictions,
        average="macro", zero_division=0
    )
    macro_f1 = f1_score(
        y_test, predictions,
        average="macro", zero_division=0
    )

    results.append({
        "Model": name,
        "Accuracy": accuracy,
        "Macro Precision": precision,
        "Macro Recall": recall,
        "Macro F1": macro_f1,
    })

    print(f"Accuracy:        {accuracy:.2%}")
    print(f"Macro Precision: {precision:.4f}")
    print(f"Macro Recall:    {recall:.4f}")
    print(f"Macro F1:        {macro_f1:.4f}")


results_df = pd.DataFrame(results).sort_values(
    ["Macro F1", "Accuracy"],
    ascending=False,
)

results_df.to_csv(
    MODELS_DIR / "model_comparison_results.csv",
    index=False,
)

print("\n========== FINAL COMPARISON ==========")
print(results_df.to_string(index=False))

# Select the best actual classifier, not a constant baseline.
real_results = results_df[
    results_df["Model"] != "Majority Baseline"
]

best_name = real_results.iloc[0]["Model"]
best_predictions = predictions_by_model[best_name]

print(f"\nSelected classifier: {best_name}")
print(
    f"Held-out accuracy: "
    f"{accuracy_score(y_test, best_predictions):.2%}"
)

print("\n========== CLASSIFICATION REPORT ==========")

report_text = classification_report(
    y_test,
    best_predictions,
    zero_division=0,
)

print(report_text)

report_dict = classification_report(
    y_test,
    best_predictions,
    output_dict=True,
    zero_division=0,
)

with open(
    MODELS_DIR / "classification_report.json",
    "w",
    encoding="utf-8",
) as file:
    json.dump(report_dict, file, indent=2)

pd.DataFrame({
    "actual": y_test.reset_index(drop=True),
    "predicted": pd.Series(best_predictions),
}).to_csv(
    MODELS_DIR / "heldout_predictions.csv",
    index=False,
)

labels = sorted(y.unique())

matrix = confusion_matrix(
    y_test,
    best_predictions,
    labels=labels,
)

pd.DataFrame(
    matrix,
    index=labels,
    columns=labels,
).to_csv(MODELS_DIR / "confusion_matrix.csv")


# =========================================================
# 6. TRAIN FINAL CLASSIFIER ON ALL DATA
# =========================================================

# Test metrics above are computed before this refit.
# Do not report full-training performance as test accuracy.

print("\nTraining final classifier on all eligible rows...")

final_tfidf = TfidfVectorizer(
    max_features=5000,
    ngram_range=(1, 2),
    sublinear_tf=True,
)

X_all = final_tfidf.fit_transform(X)

if best_name == "Logistic Regression":
    final_classifier = LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )
else:
    final_classifier = LinearSVC(
        class_weight="balanced",
        random_state=RANDOM_STATE,
        dual="auto",
    )

final_classifier.fit(X_all, y)
from sklearn.metrics import accuracy_score

# Evaluate the final model on the same data used for training.
train_predictions = final_classifier.predict(X_all)

train_accuracy = accuracy_score(y, train_predictions)

print("\n========== FULL-DATASET TRAINING ACCURACY ==========")
print(f"Training accuracy: {train_accuracy:.2%}")
print(f"Correct predictions: {(y == train_predictions).sum()}/{len(y)}")


# =========================================================
# 7. BUILD COURSE CATALOG
# =========================================================

print("\nBuilding course recommendation catalog...")

course_catalog = (
    df[
        [
            "resource_id",
            "title",
            "topic",
            "difficulty",
            "content_type",
            "description",
        ]
    ]
    .drop_duplicates(subset=["resource_id"])
    .reset_index(drop=True)
)

for col in ["title", "topic", "description"]:
    course_catalog[col] = clean_text(course_catalog[col])

course_catalog["combined_course_text"] = (
    course_catalog["title"]
    + " "
    + course_catalog["topic"]
    + " "
    + course_catalog["description"]
).str.strip()

rec_tfidf = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    sublinear_tf=True,
)

rec_vectors = rec_tfidf.fit_transform(
    course_catalog["combined_course_text"]
)


# =========================================================
# 8. SAVE COMPATIBLE MODEL ARTIFACTS
# =========================================================

artifacts = {
    "skill_classifier.pkl": final_classifier,
    "skill_tfidf.pkl": final_tfidf,
    "course_catalog.pkl": course_catalog,
    "rec_tfidf.pkl": rec_tfidf,
    "rec_vectors.pkl": rec_vectors,
}

for filename, artifact in artifacts.items():
    joblib.dump(artifact, MODELS_DIR / filename)
    print(f"Saved: {filename}")

print("\nAll model artifacts saved successfully.")
print(f"Models directory: {MODELS_DIR}")
print(
    "Use the held-out metrics above for your report. "
    "The final classifier has been refitted on all eligible data."
)
