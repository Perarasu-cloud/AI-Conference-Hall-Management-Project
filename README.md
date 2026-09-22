# AI Conference Hall Management System

A full-stack conference hall management and booking system with:

- Manual hall availability search
- AI-assisted booking requirement extraction
- Resource-based hall matching
- Booking conflict detection
- Alternative time-slot suggestions
- FastAPI backend
- SQLite database for local development
- HTML, CSS and JavaScript frontend

## Project structure

```text
Conference-Hall-Management/
├── backend/
│   ├── main.py
│   ├── ai_service.py
│   ├── database.py
│   ├── requirements.txt
│   ├── .env.example
│   └── database/
└── frontend/
    ├── index.html
    ├── script.js
    └── style.css
```

## Run locally

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Copy `backend/.env.example` to `backend/.env` and add your Gemini API key.
4. Start FastAPI from the `backend` directory:

```bash
uvicorn main:app --reload
```

5. Serve the `frontend` folder with a local static server (for example, VS Code Live Server).

## Security

Never commit `backend/.env` or any real API key. The Gemini API key must be stored as a secret/environment variable on the backend hosting service.

## Deployment note

SQLite is retained here for local development. Before production deployment for multiple users, use a persistent production database (such as PostgreSQL) or a hosting setup with a persistent disk. The deployment process should also set `GEMINI_API_KEY` and `FRONTEND_URL` as server-side environment variables.
