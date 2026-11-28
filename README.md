<h1 align="center">🧠 CodeSynapse — AI Career Architect</h1>

<p align="center"><b>A LangGraph agent that checks your real code against a job description or your own resume, and proves every claim with line-level evidence. Plus live coding analytics, an AI career coach, and an MCP server for AI assistants.</b></p>

<p align="center">
  <a href="https://github.com/SwarangiK-21/CodeSynapse/actions/workflows/ci.yml"><img src="https://github.com/SwarangiK-21/CodeSynapse/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Gradio-F97316?style=flat-square&logo=gradio&logoColor=white" alt="Gradio">
  <img src="https://img.shields.io/badge/LangGraph-agent-1C3C3C?style=flat-square&logo=langchain&logoColor=white" alt="LangGraph">
  <img src="https://img.shields.io/badge/Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white" alt="Gemini">
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="pgvector">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/MCP-server-191919?style=flat-square" alt="MCP server">
  <a href="https://huggingface.co/spaces/SwarangiK-21/CodeSynapse"><img src="https://img.shields.io/badge/Live%20demo-Hugging%20Face-FFD21E?style=flat-square&logo=huggingface&logoColor=black" alt="Live demo"></a>
</p>

| Skill-gap analysis | Live profile sync |
|:---:|:---:|
| ![Skill-gap report in light mode: 5 of 5 required skills backed by code, Redis not found](docs/images/skill_gap.png) | ![Profile tab in dark mode with live GitHub stats](docs/images/profile_sync.png) |

<sub>Screenshots from the live demo (16 Nov 2026): a real analysis of <code>pallets/itsdangerous</code> in light mode, and the Profile tab in dark mode.</sub>

