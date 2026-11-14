# Deploying the live demo

The app runs on a Hugging Face Space (Docker) and keeps its data in Supabase Postgres,
which includes pgvector. Space storage is wiped on every restart, so the database must
live outside it. Both free tiers are enough for a demo.

Every push to `main` that passes CI is uploaded to the Space by
[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml).

## 1. Create the database (Supabase)

1. In the Supabase dashboard, create a new project (any name, region `ap-south-1` is closest
   to India). Save the database password it shows.
2. Open **Connect**, choose **Session pooler**, and copy the URI. It looks like
   `postgresql://postgres.<ref>:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`.
   Put your password in place of `[YOUR-PASSWORD]`.
   - Use the session pooler, not the direct connection: free projects only offer the direct
     connection over IPv6, which Spaces can't reach.
   - Use port 5432 (session mode), not 6543 (transaction mode).
   - The plain `postgresql://` form is fine; the app selects its driver itself.

The first start creates the tables and enables pgvector (`CREATE EXTENSION vector`).

## 2. Set the Space secrets (Hugging Face)

In the Space, open **Settings → Variables and secrets** and add these as **secrets**:

| Name | Value |
|---|---|
| `DATABASE_URL` | The session pooler URI from step 1 |
| `GEMINI_API_KEY` | Your Gemini key |
| `UI_SECRET` | A long random value, for example from `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `GITHUB_TOKEN` | Optional: a GitHub token with no scopes, to raise the API rate limit |

The app refuses to start on a Space without `UI_SECRET`.

## 3. Connect GitHub to the Space (no token needed)

GitHub signs in to Hugging Face as a *trusted publisher*: each deploy run proves it is this
repository's `deploy.yml` on `main` and gets a token that lasts one hour and only works for
this Space. Nothing is stored as a secret.

1. In the Space, open **Settings → Trusted Publishers → Add trusted publisher** and set:
   - Provider: **GitHub Actions**
   - Repository: `SwarangiK-21/CodeSynapse`
   - Branch: `main`
   - Workflow: `deploy.yml`
   - Leave **Read-only** unticked.
2. In the GitHub repository, open **Settings → Secrets and variables → Actions → Variables**
   and add the variable `HF_SPACE` = `SwarangiK-21/CodeSynapse`.
3. Run the **Deploy** workflow once from the **Actions** tab, or push to `main`.

The Space then builds the Docker image, which takes a few minutes. Check `/health` on the
Space URL when it's done.

To deploy by hand instead, set `HF_SPACE` and an `HF_TOKEN` with write access, then run
`python deploy/push_space.py`.

## What gets uploaded

Only what the container needs: `app.py`, `Dockerfile`, `requirements.txt`, `alembic.ini`,
`codesynapse/`, `migrations/` and the README with its images. Tests, evals and `.env` are
never uploaded. The README gets the Space settings header (`sdk: docker`, `app_port: 7860`)
added on upload; the GitHub copy stays unchanged.

## Limits of this setup

- One container runs everything, so jobs and rate limits are kept in memory (see
  `codesynapse/services/tasks.py` and `limits.py`).
- Free Spaces sleep after a period without visitors; the first visit after that takes a
  minute to wake up.
- Free Supabase projects pause after a week without activity. Restore them from the dashboard.
