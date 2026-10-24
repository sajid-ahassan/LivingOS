# LivingOps AI — Final Build Plan

Oct 23, 2026 · Sajid Ahasan

> Source of truth for the final build. Read `CLAUDE.md` and `docs/CONTEXT.md` first.

## চূড়ান্ত সিদ্ধান্ত

LivingOps AI হবে **মানুষ আর AI agent, দুই ধরনের workforce-এর governed lifecycle**, InfraSphere-এর WorkforceOS আর AgentOps দুটো challenge একসাথে ধরে। ২৬ ডিসেম্বর ২০২৬-এর final-এ একটাই চলমান গল্প দেখানো হবে, যার কেন্দ্রে থাকবে Policy Guardian।

**এক লাইনে (pitch-এ):** The operating layer for hybrid human + AI workforces. Every access has an owner, a policy reason, an expiry, and proof.

**বাংলায়:** প্রতিটা access, মানুষের হোক বা AI agent-এর, তার একজন মালিক, policy থেকে একটা কারণ, একটা মেয়াদ আর একটা প্রমাণ থাকবে। কোনো link ভাঙলে (কেউ চলে গেল, policy বদলাল, agent-এর মালিক নেই, মেয়াদ শেষ) LivingOps নিজে ধরে, আর মানুষের অনুমতি নিয়ে ঠিক করে।

| যা রাখা হলো | যা বাদ |
| --- | --- |
| Policy Guardian (main wow), learning, verified execution | Discovery agent |
| AI agent as workforce resource, orphan detection | GraphRAG |
| আসল GitHub আর notification সহ ৩টা n8n workflow | Cross-encoder reranker |
| MCP Access Gateway, risk tier, auto-expiry | Survey, interview |
| "কেন" panel, ISO 27001 evidence report, evaluation panel, KPI | ML-এর precision দাবি (ML ছোট feature হিসেবে থাকবে) |
| Dark interactive map, frontend redesign, বড় seed data |  |
| প্রথম থেকেই cached demo mode, Docker, deployment |  |

নিয়ম: AI পড়ে আর চিন্তা করে, কাজে হাত দেওয়ার আগে policy আর মানুষের অনুমতি লাগে, n8n শুধু approve হওয়া কাজ চালায়, আর backend বাইরের system-কে জিজ্ঞেস করে প্রমাণ নেয়।

## Market evidence

দুটো সমস্যা একসাথে বড় হচ্ছে: চলে যাওয়া মানুষের access থেকে যায়, আর AI agent-দের কোনো মালিক বা বন্ধ করার প্রক্রিয়া নেই। Pitch-এ এই সংখ্যাগুলো সূত্রসহ দেখাবেন। বেশিরভাগ survey security vendor-দের টাকায় করা, সেটা slide-এ ছোট করে লিখে দেবেন।

