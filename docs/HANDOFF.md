# LivingOps AI — Engineering Handoff

Written 23 October 2026 for Claude Code, at the end of a long planning conversation between Sajid Ahasan and Claude. This is the single document to read first. It tells you what the product is becoming, what the code does today (verified by reading it), what is broken, exactly what to build, in what order, and how Sajid wants you to work.

Companion files (read after this one):

- `docs/FINAL_PLAN.md` — the frozen plan as Sajid sees it (Bangla + English): demo script, designs, schedule, cut line.
- `docs/CONTEXT.md` — hackathon facts, the 14 decisions with reasons, rejected ideas, market evidence with sources, decision log.
- `docs/ORIGINAL_PLAN_BOOK.md` — the original v2.0 plan book (9 Sep 2026). Its API contracts, state machines and conventions still apply unless this handoff or `FINAL_PLAN.md` says otherwise.

If anything here conflicts with what you see in the code, **the code is the truth about the present and this document is the truth about the target**. Tell Sajid about any conflict before acting on it.

---

## 0. First session protocol

Do these in order, and do not change any code until step 5 is approved.

1. Read this file, then `CLAUDE.md`, `docs/CONTEXT.md`, `docs/FINAL_PLAN.md`.
2. Run `git status`, `git branch -a`, `git log --oneline -5`. This handoff was written against commit **`5877e00` "stage 3 complete"** on `main` (GitHub `sajid-ahassan/LivingOS`). The local folder may have uncommitted work; report any differences.
3. Confirm the environment: activate `newenv` (Windows: `newenv\Scripts\activate`), check `python --version` (plan book says 3.11), `cd backend && python -m pytest -q` (23 tests, unit-level, no DB needed), and whether `.env` exists (never print its values).
4. Ask Sajid's permission, then create branch `final-build` from `main`, commit `CLAUDE.md` and `docs/`, push.
5. Reply to Sajid **in Bangla (technical terms in English)** with: your understanding of the goal (5 lines max), the Week 1 plan from §9 adapted to what you found, and anything unclear or missing. Wait for approval.

---

## 1. What we are building, in one paragraph

LivingOps AI becomes **the operating layer for hybrid human + AI workforces: every access has an owner, a policy reason, an expiry, and proof.** People and AI agents go through the same governed lifecycle (onboard, request access, change sponsor, offboard). An LLM reads company policy (hybrid RAG) and drafts plans with evidence IDs; deterministic validators and humans approve; n8n executes only approved actions, including against a **real GitHub organization**; the backend **independently verifies** results with its own read-only GitHub token; everything is audited. When a policy changes, the **Policy Guardian** finds every plan, learned lesson and **live agent access** that now violates it and proposes remediation. Agents ask for access through an **MCP server** with deterministic risk tiers (auto-approve low risk, human approval for high risk, deny the forbidden) and time-limited grants that expire automatically.

The demo is **one story**: Arif Hossain leaves; his **Aurora Release Bot** becomes an orphan; manager Nabil corrects the AI plan (hand the bot to me, read-only); execution revokes Arif's real GitHub access and swaps the bot's deploy key; the correction becomes an approved lesson; later the bot asks via MCP for 2 hours of write access and IT owner Tahmid approves; then **Access Policy V2** lands and Guardian flags both the bot's live grant and the lesson; one remediation fixes it. Then an ISO 27001 evidence report, an evaluation panel, KPIs.

Target event: International AI Builders Congress 2026, **final 26 Dec 2026**, InfraSphere AI track (WorkforceOS + AgentOps). Rubric: Innovation 20, Technical Execution 20, Business + Global 20, Impact + Ethical AI 20, Scalability + NRB 10, Presentation 10. Details in `CONTEXT.md` §1.

---

## 2. How Sajid works (non-negotiable)

- **No action without permission.** Before editing files or running anything that changes state (pip install, migrations, seed/reset against Supabase, git commit/push, any API call that writes, GitHub/n8n calls), describe the plan in a few lines and wait. Read-only exploration and running the unit tests is fine.
- **Bangla replies** in Bengali script, technical terms in English. Never romanized Bangla.
- He is a final-year CSE student with ~2 years of data science / ML / LangChain / LangGraph / n8n. Explain decisions briefly; don't lecture.
- He wants the product to look and feel exceptional to judges, but every AI feature must earn its place: **"Can we show a case where AI did something plain code could not? If not, use plain code."**
- He decided: no surveys, no company interviews, no new research needed to proceed. Do not suggest them.
- The plan is frozen. Change it only when a concrete technical test proves a part infeasible; then propose the smallest change and log it in `CONTEXT.md` §7 after he agrees.
- Secrets never go into chat, code, docs, commits or logs.
- Work on `final-build`; keep `main` demo-able. Commit messages name the work package (`W1.2 agent enums + migration`).

---

## 3. Environment and services

