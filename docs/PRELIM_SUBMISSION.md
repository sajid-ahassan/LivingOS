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

About 410 spoken words (≈140 words per minute). Record at 1440×900 or larger, browser zoom 100%, LIVE mode, after `reset_demo`. Speak calmly and let the screen move with your words. Record each part separately and join them; keep the final cut at or under 3:00.

### Before you press record

- Open https://livingops-frontend.onrender.com two minutes early (wakes the backend), or run locally.
- Tabs ready: (1) Dashboard, (2) GitHub → aurora repo → Settings → Deploy keys, (3) GitHub → aurora → Settings → Collaborators.
- "Acting as" starts on Farhana Islam (HR Manager).
- Close notifications; hide bookmarks bar.

---

### Part 1 — Problem (0:00–0:30) · ~70 words

| Time | On screen |
| --- | --- |
| 0:00 | Dashboard, full map. Slowly move the mouse over the orb's red particles. |
| 0:12 | Point at the orb label "5 need an owner". |
| 0:20 | Point at the insight panel: "Agents with an active sponsor 79.2%". |

**Say:**
"Every company now runs two kinds of workforce: people and AI agents. But nobody owns the access in between. 79% of people say an account stayed active after they left a job. 82% of companies found AI agents nobody knew about, and only one in five has a way to retire them. Here in Bangladesh's four and a half thousand software companies, this is still a manual checklist."

---

### Part 2 — Solution (0:30–1:00) · ~75 words

| Time | On screen |
| --- | --- |
| 0:30 | Hover the nav: Cases, Approvals, Policy Guardian (the whole lifecycle). |
| 0:42 | Back on the map: click the Engineering card; the fan opens. |
| 0:50 | Hover Arif Hossain; his two agents light up. Click Arif; the panel shows his access and agents. |

**Say:**
"LivingOps AI governs the whole lifecycle of people and AI agents: onboarding, offboarding, agent access requests, and policy changes. One rule: every access has an owner, a policy reason, an expiry, and proof. When something breaks that rule, LivingOps finds it and fixes it, with human approval. Let me show one real story. Arif is leaving, and he sponsors two AI agents with write access to our confidential repository."

---

### Part 3 — Demo (1:00–2:00) · ~145 words

| Time | On screen |
| --- | --- |
| 1:00 | Panel: "Start offboarding". The workspace opens; the AI plan appears (stopwatch starts). |
| 1:12 | Click "Why?" on the GitHub revoke step: the cited policy clause shows. |
| 1:22 | Switch "Acting as" to Nabil. "Revise as manager": set Aurora Release Bot's credential to DOWNSCOPE, type the correction, save. Approve. |
| 1:38 | "Execute approved plan". Steps turn green one by one; "verified by GitHub API" chips appear. |
| 1:48 | Switch to the GitHub tabs: Arif is gone from collaborators; the bot's key is now read-only. |
| 1:55 | Back to the map: the bot sits under Nabil; stopwatch shows the total. |

**Say:**
"HR starts the offboarding. The AI reads our own company policies and drafts the full plan: email, GitHub, laptop, handover, and both agents. Every step shows why, with the exact policy clause it relies on. Nabil, Arif's manager, keeps the release bot running, but makes it read-only under himself. That correction becomes an approved lesson the system learns from. Now we execute. n8n changes the real GitHub organisation, and our backend checks GitHub itself with a separate read-only token. We never trust the automation's word. Here it is on GitHub: Arif's access is gone, and the bot's key is read-only. Everything closed in under two minutes, with proof."

---

### Part 4 — AI approach (2:00–2:30) · ~70 words

| Time | On screen |
| --- | --- |
| 2:00 | Approvals as Tahmid: the bot's MCP request for 2 hours of write, HIGH tier, AI note. Approve. |
| 2:12 | Policy Guardian: activate Access Policy V2. Old and new rules side by side; the new rules glow green. |
| 2:22 | Scroll to impacts: the live grant and the lesson flagged in red. Click remediate. |

