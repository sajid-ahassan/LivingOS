# LivingOps AI backend

This package contains the Stage 1 foundation and the implemented Stage 2
case-planning, approval, and n8n execution flow.

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

## Recover the current interrupted plan

The previous HTTP response failed after the email resource was committed.
With this fixed backend, call the existing retry endpoint once:

```powershell
$planId = "7398803d-8a29-48e6-8fc7-e5c49c4b68b9"
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/plans/$planId/retry"
```

The runner will reconcile the existing email through its idempotency key,
mark that action successful without sending a third request, and continue the
remaining pending actions. If the database no longer contains that plan, use
the normal case workflow instead.

## Demo company seed

`python -m app.scripts.seed_company` creates the fictional Nexora Labs company:
the six story characters with their fixed UUIDs, about 80 generated people in
eight departments, their resources, and 24 AI agents (each with a credential).
A fixed random seed and uuid5 IDs make every run identical, and re-running it
is safe. Three agents start as orphans (inactive sponsor, departing sponsor,
expired access); Arif's two Aurora agents become orphans because he is
departing. Nabil deliberately has no `SECURITY-CONFIDENTIAL` training.

`python -m app.scripts.reset_demo --yes` removes demo cases, plans, approvals,
learning and audit rows for every seeded person and re-seeds the company.
Policy versions are kept.

Read-only agent endpoints: `GET /agents`, `GET /agents/orphans`,
`GET /agents/{resource_key}`, `GET /agents/{resource_key}/grants`, and
`GET /workforce/graph` for the dashboard map.

## Retained utility scripts

- `python -m app.scripts.seed_company`
- `python -m app.scripts.seed_demo` (story characters only)
- `python -m app.scripts.ingest_seed_policies` (ACCESS, EQUIPMENT, OFFBOARDING, AGENT)
- `python -m app.scripts.search_policies`

Temporary patch scripts, endpoint smoke scripts, bytecode caches, virtual
environments, and repository metadata are intentionally excluded.
