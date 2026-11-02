# 🎮 CodeSynapse: AI Career Architect

![Python](https://img.shields.io/badge/Python-3.14-blue?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Gradio](https://img.shields.io/badge/Frontend-Gradio-orange?style=for-the-badge&logo=gradio&logoColor=white)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)
![CI](https://github.com/SwarangiK-21/CodeSynapse/actions/workflows/ci.yml/badge.svg)

CodeSynapse is an AI-powered career dashboard for Computer Science students. It collects live coding stats from GitHub and LeetCode, scores them, and provides an AI Career Coach that gives advice based on your real numbers.

**Live demo:** [Hugging Face Space](https://huggingface.co/spaces/SwarangiK-21/CodeSynapse). This still runs the older January 2026 version, not the code in this repository.

---

## 🚀 Key Features

- **Live profile sync:** fetches public stats from GitHub and LeetCode at the same time. If a user doesn't exist or a service is down, the app says so instead of showing made-up numbers.
- **Competency scores:** turns each platform's stats into a 0–100 score shown in an interactive Plotly chart.
- **AI Nexus Coach:** a Gemini chatbot that sees your synced stats and your last 10 messages, with structured replies and automatic fallback to a second model.
- **Private per-user data:** each browser gets its own user, so profiles and chats stay separate and return after a reload.
- **Skill gap agent:** compares a repository with a job description using a LangGraph workflow. Every claim is checked in plain code against the real source and links to the exact lines, and a person approves the report before it is final.
- **Code search:** indexes public repositories by function and class using Tree-sitter, then finds code with hybrid keyword and vector search. Repository code is read from memory and never run.
- **Job description parsing:** extracts required skills, and drops any skill the AI can't back with a quote from the text.
- **PDF career report:** a one-click summary of your synced stats.
- **REST API:** everything in the UI is also available through FastAPI.

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| Backend | Python 3.14, FastAPI, Uvicorn |
| Frontend | Gradio, Plotly Express, Pandas |
| AI | Google Gemini via `google-genai`, LangGraph, Pydantic for structured output |
| Retrieval | Tree-sitter, BM25, pgvector, reciprocal rank fusion |
| Data fetching | HTTPX (GitHub API, LeetCode GraphQL) |
| Database | SQLAlchemy, Alembic, PostgreSQL (SQLite for quick local runs) |
| PDF | ReportLab |
| Quality | pytest, respx, ruff, GitHub Actions |
| Packaging | Docker |

---

## 🗂️ Project Structure

```
CodeSynapse/
├── app.py                  # Entry point: runs migrations, starts the server
├── codesynapse/
│   ├── main.py             # FastAPI app with the Gradio UI mounted
│   ├── config.py           # Settings from environment variables
│   ├── api/routes.py       # REST endpoints
│   ├── ui/app.py           # Gradio interface
│   ├── db/                 # Models, session and migration runner
│   └── services/           # Fetchers, AI coach, chat, profiles, reports, users
├── migrations/             # Alembic database migrations
├── scripts/check_models.py # Lists Gemini models your key can use
├── tests/                  # pytest suite; external services are mocked
└── .github/workflows/      # Lint, tests and Docker build on every push
```

---

## 🔧 Running Locally

Requires Python 3.14.

```bash
git clone https://github.com/SwarangiK-21/CodeSynapse.git
cd CodeSynapse
py -3.14 -m venv venv
venv/Scripts/python.exe -m pip install -r requirements-dev.txt
cp .env.example .env
```

Add your Gemini API key to `.env`, then start the app:

```bash
venv/Scripts/python.exe app.py
```

The app runs at `http://localhost:7860`, and the API docs are at `http://localhost:7860/docs`. On macOS or Linux, use `venv/bin/python` instead.

Run the checks:

```bash
venv/Scripts/python.exe -m pytest
venv/Scripts/python.exe -m ruff check .
```

### With Docker

Set `DATABASE_URL` to a Postgres database and `UI_SECRET` to a long random value in `.env`, then:

```bash
docker build -t codesynapse .
docker run --env-file .env -p 7860:7860 codesynapse
```

---

## 🔌 API

Create a user with `POST /api/users`, then send the returned token as `Authorization: Bearer <token>`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/users` | Create a user and get a token |
| GET, PUT | `/api/profile` | Read the profile, or sync it from live stats |
| GET, POST, DELETE | `/api/chat` | Read history, ask the coach, or clear history |
| GET | `/api/report` | Download the PDF report |
| GET, POST | `/api/repos` | List repositories, or index a public one |
| DELETE | `/api/repos/{id}` | Remove an indexed repository |
| GET | `/api/search?q=` | Search indexed code by keyword and meaning |
| POST | `/api/jobs` | Extract skills from a job description |
| GET | `/api/jobs/{id}` | Read a parsed job description |
| POST | `/api/analyses` | Start a skill gap analysis |
| GET | `/api/analyses/{id}` | Read status, report, step trace and token usage |
| POST | `/api/analyses/{id}/approve` | Approve a draft report |
| GET | `/api/analyses/{id}/markdown` | Export a report as Markdown |
| GET | `/health` | Health check |

---

## 🗺️ Roadmap

- [x] Live GitHub and LeetCode stats
- [x] AI coach with stats context, conversation memory and model fallback
- [x] Per-user data on PostgreSQL with migrations
- [x] REST API, automated tests and CI
- [x] Index public repositories and search code with hybrid retrieval
- [x] Extract skills from job descriptions, each backed by a quote
- [x] Multi-step agent with cited, verified evidence
- [ ] Evaluation suite with measured accuracy
- [ ] GitHub login, rate limiting and updated live deployment

---

*Built with 💻 and ☕ by Swarangi Kothawade*