| Thing | Value |
| --- | --- |
| OS | Windows (PowerShell / Git Bash). Paths contain a space: `C:\Users\sajid\Desktop\Living ops` — quote them. |
| Python env | `newenv/` virtualenv in the project root (Anaconda also installed). |
| Backend | `cd backend` then `python -m uvicorn app.main:app --reload` → http://127.0.0.1:8000/docs |
| Frontend | `cd frontend` then `python serve_frontend.py` → http://127.0.0.1:5173 (proxies `/api/*` to 8000; override with `LIVINGOPS_BACKEND`) |
| Demo CLI | `cd backend` then `python -m app.scripts.demo_cli` (interactive) or `python -m app.scripts.demo_cli reset` |
| Tests | `cd backend` then `python -m pytest -q` |
| Database | PostgreSQL on Supabase. `config.py` rewrites `postgresql://` to `postgresql+psycopg://`. Tables via `Base.metadata.create_all` (`database.init_db`). No Alembic yet. |
| Vectors | Qdrant Cloud, collection `policy_knowledge_v1`, 1536-dim cosine, payload index on `policy_version_id`. |
| LLM | OpenAI `gpt-4o-mini` (`OPENAI_CHAT_MODEL`), embeddings `text-embedding-3-small`. |
| n8n | Live on Render + Supabase, pinged every 3 minutes so it never sleeps. Only n8n is kept awake (Render free plan: 750 instance-hours/month for the whole workspace). Header-auth: backend sends `Authorization: <N8N_SHARED_TOKEN>` (exact value, including `Bearer ` if configured). |
| Settings loading | `.env` read from project root and `backend/.env` (pydantic-settings, `extra="ignore"`). |
| Required env today | `DATABASE_URL`, `QDRANT_URL`, `QDRANT_API_KEY`, `OPENAI_API_KEY`, `N8N_PROVISIONING_WEBHOOK`, `N8N_SHARED_TOKEN` (+ optional `OPENAI_CHAT_MODEL`, `EMBEDDING_DIMENSION`, `REQUEST_TIMEOUT_SECONDS`=30). |
| New env to add | `GITHUB_ORG`, `GITHUB_REPO` (`aurora`), `GITHUB_READ_TOKEN` (backend, read-only), `N8N_NOTIFIER_WEBHOOK`, `DEMO_MODE` (`LIVE`/`CACHED_AI`/`OFFLINE`), `MCP_SERVICE_TOKEN`, `APP_BASE_URL` (for links in notifications). The GitHub **write** token lives only inside n8n credentials. |

The Claude desktop app's local Linux sandbox fails to start on this PC (Hyper-V); that's why work happens here in the Code tab. Not your concern unless asked.

---

## 4. The code today (verified at `5877e00`)

### 4.1 Layout

```text
backend/app/
  main.py            FastAPI app, routers, /health (DB + Qdrant). version "0.2.0-stage2"
  config.py          Settings (pydantic-settings)
  database.py        engine, SessionLocal, Base, get_db, init_db (create_all)
  enums.py           all StrEnums (see 4.3)
  models.py          13 tables (see 4.2)
  schemas.py         mock-company request/response models
  audit/             record_audit_event(), timeline.py (case timeline + coverage)
  cases/             create/get/triage cases, policy_context.py (RAG for a case)
  planning/          onboarding: graph_runner.py, planner.py, prompt.py, validation.py (allow-lists), service.py
  graphs/            LangGraph builders: onboarding.py, offboarding.py, learning.py, guardian.py, contracts.py
  approvals/         submit plan for approval, decide (plan approvals)
  execution/         service.py (dispatch to n8n, retry, state), n8n_client.py, verification.py
  offboarding/       inventory + offboarding plan (graph_runner.py and service.py — duplicated logic)
  handover/          targeted handover capture + approval
  revisions/         manager revision of a plan (new revision, parent link, correction_summary)
  learning/          correction -> candidate -> approval -> sanitize -> index to Qdrant; search
  policy_guardian/   activate V(n+1), deterministic diff + LLM summary, impacts, remediation (regenerate)
  rag/               loader/splitter, chunks, embeddings, Qdrant store, dense + BM25 + RRF hybrid, learning_memory.py
  security/          access events + Isolation Forest scoring + alert review
  ml/                features.py, train.py (SPEDIA), inference.py
  mock_company/      service.py: create/assign/disable/revoke/reassign/request_return with idempotency
  routes/            mock_company.py router (/mock)
  scripts/           seed_demo, ingest_seed_policies, reset_demo, demo_cli, search_policies,
                     patch_resource_state (manual CHECK-constraint patch), smoke_* scripts
backend/tests/       test_api_contracts.py, test_business_rules.py, test_langgraphs.py (23 tests)
frontend/            zero-build HTML/JS: index (Dashboard), cases, workspace (case detail), approvals,
                     guardian, security; app.js (api() helper, base '/api'), styles.css (~270 lines)
data/seed/           access_policy_v1.md, equipment_policy_v1.md, offboarding_policy_v1.md, resource_catalog.json
data/spedia/         ML dataset (CSV, ~72k rows)
models/              isolation_forest.joblib + metrics JSON
backend.zip, frontend.zip   accidental commits (contain __pycache__) — delete in cleanup
```

### 4.2 Data model (models.py)

