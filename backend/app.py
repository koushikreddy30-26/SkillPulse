

import os
import re

import joblib

import pandas as pd
import json
from pathlib import Path
import threading
from flask import Flask, jsonify, request

from flask_cors import CORS

from career_skills import get_required_skills, get_career_goals

from sklearn.metrics.pairwise import cosine_similarity



from database import (

    init_db,

    save_profile,

    list_profiles,

    save_plan,

    list_plans,

    save_recommendations,

    list_saved_recommendations,

)



app = Flask(__name__)

CORS(app)



# Load model artifacts using paths relative to this file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_DIR = os.path.join(BASE_DIR, "models")



print("Loading model artifacts...")



skill_model = joblib.load(os.path.join(MODEL_DIR, "skill_classifier.pkl"))

skill_tfidf = joblib.load(os.path.join(MODEL_DIR, "skill_tfidf.pkl"))

course_catalog = joblib.load(os.path.join(MODEL_DIR, "course_catalog.pkl"))

rec_tfidf = joblib.load(os.path.join(MODEL_DIR, "rec_tfidf.pkl"))

rec_vectors = joblib.load(os.path.join(MODEL_DIR, "rec_vectors.pkl"))



print("Backend models loaded.")



# Initialize persistent SQLite tables

init_db()

print("Database is ready.")







# Skill-specific aliases help short labels such as "APIs" match course titles
# such as "REST API Development". Similarity scores are ranking signals, not probabilities.
SKILL_QUERY_TERMS = {
    "apis": "API APIs REST RESTful REST API development endpoints HTTP requests responses web services backend integration",
    "api": "API APIs REST RESTful REST API development endpoints HTTP requests responses web services backend integration",
    "databases": "database databases SQL relational database tables queries joins normalization schema PostgreSQL MySQL data storage",
    "database": "database databases SQL relational database tables queries joins normalization schema PostgreSQL MySQL data storage",
    "java": "Java Java programming object oriented programming OOP classes methods inheritance JVM software development",
    "python": "Python programming Python syntax functions data structures object oriented programming",
    "sql": "SQL database queries SELECT JOIN GROUP BY relational database",
    "machine learning": "machine learning supervised unsupervised models training evaluation scikit learn",
    "statistics": "statistics probability distributions hypothesis testing regression data analysis",
    "html": "HTML markup semantic elements web pages",
    "css": "CSS styling layouts responsive design web development",
    "javascript": "JavaScript programming browser scripting DOM asynchronous programming",
    "react": "React JavaScript components hooks frontend user interfaces",
    "docker": "Docker containers images containerization deployment",
    "kubernetes": "Kubernetes container orchestration clusters deployments",
    "aws": "AWS Amazon Web Services cloud computing EC2 S3 IAM deployment",
    "deep learning": "deep learning neural networks TensorFlow PyTorch",
    "nlp": "natural language processing NLP text processing transformers language models",
    "networking": "computer networking TCP IP DNS routing network protocols",
    "linux": "Linux operating system command line shell administration",
    "excel": "Microsoft Excel spreadsheets formulas pivot tables data analysis",
    "power bi": "Power BI business intelligence dashboards data visualization",
    "data visualization": "data visualization charts dashboards graphs visual analytics",
    "communication": "communication presentation writing collaboration stakeholder communication",
    "cryptography": "cryptography encryption decryption hashing public key security",
    "siem": "SIEM security information event management log analysis threat detection",
    "mlops": "MLOps machine learning operations deployment monitoring pipelines",
    "transformers": "transformer models attention NLP large language models",
}

def _text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)

def score_courses_for_skill(skill):
    """Return relevance scores using TF-IDF plus title/topic/description keyword evidence."""
    label = str(skill).strip()
    expanded = SKILL_QUERY_TERMS.get(label.casefold(), label)
    query = f"{label} {label} {expanded}"
    query_vector = rec_tfidf.transform([query])
    semantic = cosine_similarity(query_vector, rec_vectors).flatten()

    lexical = []
    label_terms = [t.casefold() for t in re.findall(r"[a-zA-Z0-9+#.]+", label) if len(t) > 1]
    aliases = [t.casefold() for t in re.findall(r"[a-zA-Z0-9+#.]+", expanded) if len(t) > 2]
    for _, row in course_catalog.iterrows():
        title = _text(row.get("title", "")).casefold()
        topic = _text(row.get("topic", "")).casefold()
        description = _text(row.get("description", "")).casefold()
        # Title/topic evidence is weighted more heavily than description mentions.
        title_topic = f"{title} {title} {topic} {topic}"
        all_text = f"{title_topic} {description}"
        direct = sum(1 for term in label_terms if term in title_topic)
        alias_hits = sum(1 for term in set(aliases) if term in title_topic)
        description_hits = sum(1 for term in set(aliases) if term in description)
        lexical.append(min(1.0, direct * 0.22 + alias_hits * 0.09 + description_hits * 0.025))

    lexical_scores = pd.Series(lexical, dtype=float).to_numpy()
    # Blend semantic similarity with explicit skill evidence; this is a ranking score.
    return (0.68 * semantic) + (0.32 * lexical_scores)


