# LivingOps AI — Preliminary Submission Pack

Competition 1 (Team-Built Product) · "Idea to Unicorn — Preliminary Submission" · deadline 31 Oct 2026, 11:59 PM GMT+6.
Copy each block into the matching form field. Every number below is either measured on our demo company or cited; keep the citations if a field allows them.

---

## Project name

LivingOps AI

## Domain and challenge area

InfraSphere AI — AI Infrastructure, Cybersecurity & Future Work · WorkforceOS + AgentOps

## Elevator pitch (one line)

The operating layer for hybrid human + AI workforces: every access, human or AI agent, has an owner, a policy reason, an expiry and proof — and LivingOps fixes it, with human approval, the moment any of those breaks.

## Public summary

**Short (≈50 words)**
Companies now run people and AI agents side by side, but nobody knows who owns which access. LivingOps AI turns company policy into governed actions: it plans offboarding, gives agents time-limited access through MCP, executes approved changes on real systems, verifies them independently, and re-checks everything when a policy changes.

**Medium (≈120 words)**
79% of people say an account stayed active after they left a job, and 82% of companies found AI agents they did not know about (Sagiss 2026; CSA 2026). LivingOps AI is one lifecycle for both. When an employee leaves, a LangGraph planner drafts the offboarding from the company's own policies (hybrid RAG, every step cites a policy clause), including the AI agents that person sponsored. A manager corrects it; the correction becomes an approved lesson. n8n executes only approved actions on real GitHub, and the backend verifies the result with its own read-only token. Agents request access through an MCP gateway with deterministic risk tiers and automatic expiry. When a policy changes, Policy Guardian finds every plan, lesson and live agent access it breaks.

**Long (≈300 words)**
The problem. Two gaps are growing together. Departing people keep access: 79% report an account still active after leaving, 64% could still reach sensitive data, and a third say nobody owned the revocation (Sagiss, Oct 2026, n=1,000; 82% in companies under 250 people). And AI agents have no owner or off-switch: 82% of enterprises found unknown agents last year and only 21% have a formal process to retire one (CSA, Apr 2026). Enterprise IGA tools exist, but they are priced and sized for large enterprises.

The solution. LivingOps AI treats people and AI agents as one workforce with one rule: every access has an owner, a policy reason, an expiry and proof.
1. Offboarding: an AI planner reads the company's policies and drafts the full plan — email, GitHub, laptop, work handover, and the agents the person sponsored — with a "why" panel citing the exact clause for each step.
2. Human in the loop: a manager revises the plan (e.g. keep the release bot but make it read-only); the approved correction becomes organisational memory.
3. Verified execution: n8n runs only approved actions on real GitHub; the backend confirms each change with a separate read-only token, never trusting the executor's word.
4. Agent access: agents ask for access through an MCP gateway; low risk is approved by rules with an expiry, high risk waits for the IT owner, production/admin is denied.
5. Policy Guardian: when a policy version changes, it compares old and new rules and flags every plan, lesson and live agent access that no longer complies, with one-click remediation.
Every action produces an ISO 27001 evidence trail (controls 5.11, 5.18, 6.5, 8.2).

Measured on our demo company (85 people, 24 agents): all access closed 1.9 minutes after termination, 100% of changes carry a policy reason, and agent sponsor coverage rose from 79.2% to 87.5% in one story run.

---

## Problem definition and target users

- Users: HR managers (start offboarding), engineering managers (own the people and the agents), IT security owners (approve risky access, own policy).
- Target companies: 100–500 person tech and IT-enabled service companies, Bangladesh first (4,500+ software/ITES companies; ICT service exports $724.6M in FY2024-25, TBS News), then similar markets.
- Urgency: agents are being deployed faster than anyone assigns owners; non-human identities already outnumber humans ~45:1 (Security Boulevard, Jul 2026). Gartner expects over 40% of agentic AI projects to be cancelled by end-2027, poor risk control among the reasons.

## Solution and differentiation

- One lifecycle for humans and AI agents (sponsor = owner of an agent; orphan detection when the sponsor departs).
- Policy-grounded AI: plans are generated from the company's own policy documents, each step cites evidence IDs (POL-ACCESS-V1-C0 …).
- Policy change re-evaluates past decisions and live access — no MCP gateway or IGA tool we reviewed does this (Kong, AWS AgentCore, Docker gateway block by rules; Entra Agent ID needs P2/Governance add-ons; SailPoint is sized for enterprise).
- Independent verification: proof comes from the target system (GitHub API), not from the automation tool.