All PKs are UUID. Enums are stored as **VARCHAR with CHECK constraints** (`string_enum(..., native_enum=False, create_constraint=True)`). **Adding an enum value in Python does not update the existing DB CHECK constraint** — `create_all` never alters existing tables. That is why `scripts/patch_resource_state.py` exists. Every new enum value needs a migration (see W1.2).

| Table | Key columns / notes |
| --- | --- |
| `people` | name, email (unique), app_role, employment_status, department, job_title, manager_id (self FK) |
| `cases` | case_type, subject_person_id, created_by_id, status, priority, case_facts (JSONB), failure_reason |
| `case_plans` | case_id, revision (unique per case), status, plan_data (JSONB), summary, parent_plan_id, correction_summary |
| `case_actions` | case_id, plan_id, action_type, resource_type, requested_data (JSONB), status, idempotency_key (unique), n8n_execution_id, attempt_count (CHECK 0..2), result_data, verification_data, error_message |
| `approvals` | target_type (PLAN/LEARNING/POLICY_IMPACT/HANDOVER), target_id, requested_by, assigned_to, status, comment, decided_at |
| `policy_versions` | policy_code, version_number, status (DRAFT/CURRENT/ARCHIVED), department, effective_from, content_text, content_hash; unique (code, version), unique (code, hash), partial unique index: one CURRENT per code |
| `policy_links` | policy_version_id, subject_type (PLAN/LEARNING), subject_id, use_reason, evidence_ids — **this is how Guardian finds dependents** |
| `learning_records` | source_case_id, source_plan_id, trigger_type, status, candidate_data, memory_text, scope (JSONB, GIN index), qdrant_point_id, stale_reason, content_hash |
| `policy_changes` | policy_code, old/new version ids, diff_data, overall_risk, status |
| `policy_impacts` | policy_change_id, target_type (PLAN/CASE/LEARNING), target_id, risk_level, explanation, recommended_action (REGENERATE/REVIEW/MARK_STALE/NO_ACTION), status, resolved_by |
| `audit_events` | occurred_at, actor_type (USER/SYSTEM/LLM/N8N/ML), actor_id, event_type, entity_type, entity_id, before/after/evidence_data, correlation_id (= case id in practice) |
| `company_resources` | person_id (owner; FK cascade), resource_type, resource_key (unique), status, details_data, source_action_id, idempotency_key (unique) |
| `access_events` | person_id, event_time, source, destination, event_type, success, features_data, anomaly_score (0..1), alert_status, reviewed_by |

### 4.3 Enums today

- `AppRole`: HR_MANAGER, LINE_MANAGER, IT_OWNER, EMPLOYEE, ADMIN
- `EmploymentStatus`: CANDIDATE, ACTIVE, DEPARTING, INACTIVE
- `CaseType`: ONBOARDING, OFFBOARDING · `CaseState`: NEW, PLANNING, PENDING_APPROVAL, APPROVED, EXECUTING, COMPLETED, FAILED, HUMAN_REVIEW, PAUSED, CANCELLED
- `PlanState`: DRAFT, PENDING_APPROVAL, APPROVED, REJECTED, SUPERSEDED, STALE
- `ActionType`: CREATE, ASSIGN, DISABLE, REVOKE, REASSIGN, REQUEST_RETURN
- `ResourceType`: EMAIL_ACCOUNT, GITHUB_ACCESS, LAPTOP, TRAINING, WORK_ITEM, KNOWLEDGE_DOCUMENT
- `ActionState`: PENDING, DISPATCHED, SUCCEEDED, VERIFIED, FAILED, RETRYING, HUMAN_REVIEW, SKIPPED
- `ResourceState`: OPEN, ACTIVE, ASSIGNED, DISABLED, REVOKED, RETURN_REQUESTED, RETURNED, REASSIGNED
- `PolicyImpactTargetType`: PLAN, CASE, LEARNING · `AuditActorType`: USER, SYSTEM, LLM, N8N, ML