# --------------------------------------------------

# 1. Health check

# --------------------------------------------------

@app.route("/api/health", methods=["GET"])

def health_check():

    return jsonify({

        "status": "healthy",

        "service": "SkillPulse API"

    }), 200





# --------------------------------------------------

# 2. Skill-gap analysis

# --------------------------------------------------

@app.route("/api/skill-gap", methods=["POST"])

def skill_gap():

    data = request.get_json(silent=True) or {}



    current_input = data.get("current_skills", "")

    required_input = data.get("required_skills", "")



    current = [

        s.strip().lower()

        for s in current_input.split(",")

        if s.strip()

    ]

    required = [

        s.strip().lower()

        for s in required_input.split(",")

        if s.strip()

    ]



    gaps = sorted(set(required) - set(current))



    return jsonify({

        "current_skills": current,

        "required_skills": required,

        "skill_gaps": gaps,

        "gap_count": len(gaps)

    }), 200





# --------------------------------------------------

# 3. Predict target skill

# --------------------------------------------------

@app.route("/api/predict-skill", methods=["POST"])

def predict_skill():

    data = request.get_json(silent=True) or {}



    text_input = (

        f"{data.get('career_goal', '')} "

        f"{data.get('current_skills', '')} "

        f"{data.get('required_skills', '')} "

        f"{data.get('skill_gaps', '')}"

    )



    try:

        vector = skill_tfidf.transform([text_input])

        prediction = skill_model.predict(vector)[0]

    except Exception as exc:

        app.logger.exception("Target-skill prediction failed")

        return jsonify({

            "error": "Target-skill prediction failed.",

            "details": str(exc)

        }), 500



    return jsonify({

        "predicted_target_skill": str(prediction)

    }), 200





# --------------------------------------------------

# 4. Course recommendations

# --------------------------------------------------

@app.route("/api/recommend-courses", methods=["POST"])

def recommend_courses():

    data = request.get_json(silent=True) or {}



    target_skill = str(data.get("target_skill", "")).strip()



    try:

        top_k = int(data.get("top_k", 3))

    except (ValueError, TypeError):

        return jsonify({"error": "top_k must be an integer."}), 400



    top_k = max(1, min(top_k, 10))



    if not target_skill:

        return jsonify({

            "error": "Please provide a target_skill."

        }), 400



    try:

        scores = score_courses_for_skill(target_skill)

    except Exception as exc:

        app.logger.exception("Course recommendation failed")

        return jsonify({

            "error": "Course recommendation failed.",

            "details": str(exc)

        }), 500



    ranked_indices = scores.argsort()[::-1]



    results = []

    seen_ids = set()

    seen_titles = set()



    for idx in ranked_indices:

        score = float(scores[idx])



        # Skip resources that have no text similarity

        if score <= 0:

            continue



        course = course_catalog.iloc[int(idx)].to_dict()



        resource_id = str(course.get("resource_id", "")).strip()

        title = str(course.get("title", "")).strip()



        identity = resource_id or title



        # Avoid duplicate resource IDs and course titles

        if identity in seen_ids or title.casefold() in seen_titles:

            continue



        seen_ids.add(identity)

        seen_titles.add(title.casefold())



        # Convert NumPy scalar values to JSON-safe Python values

        for key, value in list(course.items()):

            if hasattr(value, "item"):

                course[key] = value.item()



        course["match_score"] = round(score, 4)

        results.append(course)



        if len(results) >= top_k:

            break



    return jsonify({

        "target_skill": target_skill,

        "recommendations": results

    }), 200





# --------------------------------------------------

# 5. Generate an Individual Development Plan

# --------------------------------------------------

@app.route("/api/generate-idp", methods=["POST"])

