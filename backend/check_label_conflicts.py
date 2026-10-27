
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "datasets" / "SkillPulse_Week3_Preprocessed_Dataset.csv"

df = pd.read_csv(CSV)

features = ["career_goal", "current_skills"]
target = "target_skill"

for col in features + [target]:
    df[col] = df[col].fillna("").astype(str).str.strip()

print("Total rows:", len(df))
print("Unique target labels:", df[target].nunique())

# Count unique input combinations
groups = df.groupby(features, dropna=False)[target].agg(
    row_count="size",
    distinct_labels="nunique",
    labels=lambda s: sorted(s.unique())
)

conflicts = groups[groups["distinct_labels"] > 1]

print("Unique input combinations:", len(groups))
print("Conflicting input combinations:", len(conflicts))
print(
    "Rows in conflicting combinations:",
    int(conflicts["row_count"].sum())
)

if not conflicts.empty:
    print("\nExamples of conflicting inputs:")
    print(conflicts.head(20).to_string())

# Theoretical ceiling for a deterministic classifier using only these inputs
majority_correct = (
    df.groupby(features, dropna=False)[target]
    .agg(lambda s: s.value_counts().max())
    .sum()
)

print(
    "\nMaximum training accuracy from these inputs alone:",
    f"{majority_correct / len(df):.2%}"
)