## AI architecture (input → AI → output)

Input: HR event or agent request · company policies (versioned) · company resources (accounts, repos, laptops, agents, credentials) · access events.

AI core:
- **LLM**: OpenAI gpt-4o-mini for planning, explanations, change summaries and lesson drafting; text-embedding-3-small for retrieval.
- **Hybrid RAG**: policies chunked with stable evidence IDs in Qdrant (vector + keyword), filtered to the current policy version; approved lessons are indexed as organisational memory and retrieved alongside policy.
- **LangGraph agents**: offboarding planner (retrieve → plan → deterministic validation → one repair pass), onboarding planner, Policy Guardian (diff versions → AI summary → rule-based impact detection), learning graph (manager correction → lesson candidate → human approval → indexing).
- **Deterministic guardrails**: risk tiers, impact detection and orphan rules are code, not LLM decisions; the LLM retrieves evidence and explains.
- **MCP gateway**: agents authenticate with a hashed key and call `request_access`, `check_request`, `list_my_access`, `release_access`.
- **Execution**: n8n workflows (executor, expiry sweeper, Slack notifier) run only approved actions; backend verifies on GitHub with a read-only token.
- **ML**: Isolation Forest anomaly scoring on access events, with mandatory human review (no automatic punishment).
- **Reliability**: LIVE / CACHED_AI / OFFLINE demo modes give the same result with or without internet.

Output: approved, verified changes on real systems · explanations per step ("why" panel) · Slack notifications · ISO 27001 evidence report · KPI and evaluation dashboard.

Stack: FastAPI + PostgreSQL (Supabase), LangGraph, Qdrant Cloud, n8n, MCP Python SDK, D3 frontend, Docker, Render.

## Data and sovereignty strategy

- Demo uses a fictional company (Nexora Labs); no real personal data.
- The LLM never writes to the database or the vector store; it never executes actions.
- Secrets stay in environment variables; the backend holds only a read-only GitHub token, the write token lives only in n8n.
- Self-hostable with Docker Compose (Postgres + Qdrant + backend + MCP + frontend), so a company can keep data in-country; the model provider is swappable.
- No chain-of-thought is stored; only cited evidence and short explanations.

## Ethical safeguards

- Human approval for every plan and every high-risk agent request; low-risk grants always expire.
- Every AI step cites the policy clause it relies on; deterministic validation rejects plans without evidence.
- Anomaly scores never trigger action alone; a human reviews each alert.
- Lessons enter memory only after approval, and are retired automatically when the policy they relied on changes.
- Full audit trail for every decision (who, what, why, when, proof).

## Bangla and localization

- Current build: English UI; seed data uses Bangladeshi names and context.
- Planned: Bangla explanations in the "why" panel and Slack notifications (LLM-generated from the same cited evidence), Bangla policy documents supported by the multilingual embedding model, and a Bangla UI toggle for HR users.

## Impact and KPIs

Measured on the demo company (fictional data, labelled as such):
- Termination → all access closed: 1.9 minutes (vs ~5 hours of IT time per offboarding reported by Nudge Security, 2023).
- Changes with a policy reason: 100%.
- Agents with an active sponsor: 79.2% → 87.5% after one offboarding; orphan agents flagged automatically.
- Agent access that is time-limited vs standing: tracked live.
Target outcomes for pilots: same-day revocation for 100% of leavers, zero agents without an owner, audit evidence produced as a by-product.

## Business model (hypothesis)

Per managed identity (human or agent) per month, for 100–500 person companies; priced well below enterprise IGA (Okta LCM+IGA ≈ $9–11/user/month; Vanta ≈ $7.5k–14k/year for small companies). First market Bangladesh's IT/ITES sector, then similar mid-market companies abroad; NRB advisors in IAM/security for global pilots (plan, not yet secured).

## Scalability roadmap

- Now: modular monolith, Dockerised, deployed on Render; connectors for GitHub, mock company systems, Slack.
- Next: Google Workspace / Microsoft 365 / Slack / Jira connectors as n8n workflows; SSO; multi-tenant; Bangla.
- Later: more agent platforms through MCP, SOC 2 / ISO evidence packs, marketplace connectors.

## Links

