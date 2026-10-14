# SkillPulse

This repository contains the backend for the SkillPulse recommendation and IDP service.

## Prerequisites
- Python 3.8+ installed
- (Optional) create and activate a virtual environment

## Install dependencies
From the repository root run:

```bash
pip install -r backend/requirements.txt
```

## Run commands
All commands assume you run them from the repository root. Replace `python` with your Python executable if needed.

- Train models only:

```bash
python backend/run_all.py train
```

- Start the Flask API (foreground):

```bash
python backend/run_all.py serve
```

- Send a sample recommendation test (assumes server already running):

```bash
python backend/run_all.py test
```

- Full pipeline: train, start server, run test, then stop server:

```bash
python backend/run_all.py all
```

## API endpoints (selected)
- `GET /api/health` — health check
- `POST /api/recommend-courses` — body: `{ "target_skill": "Python", "top_k": 3 }`
- `POST /api/predict-skill` — predict target skill from text inputs
- `POST /api/skill-gap` — compute skill gaps
- `POST /api/generate-idp` — generate IDP roadmap

## Notes
- Models are saved to `backend/models/` by the training script.
- If you see package warnings (e.g., RequestsDependencyWarning), consider updating your environment packages.
