# LivingOps AI backend

FastAPI backend of LivingOps AI. See the root README for the overview and
the one-command local start.

## Run locally on Windows

1. Preserve your existing `.env`; do not copy it into source control.
2. Activate the Python 3.11 environment.
3. From this `backend` directory, install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Start the API:

   ```powershell
   uvicorn app.main:app --reload
   ```

5. Open `http://127.0.0.1:8000/docs` or check
   `http://127.0.0.1:8000/health`.

## Database schema (Alembic)

The schema is managed by Alembic migrations in `migrations/versions/`. Run
these from this `backend` directory; the database URL comes from `.env`.

- Fresh database: `alembic upgrade head`
- Database created earlier by `Base.metadata.create_all` (the Supabase demo
  database): `alembic stamp 0001` once, then `alembic upgrade head`
- Check the current revision: `alembic current`

Every change to a value in `app/enums.py` needs a migration that updates
`ENUM_CHECKS`; `tests/test_migrations.py` fails otherwise.

The n8n Header Auth credential in the current workflow uses the
`Authorization` header. `N8N_SHARED_TOKEN` must contain its exact value,
including a `Bearer ` prefix if one is configured in n8n.

## Retained utility scripts

- `python -m app.scripts.seed_company`
- `python -m app.scripts.seed_demo` (story characters only)
- `python -m app.scripts.ingest_seed_policies` (ACCESS, EQUIPMENT, OFFBOARDING, AGENT)
- `python -m app.scripts.search_policies`

Temporary patch scripts, endpoint smoke scripts, bytecode caches, virtual
environments, and repository metadata are intentionally excluded.