def generate_idp():

    data = request.get_json(silent=True) or {}



    career_goal = str(

        data.get("career_goal", "Engineering Path")

    ).strip()



    current_input = data.get("current_skills", "")

    required_input = data.get("required_skills", "")



    current = {

        s.strip().lower()

        for s in current_input.split(",")

        if s.strip()

    }

    required = {

        s.strip().lower()

        for s in required_input.split(",")

        if s.strip()

    }



    gaps = sorted(required - current)



    roadmap = []

    for idx, gap in enumerate(gaps, start=1):

        roadmap.append({

            "milestone": (

                f"Phase {idx}: {gap.title()} Core Competency"

            ),

            "skill": gap.title(),

            "duration_weeks": 2,

            "learning_objective": (

                f"Complete coursework and 1 hands-on task in "

                f"{gap.title()}."

            )

        })



    return jsonify({

        "career_goal": career_goal,

        "idp_roadmap": roadmap

    }), 200





# --------------------------------------------------

# 6. Create a learner profile

# --------------------------------------------------


@app.route("/api/profiles", methods=["POST"])
def create_profile():
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Please sign in again."}), 401

    data = request.get_json(silent=True) or {}
    career_goal = str(data.get("career_goal", "")).strip()

    if not career_goal:
        return jsonify({"error": "career_goal is required."}), 400

    profile_id = save_profile(
        str(data.get("name", "Learner")).strip() or "Learner",
        career_goal,
        str(data.get("current_skills", "")),
        str(data.get("required_skills", "")),
        user["id"]
    )

    return jsonify({
        "message": "Profile saved",
        "profile_id": profile_id
    }), 201




# --------------------------------------------------

# 7. Retrieve learner profiles

# --------------------------------------------------


@app.route("/api/profiles", methods=["GET"])
def get_profiles():
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Please sign in again."}), 401

    return jsonify({
        "profiles": list_profiles(user["id"])
    }), 200






# --------------------------------------------------

# 8. Save a generated IDP

# --------------------------------------------------


@app.route("/api/saved-plans", methods=["POST"])
def create_saved_plan():
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Please sign in again."}), 401

    data = request.get_json(silent=True) or {}
    career_goal = str(data.get("career_goal", "")).strip()
    plan = data.get("plan")

    if not career_goal or not isinstance(plan, (dict, list)):
        return jsonify({
            "error": "career_goal and a JSON plan are required."
        }), 400

    profile_id = data.get("profile_id")

    if profile_id is not None:
        try:
            profile_id = int(profile_id)
        except (ValueError, TypeError):
            return jsonify({"error": "profile_id must be an integer."}), 400

        if not profile_belongs_to_user(profile_id, user["id"]):
            return jsonify({"error": "Profile not found."}), 404

    saved_id = save_plan(
        profile_id, career_goal, plan, user["id"]
    )

    return jsonify({
        "message": "Plan saved",
        "saved_id": saved_id
    }), 201





# --------------------------------------------------

# 9. Retrieve saved IDPs

# --------------------------------------------------


@app.route("/api/saved-plans", methods=["GET"])
def get_saved_plans():
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Please sign in again."}), 401

    return jsonify({
        "plans": list_plans(user["id"])
    }), 200




# --------------------------------------------------

# 10. Save course recommendations

# --------------------------------------------------


@app.route("/api/saved-recommendations", methods=["POST"])
def create_saved_recommendations():
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Please sign in again."}), 401

    data = request.get_json(silent=True) or {}
    target_skill = str(data.get("target_skill", "")).strip()
    recommendations = data.get("recommendations")

    if not target_skill or not isinstance(recommendations, list):
        return jsonify({
            "error": (
                "target_skill and a recommendations list are required."
            )
        }), 400

    profile_id = data.get("profile_id")

    if profile_id is not None:
        try:
            profile_id = int(profile_id)
        except (ValueError, TypeError):
            return jsonify({"error": "profile_id must be an integer."}), 400

        if not profile_belongs_to_user(profile_id, user["id"]):
            return jsonify({"error": "Profile not found."}), 404

    saved_id = save_recommendations(
        profile_id,
        target_skill,
        recommendations,
        user["id"]
    )

    return jsonify({
        "message": "Recommendations saved",
        "saved_id": saved_id
    }), 201






# --------------------------------------------------

# 11. Retrieve saved recommendations

# --------------------------------------------------