**Live demo:** [Hugging Face Space](https://huggingface.co/spaces/SwarangiK-21/CodeSynapse), deployed from `main` after CI passes, with data in Supabase Postgres ([how it deploys](docs/DEPLOY.md)). The free Space sleeps when idle, so the first visit can take a minute.

---

## 📌 Problem statement

Students preparing for software roles get generic advice that ignores what they have actually built. Job descriptions list skills and resumes list claims, but checking whether your own code demonstrates them is manual and subjective — and an LLM asked "does this repo show Kubernetes skills?" will happily say yes because of a comment or an unused import.

## 🎯 Objectives

1. Compare repositories with a job description, or with the claims on a resume, and **cite the exact lines** that prove each skill — rejecting any claim the source code does not support.
2. Measure the system honestly: accuracy against a baseline, citation validity, search quality, resistance to prompt injection, and whether its confidence can be trusted.
3. Turn real, live GitHub and LeetCode statistics into comparable competency scores, and give coaching grounded in those numbers, not invented ones.
4. Run it like a real service: background jobs, rate limits, caching, a deployed demo, and an MCP server so AI assistants can use it.

---

## ✨ Key features

**Evidence-checked analysis**

- **Skill-gap agent** — a LangGraph workflow (`plan → retrieve → assess → verify → recommend`) compares repositories with a job description. A deterministic verifier checks every quoted claim against the real source, links it to exact lines, and retries or drops unsupported claims; a person approves the report before it is final.
- **Resume claim checker** — upload a resume PDF (or paste it) and the same agent checks each technical claim against up to three repositories: backed by code, partly backed, or not found, with links to the lines. Only the extracted claims are stored, never the full resume or contact details.
- **Calibrated confidence** — each skill shows "% likely present" from a small logistic regression over facts the verifier has checked, trained on 68 labelled skills and scored by leave-one-repository-out cross-validation (Brier 0.030, AUROC 0.97).
- **Hybrid code search** — indexes public repositories by function and class with Tree-sitter, then retrieves with BM25 + vector search merged by reciprocal rank fusion. Repository code is read, never executed.
- **Quote-backed parsing** — skills from a job description and claims from a resume are kept only when the model quotes them word for word from the text.

**For people and for AI assistants**

- **Four-tab web app** — Skill Gap, Resume Check, Profile and Coach, with a pastel light and dark theme that remembers your choice.
- **MCP server** — six tools that let AI assistants such as Claude or Cursor index repositories, search code and run skill and resume checks in conversation, with every result linked to the exact lines.
- **Live profile sync and scores** — fetches public GitHub and LeetCode stats; each becomes a 0–100 score in a Plotly chart. If a user doesn't exist or a service is down, the app says so instead of inventing numbers.
- **AI career coach** — a Gemini chatbot that sees your synced stats and your last 10 messages, with structured replies.
- **REST API, PDF and Markdown reports** — everything in the UI is also available through FastAPI, with private per-user data.
- **Sign in with GitHub** — optional; links an anonymous browser's work to the GitHub account and makes it available on every device. No GitHub permissions are requested and GitHub's token is never stored.

**Built to run as a service**

- **Background jobs** — indexing and analysis run outside the web request; jobs interrupted by a restart are marked failed, never left stuck.
- **Rate limits and caching** — per-user hourly limits protect the AI quota, and identical AI requests and embeddings are answered from a database cache.
- **Model fallback that learns** — if a Gemini model times out or is overloaded, requests move to the next one, and the struggling model rests at the back of the line for 5 minutes instead of slowing every later call.
- **Continuous deployment** — every push to `main` that passes CI is published to the live Space, which signs in to Hugging Face as a trusted publisher with no stored token.

---

## 🛠️ Technology stack

| Layer | Tools |
|---|---|
| Backend | Python 3.14, FastAPI, Uvicorn |
| Frontend | Gradio (custom theme, light and dark), Plotly Express, Pandas |
| AI | Google Gemini via `google-genai`, LangGraph, Pydantic structured output |
| Retrieval | Tree-sitter, BM25, pgvector, reciprocal rank fusion |
| Evaluation and ML | NumPy (calibration metrics, logistic regression), custom ranking metrics |
| Data and documents | HTTPX (GitHub REST API, LeetCode GraphQL), pypdf (resumes), ReportLab (PDF reports) |
| Database | SQLAlchemy, Alembic, PostgreSQL + pgvector (SQLite for quick local runs) |
| AI assistants | Model Context Protocol (`mcp` Python SDK) |
| Hosting | Docker on Hugging Face Spaces, Supabase Postgres with row-level security |
| Quality | pytest, respx, ruff, GitHub Actions (lint, tests against Postgres, Docker build, deploy, on-demand evals) |

---

## 🏗️ Architecture

```mermaid
flowchart LR
    U[Browser] --> G[Gradio UI]
    U --> API[REST API]
    M[AI assistant] --> MCP[MCP server] --> API
    G --> S[FastAPI app]
    API --> S
    S --> L[Rate limits]
    S --> F[Fetchers: GitHub, LeetCode]
    S --> C[AI coach + chat memory]
    S --> P[Job and resume parsing]
    S --> J[Background jobs]
    J --> R[Repo indexer: Tree-sitter chunks + embeddings]
    J --> A[Skill-gap agent]
    R --> DB[(PostgreSQL + pgvector)]
    A --> Q[Hybrid search: BM25 + vectors + RRF]
    Q --> DB
    C --> LLM[Gemini, with fallback and cache]
    P --> LLM
    A --> LLM
    S --> DB
```

The MCP server runs on the assistant's machine and calls the REST API, so it works with the live demo or any self-hosted copy.

### Skill-gap agent

```mermaid
flowchart LR
    P[plan: search queries per skill] --> RT[retrieve: hybrid code search]
    RT --> AS[assess: level + quoted claims]
    AS --> V{verify: quotes exist in the cited lines?}
    V -- unsupported claim, attempts left --> AS
    V -- all checked --> RC[recommend + confidence]
    RC --> H[Human approval]
```

The verifier is plain Python, not another model call: a claim survives only if its quote is found in the cited file and line range at the indexed commit, and a quote that is only an import line never counts. The same graph checks resumes: each claim becomes a "skill" whose quote comes from the resume, and the prompts say "the resume claims" instead of "the job asks for".

---

## 📊 Evaluation results

From [`evals/results/summary.json`](evals/results/summary.json): real open-source repositories at pinned commits (8 in the standard set, 5 in the hard set), hybrid keyword and vector search, one model (`gemini-3.5-flash-lite`) throughout. The baseline uses the same code search but makes a single prompt, with no planning, verification or retry.

| Set | System | Skill pairs | Precision | Recall | F1 | Citations real | LLM calls |
|---|---|---:|---:|---:|---:|---:|---:|
| Standard | Baseline | 46 | 1.00 | 1.00 | 1.00 | — (none given) | 8 |
| Standard | **Agent** | 46 | 1.00 | 1.00 | 1.00 | **72 / 72** | 63 |
| Hard | Baseline | 22 | 0.69 | 1.00 | 0.81 | — (none given) | 5 |
| Hard | **Agent** | 22 | **0.92** | 1.00 | **0.96** | **26 / 26** | 32 |

On the hard set's four "mentioned in the docs but not used in the code" traps, the baseline was fooled by all four and the agent by one. That one is debatable: `encode/databases` runs MySQL and PostgreSQL as container services in CI, which the agent counted as Docker use. An earlier hard-set run with keyword search only is kept in [`evals/results/archive`](evals/results/archive) (agent precision 0.91, baseline 0.67).

**Prompt injection:** 8 of 8 attacks blocked (comments addressed to the AI, fake evidence blocks, fake JSON output, unused imports, dead strings). See [`evals/injection.py`](evals/injection.py).

What this shows: on easy cases a single prompt is as accurate, but the agent is the only one that gives verifiable evidence; on harder cases the agent cuts false positives. The cost is about 6–8× more LLM calls. The sets are small, so treat the numbers as indicative.

Reproduce: `python -m evals.run agent`, `baseline`, `agent-hard`, `baseline-hard`, `injection`, then `python -m evals.run report`.

#### Larger sets, and does better search help the agent?

The same systems were run again on the larger sets (80 standard and 33 hard pairs across all eight repositories), with the app's search and with the tuned search from the next section:

| Set | System | Pairs scored | Precision | Recall | F1 | Citations real |
|---|---|---:|---:|---:|---:|---:|
| Standard | Baseline | 80 | 1.00 | 1.00 | **1.00** | — (none given) |
| Standard | **Agent, app's search** | 77 | 1.00 | 0.98 | 0.99 | **107 / 107** |
| Standard | Agent, tuned search | 77 | 1.00 | 0.94 | 0.97 | 102 / 102 |
| Hard | Baseline | 33 | 0.80 | 1.00 | 0.89 | — (none given) |
| Hard | **Agent, app's search** | 33 | 0.94 | 1.00 | **0.97** | **35 / 35** |
| Hard | Agent, tuned search | 33 | 0.88 | 0.94 | 0.91 | 35 / 35 |

The earlier findings hold on more data: the agent clearly beats a single prompt on the hard traps and is the only one whose evidence can be checked, with all 142 citations verified. The agent checks at most 12 skills per job, so 3 of the template's 15 standard skills weren't scored for it.

The tuned search, which wins the search-only test below, made the agent *worse*. What it missed were exact identifiers such as `ContextVar`, `ParamSpec`, `to_thread` and `sentry_sdk`: the agent writes its own queries full of library names, which is where keyword matching is strongest, and the tuned setting turns keywords down. The search test scores one plain query at a time, which isn't how the agent searches, so the app keeps equal weights. Reproduce with the Evals workflow's `agent-rerun` run.

### Code search quality

From [`evals/results/retrieval.json`](evals/results/retrieval.json): can search find real evidence for a skill? The queries are the 65 skills labelled present across both sets. A code chunk counts as relevant when it contains that skill's proof, the same pattern [`check_labels.py`](evals/check_labels.py) verifies against the real files, so the labels need no AI. Success@k: a relevant chunk is in the top k. MRR: how high the first one ranks.

| Method | Success@1 | Success@5 | MRR@10 | Paraphrased skills (15): Success@1 / MRR |
|---|---:|---:|---:|---:|
| Keyword (BM25) | 0.32 | 0.55 | 0.42 | 0.20 / 0.32 |
| Vector | 0.38 | **0.83** | 0.57 | **0.33** / **0.53** |
| Hybrid, equal weights (in use) | 0.32 | 0.71 | 0.49 | 0.13 / 0.36 |
| **Hybrid, tuned** | **0.46** | 0.82 | **0.61** | 0.27 / 0.48 |

The equal-weight hybrid the app uses scores *below* vector search alone, worst on paraphrased skills, because weak keyword matches push good vector matches down. Giving keywords a quarter of the weight with a sharper fusion curve (RRF k=10) fixes that. The setting was tuned on the first 26 standard queries only, so the other 39 are a held-out check, and it held: on the 28 queries added later it reached Success@1 0.43 against 0.36 for every other method, and MRR 0.61 against at most 0.57. Despite that, the full agent did worse with the tuned setting (see above), so the app keeps equal weights.

Reproduce: `python -m evals.retrieval` (reuses the evaluation index; query vectors are cached).

### Distilled reranker (tried, not adopted)

Could a small model rerank the search results better? [`evals/reranker.py`](evals/reranker.py) had Gemini score the top 20 chunks for each of the 65 queries (0-3), then fine-tuned a small cross-encoder (`ms-marco-MiniLM-L6-v2`, about 22M parameters) on those scores from five repositories, on a free CPU runner. It was tested on the other three repositories, judged by the proof-pattern labels rather than by Gemini ([`evals/results/reranker.json`](evals/results/reranker.json)):

| Method (26 test queries, unseen repositories) | Success@1 | Success@5 | MRR@10 |
|---|---:|---:|---:|
| **Search order (tuned hybrid)** | **0.42** | **0.85** | **0.61** |
| Cross-encoder, not trained | 0.23 | 0.77 | 0.44 |
| Cross-encoder, distilled from Gemini | 0.19 | 0.73 | 0.42 |

Reranking made results worse, so the app keeps the search order. Two reasons stand out: the base model was trained on web passages, not code, and the teacher was far more generous than the test (it scored 636 of 1,300 candidates as relevant, against 322 that hold the proof), agreeing with the labels only 67% of the time. Fine-tuning taught the student the teacher's broader idea of relevance, which the strict test doesn't reward. A code-trained base model and teacher scores filtered for agreement would be the next things to try.

Reproduce: the **Evals** workflow's `reranker` run (`python -m evals.reranker label`, then `train`, with `requirements-reranker.txt`).

### Confidence calibration

Can the agent's confidence be trusted? [`evals/calibration.py`](evals/calibration.py) recorded, for each of the 68 labelled skills, the verified level, the citations that held up, any rejected claims, and Gemini's own stated confidence. Four ways of turning that into a probability were compared by **leave-one-repository-out cross-validation**, so every repository was scored by a model that never saw it ([`evals/results/calibration.json`](evals/results/calibration.json)):

| Method | Calibration error (ECE) ↓ | Brier score ↓ | AUROC ↑ | Accuracy at 0.5 |
|---|---:|---:|---:|---:|
| Gemini's own confidence | **0.041** | 0.050 | 0.959 | 0.94 |
| Verified level only | 0.118 | 0.043 | 0.951 | **0.97** |
| Gemini's confidence, rescaled | 0.113 | 0.064 | 0.936 | 0.94 |
| **Logistic regression on all of it** (in use) | 0.077 | **0.030** | **0.973** | 0.96 |

<p align="center"><img src="docs/images/calibration.svg" alt="Reliability chart: how often each method was right at each confidence level" width="560"></p>

Gemini's own confidence turned out better calibrated than expected. The learned model is still the one the app uses: it has the lowest Brier score, which rewards being both calibrated and right (40% lower than Gemini's own), and it best separates real skills from absent ones. Its higher ECE comes mostly from confidence bands holding only one or two of the 68 records, where a single example moves the number a lot. The strongest signals are a verified "strong" level and the number of citations that held up; a rejected claim slightly *raises* the probability, because the agent mostly misquotes evidence that does exist. With 68 records these numbers are indicative.

