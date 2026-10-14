
from pathlib import Path
import pandas as pd


# --------------------------------------------------
# 1. Dataset path
# --------------------------------------------------
DATASET_PATH = (
    Path(__file__).resolve().parent.parent
    / "datasets"
    / "SkillPulse_Week3_Preprocessed_Dataset.csv"
)


# --------------------------------------------------
# 2. Load and validate the dataset
# --------------------------------------------------
def load_dataset():
    """Load the SkillPulse dataset and validate required columns."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {DATASET_PATH}"
        )

    df = pd.read_csv(DATASET_PATH)

    required_columns = {"career_goal", "required_skills"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Dataset is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    return df


# --------------------------------------------------
# 3. Get all available career targets
# --------------------------------------------------
def get_career_goals():
    """Return every distinct career target in the dataset."""

    df = load_dataset()

    goals = (
        df["career_goal"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    unique_goals = {
        goal for goal in goals.tolist() if goal
    }

    return sorted(unique_goals, key=str.casefold)


# --------------------------------------------------
# 4. Find required skills for a career
# --------------------------------------------------
def get_required_skills(career_goal):
    """
    Find all required skills associated with a career target.

    Career matching is case-insensitive.
    Skills are deduplicated and returned in alphabetical order.
    """

    if not career_goal or not str(career_goal).strip():
        return []

    df = load_dataset()

    target = str(career_goal).strip().casefold()

    matching = df[
        df["career_goal"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
        == target
    ]

    if matching.empty:
        return []

    skills = {}

    for value in matching["required_skills"].dropna():
        for skill in str(value).split(","):
            skill = skill.strip()

            if skill:
                # Deduplicate skills without regard to capitalization.
                skills.setdefault(skill.casefold(), skill)

    return sorted(skills.values(), key=str.casefold)


# --------------------------------------------------
# 5. Calculate skill gaps
# --------------------------------------------------
def calculate_skill_gaps(current_skills, required_skills):
    """
    Return required skills that the learner does not currently have.

    current_skills may be a comma-separated string or a list.
    Matching ignores capitalization and surrounding whitespace.
    """

    if isinstance(current_skills, str):
        current_skills = current_skills.split(",")

    if current_skills is None:
        current_skills = []

    current = {
        str(skill).strip().casefold()
        for skill in current_skills
        if str(skill).strip()
    }

    return sorted(
        [
            skill
            for skill in required_skills
            if skill.casefold() not in current
        ],
        key=str.casefold
    )
