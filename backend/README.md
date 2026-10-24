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

## Execution, GitHub and notifications

Approved actions go to the n8n executor (workflows in `../n8n/`). Each payload
names its `target`:

- `github`: the resource has a `details_data.github` block (repo plus a
  collaborator or an existing deploy key) and `GITHUB_ORG` and
  `GITHUB_READ_TOKEN` are set (not in OFFLINE mode). n8n calls the GitHub API
  with its write token. The backend then checks GitHub itself with the
  read-only token (`app/github/verifier.py`) and only then updates the
  resource row and marks the action VERIFIED. n8n's answer is never evidence.
- `mock`: everything else goes through `/mock/resources/apply` and is
  verified against the database, as before.

Agent credential DOWNSCOPE and REASSIGN rotate the deploy key (Agent Policy
rule 6): the backend generates an ed25519 public key (needs `cryptography`),
stores it on the action before dispatch so retries reuse it, and discards the
private key. n8n must answer non-2xx on failure; an explicit `status: FAILED`
in a 2xx body is also treated as a failure.

Notifications (`app/notifications/service.py`) go to `N8N_NOTIFIER_WEBHOOK`
when a plan is submitted for approval and when Guardian finds impacts. They
are best-effort and never fail the business action.

## Explainability, evidence and evaluation

- `GET /plans/{plan_id}/explanation`: data for the "why" panel. For each
  step: cited policy evidence (version, status, the policy's numbered
  clauses), approved lessons listed separately, the step's reason, how it was
  verified, and whether the AI plan passed validation first time or needed
  its one repair. No chain-of-thought.
- `GET /cases/{case_id}/evidence` (HTML, printable; `?format=json`): ISO/IEC
  27001:2022 supporting evidence for controls 6.5, 5.11, 5.18 and 8.2. It
  says on the page that it is not a certification.
- `python -m app.scripts.run_evaluation` writes `data/eval/latest.json`
  (served by `GET /evaluation/latest`): plan first-pass and after-repair
  validity, policy-evidence coverage, retrieval recall@1/@3 on seeded
  questions, Guardian recall and false impacts on seeded scenarios, verified
  completion, recovered retries and absorbed replays. Every number carries its
  sample size. Run it after rehearsals and before `reset_demo`.

## Agent access requests (MCP gateway, backend side)

Agents call these through the MCP adapter (`mcp_server/`, separate process)
with their own key in `X-Agent-Key`; the backend stores only its SHA-256 hash
on the agent (`AURORA_BOT_MCP_KEY` seeds Aurora Release Bot's hash).

| Endpoint | MCP tool |
| --- | --- |
| `GET /agent-identity` | `whoami` |
| `POST /access-requests` | `request_access(system, resource, permission, duration_minutes, reason)` |
| `GET /access-requests/{id}` | `check_request` |
| `GET /access-grants/mine` | `list_my_access` |
| `POST /access-grants/{grant_key}/release` | `release_access` |
| `POST /access-grants/expire-due` | n8n sweeper, `Authorization: MCP_SERVICE_TOKEN` |

Each request is an ACCESS_REQUEST case with one GRANT_TEMPORARY action, so
approval, execution, verification and audit are the usual ones. Tiers come
from rules (`app/access_requests/tiers.py`), not the LLM: LOW (read on a
non-confidential repo, active sponsor, ≤24 h) is approved and executed at
once; HIGH (write, or a confidential repo, ≤8 h) waits for the IT Owner and
runs as soon as it is approved; DENY (production/admin, no active sponsor,
over the limit) is refused with its reason. The LLM only writes a one- or
two-line note for the approver. Expired grants are revoked and marked EXPIRED.

## Policy Guardian and live agent access

Activating a new policy version (`POST /policy-guardian/activate`, e.g. with
`data/seed/access_policy_v2.md`) still marks linked lessons stale and pauses
open plans, and now also re-checks live agent access
(`app/policy_guardian/resource_rules.py`). For every active agent, agent
credential or GitHub access granted by a plan linked to the old version, the
clauses that are new in this version are evaluated by code, never by the LLM:

| Rule (Access Policy V2) | Finding | Fix |
| --- | --- | --- |
| 7. agent write to a confidential repo needs a sponsor with `SECURITY-CONFIDENTIAL` training | HIGH, `REGENERATE` | `POST /policy-guardian/impacts/{id}/remediate` opens an ACCESS_REQUEST case with one DOWNSCOPE action for the IT Owner to approve; it executes and verifies like any plan, and the impact is RESOLVED when the case completes |
| 8. a changed sponsor needs IT Owner re-certification | MEDIUM, `REVIEW` | `POST /policy-guardian/impacts/{id}/recertify` by an IT Owner |

`GET /workforce/graph` marks agents with an open impact (`policy_violation`).

## Demo mode

`DEMO_MODE` in `.env` decides how AI calls and execution behave
(`app/demo/`), and `GET /demo/mode` reports it for the Dashboard badge:

| Mode | LLM and embeddings | Execution |
| --- | --- | --- |
| `LIVE` | OpenAI, every answer recorded to `data/demo_cache/` | n8n, real GitHub when configured |
| `CACHED_AI` | recorded answer first, OpenAI only on a miss | n8n, real GitHub when configured |
| `OFFLINE` | recorded answers only; a miss is an error | in-process mock executor, no n8n/GitHub |

All LLM calls go through LangChain's global cache (`install_demo_llm_cache`
in `app/main.py`); embeddings go through `get_embedding_model()`. Cache keys
replace per-run case/plan/action UUIDs and full timestamps with placeholders,
so a rehearsal after `reset_demo` reuses earlier answers; seeded person IDs
are kept. Rehearse each scene once in LIVE to fill the cache, and commit
`data/demo_cache/` so another laptop can run OFFLINE (it holds model answers
and vectors, no secrets).

## Demo company seed

`python -m app.scripts.seed_company` creates the fictional Nexora Labs company:
the six story characters with their fixed UUIDs, about 80 generated people in
eight departments, their resources, and 24 AI agents (each with a credential).
A fixed random seed and uuid5 IDs make every run identical, and re-running it
is safe. Three agents start as orphans (inactive sponsor, departing sponsor,
expired access); Arif's two Aurora agents become orphans because he is
departing. Nabil deliberately has no `SECURITY-CONFIDENTIAL` training.

`python -m app.scripts.reset_demo --yes` removes demo cases, plans, approvals,
learning and audit rows for every seeded person, re-seeds the company, and
then resets the seed policies to V1 (see below).

`python -m app.scripts.reindex_policies` rebuilds the Qdrant policy index
when the collection is lost: it creates the collection and the
`policy_version_id` payload index if missing, then re-indexes V1 of each seed
policy from the text stored in PostgreSQL (checked against its content hash).
It never changes policy status. Run it before `reset_policies` on a new cluster.

`python -m app.scripts.reset_policies` brings ACCESS, EQUIPMENT, OFFBOARDING
and AGENT back to V1: it deletes later versions with their policy changes,
impacts, impact approvals and policy links, makes V1 CURRENT, and removes the
later versions' Qdrant points. It stops without changes if a V1 has no Qdrant
points. This is what lets every rehearsal activate Access Policy V2 again.

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
