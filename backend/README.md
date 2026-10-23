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

## Retained utility scripts

- `python -m app.scripts.seed_demo`
- `python -m app.scripts.ingest_seed_policies`
- `python -m app.scripts.search_policies`

Temporary patch scripts, endpoint smoke scripts, bytecode caches, virtual
environments, and repository metadata are intentionally excluded.