@app.route("/api/saved-recommendations", methods=["GET"])
def get_saved_recommendations():
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Please sign in again."}), 401

    return jsonify({
        "recommendations": list_saved_recommendations(user["id"])
    }), 200





@app.route("/api/career-skills", methods=["POST"])

def career_skills():

    data = request.get_json(silent=True) or {}

    career_goal = str(data.get("career_goal", "")).strip()



    if not career_goal:

        return jsonify({"error": "Please provide a career_goal."}), 400



    required_skills = get_required_skills(career_goal)



    if not required_skills:

        return jsonify({

            "error": "Career target not found in the dataset.",

            "career_goal": career_goal

        }), 404



    return jsonify({

        "career_goal": career_goal,

        "required_skills": required_skills

    }), 200



# --------------------------------------------------

# --------------------------------------------------
# Dynamic career targets
# --------------------------------------------------
@app.route("/api/career-goals", methods=["GET"])
def career_goals():
    """Return career goals available in the preprocessed dataset."""
    try:
        goals = get_career_goals()
        return jsonify({"career_goals": goals}), 200
    except Exception:
        app.logger.exception("Could not load career targets")
        return jsonify({"error": "Could not load career targets."}), 500


# 12. Automatic career analysis

# --------------------------------------------------

@app.route("/api/analyze-career", methods=["POST"])

def analyze_career():

    data = request.get_json(silent=True) or {}



    career_goal = str(data.get("career_goal", "")).strip()

    current_input = data.get("current_skills", "")



    if not career_goal:

        return jsonify({

            "error": "Please provide a career_goal."

        }), 400



    if isinstance(current_input, list):

        current_input = ",".join(str(s) for s in current_input)



    current = {

        s.strip().casefold()

        for s in str(current_input).split(",")

        if s.strip()

    }



    required_skills = get_required_skills(career_goal)



    if not required_skills:

        return jsonify({

            "error": "Career target not found in the dataset.",

            "career_goal": career_goal

        }), 404



    # Match skills without case sensitivity

    required_lookup = {

        skill.casefold(): skill

        for skill in required_skills

    }



    gaps = sorted(

        [

            skill for normalized, skill in required_lookup.items()

            if normalized not in current

        ],

        key=str.casefold

    )



    return jsonify({

        "career_goal": career_goal,

        "current_skills": sorted(current),

        "required_skills": required_skills,

        "skill_gaps": gaps,

        "gap_count": len(gaps)

    }), 200





# --------------------------------------------------

# 13. Generate a complete personalized IDP

# --------------------------------------------------

@app.route("/api/generate-personalized-idp", methods=["POST"])

def generate_personalized_idp():

    data = request.get_json(silent=True) or {}



    career_goal = str(data.get("career_goal", "")).strip()

    current_input = data.get("current_skills", "")



    if not career_goal:

        return jsonify({

            "error": "Please provide a career_goal."

        }), 400



    # Accept either a comma-separated string or a list of skills

    if isinstance(current_input, list):

        current_input = ",".join(str(s) for s in current_input)



    current = {

        skill.strip().casefold()

        for skill in str(current_input).split(",")

        if skill.strip()

    }



    # Automatically retrieve required skills from the dataset

    required_skills = get_required_skills(career_goal)



    if not required_skills:

        return jsonify({

            "error": "Career target not found in the dataset.",

            "career_goal": career_goal

        }), 404



    required_lookup = {

        skill.casefold(): skill

        for skill in required_skills

    }



    current_skills = sorted(

        [

            required_lookup.get(skill, skill)

            for skill in current

        ],

        key=str.casefold

    )



    skill_gaps = sorted(

        [

            skill

            for normalized, skill in required_lookup.items()

            if normalized not in current

        ],

        key=str.casefold

    )



    # Recommend courses for each missing skill

    course_recommendations = {}



    for gap in skill_gaps:

        try:

            scores = score_courses_for_skill(gap)



            ranked_indices = scores.argsort()[::-1]

            recommendations = []

            seen_titles = set()

            seen_ids = set()



            for idx in ranked_indices:

                score = float(scores[idx])



                if score <= 0:

                    continue



                course = course_catalog.iloc[int(idx)].to_dict()



                resource_id = str(

                    course.get("resource_id", "")

                ).strip()

                title = str(course.get("title", "")).strip()



                if not title:

                    continue



                identity = resource_id or title



                if identity in seen_ids or title.casefold() in seen_titles:

                    continue



                seen_ids.add(identity)

                seen_titles.add(title.casefold())



                # Convert NumPy values for JSON serialization

                for key, value in list(course.items()):

                    if hasattr(value, "item"):

                        course[key] = value.item()



                course["match_score"] = round(score, 4)

                recommendations.append(course)



                if len(recommendations) >= 3:

                    break



            course_recommendations[gap] = recommendations



        except Exception:

            app.logger.exception(

                "Recommendations failed for skill: %s", gap

            )

            course_recommendations[gap] = []



    # Build a learning roadmap from the identified gaps

    roadmap = []



    for idx, gap in enumerate(skill_gaps, start=1):

        roadmap.append({

            "phase": idx,

            "milestone": f"Phase {idx}: {gap} Core Competency",

            "skill": gap,

            "duration_weeks": 2,

            "learning_objective": (

                f"Study {gap} and complete at least one "

                f"hands-on learning task."

            ),

            "recommended_courses": course_recommendations[gap]

        })



    total_weeks = len(roadmap) * 2



    return jsonify({

        "career_goal": career_goal,

        "current_skills": current_skills,

        "required_skills": required_skills,

        "skill_gaps": skill_gaps,

        "gap_count": len(skill_gaps),

        "course_recommendations": course_recommendations,

        "idp_roadmap": roadmap,

        "estimated_duration_weeks": total_weeks

    }), 200
    
