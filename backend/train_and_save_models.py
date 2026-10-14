
from pathlib import Path
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

# Build paths relative to this script
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
MODELS_DIR = BASE_DIR / "models"
DATA_PATH = PROJECT_DIR / "datasets" / "SkillPulse_Week3_Preprocessed_Dataset.csv"

MODELS_DIR.mkdir(parents=True, exist_ok=True)

# 1. Load dataset
print(f"Loading dataset from: {DATA_PATH}")

if not DATA_PATH.exists():
    raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

df = pd.read_csv(DATA_PATH)

# Check required columns
required_columns = [
    "career_goal", "current_skills", "required_skills",
    "skill_gaps", "target_skill", "resource_id", "title",
    "topic", "difficulty", "content_type", "description"
]

missing = [col for col in required_columns if col not in df.columns]
if missing:
    raise ValueError(f"Dataset is missing columns: {missing}")

# 2. Prepare training text
df["combined_features"] = (
    df["career_goal"].fillna("").astype(str) + " " +
    df["current_skills"].fillna("").astype(str) + " " +
    df["required_skills"].fillna("").astype(str) + " " +
    df["skill_gaps"].fillna("").astype(str)
)

X = df["combined_features"]
y = df["target_skill"]

if y.isna().any():
    raise ValueError("The target_skill column contains missing values.")

# 3. Train target-skill classifier
print("Training target-skill predictor...")

tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
X_tfidf = tfidf.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(
    X_tfidf, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

clf = LogisticRegression(max_iter=1000, class_weight="balanced")
clf.fit(X_train, y_train)

print(f"Training complete. Test accuracy: {clf.score(X_test, y_test):.3f}")


# 4. Build course catalog and fitted recommendation vectorizer
print("Vectorizing course catalog...")

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

# Combine course title, topic, and description.
# This gives the recommendation model more information
# for matching each missing skill to a course.
course_catalog["combined_course_text"] = (
    course_catalog["title"].fillna("").astype(str) + " " +
    course_catalog["topic"].fillna("").astype(str) + " " +
    course_catalog["description"].fillna("").astype(str)
)

# Fit TF-IDF on the combined course text.
rec_tfidf = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    sublinear_tf=True
)

rec_vectors = rec_tfidf.fit_transform(
    course_catalog["combined_course_text"]
)


# 5. Verify vectorizers before saving
assert hasattr(tfidf, "idf_"), "Skill vectorizer is not fitted."
assert hasattr(rec_tfidf, "idf_"), "Recommendation vectorizer is not fitted."

# 6. Save artifacts
joblib.dump(clf, MODELS_DIR / "skill_classifier.pkl")
joblib.dump(tfidf, MODELS_DIR / "skill_tfidf.pkl")
joblib.dump(course_catalog, MODELS_DIR / "course_catalog.pkl")
joblib.dump(rec_tfidf, MODELS_DIR / "rec_tfidf.pkl")
joblib.dump(rec_vectors, MODELS_DIR / "rec_vectors.pkl")

print("All models saved successfully!")
print(f"Artifacts location: {MODELS_DIR}")
