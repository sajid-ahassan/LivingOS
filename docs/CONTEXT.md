# LivingOps AI — context and decision log

Written 23 October 2026 from the planning conversation between Sajid and Claude, so that any new session (Claude Code, or a later chat) starts with the reasoning, not just the plan. Read with `docs/FINAL_PLAN.md`.

## 1. The hackathon

- **Event:** International AI Builders Congress 2026 ("Build Locally. Lead Globally."). Event window 1 Jul – 26 Dec 2026, 3 phases, 11 domains. **Final: 26 December 2026, Daffodil International University, Ashulia campus, Dhaka.** 5,000+ attendees.
- **Track:** 10. InfraSphere AI — AI Infrastructure, Cybersecurity & Future Work. Challenge areas and "winning signals" from the participants guide:

| Area | What to build | AI capabilities to demonstrate | Winning signal |
| --- | --- | --- | --- |
| SecureAI | AI security monitoring and defense | Anomaly detection + agents + response | Threat detection precision |
| WorkforceOS | AI operating system for hybrid human+AI teams | Agent orchestration + workflow + memory | Productivity and coordination gains |
| Knowledge Grid | Enterprise knowledge retrieval and reasoning | RAG + GraphRAG + governance | Faster, grounded decisions |
| AgentOps | Build, deploy, monitor, govern AI agents at scale | MCP + observability + evaluation | Reliable, governable agent systems |
| Human+AI | Augmentation tools | Copilots + memory + orchestration | Measurable human productivity uplift |

We target **WorkforceOS + AgentOps** together. SecureAI is not a main claim (our ML is weak).

- **Judging rubric (100):** Innovation 20 · Technical Execution 20 (architecture, AI integration depth, robustness, explainability of the intelligence core) · Business Model + Global Readiness 20 (value proposition, monetization, adoption, cross-border, evidence of market validation) · Real-World Impact + Ethical AI 20 (problem significance, measurable outcomes/KPIs, responsible AI, transparency) · Scalability + NRB Collaboration 10 (cloud readiness, modular design, collaboration with non-resident Bangladeshis / global) · Presentation 10 (storytelling, demo, ability to explain AI decisions).

## 2. Where the project stood on 23 Oct 2026

- Commit `5877e00` "stage 3 complete" on `main` (110 files, ~16k lines excl. data). Backend Stage 2 is largely done: cases, onboarding/offboarding LangGraphs (validate + one repair), approvals, revisions, n8n dispatch/retry/verification, handover, approved learning, Policy Guardian + remediation, audit timeline, security alerts, Isolation Forest, demo CLI, reset script, 23 tests. Frontend: 6 plain HTML/JS pages.
- Original plan was a 12-week schedule from 9 Sep; the project was behind but caught up a lot in the last push.

**Known bugs / weaknesses found in review (fix when touching the area):**

- n8n workflow JSON is not in the repo; the current n8n workflow only calls the mock API, so "independent verification" reads the same DB n8n wrote to.
- `execution/service.py` treats any 2xx JSON from n8n as success — n8n must return non-2xx on failure, and the backend should also check a `status` field.
- `_required_action_for_resource` is duplicated in `offboarding/service.py` and `offboarding/graph_runner.py`.
- `mock_company/service.py` mutation path overwrites the resource's `idempotency_key`, so a replay of the original creation key no longer matches; a reused key with a different `action_type` is not detected as a conflict.
- Root `.env.example` lacks the `DATABASE_URL=` key and shows a real Supabase host; backend README has stale debugging steps with a specific plan ID; `backend.zip` / `frontend.zip` (with `__pycache__`) are committed; two `requirements.txt`; `main.py` version still `0.2.0-stage2`; no root README, no Docker, no Alembic migration.
- ML (`models/isolation_forest_metrics.json`, SPEDIA dataset not LANL): test set has 175/394 attack windows (~44% positive rate, so random PR-AUC ≈ 0.44); model PR-AUC 0.52, 419 alerts per 1,000 windows. Do not claim detection precision.

## 3. Decisions and why

