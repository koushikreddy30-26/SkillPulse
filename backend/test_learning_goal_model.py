
from pathlib import Path
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "datasets" / "SkillPulse_Week3_Preprocessed_Dataset.csv"

df = pd.read_csv(CSV)
df = df.dropna(subset=["learning_goal", "target_skill"]).copy()

X = df["learning_goal"].astype(str)
y = df["target_skill"].astype(str)

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y,
)

model = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
    ("classifier", LogisticRegression(max_iter=3000)),
])

model.fit(X_train, y_train)
predictions = model.predict(X_test)

print("\n========== LEARNING-GOAL MODEL ==========")
print(f"Test rows: {len(y_test)}")
print(f"Test accuracy: {accuracy_score(y_test, predictions):.2%}")
print("\nClassification report:")
print(classification_report(y_test, predictions, zero_division=0))

# Compare exact extraction from learning_goal as a separate baseline.
skills = sorted(y.unique(), key=len, reverse=True)

def extract_skill(text):
    text = str(text).casefold()
    matches = [s for s in skills if s.casefold() in text]
    return matches[0] if matches else None

extracted = X_test.map(extract_skill)
valid = extracted.notna()

if valid.any():
    exact_accuracy = (
        extracted[valid].str.casefold()
        == y_test[valid].str.casefold()
    ).mean()
    print(f"\nExact text-extraction accuracy: {exact_accuracy:.2%}")
    print(f"Rows with a detected skill: {valid.sum()}/{len(y_test)}")
else:
    print("\nNo skills were extracted from the test text.")
# Save the model fitted on the training split
MODEL_PATH = ROOT / "backend" / "learning_goal_classifier.pkl"
joblib.dump(model, MODEL_PATH)

print(f"\nLearning-goal model saved to: {MODEL_PATH}")