### 4.4 Existing API (complete list)

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/`, `/health` | health checks DB + Qdrant |
| POST | `/cases` | `CaseCreateRequest{case_type, subject_person_id, created_by_id, priority, case_facts}`; creator must be HR_MANAGER/LINE_MANAGER/ADMIN |
| GET | `/cases/{case_id}` | |
| POST | `/cases/{case_id}/triage` | readiness + missing fields |
| GET | `/cases/{case_id}/policy-context` | hybrid RAG evidence for the case |
| POST | `/cases/{case_id}/plan` | onboarding plan (LangGraph) |
| GET | `/cases/{case_id}/offboarding/inventory` | subject's resources |
| POST | `/cases/{case_id}/offboarding/plan` | offboarding plan (LangGraph) |
| POST | `/plans/{plan_id}/submit` | creates approval; approver role must be HR_MANAGER/LINE_MANAGER/ADMIN |
| POST | `/approvals/{approval_id}/decision` | only the assignee can decide; REJECTED needs a comment |
| POST | `/plans/{plan_id}/revise` | manager correction → new revision |
| POST | `/plans/{plan_id}/execute`, `/plans/{plan_id}/retry` | dispatch to n8n + verify |
| POST | `/cases/{case_id}/handover`, `/handover-approvals/{id}/decision` | |
| POST | `/cases/{case_id}/learning/candidate`, `/learning-approvals/{id}/decision`, `/learning/{id}/index`, `/learning/search` | |
| POST | `/policy-guardian/activate` | `PolicyActivateRequest{policy_code, title, version_number (= current+1), department, effective_from, uploaded_by, content_text≥40}` |
| GET | `/policy-guardian/changes/{change_id}` | |
| POST | `/policy-guardian/impacts/{impact_id}/regenerate` | |
| GET | `/audit/cases/{case_id}/timeline`, `/audit/cases/{case_id}/coverage` | |
| POST | `/access-events`; GET `/security/alerts`; POST `/access-events/{id}/review` | ML scoring |
| POST | `/mock/resources/apply`; GET `/mock/resources/{key}`; GET `/mock/people/{id}/resources` | mock company adapter (n8n calls these) |

**Missing compared with the plan book** (the map and dashboards will need some): list endpoints `GET /people`, `GET /cases`, `GET /approvals`, `GET /policies`, `GET /learning`. Add only the ones the new UI actually calls.

### 4.5 Key flows

- **Plan shape** (`planning/schemas.py`): `GeneratedCasePlan{summary, actions[PlannedAction], warnings}`; `PlannedAction{sequence≥1, action_type, resource_type, resource_key, requested_data, reason, evidence_ids≥1}`. Offboarding uses `OffboardingPlan{summary, revocations[], asset_returns[], reassignments[], notifications[], handover_topics, targeted_questions, evidence_refs, needs_human_review}` (`extra="forbid"`), flattened into actions.
- **Validation** (`planning/validation.py`): `ALLOWED_ACTIONS` per case type, `ALLOWED_RESOURCE_TYPES` per action, `MUTATION_ACTIONS`, onboarding requirement fields. Offboarding requires exactly the action returned by `_required_action_for_resource` for each non-terminal resource.
- **Execution** (`execution/service.py`): plan must be APPROVED; actions ordered by `requested_data.sequence` (must be 1..n consecutive). Payload to n8n: `{action_id, case_id, person_id, action_type, resource_type, resource_key, idempotency_key, requested_data: requested_data.parameters}`. `requests.post` with timeout; on exception → FAILED, or HUMAN_REVIEW after `MAX_EXECUTION_ATTEMPTS=2`. **Any 2xx JSON object → SUCCEEDED**, then `verify_action_resource`.
- **Verification** (`execution/verification.py`): looks up `company_resources` by `resource_key` and checks expected state/owner (`EXPECTED_RESOURCE_STATES`) → VERIFIED or FAILED (+case FAILED). Same DB that n8n just wrote via the mock API.
- **Audit**: `record_audit_event(db, actor_type, event_type, entity_type, entity_id, actor_id?, before_data?, after_data?, evidence_data?, correlation_id?)` — use it for every new state change; `correlation_id` = case id.
- **Learning**: revision diff (`_structured_revision_diff`) → LangGraph candidate → sanitize (regex for email, UUID, phone, secrets) → approval → `index_approved_learning` copies current policy links and upserts to Qdrant; search filters APPROVED.
- **Guardian** (`policy_guardian/service.py::activate_policy_change`): requires `version_number == current+1` and different content; registers draft, indexes chunks (payload status DRAFT), runs graph (deterministic diff + LLM summary), finds `policy_links` to the old version, creates impacts:
  - Learning linked → MARK_STALE, removed from retrieval.
  - Plan linked: case COMPLETED → **LOW / NO_ACTION** ("no automatic reversal"); action in flight → HIGH / REVIEW, case HUMAN_REVIEW; plan PENDING_APPROVAL/APPROVED → plan STALE, case PAUSED, REGENERATE (HIGH if sensitive = contains GITHUB_ACCESS or EMAIL_ACCOUNT); otherwise LOW / REVIEW.
  - **Consequence for the hero story:** the bot's MCP grant case will be COMPLETED when V2 arrives, so today's Guardian would say NO_ACTION. The new **live-resource re-check** (W4) is what makes scene 6 work.
- **Reset** (`scripts/reset_demo.py`): deletes demo transactional rows (cases, plans, actions, approvals, links, learning, audit…) for demo people, keeps policy versions (because Qdrant mirrors them), re-seeds people/resources.

### 4.6 Known bugs and weaknesses (fix when you touch the area)

1. `execution/service.py`: treats any 2xx JSON as success. Also check `result["status"]`; n8n must send non-2xx on failure.
2. Verification is not independent for GitHub (reads our DB). Add `execution/github_verifier.py` (W2).
3. `_required_action_for_resource` duplicated in `offboarding/service.py` and `offboarding/graph_runner.py` → move to one module (e.g. `offboarding/rules.py`) before adding agent rules.
4. `mock_company/service.py::mutate_resource` overwrites `resource.idempotency_key` with the mutation key, so replaying the original creation key no longer matches; replay check compares only key/type, not `action_type`. Fix: keep the resource's creation key; store applied mutation keys in `details_data["applied_keys"]` (or match on `CaseAction.idempotency_key`) and conflict when the same key comes with a different action.
5. Root `.env.example` has no `DATABASE_URL=` key and shows a real Supabase host; backend README has stale debugging steps with a hard-coded plan id; `backend.zip`, `frontend.zip` committed; two `requirements.txt` (root + backend) — keep `backend/requirements.txt`, drop `sentence-transformers` (no reranker); `main.py` version string.
6. ML: SPEDIA test set is ~44% attack windows (random PR-AUC ≈ 0.44), model PR-AUC 0.52, 419 alerts/1,000. Never claim precision. ML stays a small Security-page feature.
7. No list endpoints (4.4), no Docker, no Alembic, no root README, no n8n JSON in repo.

---

## 5. Target design (what changes)

Full rationale and Bangla text in `FINAL_PLAN.md`. This section is the engineering checklist.

### 5.1 Enum additions

| Enum | Add |
| --- | --- |
| `ResourceType` | `AI_AGENT`, `AGENT_CREDENTIAL` |
| `ActionType` | `DOWNSCOPE`, `GRANT_TEMPORARY` |
| `ResourceState` | `SUSPENDED`, `EXPIRED` |
| `CaseType` | `ACCESS_REQUEST` |
| `PolicyImpactTargetType` | `RESOURCE` |
| `AuditActorType` | `AGENT` |

Every one of these needs the matching DB CHECK constraint updated (migration).

### 5.2 Agents as resources

- An agent is a `CompanyResource` with `resource_type=AI_AGENT`; **`person_id` is the human sponsor**. Its credential is a separate `AGENT_CREDENTIAL` resource (also `person_id` = sponsor) whose `details_data` holds the GitHub deploy key id.
- `AI_AGENT.details_data`: `agent_name`, `platform` (n8n / github_app / custom), `purpose`, `scopes` (list of `{system, resource, permission}`), `credential_key`, `risk_tier` (LOW/HIGH), `expires_at` (ISO or null), `last_active_at`, `mcp_api_key_hash` (never the raw key).
- **Orphan rule (deterministic):** sponsor missing, sponsor `employment_status` in {DEPARTING, INACTIVE}, or `expires_at` in the past.
- **Offboarding rule:** every agent/credential sponsored by the leaver must get an action: `REASSIGN` (to successor; `requested_data.parameters.successor_person_id`) optionally followed by `DOWNSCOPE`, or `REVOKE`. LLM proposes which, citing AGENT/ACCESS policy; validation enforces coverage (no agent left on a departing sponsor).
- Allow-list additions in `planning/validation.py` and `mock_company/service.py::MUTATION_RESOURCE_TYPES`: REASSIGN → +AI_AGENT, AGENT_CREDENTIAL; REVOKE → +AI_AGENT, AGENT_CREDENTIAL; DOWNSCOPE → AGENT_CREDENTIAL, GITHUB_ACCESS; GRANT_TEMPORARY → AGENT_CREDENTIAL, GITHUB_ACCESS. `ACCESS_REQUEST` cases allow only GRANT_TEMPORARY.
- New module `agents/`: `GET /agents`, `GET /agents/orphans`, `GET /agents/{resource_key}`, `GET /agents/{resource_key}/grants`.

### 5.3 New policies (seed text — adjust wording only with Sajid)

`data/seed/agent_policy_v1.md`:

```markdown
# Agent Policy