- Live demo: https://livingops-frontend.onrender.com (backend sleeps on the free plan; first load can take ~1 minute)
- MCP gateway: https://livingops-mcp.onrender.com/mcp
- Code: https://github.com/sajid-ahassan/LivingOS (branch `final-build`, or `main` after merge)
- Demo video: (YouTube/Drive link after recording)

## Problem statement (required field)

Use "Problem definition and target users" above, opening with: "Companies now run people and AI agents side by side, but nobody owns the access in between."

## Solution description (required field)

Use "Solution and differentiation" above plus the five numbered capabilities from the long summary.

## Data & AI provenance (required field)

- Data: fictional demo company Nexora Labs (85 people, 24 AI agents, 385 resources) generated by a seeded script; four company policies written for the demo (Access, Equipment, Offboarding, Agent) plus Access Policy V2; anomaly model trained on the public SPEDIA access-log dataset (Isolation Forest). No real personal data.
- AI: OpenAI gpt-4o-mini (planning, explanations, change summaries, lessons) and text-embedding-3-small (retrieval) via API; Qdrant Cloud vector store; all AI answers are recorded in a demo cache so results are reproducible offline.
- Provenance in the product: every plan step stores the evidence IDs of the policy clauses it used; every action stores who approved it, the n8n execution ID and the independent GitHub verification; lessons record their source case and the policy versions they depend on.

## Tooling & IDE (required field)

Claude Code (Anthropic) as the AI pair-engineer for architecture, implementation, tests and documentation; Python 3.11 + FastAPI, LangGraph, SQLAlchemy/Alembic; Git + GitHub; Supabase (PostgreSQL); Qdrant Cloud; OpenAI API; n8n (workflow execution); MCP Python SDK; D3.js frontend; Docker Compose; Render (deployment); pytest. (Add the editor your team used, e.g. VS Code.)

## Build provenance

- Built from 9 Sep 2026; 41 commits on `final-build`; ~26,500 lines of Python/JS/CSS/HTML; 233 automated tests.
- AI-native workflow: Claude Code for architecture, implementation and tests; OpenAI models at runtime; n8n for execution; every design decision logged in `docs/CONTEXT.md`.
- Verified live on real GitHub during rehearsal on 25 Oct 2026 (offboarding, MCP grant, Policy V2 remediation).

---

## 180-second video script

Record at 1440×900 or larger, browser zoom 100%, LIVE mode, after `reset_demo`. Speak calmly; the screen does the talking.

| Time | Screen | Say |
| --- | --- | --- |
| 0:00–0:30 Problem | Dashboard: the orb with red particles, "5 need an owner"; zoom on the KPI panel | "Companies now run people and AI agents side by side. 79% of people say an account stayed active after they left a job, and 82% of companies found AI agents nobody knew about. In Bangladesh's 4,500 software companies, offboarding is still a checklist. Who owns each access? Usually, nobody." |
| 0:30–1:00 Solution | Click Engineering; hover Arif → his two agents light up | "LivingOps AI is one lifecycle for people and AI agents. Every access has an owner, a policy reason, an expiry and proof. Arif is leaving, and he sponsors two agents with write access to our confidential repo." |
| 1:00–2:00 Demo | Start Arif's offboarding → plan with "Why?" open on one step → Nabil revises bot to read-only → approve → execute; stopwatch; GitHub collaborators/keys page refreshed; back to map: bot glides under Nabil | "The AI drafts the plan from our own policies — every step cites the clause. Nabil keeps the release bot but makes it read-only; that correction becomes an approved lesson. n8n executes only what was approved, on real GitHub, and our backend verifies it with its own read-only token. All access closed in under two minutes." |
| 2:00–2:30 AI approach | Approvals: the bot's MCP request with AI note and HIGH tier → approve; then Guardian: Policy V2 side-by-side, impacts in red | "Under the hood: LangGraph planners over hybrid RAG on Qdrant, deterministic risk rules, an MCP gateway for agents, and Policy Guardian: when the policy changes, it finds the live agent access and the lesson that now break it." |
| 2:30–3:00 Impact | Insight panel KPIs; one line on Bangla and pricing | "Measured on our demo company: access closed in 1.9 minutes, 100% of changes with a policy reason, orphan agents caught automatically. Next: Bangla explanations, Google Workspace and Microsoft 365 connectors, and pilots with Bangladeshi software companies — at a fraction of enterprise prices." |

Recording tips: pre-warm the backend (open the site 2 minutes before); keep a GitHub tab open on the aurora repo's deploy keys page; record each segment separately and join them; keep the final cut at or under 3:00.
