# LivingOps AI — instructions for Claude

LivingOps AI is Sajid Ahasan's project for the **International AI Builders Congress 2026**, AI InfraSphere track (WorkforceOS + AgentOps). The final is on **26 December 2026** at Daffodil International University, Dhaka. We are now executing the final build plan.

## Read these first, every new session

1. `docs/FINAL_PLAN.md` — the frozen build plan: positioning, demo script, technical design, schedule, cut line. **Source of truth.**
2. `docs/CONTEXT.md` — why each decision was made, what was rejected and why, environment facts, known bugs. Read before proposing anything new.
3. `docs/ORIGINAL_PLAN_BOOK.md` — the original v2.0 plan book (API contracts, state machines, conventions). Still valid unless `FINAL_PLAN.md` overrides it.

## Working rules (from Sajid — always follow)

- **No action without permission.** Before editing files or running anything that changes state (installs, migrations, git commits, pushes, API calls that write), state the plan in a few lines and wait for approval. Reading files and running read-only checks is fine.
- **Reply in Bangla (Bengali script), keep technical terms in English.** Not romanized Bangla.
- Work on the **`final-build`** branch. Never commit to `main` directly; `main` must always hold a working demo.
- **Never commit or print secrets.** `.env` stays local. Never paste tokens into code, docs, chat or commits. Use `.env.example` with placeholders.
- Do not reopen the frozen plan. If a concrete technical test proves part of it infeasible, explain and propose the smallest change, then update `docs/CONTEXT.md` (decision log) after Sajid agrees.
- Do not add features outside `FINAL_PLAN.md`. Rejected ideas are listed in `docs/CONTEXT.md`.
- When behaviour changes, update the README / demo reset and add a line to the decision log.
- Commit messages name the work package, e.g. `W1 agent enums + migration`.

## Engineering conventions (from the plan book)

- **Synchronous Python only**: normal FastAPI `def` endpoints, sync SQLAlchemy sessions, `requests`, LangGraph `invoke`, sync Qdrant client. The MCP server is a thin separate adapter that calls the REST API; it holds no state.
- Modular monolith. No Celery, Redis, Kafka, WebSockets, microservices. Frontend polls.
- FastAPI + PostgreSQL own business state. LangGraph reasons. n8n executes only approved actions. Qdrant retrieves.
- The LLM never writes to the DB or Qdrant directly and never executes high-risk actions without human approval. Risk tiers and impact detection are **deterministic rules**, not LLM decisions; the LLM retrieves evidence and writes explanations.
- **Independent verification:** an action becomes `VERIFIED` only after the backend checks the external system itself (GitHub via a read-only token), never from n8n's response alone.
- n8n must return **non-2xx** on failure (the backend treats any 2xx JSON as success today).
- Every plan step cites evidence IDs (`POL-<CODE>-V<n>-C<i>`). No chain-of-thought stored or shown.
- Every demo scene must work in `LIVE`, `CACHED_AI` and `OFFLINE` modes and give the same result.

## Environment

- Windows PC, Python virtual environment at `newenv/` (also has Anaconda). Backend runs from `backend/`: `python -m uvicorn app.main:app --reload`. Frontend: `cd frontend && python serve_frontend.py` (port 5173, proxies `/api` to 8000). Demo CLI: `python -m app.scripts.demo_cli`.
- Services: PostgreSQL on Supabase, Qdrant Cloud, OpenAI (`gpt-4o-mini`, `text-embedding-3-small`), n8n deployed on Render + Supabase and pinged every 3 minutes to stay awake. Only n8n is kept awake (Render free plan has 750 instance-hours/month).
- GitHub repo: `sajid-ahassan/LivingOS`.
- Tests: `cd backend && python -m pytest -q`.

## Demo characters (fixed UUIDs in `backend/app/scripts/seed_demo.py`)

Farhana Islam (HR Manager), Nabil Chowdhury (Engineering Manager), Tahmid Hasan (IT Security Owner), Amina Rahman and Rafi Ahmed (new AI Engineers), Arif Hossain (Senior Software Engineer, departing). Hero agent: **Aurora Release Bot**, sponsored by Arif, write access to the `aurora` repo via a real GitHub deploy key.
