
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "datasets" / "SkillPulse_Week3_Preprocessed_Dataset.csv"

df = pd.read_csv(CSV)

print("DATASET COLUMNS:")
for column in df.columns:
    print(f"- {column}")

print("\nTARGET RELATIONSHIP CHECKS:")
for column in [
    "topic",
    "learning_goal",
    "title",
    "description",
    "preferred_topics",
    "required_skills",
    "skill_gaps",
]:
    if column not in df.columns:
        continue

    values = df[column].fillna("").astype(str).str.strip()
    target = df["target_skill"].fillna("").astype(str).str.strip()

    exact = (values.str.casefold() == target.str.casefold()).mean()
    contains = sum(
        bool(t) and t.casefold() in v.casefold()
        for v, t in zip(values, target)
    ) / len(df)

    print(
        f"{column:22} "
        f"exact_match={exact:.2%} "
        f"contains_target={contains:.2%}"
    )

print("\nSAMPLE ROWS:")
print(
    df[
        [
            "career_goal",
            "current_skills",
            "target_skill",
            "topic",
            "learning_goal",
        ]
    ].head(15).to_string(index=False)
)