# --------------------------------------------------
# IDP progress tracking
# --------------------------------------------------


@app.route("/api/idp-progress/<path:plan_key>", methods=["GET"])
def get_idp_progress(plan_key):
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Please sign in again."}), 401

    # Keep each user's progress under a separate key.
    user_plan_key = f"user:{user['id']}::{plan_key}"

    with progress_lock:
        progress = read_idp_progress()

    completed = progress.get(user_plan_key, [])

    return jsonify({
        "plan_key": plan_key,
        "completed_skills": completed,
        "completedSkills": completed
    }), 200


progress_lock = threading.Lock()
IDP_PROGRESS_FILE = Path(__file__).resolve().parent / "idp_progress.json"


def read_idp_progress():
    """Read saved IDP progress from the JSON file."""
    if not IDP_PROGRESS_FILE.exists():
        return {}

    try:
        with IDP_PROGRESS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        app.logger.exception("Could not read IDP progress file")
        return {}


def write_idp_progress(progress):
    """Write IDP progress to the JSON file."""
    with IDP_PROGRESS_FILE.open("w", encoding="utf-8") as file:
        json.dump(progress, file, ensure_ascii=False, indent=2)




@app.route("/api/idp-progress", methods=["POST"])
def save_idp_progress():
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Please sign in again."}), 401

    data = request.get_json(silent=True) or {}

    plan_key = str(data.get("plan_key", "")).strip()
    completed = data.get(
        "completed_skills",
        data.get("completedSkills", [])
    )

    if not plan_key:
        return jsonify({"error": "plan_key is required"}), 400

    if not isinstance(completed, list):
        return jsonify({"error": "completed skills must be a list"}), 400

    completed = [str(skill) for skill in completed]
    user_plan_key = f"user:{user['id']}::{plan_key}"

    with progress_lock:
        progress = read_idp_progress()
        progress[user_plan_key] = completed

        try:
            write_idp_progress(progress)
        except OSError:
            app.logger.exception("Could not save IDP progress")
            return jsonify({"error": "Could not save progress"}), 500

    return jsonify({
        "message": "IDP progress saved",
        "plan_key": plan_key,
        "completed_skills": completed,
        "completedSkills": completed
    }), 200




# ================= AUTHENTICATION API =================
# Paste this block above the existing if __name__ == "__main__":

import os
import re
import psycopg
from psycopg.rows import dict_row
import sqlite3
from functools import wraps

from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import request, jsonify, g


# ================= AUTHENTICATION API =================

AUTH_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "skillpulse_accounts.db",
)


if not app.config.get("SECRET_KEY"):
    app.config["SECRET_KEY"] = os.environ.get(
        "SKILLPULSE_SECRET_KEY",
        "local-development-only-change-before-deployment",
    )

auth_serializer = URLSafeTimedSerializer(
    app.config["SECRET_KEY"],
    salt="skillpulse-auth-v1",
)