| # | Decision | Why |
| --- | --- | --- |
| D1 | Position as governed lifecycle for **humans + AI agents** ("Every access has an owner, a policy reason, an expiry, and proof") | The track itself is named WorkforceOS + AgentOps; WorkforceOS is defined as hybrid human+AI teams. Market data shows both problems growing (see §5). Engine already handles resources/plans/approvals, so cost is moderate. |
| D2 | **Policy Guardian stays the main "wow"** | It is the most original part (policy change automatically revisits plans, lessons and now agent access). We found no market tool doing this. New features must support it, not compete with it. |
| D3 | **One continuous story** around Aurora Release Bot instead of separate scenes | Judges remember one character; each scene builds on the previous one (orphan → manager correction → lesson → MCP request → V2 makes both the grant and the lesson non-compliant). |
| D4 | **Learning stays in the demo** | It is one of the four product branches and WorkforceOS explicitly asks for "memory"; it makes the Guardian moment stronger. |
| D5 | **Real GitHub in n8n**, rest mock | Fixes the biggest Technical Execution weakness; verification becomes truly independent (backend read-only token). Deploy key = agent identity, so only one extra GitHub test account is needed. |
| D6 | **MCP Access Gateway included**, risk-tiered | AgentOps explicitly asks for MCP. Approval fatigue solved by deterministic tiers: LOW auto-approve, HIGH human, DENY. Crowded market is a business risk, not a hackathon risk. |
| D7 | n8n has **3 workflows**: executor, notifier, expiry sweeper; n8n never decides | Matches the plan-book boundary. Sweeper state lives in the backend. |
| D8 | **Explainability ("why" panel), ISO 27001 evidence report, evaluation panel, KPIs** | Rubric asks for explainability, measurable outcomes and business value; all read existing data, low cost. ISO controls 6.5, 5.11, 5.18, 8.2. |
| D9 | **Seed 80–100 people, 20–30 agents**, story characters unchanged | A 6-person map looks empty; cheap to generate with a fixed random seed. |
| D10 | **Demo mode from day one** (`LIVE` / `CACHED_AI` / `OFFLINE`) | Venue WiFi risk with LLM + n8n + GitHub + Slack + MCP all live. |
| D11 | Keep zero-build HTML/JS frontend; **redesign** + D3 force-directed dark map | Time goes into design and the map, not a React rewrite. |
| D12 | Agents are `CompanyResource` rows (`person_id` = sponsor); new types `AI_AGENT`, `AGENT_CREDENTIAL`; actions `DOWNSCOPE`, `GRANT_TEMPORARY`; states `SUSPENDED`, `EXPIRED`; case type `ACCESS_REQUEST`; impact target `RESOURCE` | Reuses inventory, REASSIGN, approvals, audit. Orphan detection is deterministic. |
| D13 | Business: per managed identity (human + agent) monthly pricing, 100–500 person tech/service companies, Bangladesh first; prices are a **hypothesis** | Compare against published prices (Okta LCM+IGA ~$9–11/user/month per Iden; Vanta ~$7.5k–14k/yr for small companies). |
| D14 | NRB: a plan (advisors from diaspora IAM/security professionals, first pilots with foreign-client-facing firms), stated as a plan, not an achievement | Rubric asks for it; nothing to build. |

## 4. Rejected ideas (do not re-propose without new evidence)

- **Discovery agent** (autonomous tool-calling agent that searches systems): with 2–3 known systems a deterministic query finds the same things; a judge would ask "why an agent?". Test for any new AI feature: can we show a case where AI did something plain code could not? If not, drop it.
- **GraphRAG, cross-encoder reranker**: no visible demo value for the time.
- **Surveys / company interviews**: Sajid decided none for the hackathon. Positioning relies only on published evidence.
- **"Foreign clients demand ISO evidence" / client-access positioning**: not verifiable; do not claim.
- **EU AI Act urgency**: high-risk obligations moved to 2 Dec 2027 (Digital Omnibus, in force); don't use deadlines as a scare tactic.
- **ML precision claims**: ML stays a small Security-page feature.
- **React rewrite, WebSockets, background job infra**: against plan-book principles.

## 5. Market evidence (use with sources on slides; most surveys are vendor-funded)