**Say:**
"Agents also ask for access through our MCP gateway. Deterministic rules set the risk: this write request needs the IT owner, and it expires on its own. Under the hood: LangGraph planners, hybrid RAG on Qdrant, and rules, not the LLM, for every risk decision. And when the policy changes, Policy Guardian re-checks every past decision, here a live agent grant and a lesson that now break the new rule."

---

### Part 5 — Impact and next step (2:30–3:00) · ~65 words

| Time | On screen |
| --- | --- |
| 2:30 | Dashboard insight panel: KPIs (termination to access closed, policy reason 100%, sponsor coverage). |
| 2:45 | Slowly pull back to the full map; end on the LivingOps logo. |

**Say:**
"On our demo company, every access closed within two minutes of termination, and every change carries a policy reason. LivingOps is built for 100 to 500 person companies, starting in Bangladesh, at a fraction of enterprise prices. Next: Bangla explanations, Google Workspace and Microsoft 365 connectors, and our first pilots. LivingOps AI. Every access has an owner."

---

### Recording tips

- Say numbers exactly as they appear on screen that day (the stopwatch may show 1.8 or 2.1 minutes; read what you see).
- If a step is slow, cut the waiting in editing; never speed up your voice.
- Part 3 is the longest: rehearse the clicks twice before recording.
- After recording, ask for `reset_demo` so judges see a clean demo.

---

## Split version: record the voice and the screen separately

Record the **screen** first (all clicks, with every wait — length does not matter), then read the **voiceover** in one quiet take, then cut the screen footage to match the voice in Clipchamp. Speed up or cut the waits; label sped-up parts "sped up 10×".

### A. Voiceover (read aloud, ~372 words ≈ 2:40)

Pause about one second between parts. Target time per part in brackets.

**Part 1 — Problem (0:00–0:30)**
Every company now runs two kinds of workforce: people and AI agents. But nobody owns the access in between. 79% of people say an account stayed active after they left a job. 82% of companies found AI agents nobody knew about, and only one in five has a way to retire them. Here in Bangladesh's four and a half thousand software companies, this is still a manual checklist.

**Part 2 — Solution (0:30–1:00)**
LivingOps AI governs the whole lifecycle of people and AI agents: onboarding, offboarding, agent access requests, and policy changes. One rule: every access has an owner, a policy reason, an expiry, and proof. When something breaks that rule, LivingOps finds it and fixes it, with human approval. Let me show one real story. Arif is leaving, and he sponsors two AI agents with write access to our confidential repository.

**Part 3 — Demo (1:00–2:00)**
HR starts the offboarding. The AI reads our own company policies and drafts the full plan: email, GitHub, laptop, handover, and both agents. Every step shows why, with the exact policy clause it relies on. Nabil, Arif's manager, keeps the release bot running, but makes it read-only under himself. That correction becomes an approved lesson the system learns from. Now we execute. n8n changes the real GitHub organisation, and our backend checks GitHub itself with a separate read-only token. We never trust the automation's word. Here it is on GitHub: Arif's access is gone, and the bot's key is read-only. Everything closed in under two minutes, with proof.

**Part 4 — AI approach (2:00–2:30)**
Agents also ask for access through our MCP gateway. Deterministic rules set the risk: this write request needs the IT owner, and it expires on its own. Under the hood: LangGraph planners, hybrid RAG on Qdrant, and rules, not the LLM, for every risk decision. And when the policy changes, Policy Guardian re-checks every past decision, here a live agent grant and a lesson that now break the new rule.

**Part 5 — Impact (2:30–3:00)**
On our demo company, every access closed within two minutes of termination, and every change carries a policy reason. LivingOps is built for 100 to 500 person companies, starting in Bangladesh, at a fraction of enterprise prices. Next: Bangla explanations, Google Workspace and Microsoft 365 connectors, and our first pilots. LivingOps AI. Every access has an owner.

### B. Screen capture checklist (do all of it; waits are cut later)

Before: press **Reset demo** and wait for the reload; open the two GitHub tabs (Deploy keys, Collaborators); Acting as = Farhana.