def auth_db():
    """Use PostgreSQL in deployment and SQLite locally."""
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace(
                "postgres://", "postgresql://", 1
            )
        return psycopg.connect(database_url, row_factory=dict_row)

    conn = sqlite3.connect(AUTH_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    with auth_db() as conn:
        if os.environ.get("DATABASE_URL"):
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower
                ON users (LOWER(email))
            """)
        else:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)


init_auth_db()


@app.after_request
def skillpulse_auth_cors(response):
    origin = request.headers.get("Origin")
    allowed_origins = {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }

    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization"
        )
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, OPTIONS"
        )

    return response


def make_auth_token(user_id):
    return auth_serializer.dumps({"user_id": user_id})


def get_auth_user():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None

    token = header[7:].strip()
    if not token:
        return None

    try:
        payload = auth_serializer.loads(
            token, max_age=60 * 60 * 24 * 7
        )

        with auth_db() as conn:
            if os.environ.get("DATABASE_URL"):
                user = conn.execute(
                    "SELECT id, name, email FROM users WHERE id = %s",
                    (payload.get("user_id"),),
                ).fetchone()
            else:
                user = conn.execute(
                    "SELECT id, name, email FROM users WHERE id = ?",
                    (payload.get("user_id"),),
                ).fetchone()

        return dict(user) if user else None

    except (
        BadSignature,
        SignatureExpired,
        TypeError,
        ValueError,
        psycopg.Error,
        sqlite3.Error,
    ):
        app.logger.exception("Authentication lookup failed")
        return None


@app.route("/api/auth/register", methods=["POST", "OPTIONS"])
def skillpulse_register():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not name or len(name) > 80:
        return jsonify({
            "error": "Enter a name up to 80 characters."
        }), 400

    if (
        not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
        or len(email) > 254
    ):
        return jsonify({"error": "Enter a valid email address."}), 400

    if (
        not isinstance(password, str)
        or len(password) < 10
        or len(password) > 128
    ):
        return jsonify({
            "error": "Password must be 10–128 characters."
        }), 400

    password_hash = generate_password_hash(password)

    try:
        with auth_db() as conn:
            if os.environ.get("DATABASE_URL"):
                row = conn.execute(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (name, email, password_hash),
                ).fetchone()
                user_id = row["id"]
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (name, email, password_hash),
                )
                user_id = cursor.lastrowid

    except (psycopg.errors.UniqueViolation, sqlite3.IntegrityError):
        return jsonify({
            "error": (
                "An account with that email already exists. "
                "Please sign in."
            )
        }), 409
    except (psycopg.Error, sqlite3.Error):
        app.logger.exception("Account registration database error")
        return jsonify({
            "error": "Could not create account. Check the backend logs."
        }), 500

    user = {"id": user_id, "name": name, "email": email}
    return jsonify({
        "message": "Account created.",
        "user": user,
        "token": make_auth_token(user_id),
    }), 201


@app.route("/api/auth/login", methods=["POST", "OPTIONS"])
def skillpulse_login():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not email or not isinstance(password, str):
        return jsonify({
            "error": "Enter your email and password."
        }), 400

    try:
        with auth_db() as conn:
            if os.environ.get("DATABASE_URL"):
                row = conn.execute(
                    """
                    SELECT id, name, email, password_hash
                    FROM users WHERE LOWER(email) = LOWER(%s)
                    """,
                    (email,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT id, name, email, password_hash
                    FROM users WHERE email = ?
                    """,
                    (email,),
                ).fetchone()

    except (psycopg.Error, sqlite3.Error):
        app.logger.exception("Account login database error")
        return jsonify({"error": "Could not sign in right now."}), 500

    if not row or not check_password_hash(
        row["password_hash"], password
    ):
        return jsonify({
            "error": "Incorrect email or password."
        }), 401

    user = {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
    }

    return jsonify({
        "message": "Signed in.",
        "user": user,
        "token": make_auth_token(user["id"]),
    }), 200


@app.route("/api/auth/me", methods=["GET", "OPTIONS"])
def skillpulse_me():
    if request.method == "OPTIONS":
        return "", 204

    user = get_auth_user()
    if not user:
        return jsonify({"error": "Please sign in again."}), 401

    return jsonify({"user": user}), 200


@app.route("/api/auth/logout", methods=["POST", "OPTIONS"])
def skillpulse_logout():
    if request.method == "OPTIONS":
        return "", 204

    return jsonify({"message": "Signed out."}), 200


# ================= END AUTHENTICATION API =================

@app.route("/")
def home():
    return "SkillPulse API is running"
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5000)),
        debug=not bool(os.environ.get("DATABASE_URL")),
    )