Policy code: AGENT
Version: 1
Department: GLOBAL

1. Every AI agent must have one active human sponsor who is accountable for its access.
2. When a sponsor leaves, each of their agents must be reassigned to the named successor or manager, or disabled, no later than the sponsor's final working day.
3. Agent write access to a confidential repository requires IT Owner approval and must expire within 8 hours.
4. Agent read access to a non-confidential repository is low risk and may be approved automatically when this policy is satisfied, with an expiry of at most 24 hours.
5. Agents must never receive production or administrator access through self-service requests.
6. Agent credentials must be revoked or rotated whenever the agent's sponsor or scope changes.
```

`data/seed/access_policy_v2.md` = Access Policy V1 (6 rules, unchanged text) **plus**:

```markdown
7. An AI agent may hold write access to a confidential repository only while its sponsor has completed confidential security training.
8. When an agent's sponsor changes, the IT Owner must re-certify the agent's access within 24 hours.
```

Hero mechanics: Nabil (new sponsor) has **no** `SECURITY-CONFIDENTIAL` training resource in the seed, so after V2 the bot's live write grant violates rule 7, and the reassignment violates rule 8 until re-certified. The `aurora` repo is confidential (`AURORA` project).

**Linking rule:** offboarding agent steps and every `ACCESS_REQUEST` plan must cite **ACCESS** evidence (plus AGENT), so `policy_links` point to ACCESS V1 and Guardian finds them when ACCESS V2 is activated. Add a validator check.

### 5.4 n8n + real GitHub

Three workflows, JSON exported to `n8n/` (no credentials inside):

| Workflow | Trigger | Does |
| --- | --- | --- |
| `livingops-executor` | Webhook (existing `N8N_PROVISIONING_WEBHOOK`) | Check header token → Switch on `resource_type`/`action_type` → GitHub API for GitHub resources, `/mock/resources/apply` for the rest → respond `{status, execution_id, external_ref, details}`; **non-2xx on failure** |
| `livingops-notifier` | Webhook (`N8N_NOTIFIER_WEBHOOK`) | Post to Slack or Discord (Sajid to choose) with summary + link |
| `livingops-expiry-sweeper` | Schedule every 5 min | `POST {backend}/access-grants/expire-due` with `MCP_SERVICE_TOKEN`; the backend finds expired grants and dispatches REVOKE via the executor, then verifies. State stays in the backend. |

Note: the sweeper needs the backend reachable from Render (deployed backend, or a tunnel during development). Until then, also expose a manual "expire now" in the demo CLI.

GitHub demo setup (Sajid creates): org (e.g. `nexora-labs-demo`), private repo `aurora`, one extra test account as Arif (write collaborator, invitation accepted), fine-grained tokens: write (collaborators + deploy keys administration) in n8n, **read-only** in backend `.env`.

| Operation | GitHub REST |
| --- | --- |
| Remove person | `DELETE /repos/{owner}/{repo}/collaborators/{username}` |
| Change person permission | `PUT /repos/{owner}/{repo}/collaborators/{username}` `{permission: "pull"|"push"}` |
| Agent write → read (DOWNSCOPE) | `DELETE /repos/{owner}/{repo}/keys/{key_id}` then `POST /repos/{owner}/{repo}/keys` `{title, key, read_only: true}` (deploy key permission can't be edited) |
| Temporary write (GRANT_TEMPORARY) | `POST .../keys` `{read_only: false}`; expiry handled by sweeper |
| Revoke agent | `DELETE .../keys/{key_id}` |
| Verify | `GET /repos/{owner}/{repo}/collaborators/{username}/permission`, `GET /repos/{owner}/{repo}/keys` |

Backend generates the ed25519 public key (`cryptography`), discards the private key, and passes `requested_data.parameters.github = {owner, repo, username?, permission?, key_id?, public_key?, key_title?}`. After n8n returns, `github_verifier.py` checks GitHub with the read-only token; only then `VERIFIED`, and the matching `company_resources` row is updated by the backend (not trusted from n8n). Mock resources keep the existing DB verification.

### 5.5 MCP Access Gateway

- Separate process `mcp_server/` using the Python MCP SDK (FastMCP), Streamable HTTP. It is a **thin adapter**: calls backend REST, holds no state. Backend stays synchronous.
- Auth: per-agent API key (hash stored in the agent's `details_data`), sent by the MCP client; MCP server forwards it to the backend.
- Tools: `whoami`, `request_access(system, resource, permission, duration_minutes, reason)`, `check_request(request_id)`, `list_my_access`, `release_access(grant_id)`.
- Backend: `POST /access-requests` creates an `ACCESS_REQUEST` case with a one-action plan (`GRANT_TEMPORARY`, `expires_at`), then applies the tier:

| Tier | Rule (deterministic) | Outcome |
| --- | --- | --- |
| LOW | read, non-confidential, sponsor active, duration ≤ 24h | auto-approve (approval decided by SYSTEM, audited), execute |
| HIGH | write, or confidential resource, duration ≤ 8h | approval assigned to IT_OWNER (Tahmid) + notifier |
| DENY | production/admin, no active sponsor, duration over limit | rejected with reason |

  The LLM only retrieves policy evidence and writes a 1–2 line explanation for the approver. Note: `approvals/service.py::ALLOWED_APPROVER_ROLES` lacks `IT_OWNER` — add it for ACCESS_REQUEST (and keep existing behaviour for other case types).
- Other endpoints: `GET /access-requests/{id}`, `GET /agents/{key}/grants`, `POST /access-grants/{id}/release`, `POST /access-grants/expire-due` (service token).
- Demo client: `mcp_server/demo_client.py`, a scripted client that plays Aurora Release Bot in the terminal. Optional later: connect Claude Desktop to the same server.

### 5.6 Guardian and Learning extensions

- Scene 3 lesson: AI proposes `REVOKE` for the bot; Nabil revises to `REASSIGN` + `DOWNSCOPE`. The learning candidate is created **after** the case is verified complete (existing rule). Scope `{case_type: OFFBOARDING, resource_type: AI_AGENT, department: ENGINEERING}`. Links to ACCESS V1 via copied policy links.
- New `_recheck_live_resources(db, change)` in Guardian: after diff, for every **active** `AI_AGENT` / `AGENT_CREDENTIAL` / `GITHUB_ACCESS` grant whose originating plan links to the old version (via `source_action_id → plan → policy_links`), re-evaluate the new deterministic rules (rule 7: sponsor has `SECURITY-CONFIDENTIAL` training in ASSIGNED/ACTIVE state; rule 8: sponsor changed and no re-certification) and create `PolicyImpact(target_type=RESOURCE, recommended_action=REVIEW|REGENERATE)`. Impacts must be identical on every run (no LLM in detection).
- Remediation for RESOURCE impacts (`policy_guardian/remediation.py`): open a small ACCESS_REQUEST-style case with a `DOWNSCOPE` (or REVOKE) action → same approval → executor → GitHub verification → audit.
- `_plan_contains_sensitive_access`: include `AI_AGENT`, `AGENT_CREDENTIAL`.

### 5.7 Explainability, evidence, evaluation, KPIs

- "Why" panel data per plan step: evidence IDs with clause text, policy version, lessons used (separate from policy), the step's `reason`, validation result, repaired yes/no. Never chain-of-thought.
- `GET /cases/{id}/evidence` → printable HTML report mapped to ISO 27001:2022 controls 6.5 (termination date vs each revocation timestamp, within 24h?), 5.11 (asset return), 5.18 (access rights: policy reason, approver, time, evidence ID), 8.2 (privileged: GitHub write, agent credentials, with GitHub verification). Label it "supporting evidence, not certification".
- `scripts/run_evaluation.py` → `data/eval/latest.json`: plan schema-valid rate (first pass / after repair), % steps with current-policy evidence, retrieval recall@K on seeded questions, Guardian recall + false impacts on seeded cases, verified completion / duplicate prevention / retry recovery. Report real numbers only.
- KPIs on Dashboard: termination→all-access-closed time, % access with owner (humans vs agents), % with policy reason, orphan agents count, time-limited vs standing agent access, manual steps vs approvals. Label "measured on Nexora Labs demo company (simulated operational comparison)".

### 5.8 Frontend

- Keep zero-build HTML/JS. Dark-first token-based design system, consistent across all pages; status colours plus shape/icon (projector-safe).
- Dashboard: D3 v7 force-directed map (people = circles sized by access count, agents = hexagons, manager edges thin, sponsor edges dashed, department clusters), click → side panel, table below with search/filters (department, status, orphan) linked to the map, KPI row, evaluation summary, demo-mode badge. Poll every 2–3 s (no WebSocket). Animations: Arif's node fades, bot's sponsor edge moves to Nabil, Guardian impacts pulse red.
- New endpoint `GET /workforce/graph` returns all nodes and edges in one call.
- Workspace: why panel per step, stopwatch, n8n execution id and GitHub verification shown separately, evidence report button. Approvals: agent request explanation + tier. Guardian: old vs new rule side by side, impact list linked to map. Cases: ACCESS_REQUEST type. Security: restyle only.
- Freeze backend responses for new endpoints before building UI.

### 5.9 Seed data

- Keep the 6 story people and their UUIDs (`11111111-…` Farhana, `22222222-…` Nabil, `33333333-…` Tahmid, `44444444-…` Amina, `55555555-…` Rafi, `66666666-…` Arif) and Arif's 5 resources.
- Add a generator with a fixed random seed: 80–100 people across Engineering, Product, Design, Sales, Support, Finance, People, IT Security with a manager tree; some DEPARTING/INACTIVE; 3–6 resources each; 20–30 agents (release bot, support triage, invoice reconciler, meeting summarizer…) with sponsors and scopes; **3–4 pre-existing orphans** so the map shows red on first load. Bangladeshi names, `@nexora.demo` emails. Clearly fictional.
- Aurora Release Bot: sponsor Arif, platform n8n, purpose "release tags and changelog for Aurora", scope `aurora` write, credential = real deploy key, risk tier HIGH.
- Nabil has **no** `SECURITY-CONFIDENTIAL` training (needed for scene 6).
- `reset_demo.py` must also restore GitHub demo state (re-add Arif as write collaborator, recreate the bot's write deploy key) and write ids to `data/seed/demo_ids.json` (already git-ignored). Ingest AGENT V1. Policy reset must handle ACCESS V2 being active after a run (plan how: re-activate V1 as a new version is not allowed by the guardian rule, so reset needs a controlled policy reset that also cleans Qdrant points — design this explicitly and ask Sajid).

### 5.10 Demo modes

`DEMO_MODE` = `LIVE` (everything real) / `CACHED_AI` (LLM + embeddings from cache, n8n + GitHub real) / `OFFLINE` (cached AI, mock executor, local verification, local Docker Compose). Implement as a wrapper around LLM and embedding calls keyed by a hash of the input, stored in `data/demo_cache/`; rehearsals in LIVE fill the cache. Every scene must give the same result in all three modes (ids/timestamps aside). Show the mode on the Dashboard.

### 5.11 Deployment and cleanup

Docker Compose (Postgres, Qdrant, backend, mcp_server, frontend static; mock executor for OFFLINE), `backend/Dockerfile`, `mcp_server/Dockerfile`, one Alembic baseline migration (replaces `patch_resource_state.py`), deploy backend + MCP (Render or small VPS, awake only for demo days), frontend static host, root README (one-liner, architecture diagram, demo GIF, one-command local start, characters, tests, limitations + sources), `.env.example` fixed and complete, delete zips and `__pycache__`, one requirements file, version string, n8n JSON in `n8n/`, release tag before the final.

---

## 6. Schedule (weeks start Sunday)

| Dates 2026 | Work |
| --- | --- |
| Oct 26 – Nov 8 | W1 agent model + seed; W2 n8n + real GitHub |
| Nov 9 – Nov 15 | W3 hero story end to end (Arif + bot, correction, execution, verification, lesson), `CACHED_AI` works — **Gate Nov 15** |
| Nov 16 – Nov 22 | W4 Guardian + learning extensions |
| Nov 16 – Nov 29 | W5 MCP gateway, risk tiers, sweeper; W6 evidence + evaluation; freeze new API responses — **Gate Nov 29** |
| Nov 30 – Dec 13 | W7 design system, map, Dashboard, then Workspace/Approvals/Guardian; W8 Docker, deploy, README, cleanup (Dec 7–13) |
| Dec 14 – Dec 25 | Pitch deck, business slide, ≥10 full rehearsals from reset across all 3 modes, recording, Q&A practice. No new features. |
| Dec 26 | Final, Daffodil International University |

If the Nov 15 gate is missed: shrink MCP to one HIGH request via the scripted client.

**Cut line (cut from the top first):** ML improvements → Claude Desktop MCP demo → Security/Cases redesign → evaluation panel (numbers can go on a slide) → phone notification. **Never cut:** Arif + bot offboarding, real GitHub verification, Policy V2 Guardian scene, map, demo mode.

---

## 7. Week 1 in detail (Oct 26 – Nov 1) — no external setup needed

Each package: plan → Sajid approves → implement → tests → commit.

**W1.1 Hygiene that unblocks the rest**
- Move `_required_action_for_resource` + `TERMINAL_RESOURCE_STATES` + `_safe_resource_metadata` into `offboarding/rules.py`; import from both callers. Existing tests in `test_business_rules.py` must still pass.
- Fix the mock-company idempotency bug (§4.6 #4) with a test.
- Done when: `pytest` green, behaviour unchanged for existing resource types.

**W1.2 Enums + migration**
- Add the §5.1 values. Introduce Alembic now (baseline from current models) **or** a single idempotent `scripts/migrate_constraints.py` that rebuilds every enum CHECK constraint from the Python enums (generalising `patch_resource_state.py`). Propose which to Sajid; Alembic is in the plan book's Stage 3 anyway.
- Done when: running it twice on Supabase is safe; inserting each new value works; old data intact.

**W1.3 Agent rules + validation**
- Orphan detection function + tests (sponsor DEPARTING/INACTIVE/missing, expired).
- Offboarding required actions for AI_AGENT/AGENT_CREDENTIAL (REASSIGN or REVOKE; DOWNSCOPE allowed after REASSIGN), allow-list updates (§5.2), coverage validator, ACCESS-evidence linking validator, prompt update in `offboarding/prompt.py`.
- Done when: unit tests cover each rule; offboarding graph test with an agent passes.

**W1.4 Agent Policy V1 + seed generator**
- Add `agent_policy_v1.md`, ingest via `ingest_seed_policies.py` (AGENT, GLOBAL, effective 2026-10-01, uploader Tahmid).
- `scripts/seed_company.py` (fixed seed) per §5.9, idempotent upserts; Aurora Release Bot + credential (GitHub key id placeholder until W2).
- `agents/` read endpoints + `GET /workforce/graph` (simple version, for later UI).
- Done when: `seed` + `reset` run cleanly twice; `/agents/orphans` returns the pre-seeded orphans; Arif's offboarding inventory includes the bot and its credential.

**W1.5 GitHub dry run (needs Sajid's org/tokens; can slip to W2)**
- With curl or a small script, prove every GitHub call in §5.4 works against the demo org before building n8n.

---

## 8. What only Sajid can provide (ask when needed, never guess)

- n8n version and the current workflow export (JSON).
- GitHub demo org name, repo, Arif's test username; tokens placed by him in `.env` / n8n credentials.
- Slack or Discord choice + webhook (stored as a secret).
- Approval before any action that touches Supabase data, Qdrant, GitHub, n8n, or git history.
- Decisions on: Alembic vs constraint script; policy reset strategy (§5.9); pricing numbers for the business slide.

---

## 9. Pitfalls

- Do not let the LLM decide tiers, impacts or orphans. Rules decide; the LLM explains.
- Do not mark anything VERIFIED from n8n's response.
- Do not break existing flows (onboarding of Amina/Rafi, handover, security) while adding agents; keep their tests green.
- `create_all` won't alter tables; every enum change needs the migration step.
- Qdrant mirrors policy versions; never delete policy rows without cleaning points.
- Windows paths with spaces; PowerShell vs Git Bash quoting.
- Keep everything synchronous; no new infrastructure.
- Don't add features outside the plan; log any agreed change in `CONTEXT.md` §7.
- Market numbers in UI/pitch must carry their source; KPIs are labelled simulated.

## 10. Definition of done for the final

The six-minute demo in `FINAL_PLAN.md` runs from one-command reset to the end, ten times in a row, in LIVE and CACHED_AI, and the core story in OFFLINE; GitHub state visibly changes and is verified by the backend; Guardian flags the bot's grant and the lesson deterministically; evidence report and evaluation panel show real numbers; repo has a clear README, no secrets, no stray zips; a recording exists as the last fallback.