- 79% of former employees said at least one work account still worked after leaving; 64% could reach sensitive data; 33% said nobody owned shutting off access; 82% at companies <250 people vs 70% at 1,000+ (Sagiss/Pollfish, 1,000 US adults, Sep 2026) — https://www.globenewswire.com/news-release/2026/10/20/3384591/0/en/64-of-former-employees-could-still-reach-sensitive-company-data-after-leaving-a-job-sagiss-managed-security-survey-finds.html
- 82% discovered previously unknown AI agents in the past year; only 21% have formal agent decommissioning (CSA for Token Security, 418 resp., Jan 2026) — https://cloudsecurityalliance.org/press-releases/2026/04/21/new-cloud-security-alliance-survey-reveals-82-of-enterprises-have-unknown-ai-agents-in-their-environments
- 53% had agents exceed intended permissions (CSA for Zenity, 445 resp.) — https://cloudsecurityalliance.org/press-releases/2026/04/16/more-than-half-of-organizations-experience-ai-agent-scope-violations-cloud-security-alliance-study-finds
- 94% confident agents aren't over-provisioned, only 33% enforce least privilege; abandoned pilots left live credentials (Cequence & EMA, 202 leaders at 1,000+ employee orgs, Aug 2026) — https://www.globenewswire.com/news-release/2026/08/31/3353329/0/en/new-cequence-ema-research-94-of-enterprises-trust-their-ai-agents-aren-t-over-provisioned-only-33-actually-enforce-it.html
- NHIs outnumber humans ~45:1; half have no clear agent ownership — https://securityboulevard.com/2026/07/the-agent-identity-problem-non-human-identities-outnumber-humans-45-to-1-and-ai-agents-are-making-it-worse/
- Gartner: >40% of agentic AI projects cancelled by end of 2027 (costs, unclear value, inadequate risk controls) — https://www.outlookbusiness.com/artificial-intelligence/over-40-of-agentic-ai-projects-will-be-scrapped-by-2027-says-gartner
- IT spends ~5 hours per employee offboarding SaaS access (Nudge Security, 2023, vendor) — https://www.nudgesecurity.com/post/employee-offboarding-by-the-numbers
- MCP gateways (Kong, AgentCore, Docker, TrueFoundry, etc.) are rule-based; none described with policy-document grounding, request-based human approval records, or owner-departure handling — https://mastra.ai/articles/best-mcp-gateways
- Microsoft Entra Agent ID (GA Apr 2026) handles sponsor change but needs Entra ID P2 / Governance add-ons — https://www.bighatgroup.com/blog/entra-agent-id-ga-deep-dive/ ; Okta for AI Agents names the "developer leaves, agent keeps running" risk without describing the fix — https://www.okta.com/blog/ai/okta-ai-agents-early-access-announcement/
- SailPoint is overkill for 50–2,000 employees, 6+ months to deploy (Iden, vendor) — https://www.idenhq.com/en/blog/the-complete-guide-to-joiner-mover-leaver
- Vanta small-company pricing ~$7.5k–14k/yr — https://soc2auditors.org/insights/vanta-pricing/
- ISO 27001:2022 control 6.5 evidence: auditors compare HR termination date with revocation timestamp; >24h gap usually a finding — https://www.upguard.com/compliance/iso-27001/6-5.md
- Bangladesh: 4,500+ software/ITES companies; ICT service exports $724.6M in FY2024-25 — https://www.tbsnews.net/economy/5b-ict-export-target-missed-huge-margin-heres-why-1281591

## 6. Setup facts and open items

- n8n: live on Render + Supabase, kept awake every 3 min. Version and current workflow export: **still to be provided by Sajid**.
- GitHub demo org + `aurora` private repo + one test account for Arif + two fine-grained tokens (write in n8n, read-only in backend): **to be created by Sajid**. Tokens never go into chat or the repo.
- Notification channel (Slack or Discord) + incoming webhook: **to be chosen by Sajid**.
- The Claude desktop app's local Linux sandbox failed to start on this Windows PC ("isolated Linux environment failed to start", Hyper-V based). That is why development moved to the desktop app's Code tab (Local), which runs natively.
- Planning conversation and the editable plan doc live in Sajid's Claude account ("LivingOps AI — Final Build Plan").

## 7. Decision log (append one line per change)