| সমস্যা | সংখ্যা | সূত্র |
| --- | --- | --- |
| প্রাক্তন employee-র access চালু থাকে | ৭৯% বলেছে অন্তত একটা account চালু ছিল; ৬৪% sensitive data-তে ঢুকতে পারত; ৩৩% বলেছে access বন্ধের দায়িত্ব কারো ছিল না | [Sagiss, ১,০০০ জন, Oct 2026](https://www.globenewswire.com/news-release/2026/10/20/3384591/0/en/64-of-former-employees-could-still-reach-sensitive-company-data-after-leaving-a-job-sagiss-managed-security-survey-finds.html) |
| ছোট company-তে বেশি | ২৫০ জনের কম company-তে ৮২%, ১,০০০+ company-তে ৭০% | Sagiss (একই) |
| অজানা AI agent | ৮২% company গত বছর অজানা agent পেয়েছে; মাত্র ২১%-এর agent বন্ধের formal process আছে | [CSA, ৪১৮ জন, Apr 2026](https://cloudsecurityalliance.org/press-releases/2026/04/21/new-cloud-security-alliance-survey-reveals-82-of-enterprises-have-unknown-ai-agents-in-their-environments) |
| Agent অনুমতির বাইরে কাজ করে | ৫৩% company-তে ঘটেছে | [CSA, ৪৪৫ জন](https://cloudsecurityalliance.org/press-releases/2026/04/16/more-than-half-of-organizations-experience-ai-agent-scope-violations-cloud-security-alliance-study-finds) |
| বিশ্বাস বনাম বাস্তব | ৯৪% মনে করে agent-দের বাড়তি access নেই, ৩৩% আসলে least-privilege চালু রাখে; বাতিল pilot-এ live credential থেকে যায় | [Cequence & EMA, ২০২ জন, Aug 2026](https://www.globenewswire.com/news-release/2026/08/31/3353329/0/en/new-cequence-ema-research-94-of-enterprises-trust-their-ai-agents-aren-t-over-provisioned-only-33-actually-enforce-it.html) |
| মালিকহীন agent | অর্ধেক company-তে agent-এর পরিষ্কার মালিক নেই; non-human identity মানুষের ৪৫ গুণ | [Security Boulevard, Jul 2026](https://securityboulevard.com/2026/07/the-agent-identity-problem-non-human-identities-outnumber-humans-45-to-1-and-ai-agents-are-making-it-worse/) |
| Governance না থাকায় project বাতিল | ২০২৭-এর শেষে ৪০%-এর বেশি agentic AI project বাতিল হবে, কারণের মধ্যে দুর্বল risk control | [Gartner, Outlook Business](https://www.outlookbusiness.com/artificial-intelligence/over-40-of-agentic-ai-projects-will-be-scrapped-by-2027-says-gartner) |
| Offboarding-এ সময় | IT team প্রতি offboarding-এ গড়ে ৫ ঘণ্টা (২০২৩, vendor survey) | [Nudge Security](https://www.nudgesecurity.com/post/employee-offboarding-by-the-numbers) |

**Competitor-দের ফাঁক:** ২০২৬-এর MCP gateway-গুলো (Kong, AWS AgentCore, Docker, TrueFoundry ইত্যাদি) নিয়ম দিয়ে access আটকায়, কিন্তু policy document থেকে সিদ্ধান্ত নেয় না, request-ভিত্তিক human approval-এর রেকর্ড রাখে না, আর মালিক চলে গেলে কী হবে সেটা handle করে না ([Mastra comparison](https://mastra.ai/articles/best-mcp-gateways))। Microsoft Entra Agent ID মালিক বদল handle করে, কিন্তু Entra ID P2 বা Governance add-on লাগে ([Big Hat Group](https://www.bighatgroup.com/blog/entra-agent-id-ga-deep-dive/))। SailPoint ৫০-২,০০০ জনের company-র জন্য অতিরিক্ত আর ৬ মাসের বেশি লাগে deploy করতে ([Iden](https://www.idenhq.com/en/blog/the-complete-guide-to-joiner-mover-leaver))। Vanta ছোট company-র জন্যও বছরে প্রায় $৭,৫০০-১৪,০০০, আর সেটা নিজে offboarding করে না ([SOC2Auditors](https://soc2auditors.org/insights/vanta-pricing/))।

**ISO 27001-এর যোগসূত্র:** Control 6.5, 5.11, 5.18, 8.2। Auditor-রা HR-এর termination date আর access বন্ধের timestamp মিলিয়ে দেখে, ২৪ ঘণ্টার বেশি ফাঁক থাকলে সাধারণত finding হয় ([UpGuard](https://www.upguard.com/compliance/iso-27001/6-5.md))।

**Regulation-এ সাবধান:** EU AI Act-এর high-risk নিয়ম ডিসেম্বর ২০২৭-এ পিছিয়েছে ([Orrick](https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes)), তাই pitch-এ আইনের deadline দেখিয়ে জরুরি ভাব আনবেন না।

**বাংলাদেশ প্রসঙ্গ:** ৪,৫০০+ software আর IT-enabled service company, FY২০২৪-২৫-এ ICT service export $৭২৪.৬M ([TBS News](https://www.tbsnews.net/economy/5b-ict-export-target-missed-huge-margin-heres-why-1281591))। প্রথম বাজার হিসেবে বলা যায়, কিন্তু "বিদেশি client-রা প্রমাণ চায়" ধরনের দাবি যাচাই করা নেই, তাই করবেন না।

## Judging rubric mapping

সবচেয়ে বড় ঘাটতি এখন Business Model আর measurable outcome-এ, যেখানে মোট ৪০ নম্বরের বড় অংশ। নিচের প্রতিটা feature অন্তত একটা rubric অংশের জন্য বানানো হচ্ছে।

| Criterion (নম্বর) | Judges কী চায় | আমাদের প্রমাণ | কোথায় দেখাবেন |
| --- | --- | --- | --- |
| Innovation (২০) | Non-obvious AI ব্যবহার, systems-level চিন্তা | Policy বদলালে plan, lesson আর agent access নিজে stale হয়; মানুষ আর agent একই lifecycle-এ | Demo দৃশ্য ৬ (Policy V2) |
| Technical Execution (২০) | Architecture, AI integration-এর গভীরতা, robustness, AI core-এর explainability | Hybrid RAG, structured LangGraph, আসল GitHub-এ n8n execution, GitHub API দিয়ে independent verification, MCP server, "কেন" panel, evaluation panel | দৃশ্য ২, ৪, ৫, ৭ |
| Business Model + Global Readiness (২০) | Value proposition, monetization, adoption pathway, cross-border | Per managed identity pricing, mid-market লক্ষ্য, ISO 27001 evidence report, competitor দামের তুলনা | দৃশ্য ৭ আর ৮, business slide |
| Real-World Impact + Ethical AI (২০) | সমস্যার গুরুত্ব, measurable outcome, responsible AI | Survey সংখ্যা, termination-to-revocation stopwatch, KPI; human approval, privacy boundary, ML দিয়ে শাস্তি নয় | দৃশ্য ১, ৪, ৮ |
| Scalability + NRB Collaboration (১০) | Cloud readiness, modular design, global collaboration | Docker, deployed URL, connector-ভিত্তিক architecture, NRB advisor-এর পরিকল্পনা | দৃশ্য ৮, architecture slide |
| Presentation (১০) | পরিষ্কার গল্প, AI সিদ্ধান্ত ব্যাখ্যা | একটাই চরিত্রের গল্প, dark map, "কেন" panel, নির্ভরযোগ্য demo mode | পুরো demo |

**InfraSphere challenge-এর সাথে:** WorkforceOS চায় hybrid human+AI team-এর operating system (agent orchestration + workflow + memory)। AgentOps চায় agent govern করা (MCP + observability + evaluation)। SecureAI চায় anomaly detection-এর precision, যেটা আমাদের মূল দাবি হবে না।

**NRB নিয়ে:** Code-এ কিছু লাগবে না। Pitch-এ একটা পরিকল্পনা দেখাবেন, যেমন বিদেশে IAM বা security-তে কাজ করা প্রবাসী বাংলাদেশিদের advisor হিসেবে নেওয়া আর বিদেশি client-কেন্দ্রিক company-কে প্রথম pilot হিসেবে লক্ষ্য করা। এটা পরিকল্পনা হিসেবেই বলবেন, অর্জন হিসেবে না।

## ৬ মিনিটের demo script

পুরো demo একটাই চরিত্রকে ঘিরে: **Aurora Release Bot**, Arif-এর বানানো একটা AI agent, যার Aurora repo-তে write access আছে। প্রতিটা দৃশ্য আগেরটার উপর দাঁড়ায়, তাই judges-কে কখনো নতুন context শিখতে হয় না।

| সময় | দৃশ্য | Screen-এ যা ঘটে | কী বলবেন (মূল কথা) |
| --- | --- | --- | --- |
| ০:০০-০:৩৫ | ১. সমস্যা | Dark map: Nexora-র ৮০-১০০ জন মানুষ আর ২০-৩০টা agent, sponsor-এর line দিয়ে যুক্ত। উপরে ৭৯% আর ৮২%-এর দুটো সংখ্যা | "আজকের company-তে মানুষ আর AI agent একসাথে কাজ করে, কিন্তু কে কীসে access রাখে, কেউ পুরো জানে না" |
| ০:৩৫-১:২০ | ২. Arif চলে যাচ্ছে | HR offboarding case খোলে। Plan আসে: email disable, GitHub revoke, laptop return, কাজ reassign, আর **২টা অনাথ agent**। প্রতিটা ধাপের পাশে "কেন" panel: কোন policy clause | "AI plan বানায়, কিন্তু প্রতিটা ধাপের পেছনে company-র নিজের policy" |
| ১:২০-১:৫০ | ৩. Manager-এর সংশোধন | Nabil বলে: bot বন্ধ কোরো না, আমার কাছে দাও, কিন্তু write থেকে read। Plan-এর নতুন revision, আর এই সংশোধন একটা lesson candidate হয়, approve হয় | "মানুষের সংশোধন থেকে system শেখে, কিন্তু শুধু approve করা শিক্ষা" |
| ১:৫০-২:৪০ | ৪. Execution আর প্রমাণ | Approve চাপতেই stopwatch চালু। n8n canvas-এ workflow চলে। **আসল GitHub-এ** Arif-এর access কাটে, bot-এর deploy key বদলে read-only হয়। Backend GitHub API থেকে যাচাই করে। Map-এ Arif-এর node নিভে যায়, bot Nabil-এর সাথে যুক্ত হয়। Stopwatch থামে, যেমন "৩ মিনিট ৪০ সেকেন্ড" | "৩০% ক্ষেত্রে এটা এক মাসের বেশি লাগে। আমাদের লাগল কয়েক মিনিট, আর প্রমাণ এসেছে GitHub থেকে, n8n-এর কথা থেকে না" |
| ২:৪০-৩:৩০ | ৫. Bot নিজে access চায় | একটা AI client MCP দিয়ে বলে: bot-এর release-এর জন্য ২ ঘণ্টা write access দরকার। Policy বলে confidential repo-তে IT owner লাগে। Tahmid-এর phone-এ notification, approve, মেয়াদসহ access। পাশে একটা low-risk read request নিজে approve হয়ে যায় | "Agent-ও access চায় একই নিয়মে: কম ঝুঁকি হলে সাথে সাথে, বেশি হলে মানুষের অনুমতি, আর মেয়াদ শেষে নিজে বন্ধ" |
| ৩:৩০-৪:৪০ | ৬. Main wow: Policy V2 | IT owner Access Policy V2 upload করে: confidential repo-তে agent-এর write access-এর জন্য sponsor-এর security training লাগবে। Guardian পুরনো আর নতুন নিয়ম পাশাপাশি দেখায়, আর খুঁজে বের করে: bot-এর নতুন access, আর দৃশ্য ৩-এর lesson, দুটোই এখন নিয়ম ভাঙছে। Map-এ লাল হয়ে জ্বলে। একটা remediation approve করলে access নামে, lesson stale হয় | "Policy বদলায়, কিন্তু পুরনো সিদ্ধান্ত কেউ আবার দেখে না। LivingOps দেখে" |
| ৪:৪০-৫:১৫ | ৭. প্রমাণ আর মান | এক click-এ ISO 27001 evidence report (6.5, 5.11, 5.18, 8.2)। Evaluation panel: plan schema-valid %, evidence থাকা ধাপের %, Guardian-এর impact recall | "Auditor যা চায়, সেটা কাজের সাথেই তৈরি হয়" |
| ৫:১৫-৬:০০ | ৮. ব্যবসা আর দায়িত্ব | KPI (demo company-তে মাপা, সেভাবেই লেখা), pricing, scale, ethical safeguard, NRB পরিকল্পনা | "১০০-৫০০ জনের company-র জন্য, enterprise tool-এর দামের ভগ্নাংশে" |

**Fallback:** প্রতিটা দৃশ্যের জন্য cached demo mode চালু রাখার switch, আর পুরো demo-র একটা recording। বিস্তারিত নিচে Demo mode অংশে।

## Repo-র বর্তমান অবস্থা

২৩ অক্টোবরের commit "stage 3 complete" অনুযায়ী backend-এর মূল কাজ প্রায় শেষ, তাই নতুন কাজ মূলত বাড়ানো, নতুন করে লেখা না। ১১০টা file, প্রায় ১৬,০০০ লাইন code (data বাদে), সব Python file-এর syntax ঠিক, কোনো secret leak নেই।

| অংশ | অবস্থা | মূল file |
| --- | --- | --- |
| Cases, triage, policy context | আছে | `cases/` |
| Onboarding আর offboarding LangGraph (validate + একবার repair) | আছে | `graphs/`, `planning/`, `offboarding/` |
| Approval, manager revision | আছে | `approvals/`, `revisions/` |
| n8n dispatch, retry, verification | আছে, কিন্তু verification একই database পড়ে | `execution/` |
| Handover, approved learning | আছে | `handover/`, `learning/` |
| Policy Guardian আর remediation | আছে | `policy_guardian/` |
| Audit timeline, coverage | আছে | `audit/` |
| Security alert, Isolation Forest | আছে, ফলাফল দুর্বল | `security/`, `ml/` |
| Frontend, ৬ page | আছে, plain HTML/JS, দেখতে সাধারণ | `frontend/` |
| Demo CLI, reset, ২৩টা test | আছে | `scripts/`, `tests/` |

**যা নেই বা দুর্বল:**

- n8n workflow-এর JSON repo-তে নেই, আর workflow শুধু mock API দিয়ে database update করে
- Verification n8n যে database-এ লিখেছে সেটাই পড়ে, তাই "independent" দাবি দুর্বল
- ML: test set-এর ৪৪% window-ই attack, তাই random-এর baseline PR-AUC প্রায় ০.৪৪; model পেয়েছে ০.৫২, আর প্রতি ১,০০০ window-এ ৪১৯টা alert
- Agent, MCP, evidence report, evaluation panel, "কেন" panel নেই
- Docker Compose, Alembic, deployment, offline fallback নেই
- Seed data মাত্র ৬ জন মানুষ
- Repo-তে `backend.zip` আর `frontend.zip` (ভেতরে `__pycache__`), root `.env.example`-এ `DATABASE_URL=` key নেই, backend README-তে একটা নির্দিষ্ট plan ID দিয়ে পুরনো debugging নির্দেশনা, root-এ README নেই
- `_required_action_for_resource` একই logic `offboarding/service.py` আর `offboarding/graph_runner.py` দুই জায়গায়, agent যোগ করার সময় দুটোই বদলাতে হবে বা একটায় আনতে হবে
- `main.py`-তে version এখনো `0.2.0-stage2`

## Technical design: AI agent as workforce

Agent হবে একটা `CompanyResource`, নতুন table লাগবে না। সবচেয়ে বড় সুবিধা: `CompanyResource.person_id` স্বাভাবিকভাবেই agent-এর **sponsor** হয়ে যায়, তাই Arif-এর offboarding inventory নিজে থেকেই তার agent-গুলো তুলে আনবে, আর sponsor বদল মানে already থাকা `REASSIGN` action।

**Enum পরিবর্তন (`enums.py`):**

| Enum | যোগ হবে | কেন |
| --- | --- | --- |
| `ResourceType` | `AI_AGENT`, `AGENT_CREDENTIAL` | Agent নিজে, আর তার GitHub deploy key |
| `ActionType` | `DOWNSCOPE`, `GRANT_TEMPORARY` | Write থেকে read নামানো; MCP দিয়ে মেয়াদসহ access |
| `ResourceState` | `SUSPENDED`, `EXPIRED` | Agent সাময়িক বন্ধ; মেয়াদ শেষ হওয়া access |
| `AuditActorType` | `AGENT` | Agent নিজে যখন MCP দিয়ে request করে |

**AI\_AGENT-এর `details_data`:** `agent_name`, `platform` (n8n, GitHub App, custom), `purpose`, `scopes` (যেমন `[{system: github, repo: aurora, permission: write}]`), `credential_key` (তার `AGENT_CREDENTIAL`-এর resource key), `risk_tier`, `expires_at`, `last_active_at`।

**Orphan-এর সংজ্ঞা (deterministic, LLM ছাড়া):** একটা agent অনাথ যদি তার sponsor-এর `employment_status` হয় `DEPARTING` বা `INACTIVE`, অথবা `expires_at` পার হয়ে গেছে, অথবা sponsor-এর কোনো record নেই।

**Offboarding-এ নিয়ম:** Sponsor চলে গেলে প্রতিটা agent-এর জন্য plan-এ একটা action থাকতেই হবে: `REASSIGN` (successor-কে sponsor বানানো, চাইলে সাথে `DOWNSCOPE`) অথবা `REVOKE` (agent বন্ধ, credential মুছে ফেলা)। কোনটা, সেটা LLM policy দেখে প্রস্তাব করবে, manager বদলাতে পারবে। Validation নিশ্চিত করবে কোনো agent বাদ পড়েনি আর কোনো agent চলে যাওয়া মানুষের নামে থেকে যায়নি।

**নতুন seed policy: Agent Policy V1 (`AGENT`):**

1. প্রতিটা AI agent-এর একজন active human sponsor থাকবে।
2. Sponsor চলে গেলে শেষ কর্মদিবসের মধ্যে agent অন্য sponsor-এর কাছে যাবে বা বন্ধ হবে।
3. Confidential repo-তে agent-এর write access-এর জন্য IT Owner-এর approval লাগবে, আর সেটা ৮ ঘণ্টার বেশি হবে না।
4. Read access low-risk, policy মিললে নিজে approve হতে পারে।

**যা বদলাবে:**

| File | পরিবর্তন |
| --- | --- |
| `enums.py` | উপরের নতুন value |
| `scripts/patch_*.py` বা প্রথম Alembic migration | `company_resources` আর `case_actions`-এর check constraint-এ নতুন value (আগের `patch_resource_state.py`-এর মতো) |
| `offboarding/service.py`, `offboarding/graph_runner.py` | `_required_action_for_resource`-এ AI\_AGENT আর AGENT\_CREDENTIAL, দুই জায়গার duplicate একটায় আনা |
| `planning/validation.py` | `ALLOWED_RESOURCE_TYPES`-এ নতুন action আর type |
| `mock_company/service.py` | `MUTATION_RESOURCE_TYPES`-এ নতুন নিয়ম; GitHub-এর resource-গুলো এখান থেকে n8n-এ যাবে |
| `offboarding/prompt.py` | Agent নিয়ে নির্দেশনা |
| নতুন `agents/` module | `GET /agents`, `GET /agents/orphans`, `GET /agents/{key}`; map আর dashboard এখান থেকে পড়বে |
| `data/seed/agent_policy_v1.md` | উপরের policy |

## Technical design: n8n workflow আর GitHub verification

তিনটা আসল workflow বানানো হবে, যার মধ্যে Executor সত্যিকারের GitHub-এ কাজ করে। n8n কোনো সিদ্ধান্ত নেয় না; backend state রাখে আর নিজে GitHub-কে জিজ্ঞেস করে যাচাই করে। তিনটার JSON থাকবে repo-র `n8n/` folder-এ। n8n চলবে আপনার Render + Supabase deployment-এ, প্রতি ৩ মিনিটে জাগিয়ে রাখা।

```text
Manager approves -> Backend dispatches -> n8n Executor --(write token)--> GitHub org (real)
                                              |                                |
                                 email, laptop, training              (read-only token)
                                              v                                v
                                      Mock company API --(DB state)--> Backend verifier
                                                                               |
                                                                               v
                                                                      VERIFIED + audit
```

n8n যা-ই ফেরত দিক, action `VERIFIED` হয় শুধু backend নিজের read-only token দিয়ে GitHub থেকে ফল দেখার পরে।

| Workflow | Trigger | কী করে |
| --- | --- | --- |
| `livingops-executor` | Webhook (backend থেকে) | Token যাচাই → `resource_type` দেখে ভাগ → GitHub resource হলে আসল GitHub API, বাকিগুলো mock API → একই format-এ ফল |
| `livingops-notifier` | Webhook (backend থেকে) | Approval দরকার বা Guardian impact হলে Slack বা Discord-এ বার্তা, সারসংক্ষেপ আর page-এর link সহ |
| `livingops-expiry-sweeper` | Schedule, প্রতি ৫ মিনিট | Backend-এর `POST /access-grants/expire-due` ডাকে; backend মেয়াদোত্তীর্ণ access বের করে Executor দিয়ে কাটে আর যাচাই করে। State backend-এই থাকে |

**GitHub-এর demo setup (একবার করতে হবে):** একটা ফ্রি GitHub organization (যেমন `nexora-labs-demo`), তাতে `aurora` নামে একটা private repo। একটা আলাদা test account Arif হিসেবে, collaborator, write permission (invitation আগেই accept করা)। Aurora Release Bot-এর পরিচয় হবে একটা **deploy key**, write-সহ। তাহলে মাত্র একটা বাড়তি GitHub account লাগে।

| Action | GitHub API (REST) |
| --- | --- |
| মানুষের access revoke | `DELETE /repos/{owner}/{repo}/collaborators/{username}` |
| মানুষের permission বদল | `PUT /repos/{owner}/{repo}/collaborators/{username}` (`permission: pull` বা `push`) |
| Agent downscope | Write deploy key মুছে (`DELETE /repos/{owner}/{repo}/keys/{key_id}`) read-only নতুন key যোগ (`POST /repos/{owner}/{repo}/keys`, `read_only: true`); deploy key-এর permission পরে বদলানো যায় না |
| Agent-কে মেয়াদসহ write (MCP) | নতুন write deploy key যোগ, মেয়াদ শেষে Sweeper মুছে দেয় |
| Agent revoke | Deploy key মুছে ফেলা |
| যাচাই | `GET /repos/{owner}/{repo}/collaborators/{username}/permission` আর `GET /repos/{owner}/{repo}/keys` |

Deploy key-এর public key backend বানাবে (ed25519, `cryptography` library), private key কোথাও রাখা হবে না, demo-তে এটা ঠিক আছে।

**দুটো আলাদা token, যাতে যাচাই সত্যিই independent হয়:** n8n-এ থাকবে লেখার অনুমতিসহ একটা fine-grained token (collaborator আর deploy key administration); backend-এ থাকবে শুধু পড়ার একটা token। Executor যা-ই বলুক, backend নিজের token দিয়ে GitHub থেকে ফল দেখে action-কে `VERIFIED` করবে।

**Contract (এখনকার payload-এর সাথে মিল রেখে):** Backend পাঠায় `action_id`, `case_id`, `person_id`, `action_type`, `resource_type`, `resource_key`, `idempotency_key`, `requested_data`। GitHub action-এর জন্য `requested_data.github` = `{owner, repo, username?, permission?, key_id?, public_key?, key_title?}`। n8n ফেরত দেয় `{status, execution_id, external_ref, details}`।

**একটা জরুরি সংশোধন:** এখনকার `execution/service.py` যেকোনো 2xx JSON উত্তরকে সফল ধরে। তাই Executor কাজ ব্যর্থ হলে অবশ্যই non-2xx (যেমন 502) ফেরত দেবে, body-তে শুধু `status: FAILED` লিখলে চলবে না। Backend-এও `status` field যাচাই যোগ করা হবে।

**Backend-এ যা বদলাবে:** `execution/verification.py`-তে GitHub resource-এর জন্য নতুন `github_verifier.py`; `config.py`-তে `GITHUB_ORG`, `GITHUB_READ_TOKEN`, `N8N_NOTIFIER_WEBHOOK`; নতুন `notifications/` module যেটা approval তৈরি আর Guardian impact-এর সময় Notifier ডাকে।

## Technical design: MCP Access Gateway

Agent-রা MCP দিয়ে access চাইবে, আর সেই request মানুষের case-এর মতোই case, plan, approval, execution আর audit-এর ভেতর দিয়ে যাবে। নতুন pipeline না বানিয়ে নতুন একটা case type যোগ করা হবে: `ACCESS_REQUEST`।

**Architecture:** MCP server হবে আলাদা ছোট একটা process (`mcp_server/`), Python MCP SDK-এর FastMCP দিয়ে, Streamable HTTP transport-এ। MCP SDK async, কিন্তু আপনার plan book-এর নিয়ম backend synchronous রাখা। তাই MCP server শুধু একটা পাতলা adapter: সে backend-এর REST API ডাকে, নিজে কোনো state রাখে না। Backend আগের মতো synchronous থাকে।

**পরিচয়:** প্রতিটা agent-এর একটা আলাদা API key, যেটা তার `AI_AGENT` resource-এর সাথে যুক্ত। Key দিয়ে MCP server জানে কে চাইছে, আর তার sponsor কে।

**MCP tools:**

| Tool | কাজ |
| --- | --- |
| `whoami` | Agent-এর পরিচয়, sponsor, বর্তমান access |
| `request_access` | `system`, `resource`, `permission`, `duration_minutes`, `reason` নিয়ে request খোলে |
| `check_request` | Request-এর অবস্থা: auto-approved, অপেক্ষায়, approved, denied, active, expired |
| `list_my_access` | চালু থাকা সব grant আর তাদের মেয়াদ |
| `release_access` | কাজ শেষ হলে agent নিজে access ছেড়ে দেয় |

**Risk tier, deterministic নিয়মে (LLM সিদ্ধান্ত নেয় না):**

| Tier | কখন | কী হয় |
| --- | --- | --- |
| LOW | Non-confidential resource-এ read, sponsor active, policy মেলে | নিজে approve, `SYSTEM` approver হিসেবে audit, তবুও মেয়াদসহ |
| HIGH | Write, অথবা confidential resource | IT Owner-এর approval, Notifier দিয়ে phone-এ বার্তা |
| DENY | Production বা admin access, sponsor নেই, মেয়াদ policy-র সীমার বেশি | সাথে সাথে প্রত্যাখ্যান, কারণসহ |

**LLM-এর কাজ:** Hybrid RAG দিয়ে প্রাসঙ্গিক policy clause খুঁজে আনা, আর approver-এর জন্য এক-দুই লাইনে ব্যাখ্যা লেখা: কে চাইছে, কেন, কোন clause প্রযোজ্য। Tier ঠিক করে নিয়ম, ব্যাখ্যা দেয় AI। এতে approval fatigue কমে, কারণ low-risk request কখনো মানুষের কাছে যায় না।

**Flow:** `request_access` → backend `ACCESS_REQUEST` case খোলে → plan-এ একটাই `GRANT_TEMPORARY` action, `expires_at` সহ → tier অনুযায়ী auto-approve বা approval queue → approve হলে Executor GitHub-এ write deploy key যোগ করে → backend GitHub থেকে যাচাই → agent `check_request`-এ দেখে active → মেয়াদ শেষে Sweeper থেকে backend key মুছে দেয় আর `EXPIRED` করে।

**নতুন backend endpoint:** `POST /access-requests`, `GET /access-requests/{id}`, `GET /agents/{key}/grants`, `POST /access-grants/{id}/release`, `POST /access-grants/expire-due` (service token দিয়ে সুরক্ষিত)।

**Demo client:** Stage-এ নির্ভরযোগ্যতার জন্য একটা ছোট scripted Python MCP client, যেটা Aurora Release Bot সেজে terminal-এ request পাঠায় আর উত্তর দেখায়। সময় থাকলে Claude Desktop বা অন্য কোনো MCP client-এ একই server যোগ করে দেখানো যায় যে যেকোনো standard agent এটা ব্যবহার করতে পারে।

## Technical design: Guardian আর Learning-কে agent পর্যন্ত

Guardian আর Learning দুটোই already কাজ করে; শুধু তাদের agent চিনতে শেখাতে হবে, যাতে দৃশ্য ৬-এ bot-এর access আর দৃশ্য ৩-এর lesson একসাথে ধরা পড়ে।

**দৃশ্য ৩-এর lesson (already থাকা `create_plan_correction_candidate` দিয়ে):** AI plan প্রস্তাব করে bot বন্ধ করতে (`REVOKE`)। Nabil সংশোধন করে: bot আমার কাছে দাও, write থেকে read (`REASSIGN` + `DOWNSCOPE`)। এই revision থেকে lesson: "চলমান project-এর release bot-এর sponsor চলে গেলে বন্ধ না করে manager-এর কাছে read-only হিসেবে দাও"। Scope: `{case_type: OFFBOARDING, resource_type: AI_AGENT, department: ENGINEERING}`। Plan-এ agent-এর ধাপ ACCESS আর AGENT policy cite করবে, তাই lesson-এর `policy_links`-এ ACCESS V1 থাকবে।

**Access Policy V2-এর দুটো নতুন নিয়ম (`data/seed/access_policy_v2.md`):**

1. Confidential repo-তে কোনো agent-এর write access-এর জন্য তার sponsor-এর confidential security training শেষ থাকতে হবে।
2. যে agent-এর sponsor বদলেছে, নতুন sponsor-এর কাছে যাওয়ার ২৪ ঘণ্টার মধ্যে IT Owner-কে সেটা পুনরায় অনুমোদন করতে হবে।

**Guardian কী ধরবে:**

| Target | কীভাবে খুঁজে পায় | প্রস্তাবিত কাজ |
| --- | --- | --- |
| দৃশ্য ৩-এর lesson | `policy_links`-এ ACCESS V1 (already আছে) | `MARK_STALE`, retrieval থেকে সরানো (already আছে) |
| Bot-এর চালু write grant (দৃশ্য ৫) | `ACCESS_REQUEST` plan-এর `policy_links`-এ ACCESS V1, আর নতুন deterministic re-check: Nabil-এর `SECURITY-CONFIDENTIAL` training resource নেই | `DOWNSCOPE` বা `REVOKE`, Executor দিয়ে GitHub-এ |
| Bot নিজে | নতুন নিয়ম ২: sponsor বদলেছে, IT Owner-এর re-certification নেই | `REVIEW`, IT Owner-এর approval queue |

**যা বদলাবে:**

| File | পরিবর্তন |
| --- | --- |
| `enums.py` | `PolicyImpactTargetType`-এ `RESOURCE`; `CaseType`-এ `ACCESS_REQUEST` |
| `policy_guardian/service.py` | `_plan_contains_sensitive_access`-এ `AI_AGENT` আর `AGENT_CREDENTIAL`; নতুন `_recheck_agent_resources` যেটা চালু agent grant নতুন নিয়মে মিলিয়ে দেখে |
| `policy_guardian/remediation.py` | Resource impact-এর জন্য remediation: একটা ছোট `ACCESS_REQUEST`-ধরনের case খুলে `DOWNSCOPE` action চালানো, যাতে approval আর audit আগের মতোই থাকে |
| `policy_guardian/prompt.py` | Agent-সংক্রান্ত নিয়ম চেনার নির্দেশনা |
| `learning/service.py` | Agent-scope lesson-এর জন্য sanitization আর scope নিয়ম |

**সতর্কতা:** Re-check-টা deterministic রাখবেন, LLM দিয়ে না। Guardian-এর LLM শুধু পুরনো আর নতুন নিয়মের পার্থক্য সহজ ভাষায় লেখে। কোন জিনিস প্রভাবিত, সেটা policy link আর নিয়ম দিয়ে ঠিক হয়, যাতে demo প্রতিবার একই ফল দেয়।

## Explainability, evidence, evaluation আর KPI

এই চারটা অংশ নতুন data তৈরি করে না; already জমা থাকা plan, policy link আর audit event থেকে পড়ে দেখায়। তাই খরচ কম, কিন্তু Technical, Business আর Impact তিন জায়গায় নম্বর আনে।

**১. "কেন" panel (প্রতিটা plan ধাপে):** কোন policy, version আর clause (evidence ID যেমন `POL-AGENT-V1-C0`, ক্লিক করলে clause-এর লেখা), কোন approved lesson ব্যবহার হয়েছে (policy-র নিচে আলাদা করে, plan book-এর নিয়ম মেনে), AI-এর এক লাইনের ব্যাখ্যা, validation ফল, আর একবার repair হয়েছে কিনা। Chain-of-thought কখনো দেখানো হবে না।

**২. ISO 27001 evidence report:** `GET /cases/{id}/evidence` থেকে একটা printable HTML report, frontend থেকে PDF হিসেবে save করা যায়।

| Control | Report-এ যা থাকে |
| --- | --- |
| 6.5 চাকরি ছাড়া বা role বদলের পরের দায়িত্ব | Termination date, প্রতিটা access বন্ধের timestamp, মাঝের সময়, ২৪ ঘণ্টার মধ্যে হয়েছে কিনা |
| 5.11 Asset ফেরত | Laptop-এর return request, তারিখ, অবস্থা |
| 5.18 Access rights | প্রতিটা access-এর policy কারণ, কে approve করল, কখন, কোন evidence ID |
| 8.2 Privileged access | GitHub write আর agent credential আলাদা করে, verification-এর প্রমাণসহ |

Report-এ স্পষ্ট লেখা থাকবে যে এটা audit-এর সহায়ক প্রমাণ, certification না।

**৩. Evaluation panel:** একটা ছোট page বা Dashboard-এর একটা অংশ, `scripts/run_evaluation.py` চালিয়ে তৈরি JSON থেকে। Plan book-এর ১৭.৩-এর metrics থেকে বাছাই:

- Plan schema-valid rate, আর একবার repair-এর পরে valid rate
- কত % plan ধাপে বর্তমান policy-র evidence আছে
- Seeded প্রশ্নে policy retrieval-এর recall@K
- Guardian: seed করা প্রভাবিত item-এর কত % ধরল, কয়টা ভুল impact
- Execution: verified completion rate, duplicate রোধ, retry-তে উদ্ধার

সংখ্যা যা আসবে তাই দেখাবেন, নিজে থেকে বাড়িয়ে না।

**৪. KPI (Dashboard-এর উপরে):**

- Termination থেকে সব access বন্ধ: সময় (দৃশ্য ৪-এর stopwatch এটাই)
- মালিকসহ access-এর %, মানুষ আর agent আলাদা
- Policy কারণসহ access-এর %
- অনাথ agent-এর সংখ্যা
- মেয়াদসহ বনাম স্থায়ী agent access
- Manual কাজের তুলনা: আগে কয়টা ধাপ কয়জন মানুষের হাতে, এখন কয়টা approval

সব KPI-র নিচে লেখা থাকবে "Nexora Labs demo company-তে মাপা, simulated operational comparison"। বাস্তব customer-এর ফল হিসেবে দেখাবেন না।

## Frontend redesign আর dark interactive map

এখনকার zero-build HTML/JS frontend রাখা হবে, React-এ নতুন করে লেখা হবে না; সময় যাবে design আর map-এ। ৬টা page-এর কাঠামো থাকবে, শুধু চেহারা আর কয়েকটা নতুন অংশ বদলাবে।

**Design system:** Dark-first, সব রং CSS token-এ, একই typography আর spacing সব page-এ। Status-এর জন্য নির্দিষ্ট রং: active, departing (amber), inactive (ধূসর), অনাথ বা নিয়ম ভাঙছে (লাল), approval-এর অপেক্ষায় (নীল), verified (সবুজ)। রঙের পাশাপাশি আকার বা icon দিয়েও অবস্থা বোঝানো, যাতে projector-এ রং ফিকে হলেও পড়া যায়।

**Map (Dashboard-এর কেন্দ্র):**

- Library: D3 v7-এর force simulation, SVG-এ। ১০০-১৩০টা node-এ মসৃণ চলে, আর ধীরে নড়া node-গুলো "জীবন্ত company" অনুভূতি দেয়
- Node: মানুষ বৃত্ত (আকার = কতগুলো access), agent ছোট ষড়ভুজ; department অনুযায়ী গুচ্ছ
- Edge: manager-এর সম্পর্ক পাতলা line, agent-এর sponsor dashed line
- Click: পাশে details panel খোলে (role, manager, resources, agents, কোন policy-র কারণে)
- নিচে table: মানুষ আর agent, search আর filter (department, status, অনাথ); row-এ click করলে map-এ সেই node highlight
- Live: প্রতি ২-৩ সেকেন্ডে backend থেকে poll (plan book-এর নিয়ম মেনে WebSocket নয়)। Action verify হলে animation: Arif-এর node ধীরে নিভে যায়, bot-এর sponsor line Arif থেকে সরে Nabil-এ যায়, Guardian impact-এ প্রভাবিত node লাল হয়ে স্পন্দিত হয়
- Data: নতুন `GET /workforce/graph` endpoint, একটা call-এ সব node আর edge

**Page অনুযায়ী পরিবর্তন:**

| Page | নতুন বা বদলানো |
| --- | --- |
| Dashboard | Map, KPI সারি, evaluation-এর সংক্ষেপ, "Demo mode" নির্দেশক |
| Cases | নতুন case type `ACCESS_REQUEST`, agent-দের request আলাদা করে দেখা |
| Workspace | প্রতিটা ধাপে "কেন" panel, stopwatch, n8n execution ID আর GitHub verification আলাদা করে, evidence report button |
| Approvals | Agent request-এর জন্য AI-এর ব্যাখ্যা আর risk tier, এক click-এ approve |
| Guardian | পুরনো আর নতুন নিয়ম পাশাপাশি সহজ ভাষায়, impact list, প্রতিটা impact-এ click করলে map-এ highlight |
| Security | চেহারা নতুন design-এ, বাকি আগের মতো |

**কাজের নিয়ম:** Frontend বানানোর আগে নতুন endpoint-গুলোর response freeze করা (plan book-এর ৩.১-এর মতো), তারপর UI। বানানোর সময় frontend-design নির্দেশিকা মেনে চলা।

## Seed data

গল্পের ৬টা চরিত্র আর তাদের UUID ঠিক যেমন আছে তেমন থাকবে, তাদের চারপাশে একটা বড়, বিশ্বাসযোগ্য company তৈরি হবে। সব data কাল্পনিক, README আর UI-তে সেটা স্পষ্ট লেখা থাকবে।

**গল্পের চরিত্র (অপরিবর্তিত):** Farhana Islam (HR Manager), Nabil Chowdhury (Engineering Manager), Tahmid Hasan (IT Security Owner), Amina Rahman আর Rafi Ahmed (নতুন AI Engineer), Arif Hossain (Senior Software Engineer, চলে যাচ্ছেন)।

**যা যোগ হবে:**

| জিনিস | সংখ্যা | বিস্তারিত |
| --- | --- | --- |
| মানুষ | মোট ৮০-১০০ | Engineering, Product, Design, Sales, Support, Finance, People, IT Security; manager tree; কয়েকজন DEPARTING আর INACTIVE |
| AI agent | ২০-৩০ | Release bot, support triage bot, invoice reconciler, meeting summarizer ইত্যাদি; প্রত্যেকের sponsor আর scope |
| আগে থেকেই অনাথ agent | ৩-৪ | যাদের sponsor আগে চলে গেছে, যাতে প্রথম দৃশ্যেই map-এ কিছু লাল দেখা যায় |
| Resource | প্রতি জনে ৩-৬টা | Email, GitHub, laptop, training, work item, document |
| Policy | ৪টা V1 + ACCESS V2 | ACCESS, EQUIPMENT, OFFBOARDING, নতুন AGENT; V2 দৃশ্য ৬-এর জন্য |

**Aurora Release Bot:** Sponsor Arif, platform n8n, purpose "Aurora-র release tag আর changelog", scope `aurora` repo-তে write, credential একটা আসল GitHub deploy key, risk tier HIGH।

**তৈরির নিয়ম:**

- Generator script নির্দিষ্ট random seed দিয়ে চলবে, যাতে প্রতিবার একই company তৈরি হয়; নামগুলো বাংলাদেশি নামের মিশ্রণ, email `@nexora.demo`
- শুধু গল্পের resource-গুলো (Arif, bot, Aurora repo) আসল GitHub-এর সাথে যুক্ত; বাকি সব mock
- `reset_demo.py` সব কিছু এক command-এ আগের অবস্থায় ফেরায়, GitHub-এর demo অবস্থাও (Arif collaborator হিসেবে ফিরে আসে, bot-এর write deploy key আবার তৈরি হয়)
- Generated ID আর GitHub key ID `data/seed/demo_ids.json`-এ, যেটা `.gitignore`-এ already আছে

## Demo mode আর offline fallback

Venue-র WiFi-তে LLM, n8n, GitHub, Slack আর MCP একসাথে চলবে, তাই নির্ভরযোগ্যতা প্রথম দিন থেকেই design-এর অংশ, সপ্তাহ ৮-এর কাজ না। তিনটা স্তর থাকবে, প্রতিটা একটা switch দিয়ে বদলানো যায়।

| Mode | কী live, কী cached | কখন |
| --- | --- | --- |
| `LIVE` | সবকিছু আসল: OpenAI, n8n, GitHub, notification | Internet ভালো থাকলে, এটাই প্রথম পছন্দ |
| `CACHED_AI` | LLM-এর উত্তর আগে থেকে রাখা; n8n আর GitHub আসল | OpenAI ধীর বা বন্ধ |
| `OFFLINE` | LLM cached, execution mock, verification local; সব laptop-এ চলে | Internet একেবারে নেই |

**কীভাবে:**

- একটা `DEMO_MODE` setting, Dashboard-এ ছোট করে দেখানো
- LLM call-এর চারপাশে একটা wrapper: input-এর hash দিয়ে উত্তর `data/demo_cache/`-এ রাখে; `LIVE`-এ rehearsal চালালেই cache ভরে যায়, পরে `CACHED_AI`-এ একই input-এ একই উত্তর
- Hybrid RAG-এর embedding-ও cache করা, কারণ OpenAI embedding ছাড়া retrieval চলে না
- `OFFLINE`-এর জন্য local Docker Compose: PostgreSQL, Qdrant, backend, frontend, MCP server; n8n-এর বদলে mock executor
- প্রতিটা mode-এ demo-র ফল একই দেখাবে, শুধু execution ID আর timestamp বদলাবে

**শেষ ভরসা:** পুরো ৬ মিনিটের demo-র একটা ভালো মানের screen recording, আর প্রতিটা দৃশ্যের screenshot pitch deck-এর পেছনে রাখা।

**Rehearsal-এর নিয়ম:** Final-এর আগে অন্তত ১০ বার পুরো demo reset থেকে শেষ পর্যন্ত, তিনটা mode-এই অন্তত একবার করে।

## Deployment আর repo পরিষ্কার

Judges বা যে কেউ একটা link-এ live product দেখতে পারবে, আর repo খুললে প্রথম দেখাতেই বোঝা যাবে এটা কী। n8n already Render + Supabase-এ চলছে, প্রতি ৩ মিনিটে জাগিয়ে রাখা; বাকি অংশ জাগিয়ে রাখা হবে না, যাতে Render-এর free plan-এর মাসিক ৭৫০ instance-hour শেষ না হয়।

**Deployment:**

| অংশ | কোথায় | মন্তব্য |
| --- | --- | --- |
| PostgreSQL | Supabase (already) | Demo data আর আসল data আলাদা schema বা project-এ |
| Qdrant | Qdrant Cloud (already) |  |
| n8n | Render + Supabase (already, সবসময় জাগানো) | ৩টা workflow import |
| Backend + MCP server | Render-এ আলাদা service, অথবা একটা ছোট VPS | Demo-র আগের দিন থেকে জাগিয়ে রাখা, ঘণ্টার হিসাব দেখে |
| Frontend | Static host (Render static site, Netlify বা Vercel) | Backend URL environment থেকে |
| Local fallback | Laptop-এ Docker Compose | `OFFLINE` mode-এর জন্য |

**নতুন file:** `docker-compose.yml`, `backend/Dockerfile`, `mcp_server/Dockerfile`, একটা Alembic baseline migration (নতুন enum value-গুলো এখানে, হাতে চালানো patch script-এর বদলে)।

**Repo পরিষ্কার:**

- [ ] `backend.zip` আর `frontend.zip` মুছে ফেলা; সব `__pycache__` সরানো
- [ ] Root `.env.example` ঠিক করা: `DATABASE_URL=` key, Supabase host-এর বদলে placeholder, সব নতুন variable (`GITHUB_ORG`, `GITHUB_READ_TOKEN`, `N8N_NOTIFIER_WEBHOOK`, `DEMO_MODE`, `MCP_SERVICE_TOKEN`)
- [ ] Backend README থেকে নির্দিষ্ট plan ID-সহ পুরনো debugging অংশ সরানো
- [ ] দুটো `requirements.txt` একটায় আনা, `sentence-transformers` বাদ (reranker বাদ দেওয়া হয়েছে)
- [ ] `main.py`-তে version ঠিক করা
- [ ] `n8n/` folder-এ ৩টা workflow JSON, credential ছাড়া
- [ ] Root README: এক লাইনের পরিচয়, architecture diagram, demo GIF, এক command-এ local চালানো, demo-র চরিত্র, test চালানো, সীমাবদ্ধতা আর সূত্র
- [ ] Commit message-এ work package-এর নাম, plan book-এর নিয়ম মেনে; final-এর আগে release tag

## ৯ সপ্তাহের schedule

প্রথম ৩ সপ্তাহ সব শক্তি hero গল্পে; ১৫ নভেম্বরের gate পার না হলে MCP ছোট হবে। ২৯ নভেম্বর API freeze, তারপর frontend আর deployment, শেষ দুই সপ্তাহ শুধু pitch আর rehearsal। প্রতিটা সপ্তাহ রবিবার শুরু, শনিবার শেষ।

| Dates (2026) | Workstream |
| --- | --- |
| Oct 26 - Nov 8 | Agent model + seed; n8n + real GitHub |
| Nov 9 - Nov 15 | Hero scene end to end |
| **Nov 15** | **Gate: hero scene runs** |
| Nov 16 - Nov 22 | Guardian + learning |
| Nov 16 - Nov 29 | MCP Access Gateway |
| Nov 23 - Nov 29 | Evidence + evaluation |
| **Nov 29** | **Gate: API freeze** |
| Nov 30 - Dec 13 | Map + frontend |
| Dec 7 - Dec 13 | Docker, deploy, README |
| Dec 14 - Dec 25 | Pitch + rehearsal |
| **Dec 26** | **Final, Daffodil International University** |

**প্রতি সপ্তাহের শেষে যা প্রমাণ থাকবে:**

1. **২৬ অক্টো-১ নভে:** নতুন enum আর migration, Agent Policy V1, seed generator; GitHub org-এ curl দিয়ে প্রতিটা API call পরীক্ষিত
2. **২-৮ নভে:** Executor workflow আসল GitHub-এ revoke আর deploy key বদল করে; backend নিজের token দিয়ে যাচাই করে; Notifier বার্তা পাঠায়
3. **৯-১৫ নভে:** Arif-এর case থেকে plan, Nabil-এর সংশোধন, lesson, execution, verification একটানা চলে; `CACHED_AI` mode কাজ করে **(gate)**
4. **১৬-২২ নভে:** Policy V2 bot-এর grant আর lesson দুটোই ধরে; remediation GitHub-এ downscope করে
5. **২৩-২৯ নভে:** MCP server, risk tier, auto-expiry Sweeper; evidence report আর evaluation script; নতুন endpoint-এর response freeze **(gate)**
6. **৩০ নভে-৬ ডিসে:** Design system, map, Dashboard
7. **৭-১৩ ডিসে:** Workspace, Approvals, Guardian redesign; Docker Compose, deployment, README, repo পরিষ্কার
8. **১৪-২০ ডিসে:** Pitch deck, business slide, প্রথম ৫টা পূর্ণ rehearsal, recording
9. **২১-২৫ ডিসে:** বাকি rehearsal, তিনটা mode-এ পরীক্ষা, Q&A অনুশীলন; নতুন feature নয়

## ঝুঁকি আর cut line

সবচেয়ে বড় ঝুঁকি সময়: প্রায় একা ৯ সপ্তাহে এতটা কাজ। তাই আগে থেকে ঠিক করা আছে কোন তারিখে পিছিয়ে থাকলে কী কাটবেন, যাতে hero গল্প কখনো ঝুঁকিতে না পড়ে।

| ঝুঁকি | আগাম সংকেত | ব্যবস্থা |
| --- | --- | --- |
| Hero গল্প সময়ে চালু হয় না | ১৪ নভেম্বরের মধ্যে Arif-এর দৃশ্য end-to-end চলে না | MCP অংশ ছোট করে শুধু একটা HIGH request, Claude Desktop বাদ |
| GitHub API-র অপ্রত্যাশিত আচরণ (invitation, permission) | Setup-এর প্রথম দিনেই curl দিয়ে কাজ করে না | n8n-এর আগে curl দিয়ে প্রতিটা call পরীক্ষা; সমস্যা থাকলে শুধু deploy key দিয়ে গল্প |
| Guardian অপ্রত্যাশিত impact ধরে বা মিস করে | Evaluation-এ recall বা ভুল impact খারাপ | Agent re-check deterministic রাখা; seed করা impact দিয়ে test |
| LLM-এর উত্তর demo-তে বদলে যায় | Rehearsal-এ ভিন্ন plan আসে | `CACHED_AI` mode; validation আর deterministic নিয়ম |
| Map ধীর বা জটলা | ১০০+ node-এ ঝাঁকুনি | Canvas rendering বা node কমানো; department গুচ্ছ স্থির রাখা |
| Frontend redesign সময় খায় | ১২ ডিসেম্বরেও অর্ধেক page পুরনো | Dashboard, Workspace, Guardian তিনটা page আগে; Security আর Cases পুরনো design-এ থাকতে পারে |
| Render-এর ঘণ্টা শেষ | Dashboard-এ usage দ্রুত বাড়ছে | শুধু n8n জাগানো; final-এর সপ্তাহে দরকার হলে এক মাসের paid plan |
| Venue-তে internet নেই | Final-এর দিন | `OFFLINE` mode আর recording |

**Cut line, গুরুত্বের উল্টো ক্রমে (সবার আগে কাটবেন উপরেরটা):**

1. ML-এর উন্নতি
2. Claude Desktop দিয়ে MCP দেখানো (scripted client থাকবে)
3. Security আর Cases page-এর redesign
4. Evaluation panel (সংখ্যাগুলো slide-এ রাখা যায়)
5. Notifier-এর phone notification (approval page-ই যথেষ্ট)

**কখনো কাটবেন না:** Arif আর bot-এর offboarding, আসল GitHub verification, Policy V2-এর Guardian দৃশ্য, map, demo mode।

## Judges-এর কঠিন প্রশ্ন আর উত্তর

প্রতিটা উত্তর ২০-৩০ সেকেন্ডে বলার মতো, আর সৎ। যা করিনি সেটা দাবি করবেন না; সীমাবদ্ধতা স্বীকার করা আন্তর্জাতিক judges-এর কাছে বিশ্বাসযোগ্যতা বাড়ায়।

| প্রশ্ন | উত্তরের মূল কথা |
| --- | --- |
| Okta বা Microsoft তো এটা করে, আপনারা কেন? | তারা বড় enterprise-এর জন্য, আলাদা license লাগে। ৫০-২,০০০ জনের company-র জন্য SailPoint অতিরিক্ত। আমরা policy document থেকে সিদ্ধান্ত নিই, policy বদলালে পুরনো সিদ্ধান্ত নিজে আবার দেখি, আর প্রমাণ বানাই; gateway-গুলো এর কোনোটাই করে না |
| এটা কি সত্যিকারের agentic AI? | ইচ্ছা করেই সীমিত। AI পড়ে, policy খোঁজে, plan আর ব্যাখ্যা বানায়; কাজে হাত দেয় policy আর মানুষের অনুমতির পরে। যে product agent-দের নিয়ন্ত্রণ করে, সে নিজে অনিয়ন্ত্রিত agent হলে বিশ্বাস হারায় |
| LLM ভুল policy বানালে? | প্রতিটা ধাপে evidence ID লাগে, validation archived বা অজানা policy আটকায়, একবার repair, তারপর human review। Evaluation panel-এ সংখ্যা দেখুন |
| n8n কেন, Python দিয়েই তো হতো? | Approve হওয়া কাজ একটা দৃশ্যমান, নির্দিষ্ট পথে চলে, আর connector বদলানো সহজ। সিদ্ধান্ত backend-এ, যাচাই GitHub থেকে, n8n শুধু চালায় |
| এগুলো তো mock company? | GitHub অংশ আসল, যাচাইও আসল GitHub API থেকে। Email, laptop mock, কারণ hackathon-এ আসল Google Workspace সম্ভব না; connector-ভিত্তিক design-এ বদলানো যায় |
| সংখ্যাগুলো কোথা থেকে? | Market-এর সংখ্যা প্রকাশিত survey থেকে, বেশিরভাগ security vendor-এর করা, slide-এ সূত্র আছে। আমাদের KPI demo company-তে মাপা, সেভাবেই লেখা |
| Approval fatigue হবে না? | Low-risk request policy মিললে নিজে approve হয়, মেয়াদসহ। মানুষ দেখে শুধু write, confidential আর ব্যতিক্রম |
| Privacy? | শুধু অনুমোদিত resource আর metadata পড়ি, private message বা personal file না। Learning-এ যাওয়ার আগে email, phone, secret মুছে ফেলা হয়, আর approval লাগে |
| ML দিয়ে কাউকে শাস্তি? | না। Score শুধু human review-এর জন্য, কখনো নিজে block বা disciplinary সিদ্ধান্ত নয় |
| Business model কী? | Managed identity প্রতি মাসিক দাম, মানুষ আর agent দুটোই; লক্ষ্য ১০০-৫০০ জনের tech আর service company, প্রথমে বাংলাদেশ, তারপর একই ধরনের অন্য বাজার। দাম এখনো hypothesis |
| Scale করবে কীভাবে? | Modular monolith, Docker, connector-ভিত্তিক execution, stateless MCP adapter। প্রতিটা নতুন system মানে একটা নতুন n8n branch আর একটা verifier |
| EU AI Act? | High-risk নিয়ম ডিসেম্বর ২০২৭-এ পিছিয়েছে; আমরা আইনের ভয় দেখিয়ে বিক্রি করি না, তবে human oversight আর traceability শুরু থেকেই আছে |

**Pricing নিয়ে একটা কথা:** নির্দিষ্ট সংখ্যা slide-এ দিলে "hypothesis" লিখবেন। তুলনার জন্য প্রকাশিত দাম ব্যবহার করবেন, যেমন Okta-র lifecycle আর governance প্রতি user প্রতি মাসে প্রায় $৯-১১ (Iden-এর লেখা অনুযায়ী) আর Vanta বছরে প্রায় $৭,৫০০-১৪,০০০।

## শুরু করার আগে যা লাগবে

সপ্তাহ ১-এর কাজ শুরু করতে আপনার কাছ থেকে এগুলো লাগবে; বেশিরভাগ ১০ মিনিটের কাজ।

- [ ] n8n-এর version, আর এখনকার workflow-এর JSON export
- [ ] ফ্রি GitHub organization (যেমন `nexora-labs-demo`) আর তাতে private repo `aurora`
- [ ] Arif-এর জন্য একটা আলাদা GitHub test account, `aurora`-তে write collaborator, invitation accept করা
- [ ] দুটো fine-grained GitHub token: একটা লেখার অনুমতিসহ (n8n-এ রাখবেন), একটা শুধু পড়ার (backend-এর `.env`-এ); token কখনো chat বা repo-তে দেবেন না
- [ ] Notification-এর জন্য Slack নাকি Discord, আর তার incoming webhook
- [ ] কাজের জন্য একটা নতুন branch (যেমন `final-build`), যাতে `main`-এর এখনকার demo সবসময় চালু থাকে
- [ ] Repo-তে আমার push access দরকার হলে সেটা জানানো; না দিলে আমি code বানিয়ে file হিসেবে দেব, আপনি push করবেন