1. Dashboard: slow mouse over the orb's red particles → point at "5 need an owner" → point at "79.2%". *(Part 1)*
2. Hover nav: Cases, Approvals, Policy Guardian → click Engineering → hover Arif (agents light up) → click Arif. *(Part 2)*
3. **Start offboarding** → **Generate AI plan** *(wait)* → **Why?** on the GitHub revoke step. *(Part 3)*
4. Acting as → Nabil → **Revise as manager** → credential DOWNSCOPE → type the correction → **Save revision and send for approval** → **Approve plan**. *(Part 3)*
5. **Execute approved plan** *(wait ~90 s; keep recording — steps turn green)*. *(Part 3)*
6. GitHub tabs: refresh Collaborators (Arif gone) and Deploy keys (bot key read-only). *(Part 3)*
7. Back in the workspace: **Turn the correction into a lesson** *(wait)*. Dashboard: bot now under Nabil. *(Part 3)*
8. Terminal: `newenv\Scripts\python.exe -m mcp_server.demo_client --url https://livingops-mcp.onrender.com/mcp --wait 300` → Acting as → Tahmid → **Approvals**: approve the lesson, then the bot's HIGH request (AI note visible) *(wait for ACTIVE)*. *(Part 4)*
9. **Policy Guardian** → **Activate Access Policy V2** *(wait)* → old vs new rules → scroll to the red impacts → **Downscope to read-only** on the live grant → approve it on Approvals. *(Part 4)*
10. Dashboard: insight panel KPIs → slow pull-back on the full map. *(Part 5)*

After recording: press **Reset demo** so judges see a clean start.

---

## Voiceover for the edited cut (media/livingops-prelim-cut.mp4, 2:57)

Written against the actual cut. Each block starts when its scene starts; about 2.3 words per second leaves room to breathe. The collaborators page after execution was not refreshed in the recording, so it is not shown; the deploy-key page is the on-screen proof.

| Cut time | On screen | Say |
| --- | --- | --- |
| 0:00–0:30 | Workforce map, orb with red particles, "5 need an owner", 79.2% | Every company now runs two kinds of workforce: people and AI agents. But nobody owns the access in between. 79% of people say an account stayed active after they left a job. 82% of companies found AI agents nobody knew about. This map is our demo company: every red point is an agent with no owner. |
| 0:30–0:44 | Arif's panel: departing, two agents | LivingOps AI governs the whole lifecycle of people and AI agents: onboarding, offboarding, agent access, and policy changes. Arif is leaving, and he sponsors two agents. |
| 0:44–1:00 | Approvals and Guardian pages, then GitHub: the bot's write key | Every access has an owner, a policy reason, an expiry and proof. Here is the real GitHub repository: the release bot holds a write key. |
| 1:00–1:09 | Start offboarding; AI drafting (sped up) | HR starts the offboarding, and the AI drafts the plan from our own policies. |
| 1:09–1:23 | Plan, then "Why?" with policy clauses | Email, GitHub, laptop, handover, and both agents. Every step shows why, citing the exact policy clause. |
| 1:23–1:44 | Nabil revises: bot read-only; approve; execute | Nabil, the manager, keeps the release bot but makes it read-only under himself. He approves, and we execute. |
| 1:44–1:57 | Steps verified one by one (sped up); completed | n8n changes the real systems, and our backend verifies each change on GitHub itself, never trusting the automation's word. |
| 1:57–2:01 | GitHub: the bot's key is now read-only | Here is the proof: the bot's key is now read-only. |
| 2:01–2:11 | Approvals: the bot's MCP request, HIGH tier, AI note; approve | Agents ask for access through our MCP gateway. Rules set the risk; this write request needs the IT owner, and it expires on its own. |
| 2:11–2:26 | Policy V2: old vs new rules; impacts | When the policy changes, Policy Guardian re-checks every past decision: the agent's live write access and two sponsor changes now need action. |
| 2:26–2:31 | Downscope remediation approved | One approval brings it back into compliance. |
| 2:31–2:57 | Final map, KPIs (2.6 min, 100%), Nabil with his agents | On our demo company, all access closed in under three minutes, and every change carries a policy reason. LivingOps is built for 100 to 500 person companies, starting in Bangladesh. Next: Bangla explanations, more connectors, and our first pilots. LivingOps AI. Every access has an owner. |
