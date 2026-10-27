
from pathlib import Path
import pandas as pd

# Locate the project dataset
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DATASET_PATH = (
    PROJECT_DIR
    / "datasets"
    / "SkillPulse_Week3_Preprocessed_Dataset.csv"
)

def main():
    if not DATASET_PATH.exists():
        print(f"Dataset not found: {DATASET_PATH}")
        return

    df = pd.read_csv(DATASET_PATH)

    required_columns = {"topic", "target_skill"}
    if not required_columns.issubset(df.columns):
        print("Missing required columns:", required_columns - set(df.columns))
        return

    # Normalize text before comparing
    topic = df["topic"].fillna("").astype(str).str.strip().str.casefold()
    target = (
        df["target_skill"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    valid = topic.ne("") & target.ne("")
    total = int(valid.sum())

    if total == 0:
        print("No valid rows to evaluate.")
        return

    correct = int((topic[valid] == target[valid]).sum())
    accuracy = correct / total * 100

    print("\n========== DATASET LOOKUP EVALUATION ==========")
    print(f"Total dataset rows: {len(df)}")
    print(f"Rows evaluated: {total}")
    print(f"Exact matches: {correct}/{total}")
    print(f"Exact-match accuracy: {accuracy:.2f}%")

    mismatches = df.loc[valid].loc[
        (topic[valid] != target[valid]).to_numpy(),
        ["topic", "target_skill"],
    ]

    if mismatches.empty:
        print("\nAll evaluated topic values match target_skill.")
    else:
        print(f"\nMismatched rows: {len(mismatches)}")
        print(mismatches.head(20).to_string(index=False))

    print("\nNOTE:")
    print(
        "This measures exact matching between topic and target_skill. "
        "It is not the ML classifier's predictive accuracy because "
        "topic may already contain the target answer."
    )

if __name__ == "__main__":
    main()