- 2026-10-23 — Final plan frozen (D1–D14). Work moves to `final-build` branch.
- 2026-10-24 — W1.2 uses Alembic (frozen baseline `0001` + enum CHECK rebuild `0002`) instead of a standalone constraint script; Supabase is marked with `alembic stamp 0001`. Replaces `scripts/patch_resource_state.py`. A test fails if `app/enums.py` changes without a migration.
- 2026-10-24 — W1.3 agent offboarding: one action per resource. AI_AGENT gets REASSIGN or REVOKE; its AGENT_CREDENTIAL follows (REVOKE with REVOKE; REASSIGN or DOWNSCOPE to the same ACTIVE successor with REASSIGN). In offboarding, DOWNSCOPE carries `successor_person_id` and moves the credential owner, so scene 3 is agent REASSIGN + credential DOWNSCOPE. A reassigned agent or credential stays ACTIVE (work items still become REASSIGNED). Agent steps must cite ACCESS evidence (and AGENT when retrieved). Expected state/owner rules live in `app/resource_rules.py`, shared by mock company and verification. Removed dead `validate_offboarding_plan` / `_generate_offboarding_plan` from `offboarding/service.py`.
- 2026-10-24 — W1.4 Agent Policy V1 uses the 6-rule text from HANDOFF §5.3 (rule 5 backs the MCP DENY tier). Arif sponsors a second agent, Aurora Test Triage Bot (read-only, LOW risk), because the demo script shows two orphaned agents in scene 2. Seed company: 85 people, 24 agents, 3 preset orphans plus Arif's 2; `seed_company.py` replaces `seed_demo.py` in reset and the demo CLI. ACCESS V2 reset design is deferred to W4.
- 2026-10-24 — Policy reset moved forward from W4: Supabase already had an old onboarding-era ACCESS V2 CURRENT (from 15 Sep tests), which would make the demo's V2 a "V3". `scripts/reset_policies.py` restores every seed policy to V1 (deletes later versions with changes, impacts, impact approvals, links, then their Qdrant points; refuses if V1 has no Qdrant points) and runs at the end of `reset_demo`. Qdrant Cloud was unreachable on 2026-10-24 (connection closed by remote host).
- 2026-10-24 — The old Qdrant free cluster was deleted; Sajid created a new one (URL and key in `.env`). Added `scripts/reindex_policies.py` to rebuild the index from `policy_versions.content_text` (hash-checked, status untouched). Observed: each seed policy is a single chunk (chunk_size 800), so evidence IDs are policy-level (`POL-ACCESS-V1-C0`), not clause-level, and top_k=5 retrieves every policy while there are at most 5 chunks.
- 2026-10-24 — Sajid: "choose the best always"; packages now run through to push on `final-build` without per-step approval, except data deletes, installs, GitHub/n8n writes and plan changes.
- 2026-10-24 — W2 backend: payloads carry `target` (`github`/`mock`). GitHub-backed = `details_data.github` with repo + collaborator (`demo_account: ARIF` → `GITHUB_ARIF_USERNAME`) or deploy `key_id`, and GitHub configured; otherwise mock, so the demo works before the org exists. Verification for GitHub targets uses only the backend read-only token; the backend then writes the resource row. Credential REASSIGN also rotates the key (Agent Policy rule 6). Explicit `status: FAILED` in a 2xx n8n body fails the action. Notifier hooks on plan submission and Guardian activation. Three n8n workflows in `n8n/` (n8n 1.x format, credentials by name only). Removed dead `execution/verification.py`. `cryptography` added to requirements but not installed yet (needs Sajid's OK). Root `.env.example` now uses placeholders only.
- 2026-10-24 — Demo mode: one global LangChain LLM cache plus a cached embeddings wrapper (`app/demo/ai_cache.py`) instead of wrapping each call site. LIVE records, CACHED_AI reads then falls back to live, OFFLINE reads only. Keys normalize per-run UUIDs/timestamps (seeded person IDs kept) so answers survive `reset_demo`. Cache files revive only generation/AI-message types. OFFLINE execution uses an in-process mock executor instead of n8n. `data/demo_cache/` is meant to be committed after LIVE rehearsals.
- 2026-10-24 — First live hero rehearsal (scenes 2–4, offline executor): case COMPLETED, all 9 actions VERIFIED, bot + credential moved to Nabil read-only, lesson APPROVED with 4 policy links; plan identical across two CACHED_AI runs (plan step 4.9 s). Fixes found live: (1) gpt-4o-mini could not keep agent/credential actions consistent, so credential actions are now derived deterministically from the planner's agent decision (REVOKE→REVOKE, REASSIGN→key-rotating REASSIGN to the same successor); the planner decides only the agent; (2) the prompt names the exact ACCESS/AGENT evidence IDs to cite (computed from retrieval); (3) existing bug since 5877e00: unescaped `{"questions"}` in the offboarding question prompts broke the graph; (4) `_structured_revision_diff` ignored the offboarding plan shape, so lessons saw no real diff. Open: the AI proposes REASSIGN (with write) for the release bot, not REVOKE as FINAL_PLAN scene 3 assumes; Nabil's correction becomes "keep it, but read-only" (needs Sajid's story decision). Open: the lesson step missed the cache between runs; cache files now store the normalized prompt to find why at the next milestone rehearsal.
- 2026-10-24 — Scene 3 follows the AI's real choice (recommended by Claude, Sajid said "ok start"): the AI hands the bot to Nabil with write access; Nabil's correction is "keep it, but read-only". The AI is not steered to REVOKE. FINAL_PLAN text not edited yet; revert here if Sajid objects.
- 2026-10-24 — W4 Guardian: `data/seed/access_policy_v2.md` (V1 + rules 7, 8). Live-resource re-check runs inside activation: rules apply only when their clause is new in the new text; candidates are live AI_AGENT / AGENT_CREDENTIAL / GITHUB_ACCESS whose `source_action_id` → plan links the old version. Rule 7 → HIGH REGENERATE (remediate = ACCESS_REQUEST case with one DOWNSCOPE, approved by the IT Owner, resolved on case completion); rule 8 → MEDIUM REVIEW (IT Owner re-certifies). ACCESS_REQUEST allows GRANT_TEMPORARY, DOWNSCOPE, REVOKE (handoff said GRANT_TEMPORARY only; remediation needs the other two). Mock DOWNSCOPE now sets `permission: read` itself.