Reproduce: the hand-started **Evals** workflow collects records (`python -m evals.calibration collect`, uses Gemini) and analyses them (`python -m evals.calibration analyze`, no AI), writing the model to [`confidence_model.json`](codesynapse/agents/confidence_model.json).

---

## 🔧 Running locally

Requires Python 3.14 and a [Gemini API key](https://aistudio.google.com/apikey).

```bash
git clone https://github.com/SwarangiK-21/CodeSynapse.git
cd CodeSynapse
py -3.14 -m venv venv                         # macOS/Linux: python3.14 -m venv venv
venv/Scripts/python.exe -m pip install -r requirements-dev.txt
cp .env.example .env                          # then add GEMINI_API_KEY
venv/Scripts/python.exe app.py
```

The app runs at `http://localhost:7860`; API docs are at `http://localhost:7860/docs`. Without `DATABASE_URL` it uses a local SQLite file. On macOS/Linux use `venv/bin/python`. `requirements-dev.txt` includes the test tools and the MCP server's dependencies.

Optional settings in `.env`:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL with pgvector; plain `postgresql://` URLs, as Supabase gives them, work as-is |
| `GITHUB_TOKEN` | Raises GitHub's rate limit for downloading repositories |
| `GEMINI_MODELS` | Comma-separated models to try in order |
| `UI_SECRET` | Encrypts the browser's copy of the user token; required when deployed |
| `WORKERS` | How many indexing and analysis jobs run at once (default 2) |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `PUBLIC_URL` | Turn on "Sign in with GitHub" ([setup](docs/DEPLOY.md)) |

Checks:

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

### Deploying your own copy

The live demo runs on a Hugging Face Space (Docker) with Supabase Postgres. [`docs/DEPLOY.md`](docs/DEPLOY.md) covers the database, the Space secrets and the trusted-publisher setup that lets GitHub Actions deploy without a stored token.

---

## 🤖 Use it from an AI assistant (MCP)

[`codesynapse/mcp_server.py`](codesynapse/mcp_server.py) is a [Model Context Protocol](https://modelcontextprotocol.io) server, so Claude Desktop, Claude Code, Cursor or any MCP client can use CodeSynapse in conversation: *"index my repo and check it against this job post"*, *"which claims on my resume does my code back up?"*.

| Tool | What it does |
|---|---|
| `index_repository` | Adds a public GitHub repository and waits until it is searchable |
| `list_repositories` | Lists your indexed repositories |
| `search_code` | Searches by keywords and meaning; every result links to the exact lines |
| `start_skill_check` | Starts checking repositories against a job description |
| `start_resume_check` | Starts checking each claim on a resume against repositories |
| `get_report` | Returns progress, or the finished report with its evidence links |

Analyses take minutes, longer than assistants wait for one call, so they are started by one tool and collected with `get_report`. The server talks to the live demo by default; set `CODESYNAPSE_URL` to use your own. On first use it creates a private user and keeps the token in `~/.codesynapse/token`.

```bash
pip install -r requirements-mcp.txt
```

**Claude Code:**

```bash
claude mcp add codesynapse -- python /path/to/CodeSynapse/codesynapse/mcp_server.py
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "codesynapse": {
      "command": "python",
      "args": ["/path/to/CodeSynapse/codesynapse/mcp_server.py"]
    }
  }
}
```

---

## 🔌 API

Create a user with `POST /api/users`, then send the returned token as `Authorization: Bearer <token>`. Expensive actions are limited per user each hour (5 analyses, 10 repositories, 20 job descriptions or resumes, 40 coach messages); over the limit the API returns `429` with a `Retry-After` header. Indexing and analysis return `202` at once and finish in the background, so poll their status.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/users` | Create a user and get a token |
| GET, PUT | `/api/profile` | Read the profile, or sync it from live stats |
| GET, POST, DELETE | `/api/chat` | Read history, ask the coach, or clear history |
| GET | `/api/report` | Download the PDF report |
| GET, POST | `/api/repos` | List repositories with their status, or start indexing a public one in the background |
| DELETE | `/api/repos/{id}` | Remove an indexed repository |
| GET | `/api/search?q=` | Search indexed code by keyword and meaning |
| POST | `/api/jobs` | Extract skills from a job description |
| GET | `/api/jobs/{id}` | Read a parsed job description |
| POST | `/api/resumes` | Read a resume (PDF upload or `text` form field) and extract its claims; pass the returned id as `job_id` to `/api/analyses` |
| POST | `/api/analyses` | Start a skill-gap analysis |
| GET | `/api/analyses/{id}` | Read status, report, step trace and token usage |
| POST | `/api/analyses/{id}/approve` | Approve a draft report |
| GET | `/api/analyses/{id}/markdown` | Export a report as Markdown |
| GET | `/health` | Health check |

---

## 🗂️ Project structure

```
CodeSynapse/
├── app.py                     # Entry point: runs migrations, recovers interrupted jobs, starts the server
├── codesynapse/
│   ├── main.py                # FastAPI app with the Gradio UI mounted
│   ├── config.py              # Settings from environment variables
│   ├── mcp_server.py          # MCP server for AI assistants (talks to the REST API)
│   ├── agents/                # LangGraph agent, deterministic verifier, confidence model
│   ├── api/routes.py          # REST endpoints
│   ├── services/              # Search, indexing, job and resume parsing, analyses, background jobs,
│   │                          # rate limits, cache, Gemini calls and model fallback, coach, reports
│   ├── ui/                    # Gradio interface, report components and theme
│   └── db/                    # Models, session and migration runner
├── evals/                     # Benchmark cases, agent/baseline runner, retrieval and calibration
│                              # evaluations, injection attacks, metrics, saved results
├── migrations/                # Alembic migrations
├── deploy/push_space.py       # Uploads the app to the Hugging Face Space
├── docs/                      # Deployment guide and screenshots
├── scripts/check_models.py    # Lists Gemini models your key can use
├── tests/                     # pytest suite; external services are mocked
├── requirements-mcp.txt       # Extra dependencies for the MCP server only
└── .github/workflows/         # ci.yml (lint, tests, Docker build), deploy.yml, evals.yml
```

---

## 💼 Use cases

- A student checks which skills from a target job description their repositories already prove — with links to the lines.
- A student checks their resume before applying: which claims are backed by public code, and what to build for the rest.
- Someone asks their AI assistant, through the MCP server, to search their projects or check them against a job post, without leaving the chat.
- A mentor reviews a student's live coding stats and asks the coach for a focused 4-week plan.
- Recruiters or reviewers search a candidate's public code by concept ("JWT validation", "retry with backoff").

## ⚠️ Limitations

- Evaluation sets are small (standard: 8 repositories, 80 skill pairs; hard: 8 repositories, 33 pairs), so results are indicative, not statistically strong. The agent and baseline results above were measured on the first 46 and 22 pairs.
- The confidence model was trained on 68 labelled skills; its probabilities are a guide, not a guarantee.
- The live demo runs on free tiers: the Space sleeps when idle, Gemini's daily embedding quota limits how much new code can be indexed in a day, and an overloaded Gemini model can make an analysis slow.
- Only public repositories are indexed; GitHub and Gemini rate limits apply (set `GITHUB_TOKEN` for higher GitHub limits). Scanned-image resumes need their text pasted.
- "Not found" means no evidence was found in the code searched, not that the person lacks the skill or that a resume claim is false.
- Without the GitHub OAuth settings, users are anonymous per browser.
- Background jobs, rate limits and model fallback live in one process, which suits a single server. Several servers would need a shared queue and store such as Redis.

## 🗺️ Roadmap

- [x] Live GitHub and LeetCode stats
- [x] AI coach with stats context, conversation memory and model fallback
- [x] Per-user data on PostgreSQL with migrations
- [x] REST API, automated tests and CI
- [x] Index public repositories and search code with hybrid retrieval
- [x] Extract skills from job descriptions, each backed by a quote
- [x] Multi-step agent with cited, verified evidence
- [x] Evaluation suite with measured accuracy and prompt-injection tests
- [x] Background indexing and analysis, rate limiting, and caching of AI results
- [x] Live deployment on Hugging Face with Supabase, deployed automatically from CI
- [x] Redesigned interface with light and dark themes
- [x] Retrieval evaluation (Success@k, MRR, nDCG) and tuned hybrid search
- [x] Resume claim checker
- [x] MCP server for AI assistants
- [x] Calibrated confidence, trained and evaluated with leave-one-repository-out cross-validation
- [x] Re-ran the agent with the tuned search (it did worse end to end, so the app keeps equal weights)
- [x] Distilled reranker experiment (measured; it didn't beat the search order, so it isn't used)
- [x] Larger evaluation sets (68 → 113 labelled pairs, every label checked against the real files)
- [x] Sign in with GitHub, with data shared across devices

## 🤝 Contributing

Issues and pull requests are welcome. Run `ruff check .` and `pytest` before opening a PR, and never commit `.env` or API keys.

---

<p align="center">Built by <a href="https://github.com/SwarangiK-21">Swarangi Kothawade</a> · <a href="https://www.linkedin.com/in/swarangikothawade/">LinkedIn</a></p>
