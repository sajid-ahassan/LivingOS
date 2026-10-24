**International AI Builders Congress 2026**

InfraSphere AI \| WorkforceOS and AgentOps

**Version 2.0  
**Prepared for Sajid Ahasan and the LivingOps AI team  
9 September 2026

# How to use this book

This manual is the authoritative implementation specification for LivingOps AI. Sections 1 through 19 preserve the approved product, scope, architecture, workflows, and three delivery stages. Sections 20 through 35 provide the exact contracts, algorithms, payloads, commands, test cases, deployment procedure, and solo execution schedule needed to build it without redesigning the product.

The project is intentionally divided into three delivery stages. Stage 1 creates the foundation. Stage 2 delivers a complete backend product that can be demonstrated from the terminal and FastAPI Swagger documentation. Stage 3 adds the final React interface, deployment, evaluation package, and event-ready presentation. Stage 2 and Stage 3 must each end in a stable, demonstrable product.

## Frozen implementation principles

- Use synchronous Python only: normal FastAPI def endpoints, normal SQLAlchemy sessions, requests, LangGraph invoke, and the synchronous Qdrant client.

- Use a modular monolith. Do not introduce microservices, Celery, Redis, Kafka, Kubernetes, WebSockets, or background job infrastructure.

- FastAPI and PostgreSQL own business state. LangGraph reasons, n8n executes fixed approved actions, and Qdrant retrieves knowledge.

- The LLM never writes directly to PostgreSQL or Qdrant and never executes high-risk actions without human approval.

- Build the complete backend before generating the final frontend. The frontend must follow the stable API contracts.

- Preserve the three approved workflows and four product branches. Do not add unrelated features.

## Contents

- 1 Product decision and market position

- 2 Scope users and measurable outcomes

- 3 Final system architecture

- 4 The three operational workflows

- 5 The four product branches

- 6 Retrieval augmented generation design

- 7 LangGraph and structured AI contracts

- 8 n8n execution and mock company system

- 9 PostgreSQL and Qdrant data design

- 10 REST API contract

- 11 ML access anomaly detector

- 12 Reliability security and audit rules

- 13 Repository dependencies and configuration

- 14 Stage 1 Building the foundation

- 15 Stage 2 Complete backend product

- 16 Stage 3 Complete event ready product

- 17 Testing and evaluation

- 18 Demonstration and judging strategy

- 19 Risks controls and definition of done

- 20 Exact implementation conventions and bootstrap

- 21 Exact PostgreSQL model contract

- 22 State machines roles and transaction rules

- 23 File by file backend implementation

- 24 Exact REST API and payload contracts

- 25 Hybrid RAG implementation specification

- 26 LangGraph workflows prompts and validators

- 27 n8n and mock company execution manual

- 28 Approved learning and Policy Guardian algorithms

- 29 ML training evaluation and serving manual

- 30 Exact Nexora Labs seed package

- 31 Complete test and evaluation catalog

- 32 Stage 3 frontend implementation specification

- 33 Deployment operations and recovery

- 34 Solo execution schedule and final handoff

- 35 Troubleshooting and authoritative references

# 1 Product decision and market position

## 1.1 Product definition

LivingOps AI is a governed internal operations platform for 100 to 500 employee digital, technology, and service companies. It reduces repetitive work across HR, IT, access management, equipment, training, and knowledge handover while keeping policies, workflow decisions, learned experience, execution evidence, and audit records aligned.

The product is not positioned primarily as an employee replacement tool. Its defensible value is workload reduction, faster case completion, fewer repeated coordination tasks, fewer policy mistakes, reliable automation, and the ability to grow without proportional growth in administrative workload.

## 1.2 Market problem

- Internal operations are distributed across email, chat, policy documents, spreadsheets, ticketing tools, and employee knowledge.

- Employees repeatedly interpret the same policies and manually coordinate the same account, equipment, training, and handover tasks.

- Normal automation becomes unsafe when policies change but old plans, learned decisions, and pending actions remain unchanged.

- Conventional RAG may answer from current documents but does not automatically revisit earlier decisions or prove that downstream actions succeeded.

- Knowledge is lost when employees leave because handovers are incomplete, generic, or stored without review.

## 1.3 Product differentiation

| **Common market capability** | **LivingOps AI difference**                                                                             |
|------------------------------|---------------------------------------------------------------------------------------------------------|
| Document chatbot             | Policy-authoritative hybrid RAG produces structured operational plans with evidence.                    |
| AI automation                | Every sensitive plan is approved; every executed action is independently verified.                      |
| AI memory                    | Only sanitized, policy-aligned, human-approved lessons enter organizational memory.                     |
| Policy search                | A Policy Change Guardian finds active plans and learned decisions affected by a new policy version.     |
| Security alerts              | A small real-data anomaly detector adds evidence-based access monitoring without autonomous punishment. |

## 1.4 Hackathon positioning

Position LivingOps AI under InfraSphere AI as a WorkforceOS and AgentOps infrastructure product. The presentation should emphasize that it provides a governed operating layer for human and AI work, rather than describing it as a generic HR application.

# 2 Scope users and measurable outcomes

## 2.1 MVP organization and actors

| **Actor**             | **Primary responsibilities**                                                                     |
|-----------------------|--------------------------------------------------------------------------------------------------|
| HR Manager            | Creates onboarding and offboarding cases and supplies employee facts.                            |
| Line Manager          | Reviews plans, corrects recommendations, approves handovers, and confirms business context.      |
| IT and Security Owner | Approves sensitive access, learning candidates, policy remediation, and security-alert outcomes. |
| Employee or candidate | Receives resources and responds to targeted offboarding knowledge questions.                     |

## 2.2 MVP boundaries

| **Included**                                 | **Explicitly excluded**                                                      |
|----------------------------------------------|------------------------------------------------------------------------------|
| Three employee-lifecycle workflows           | Additional finance, procurement, sales, and customer-support branches        |
| One demo organization named Nexora Labs      | Multi-tenant enterprise administration                                       |
| One mock company resource system             | Real Google Workspace, GitHub, Jira, HRIS, or identity-provider integrations |
| Three policy documents and one policy update | Large policy libraries and enterprise document connectors                    |
| One Isolation Forest model                   | Deep learning, multiple ML models, or automatic account blocking             |
| Six final frontend pages                     | Separate pages for every workflow step                                       |

## 2.3 Success outcomes

- A current-policy onboarding plan can be generated, reviewed, approved, executed, and verified end to end.

- A manager correction can become a governed lesson and improve a similar future case.

- A new policy version can automatically invalidate a stale lesson and pause an affected pending case.

- An offboarding case can revoke mock resources, reassign work, and preserve an approved handover.

- An unusual access event can receive an anomaly score and appear for human review.

- Every critical decision and state change can be reconstructed from the audit timeline.

# 3 Final system architecture

## 3.1 Architecture style

Use a modular monolith. The React application calls one FastAPI backend. The backend contains business services, LangGraph workflows, retrieval, anomaly scoring, audit logic, and a mock company module. PostgreSQL stores authoritative state. Qdrant stores searchable vectors. n8n runs fixed operational workflows through webhooks.

> React dashboard  
> \|  
> FastAPI modular backend  
> \|-- SQLAlchemy -\> PostgreSQL  
> \|-- Hybrid RAG -\> Qdrant + in-memory BM25 + reranker  
> \|-- LangGraph -\> OpenAI LLM or local Qwen fallback  
> \|-- requests -\> n8n -\> mock company endpoints  
> \`-- Isolation Forest -\> access-event score

## 3.2 Component ownership

| **Component**    | **Owns**                                                      | **Does not own**                                |
|------------------|---------------------------------------------------------------|-------------------------------------------------|
| React            | Forms, dashboards, filters, approval interactions             | Business state or direct database access        |
| FastAPI          | Cases, validation, approvals, state transitions, verification | Long-term vector similarity                     |
| LangGraph        | Bounded planning and analysis workflows                       | Direct execution or unrestricted writes         |
| n8n              | Fixed approved actions and workflow visualization             | Business truth and approval decisions           |
| PostgreSQL       | Authoritative operational and audit data                      | Embedding similarity search                     |
| Qdrant           | Dense vectors and retrieval payloads                          | Approval authority                              |
| Isolation Forest | Anomaly score                                                 | Blocking, disciplinary, or employment decisions |

## 3.3 Synchronous request model

All project code is synchronous. FastAPI uses normal def endpoints and SQLAlchemy Session objects. LangGraph is called with invoke. HTTP calls use requests with explicit timeouts. n8n responds after its workflow completes. A dashboard request may wait several seconds for an LLM or automation result; this is acceptable for the hackathon and substantially easier to debug.

# 4 The three operational workflows

## 4.1 Workflow 1 Intelligent onboarding planning

Purpose: determine what a new employee needs by combining employee facts, current authoritative policies, and approved organizational experience.

> 1\. HR submits employee name, role, department, manager, project sensitivity, start date, work mode, and location.
>
> 2\. FastAPI validates the request, creates the person and case records, and changes the case to PLANNING.
>
> 3\. The retrieval service searches current policy chunks and approved learning records using dense retrieval, BM25, RRF, and cross-encoder reranking.
>
> 4\. The onboarding LangGraph produces a structured plan containing equipment, accounts, access level, training, approvals, restrictions, and evidence references.
>
> 5\. Deterministic validation rejects unknown catalog items, archived policy references, missing evidence, and prohibited actions. The graph may make one repair attempt.
>
> 6\. FastAPI stores the plan as PENDING_APPROVAL. The line manager approves, rejects, or edits it through a later endpoint.
>
> 7\. An approved plan becomes the input to Workflow 2.

### Workflow 1 exceptions

- No relevant policy: produce NEEDS_HUMAN_REVIEW instead of inventing a rule.

- Sensitive production access: recommend a safer alternative and require IT approval.

- Invalid LLM schema after one repair: store failure evidence and send the case to human review.

- Policy changed before approval: mark the plan stale and regenerate using the current version.

### Workflow 1 acceptance criteria

> \[ \] Standard onboarding produces a valid JSON plan with current-policy citations.
>
> \[ \] A confidential-project case recommends restricted access and mandatory training.
>
> \[ \] No action is executable before approval.
>
> \[ \] Archived policies and stale learning are never placed in final context.

## 4.2 Workflow 2 Provisioning and verification

Purpose: convert the approved onboarding plan into verified resource state. This workflow does not decide what the employee needs; it executes the approved plan.

> 1\. FastAPI confirms that the plan is approved, non-stale, and based on current policy versions.
>
> 2\. FastAPI creates one case_action for each account, asset, access grant, or training assignment.
>
> 3\. For each action, FastAPI creates a unique idempotency key and sends a synchronous webhook request to the provisioning n8n workflow.
>
> 4\. n8n routes the action by resource type and calls the appropriate mock company endpoint.
>
> 5\. n8n returns the external resource identifier and execution result.
>
> 6\. FastAPI queries the mock company state independently and records verification_data.
>
> 7\. A failed action is retried once with the same idempotency key. A second failure becomes HUMAN_REVIEW.
>
> 8\. The case becomes COMPLETED only when every required action is verified.

### Workflow 2 acceptance criteria

> \[ \] An approved plan creates a company email, laptop assignment, repository access, and training assignment.
>
> \[ \] Repeating the same request cannot create duplicate resources.
>
> \[ \] A simulated failed action retries once and then creates a visible human-review item.
>
> \[ \] The audit timeline contains dispatch, n8n result, verification, retry, and completion events.

## 4.3 Workflow 3 Offboarding and knowledge handover

Purpose: remove access and preserve important operational knowledge when an employee leaves.

> 1\. HR starts an offboarding case and provides last working date and successor or manager.
>
> 2\. FastAPI retrieves the employee's accounts, assets, access grants, training, work items, and owned documents from company_resources.
>
> 3\. Hybrid RAG retrieves current offboarding, access, and knowledge-retention policies.
>
> 4\. The offboarding LangGraph creates a structured revocation, return, reassignment, notification, and handover plan.
>
> 5\. The graph analyzes authorized task and document metadata and produces targeted questions about unfinished work, recurring tasks, failures, contacts, and undocumented procedures.
>
> 6\. The line manager approves the plan. n8n disables mock accounts, revokes access, reassigns work, and requests asset return.
>
> 7\. FastAPI verifies each outcome. The manager reviews the generated handover document.
>
> 8\. Only the approved and sanitized handover enters organizational memory.

### Workflow 3 privacy boundary

The system reads only authorized resource, task, and document metadata used in the demo. It does not inspect private messages, personal files, passwords, or unrelated employee content.

# 5 The four product branches

| **Branch**                       | **Responsibility**                                                            | **Visible proof**                                               |
|----------------------------------|-------------------------------------------------------------------------------|-----------------------------------------------------------------|
| Internal Operations Engine       | Runs the three employee-lifecycle workflows                                   | Cases, plans, actions, resources, and outcomes                  |
| Approved Organizational Learning | Converts successful corrections into governed reusable knowledge              | Correction becomes an approved lesson and improves a later case |
| Policy Change Guardian           | Finds plans and lessons affected by a policy version change                   | V2 upload makes V1-dependent items stale or paused              |
| Reliability Security and Audit   | Verifies execution, handles failure, scores anomalies, and preserves evidence | Retry, verification, security alert, and audit timeline         |

## 5.1 Approved Organizational Learning

> 1\. Compare the original AI plan with the manager-approved revision after the case outcome is verified.
>
> 2\. Use the learning LangGraph to generate a candidate with situation, conditions, recommended action, scope, evidence, and policy references.
>
> 3\. Validate that the policy versions are current, the scope is no broader than the evidence, the candidate is not a duplicate, and private details are removed.
>
> 4\. Store the record as PENDING_APPROVAL and show it to the responsible owner.
>
> 5\. After approval, store the authoritative record in PostgreSQL and upsert its sanitized memory card into Qdrant.
>
> 6\. Future retrieval includes only status APPROVED. Rejected, pending, stale, and expired records are filtered out.

## 5.2 Policy Change Guardian

> 1\. An authorized owner uploads a new approved version for an existing policy code.
>
> 2\. PostgreSQL stores the version, marks it CURRENT, archives the previous version, and updates the retrieval index.
>
> 3\. The Guardian LangGraph loads the exact old and new texts and produces a structured change summary. It does not use similarity search for the comparison.
>
> 4\. The policy_links table identifies plans and learning records that used the old version.
>
> 5\. High-risk pending actions are paused. Affected lessons are marked STALE and removed from retrieval.
>
> 6\. The Guardian stores proposed impacts for human review. Approved remediation regenerates the plan or replaces the lesson using the current policy.

# 6 Retrieval augmented generation design

## 6.1 Knowledge sources

| **Source**                      | **Authority**                      | **Storage**                                     |
|---------------------------------|------------------------------------|-------------------------------------------------|
| Current company policies        | Highest                            | PostgreSQL source text and Qdrant policy chunks |
| Approved organizational lessons | Advisory below policy              | PostgreSQL record and Qdrant memory vector      |
| Approved handover knowledge     | Advisory and scoped                | Learning record and Qdrant memory vector        |
| Employee and case facts         | Authoritative for the current case | PostgreSQL; never embedded by default           |

## 6.2 Policy ingestion

> 1\. Validate the uploader and policy code, version number, department, and effective date.
>
> 2\. Extract PDF text with PyMuPDF. Accept plain text or Markdown through simple loaders.
>
> 3\. Normalize whitespace and calculate a SHA-256 content hash to reject duplicate uploads.
>
> 4\. Split text with RecursiveCharacterTextSplitter using approximately 800 characters and 120 characters of overlap. Keep section titles in metadata when available.
>
> 5\. Create dense embeddings using the configured OpenAI embedding model and upsert points to policy_knowledge.
>
> 6\. Rebuild the in-memory BM25 index from all CURRENT policy chunks and APPROVED memory records.

## 6.3 Hybrid retrieval and reranking

> One query  
> -\> Qdrant dense retrieval: top 10  
> -\> in-memory BM25 retrieval: top 10  
> -\> reciprocal rank fusion: top 10 unique candidates  
> -\> BAAI/bge-reranker-base cross-encoder  
> -\> final context: 4 policy chunks plus up to 2 approved memories

Do not use multi-query RAG Fusion. Reciprocal Rank Fusion is used only to merge the dense and BM25 rankings. This avoids extra LLM calls and query-generation complexity.

## 6.4 Retrieval controls

- Policy filter: status CURRENT and department equal to the case department or GLOBAL.

- Learning filter: status APPROVED and scope compatible with the case type, department, and role.

- Policy evidence remains separate from organizational memory in the final prompt.

- If a lesson conflicts with policy, discard the lesson and create an audit warning.

- Store the selected policy version IDs and chunk identifiers through policy_links for later Guardian impact detection.

- Final answers and plans cite evidence identifiers; they never cite unsupported model memory as company policy.

# 7 LangGraph and structured AI contracts

## 7.1 Graph design rule

Use LangGraph only for bounded reasoning. Human approval occurs through FastAPI endpoints and PostgreSQL states rather than a complicated asynchronous graph interrupt. Each graph runs synchronously, returns a Pydantic-validated object, and makes at most one correction attempt.

## 7.2 Required graphs

| **Graph**          | **Nodes**                                                              | **Output**           |
|--------------------|------------------------------------------------------------------------|----------------------|
| Onboarding plan    | Load case, retrieve evidence, generate plan, validate, repair once     | OnboardingPlan       |
| Offboarding plan   | Load resources, retrieve policy, generate plan and questions, validate | OffboardingPlan      |
| Learning candidate | Compare plans, retrieve policy, extract lesson, sanitize, validate     | LearningCandidate    |
| Policy Guardian    | Load exact versions, extract diff, find dependencies, classify impacts | PolicyChangeAnalysis |

## 7.3 Structured output contracts

| **Model**            | **Required fields**                                                                                           |
|----------------------|---------------------------------------------------------------------------------------------------------------|
| OnboardingPlan       | equipment, accounts, access, training, approvals, restrictions, evidence_refs, confidence, needs_human_review |
| OffboardingPlan      | revocations, asset_returns, reassignments, handover_questions, notifications, evidence_refs                   |
| LearningCandidate    | situation, conditions, recommended_action, scope, rationale, policy_refs, sensitive_data_removed              |
| PolicyChangeAnalysis | change_type, old_rule, new_rule, effective_date, affected_areas, risk_level, explanation                      |

## 7.4 Deterministic validation

- Every resource type and action must exist in an allow-listed catalog.

- Every cited policy version must be CURRENT at plan creation and approval time.

- Every sensitive access action must request IT approval.

- The model cannot remove mandatory training or override a direct policy requirement.

- Invalid output is returned to the same graph for one repair. A second failure becomes human review.

- Do not store chain-of-thought. Store structured decisions, short explanations, inputs, outputs, and evidence references.

# 8 n8n execution and mock company system

## 8.1 n8n boundary

n8n implements predictable integration steps. It must not interpret policies, choose access levels, or approve requests. FastAPI sends only an approved action with an idempotency key. n8n calls mock endpoints and returns the result synchronously.

## 8.2 Provisioning n8n workflow

> Webhook  
> -\> Validate shared token and required fields  
> -\> Switch on resource_type  
> -\> HTTP Request to mock company endpoint  
> -\> Normalize result  
> -\> Respond to webhook

## 8.3 Offboarding n8n workflow

> Webhook  
> -\> Validate shared token  
> -\> For each approved action  
> -\> disable account or access  
> -\> mark asset return requested  
> -\> reassign task or document  
> -\> Return per-action results

## 8.4 Mock company resource model

Represent all demo resources in one company_resources table. resource_type distinguishes EMAIL_ACCOUNT, GITHUB_ACCESS, LAPTOP, TRAINING, WORK_ITEM, and KNOWLEDGE_DOCUMENT. details_json stores type-specific fields. An idempotency key prevents duplicate creation.

## 8.5 Verification rule

Never trust only the n8n response. After n8n returns, FastAPI queries company_resources by resource key and confirms that the requested state exists. Only the verified state moves the action to COMPLETED.

# 9 PostgreSQL and Qdrant data design

## 9.1 Database implementation

Use PostgreSQL with normal synchronous SQLAlchemy. Start with Base.metadata.create_all during development. Add one Alembic baseline migration only after the schema is stable in Stage 3. Use UUID primary keys, UTC timestamps, JSONB only for flexible structured objects, explicit status strings or enums, and normal foreign keys where relationships are stable.

| **Table**         | **Core fields**                                                                                                                                                           | **Purpose**                                                       |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| people            | id, name, email, app_role, employment_status, department, job_title, manager_id                                                                                           | Managers, system users, employees, and candidates                 |
| cases             | id, case_type, subject_person_id, created_by_id, status, priority, failure_reason                                                                                         | One onboarding or offboarding case                                |
| case_plans        | id, case_id, revision, status, plan_data, summary, parent_plan_id, correction_summary                                                                                     | AI plans and manager revisions                                    |
| case_actions      | id, case_id, plan_id, action_type, resource_type, requested_data, status, idempotency_key, n8n_execution_id, attempt_count, result_data, verification_data, error_message | Execution and retry state                                         |
| approvals         | id, target_type, target_id, requested_by, assigned_to, status, comment, requested_at, decided_at                                                                          | One generic HITL queue                                            |
| policy_versions   | id, policy_code, title, version_number, status, department, effective_from, content_text, content_hash, uploaded_by                                                       | Logical policy versions in one table                              |
| policy_links      | id, policy_version_id, subject_type, subject_id, use_reason, evidence_ids                                                                                                 | Dependency link from policy version to plan or lesson             |
| learning_records  | id, source_case_id, source_plan_id, trigger_type, status, candidate_data, memory_text, scope, qdrant_point_id, stale_reason                                               | Governed organizational memory                                    |
| policy_changes    | id, policy_code, old_version_id, new_version_id, diff_data, overall_risk, status                                                                                          | Exact policy version comparison                                   |
| policy_impacts    | id, policy_change_id, target_type, target_id, risk_level, explanation, recommended_action, status, resolved_by                                                            | Guardian dashboard items                                          |
| audit_events      | id, occurred_at, actor_type, actor_id, event_type, entity_type, entity_id, before_data, after_data, evidence_data, correlation_id                                         | Append-only evidence timeline                                     |
| company_resources | id, person_id, resource_type, resource_key, status, details_data, source_action_id, idempotency_key                                                                       | All mock accounts, assets, access, training, tasks, and documents |
| access_events     | id, person_id, event_time, source, destination, event_type, success, features_data, anomaly_score, alert_status, reviewed_by                                              | Authentication event and ML result                                |

## 9.2 Essential indexes and constraints

- Unique case plan revision for each case: case_id plus revision.

- Unique case-action idempotency key and unique company-resource idempotency key.

- Unique policy_code plus version_number and only one CURRENT row per policy_code.

- Indexes on cases status, approvals status, learning_records status and scope, policy_links policy_version_id, policy_impacts status, audit correlation_id, and access_events person_id plus event_time.

- Referenced policy versions are archived, never deleted.

- Audit events are append-only through application rules.

## 9.3 Qdrant collections

| **Collection**              | **Payload**                                                                                     | **Required filter**                    |
|-----------------------------|-------------------------------------------------------------------------------------------------|----------------------------------------|
| policy_knowledge            | policy_version_id, policy_code, version, status, department, section, chunk_index, content_hash | status CURRENT and relevant department |
| approved_operational_memory | learning_id, status, scope, trigger_type, policy_version_ids, sensitivity                       | status APPROVED and compatible scope   |

# 10 REST API contract

All endpoints are synchronous and return JSON. Use FastAPI dependencies for a normal SQLAlchemy session and a simple demo-role header or role selector. Final React code must consume these contracts rather than redefining backend behavior.

| **Method** | **Path**                            | **Responsibility**                                                 |
|------------|-------------------------------------|--------------------------------------------------------------------|
| GET        | /health                             | Backend, PostgreSQL, and Qdrant status                             |
| POST       | /people                             | Create employee or demo user                                       |
| GET        | /people                             | List and filter people                                             |
| POST       | /cases                              | Create onboarding or offboarding case                              |
| GET        | /cases                              | List cases by type, status, or person                              |
| GET        | /cases/{case_id}                    | Complete case, plan, actions, approvals, resources, and audit view |
| POST       | /cases/{case_id}/generate-plan      | Run the relevant LangGraph and save a pending plan                 |
| POST       | /plans/{plan_id}/approve            | Approve plan or approved manager revision                          |
| POST       | /plans/{plan_id}/reject             | Reject plan with reason                                            |
| POST       | /plans/{plan_id}/revise             | Save manager correction as a new revision                          |
| GET        | /approvals                          | List approvals assigned to the demo actor or filtered by status    |
| POST       | /cases/{case_id}/execute            | Dispatch approved actions through n8n and verify results           |
| POST       | /policies                           | Upload first policy version                                        |
| POST       | /policies/{policy_code}/versions    | Upload new version and run Guardian                                |
| GET        | /policies                           | List current and archived policy versions                          |
| GET        | /policy-changes/{change_id}         | Show change and impact list                                        |
| POST       | /policy-impacts/{impact_id}/resolve | Approve remediation and update target                              |
| POST       | /learning/from-case/{case_id}       | Create learning candidate from verified correction or handover     |
| GET        | /learning                           | List candidates by status and scope                                |
| POST       | /learning/{learning_id}/approve     | Approve and index lesson                                           |
| POST       | /learning/{learning_id}/reject      | Reject lesson                                                      |
| POST       | /access-events                      | Create event and run synchronous anomaly scoring                   |
| GET        | /security/alerts                    | List anomalous events requiring review                             |
| POST       | /access-events/{event_id}/review    | Record IT review result                                            |
| GET        | /audit                              | Filter audit events by correlation or entity                       |

## 10.1 Standard response rules

- Use 400 for invalid business input, 403 for role failure, 404 for missing records, 409 for stale or conflicting state, 422 for schema validation, and 500 only for unexpected failure.

- Return case_id and correlation_id from case-changing endpoints.

- Return current status and a concise next_action field so terminal and frontend clients know what to do.

- Never expose secrets, raw prompts, passwords, or chain-of-thought in API responses.

# 11 ML access anomaly detector

## 11.1 Final ML decision

Use scikit-learn IsolationForest, not RandomForest. The product has many normal authentication events and few known attacks, so an anomaly detector is a better match than a supervised classifier. The model only produces a risk score and cannot automatically block an employee.

## 11.2 Genuine public data

Use the Los Alamos National Laboratory Comprehensive Multi-Source Cyber-Security Events dataset. auth.txt.gz contains de-identified enterprise authentication events. redteam.txt.gz identifies known compromise events and is used as evaluation ground truth. Official source: https://csr.lanl.gov/data/cyber1/

## 11.3 Practical data pipeline

> 1\. Download auth.txt.gz and redteam.txt.gz without modifying their ground-truth meaning.
>
> 2\. Read authentication data in chunks so the 16 GB development machine is not exhausted.
>
> 3\. Aggregate events into user and time-window feature rows instead of training on raw strings.
>
> 4\. Create features such as authentication count, failure count, failure ratio, unique sources, unique destinations, destination novelty, source novelty, and off-hours activity.
>
> 5\. Exclude known red-team rows from the normal training partition. Use an earlier time period for training and a later period for evaluation to avoid random-split leakage.
>
> 6\. Scale only where needed, fit IsolationForest, choose a review threshold using a validation period, and save the pipeline with joblib.
>
> 7\. Report PR-AUC, red-team recall at the selected alert budget, precision at top K, and the number of alerts per thousand events. Do not rely only on accuracy or ROC-AUC.

## 11.4 Product integration

FastAPI loads the saved joblib pipeline during startup. POST /access-events converts the new event into the same feature schema, calls model.decision_function or score_samples, writes the score into access_events, and sets alert_status to OPEN only when the configured threshold is crossed.

# 12 Reliability security and audit rules

| **Risk**                  | **Required control**                                                                          |
|---------------------------|-----------------------------------------------------------------------------------------------|
| LLM invents policy        | Use retrieved evidence, structured output, policy ID validation, and one repair attempt.      |
| Old policy retrieved      | Filter CURRENT policy versions and run a current-version check before approval and execution. |
| Duplicate execution       | Reuse the same unique idempotency key across retries.                                         |
| n8n reports false success | FastAPI independently queries company_resources before completion.                            |
| Unsafe learning           | Sanitize, check policy and scope, require owner approval, and filter by APPROVED.             |
| Policy invalidates lesson | Guardian marks the record STALE before future retrieval.                                      |
| Sensitive access          | Require IT approval and keep an audit event.                                                  |
| ML false positive         | Human review only; no automatic revocation or disciplinary action.                            |
| Secret exposure           | Environment variables only; redact prompts, responses, and logs.                              |

## 12.1 Audit event minimum

- Case created, plan generated, plan revised, approval requested, approved, or rejected.

- Evidence retrieved and policy versions linked.

- Action dispatched, n8n result returned, verification passed or failed, and retry occurred.

- Learning candidate created, approved, rejected, indexed, or marked stale.

- Policy version activated, old version archived, impact detected, case paused, and remediation resolved.

- Access event scored and security alert reviewed.

# 13 Repository dependencies and configuration

## 13.1 Repository structure

> livingops-ai/  
> backend/  
> app/  
> main.py  
> database.py  
> models.py  
> schemas.py  
> config.py  
> routes/  
> services/  
> rag/  
> graphs/  
> ml/  
> mock_company/  
> tests/  
> scripts/  
> requirements.txt  
> n8n/  
> provisioning_workflow.json  
> offboarding_workflow.json  
> frontend/ \# created in Stage 3  
> data/  
> seed/  
> models/  
> isolation_forest.joblib  
> docker-compose.yml  
> .env.example  
> README.md

## 13.2 Backend dependencies

| **Area**           | **Packages**                                                    |
|--------------------|-----------------------------------------------------------------|
| API and validation | fastapi, uvicorn, pydantic, pydantic-settings, python-multipart |
| Database           | sqlalchemy, psycopg                                             |
| AI workflow        | langchain, langgraph, langchain-openai                          |
| Retrieval          | qdrant-client, rank-bm25, sentence-transformers, pymupdf        |
| HTTP and utilities | requests, tenacity, python-dotenv                               |
| ML                 | scikit-learn, pandas or polars, joblib                          |
| Testing            | pytest, httpx only through FastAPI TestClient if required       |

## 13.3 Environment variables

> DATABASE_URL=postgresql+psycopg://livingops:livingops_dev@localhost:5432/livingops  
> QDRANT_URL=http://localhost:6333  
> QDRANT_API_KEY=  
> OPENAI_API_KEY=  
> OPENAI_MODEL=gpt-4.1-mini  
> OPENAI_EMBEDDING_MODEL=text-embedding-3-small  
> N8N_PROVISIONING_WEBHOOK=http://localhost:5678/webhook/livingops-provision  
> N8N_OFFBOARDING_WEBHOOK=http://localhost:5678/webhook/livingops-offboard  
> N8N_SHARED_TOKEN=replace-me  
> ML_MODEL_PATH=models/isolation_forest.joblib  
> ANOMALY_THRESHOLD=  
> FRONTEND_URL=http://localhost:5173

Never commit .env. Commit only .env.example with empty values and descriptions.

# 14 Stage 1 Building the foundation

## 14.1 Stage objective

Create a stable technical skeleton that proves every external dependency and data boundary before implementing complete workflows. Stage 1 is not required to be presentation ready, but it must be testable from the terminal and safe to extend.

## 14.2 Stage 1 task sequence

| **ID** | **Work package**                | **Required result**                                                                                                               |
|--------|---------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| 1.1    | Initialize repository           | Create backend package, tests, scripts, .env.example, README checkpoints, and Git ignore rules.                                   |
| 1.2    | Start infrastructure            | Run PostgreSQL, Qdrant, and n8n through Docker Compose; confirm health from terminal.                                             |
| 1.3    | Create synchronous FastAPI core | Add config, normal SQLAlchemy engine and SessionLocal, dependency injection, exception handling, and /health.                     |
| 1.4    | Implement 13 models             | Create the lean schema with create_all, relationships, enums, indexes, and seed reset script.                                     |
| 1.5    | Seed Nexora Labs                | Create three managers, sample employees, two onboarding candidates, one departing employee, resource catalog, and mock resources. |
| 1.6    | Build policy ingestion          | Upload three policies, extract and split text, create dense vectors, store Qdrant payloads, and build BM25 index.                 |
| 1.7    | Build retrieval smoke test      | Run one dense plus BM25 plus RRF plus reranker query and print evidence with policy version IDs.                                  |
| 1.8    | Build mock company endpoints    | Create, disable, reassign, list, and verify company_resources with idempotency.                                                   |
| 1.9    | Connect n8n smoke workflow      | Send one approved mock action from FastAPI to n8n and verify the resulting resource.                                              |
| 1.10   | Establish audit helper          | Create one reusable append_audit_event function and use it for policy upload and mock action.                                     |

## 14.3 Stage 1 exit test

> \[ \] docker compose starts PostgreSQL, Qdrant, and n8n without manual repair.
>
> \[ \] FastAPI starts with no async code and /health confirms required dependencies.
>
> \[ \] The 13 tables exist and the seed command is repeatable.
>
> \[ \] A policy query returns reranked current-policy evidence.
>
> \[ \] A test n8n action creates exactly one mock resource and FastAPI verifies it.
>
> \[ \] Foundation tests pass from one documented terminal command.

# 15 Stage 2 Complete backend product

## 15.1 Stage objective

Complete 60 to 70 percent of the total project work by delivering all core product behavior through terminal commands, Swagger, and a deterministic demo script. Stage 2 does not need deployment or the final React frontend. It must still be a complete working backend product, not a collection of unfinished modules.

## 15.2 Stage 2 task sequence

| **ID** | **Work package**                | **Required result**                                                                                                    |
|--------|---------------------------------|------------------------------------------------------------------------------------------------------------------------|
| 2.1    | People and case APIs            | Complete synchronous CRUD, filters, states, role checks, and case-detail aggregation.                                  |
| 2.2    | Onboarding graph                | Implement hybrid retrieval, structured planning, validation, one repair, policy links, and plan persistence.           |
| 2.3    | Approval and revision flow      | Implement pending queue, approve, reject, revise, and current-policy recheck.                                          |
| 2.4    | Provisioning workflow           | Create actions, call n8n, verify resources, enforce idempotency, retry once, and expose failure state.                 |
| 2.5    | Offboarding graph and execution | Inventory resources, generate plan and targeted questions, approve, revoke, reassign, verify, and generate handover.   |
| 2.6    | Approved Learning Engine        | Detect correction, create and validate candidate, approve, index, retrieve in a similar case, and audit.               |
| 2.7    | Policy Change Guardian          | Upload V2, compare exact versions, find policy links, create impacts, mark stale, pause case, and resolve remediation. |
| 2.8    | Audit and reliability           | Complete audit coverage, verification, timeout handling, retry behavior, and terminal timeline output.                 |
| 2.9    | Isolation Forest pipeline       | Stream LANL data, aggregate features, train, evaluate, save model, score API event, and create human-review alert.     |
| 2.10   | Backend presentation layer      | Polish OpenAPI tags/descriptions, build demo_cli.py, seed scenarios, and provide one-command demo reset.               |
| 2.11   | Backend test suite              | Unit, integration, RAG authority, idempotency, Guardian, learning, and ML smoke tests.                                 |

## 15.3 Stage 2 complete-product demonstration

> 1\. Reset and seed Nexora Labs from one terminal command.
>
> 2\. Create Amina Rahman's confidential-project onboarding case through demo_cli.py or Swagger.
>
> 3\. Generate and approve a cited plan, execute n8n provisioning, and display verified resources.
>
> 4\. Revise one access decision, complete the case, approve the learning candidate, and show it retrieved for a similar employee.
>
> 5\. Upload Access Policy V2, show the stale lesson and paused case, approve remediation, and regenerate safely.
>
> 6\. Run the offboarding scenario and display approved handover knowledge.
>
> 7\. Submit an access event, display the anomaly score and review state, and print the correlated audit timeline.

## 15.4 Stage 2 exit criteria

> \[ \] All three workflows complete through API and terminal without editing the database manually.
>
> \[ \] All four product branches are functional and connected.
>
> \[ \] Every AI output is structured, validated, and evidence-linked.
>
> \[ \] No stale policy or stale lesson can be retrieved in authority tests.
>
> \[ \] n8n execution is idempotent and independently verified.
>
> \[ \] The LANL model has a reproducible evaluation report and product scoring endpoint.
>
> \[ \] A fresh clone can be started using documented commands and sample environment configuration.

# 16 Stage 3 Complete event ready product

## 16.1 Stage objective

Turn the proven Stage 2 backend into the final event-ready product. Stage 3 must not redesign core logic. It adds the six-page React interface, deployment, stronger end-to-end testing, evaluation evidence, usability polish, and the final judge demonstration.

## 16.2 Six-page frontend

| **Page**               | **Minimum content**                                                                 |
|------------------------|-------------------------------------------------------------------------------------|
| Dashboard              | Case counts, pending approvals, policy impacts, failed actions, and security alerts |
| Cases                  | Searchable case list and create-case modal                                          |
| Case Details           | Plan, evidence, approvals, actions, resources, handover, and audit tabs             |
| Approvals and Learning | Pending approval queue and learning-record tabs                                     |
| Policy Guardian        | Version upload, change summary, impact list, remediation controls                   |
| Security               | Access-event table, anomaly score explanation, review action                        |

Use AI to generate the frontend only after the OpenAPI contract and sample responses are frozen. Provide the AI with endpoint schemas, enums, sample success and error payloads, route list, component list, and design requirements. Review generated code for API mismatches and unnecessary dependencies before accepting it.

## 16.3 Stage 3 task sequence

| **ID** | **Work package**             | **Required result**                                                                                                  |
|--------|------------------------------|----------------------------------------------------------------------------------------------------------------------|
| 3.1    | Freeze backend contract      | Export OpenAPI JSON, freeze enums and response models, and create sample payload fixtures.                           |
| 3.2    | Generate frontend foundation | Create React and Vite app, routing, API client, role selector, layout, and reusable status components.               |
| 3.3    | Implement six pages          | Connect every page to real backend endpoints with loading, empty, success, and error states.                         |
| 3.4    | Polish judge journey         | Prioritize the connected onboarding, learning, policy-change, and remediation sequence.                              |
| 3.5    | Add deployment configuration | Create production Dockerfiles, environment settings, CORS rules, persistent volumes, and deployment instructions.    |
| 3.6    | Baseline migration           | Replace development-only create_all with one reviewed Alembic baseline migration.                                    |
| 3.7    | Run final evaluation         | Freeze RAG, Guardian, reliability, workflow, and ML results with scripts and reproducible output.                    |
| 3.8    | Run end-to-end tests         | Test full journeys through frontend, backend, n8n, PostgreSQL, Qdrant, and mock resources.                           |
| 3.9    | Prepare event package        | Seeded demo, reset script, fallback screenshots or recording, README, architecture summary, and presentation script. |

## 16.4 Stage 3 exit criteria

> \[ \] The complete product runs from the deployed URL or documented final environment.
>
> \[ \] All six pages use real backend data and preserve role restrictions.
>
> \[ \] The six-minute demo completes reliably after a one-command reset.
>
> \[ \] Evaluation results are reproducible and no business-impact number is presented as real customer evidence unless measured.
>
> \[ \] The system has a fallback demo path if the LLM, internet, or deployment provider fails during judging.

# 17 Testing and evaluation

## 17.1 Test layers

| **Layer**  | **Required coverage**                                                                                                    |
|------------|--------------------------------------------------------------------------------------------------------------------------|
| Unit       | Pydantic schemas, state transitions, validators, RRF, policy precedence, feature construction, and resource verification |
| Database   | Model creation, unique constraints, relationship behavior, status filters, and audit append                              |
| RAG        | Current-policy retrieval, archived exclusion, stale-learning exclusion, citation traceability, and reranker output       |
| LangGraph  | Valid output, one repair, unsupported-policy abstention, and deterministic failure path                                  |
| n8n        | Happy path, duplicate idempotency key, timeout, one retry, and partial failure                                           |
| End to end | Three workflows plus learning reuse and policy invalidation                                                              |
| ML         | Feature reproducibility, saved pipeline loading, threshold behavior, and real-data evaluation                            |

## 17.2 Frozen scenario tests

| **Scenario**                    | **Expected result**                                                        |
|---------------------------------|----------------------------------------------------------------------------|
| Standard onboarding             | Current-policy plan, approval, verified resources, completed case          |
| Confidential-project onboarding | Restricted repository access and required security training                |
| Manager correction              | New plan revision; candidate lesson only after successful completion       |
| Similar employee                | Approved lesson retrieved below current policy authority                   |
| Access Policy V2                | Old lesson becomes stale; affected pending plan pauses                     |
| n8n duplicate request           | One resource only                                                          |
| n8n repeated failure            | One retry followed by human review                                         |
| Offboarding                     | Access removed, work reassigned, asset return requested, handover approved |
| Unusual access event            | Anomaly score recorded; high score opens IT review without blocking        |

## 17.3 Evaluation metrics

| **Area**         | **Metrics**                                                                                                 |
|------------------|-------------------------------------------------------------------------------------------------------------|
| RAG              | Recall at K on a small manually defined policy-query set, reranker hit rate, archived/stale retrieval count |
| Plan reliability | Schema-valid rate, evidence-supported field rate, human correction rate, unsupported-action count           |
| Guardian         | Seeded affected-item recall, false impact count, stale-item exclusion rate                                  |
| Automation       | Verified completion rate, duplicate-prevention rate, retry recovery rate, median action time                |
| Learning         | Approval rate, reuse success, policy-conflict rejection, stale invalidation                                 |
| ML               | PR-AUC, red-team recall at review budget, precision at top K, alerts per thousand events                    |

Do not invent market savings or employee-replacement claims. If business impact is demonstrated through the seeded company, label it as a simulated operational comparison. Report measured technical outcomes separately from estimated market value.

# 18 Demonstration and judging strategy

## 18.1 Six-minute judge flow

| **Time**  | **Scene**                 | **Evidence**                                                                              |
|-----------|---------------------------|-------------------------------------------------------------------------------------------|
| 0:00-0:35 | Problem and dashboard     | Show scattered internal work, policy risk, and current operations overview.               |
| 0:35-1:25 | Onboarding plan           | Create Amina's case and show current-policy citations and structured plan.                |
| 1:25-2:05 | Approval and automation   | Approve, execute n8n, and show independently verified resources.                          |
| 2:05-2:45 | Approved learning         | Show manager correction becoming an approved reusable lesson.                             |
| 2:45-3:55 | Main wow moment           | Upload Policy V2; show affected lesson and case; block stale use and approve remediation. |
| 3:55-4:40 | Offboarding and knowledge | Show targeted handover and verified resource removal.                                     |
| 4:40-5:15 | ML security               | Show unusual access score and human review.                                               |
| 5:15-6:00 | Audit and value           | Show complete evidence timeline, workload reduction, and market positioning.              |

## 18.2 Judging-criteria evidence

| **Criterion**                    | **Proof to present**                                                                           |
|----------------------------------|------------------------------------------------------------------------------------------------|
| Innovation                       | Controlled organizational learning plus policy-change impact detection                         |
| Technical execution              | Hybrid RAG, reranking, structured LangGraph, verified n8n, relational state, and ML            |
| Business and global readiness    | Reusable internal operations layer for 100 to 500 employee companies                           |
| Real-world impact and ethical AI | Reduced repetitive workload, HITL, traceability, least privilege, and no autonomous punishment |
| Scalability and collaboration    | Modular architecture, fixed connectors, policy scopes, and replaceable mock integrations       |
| Presentation                     | One coherent employee-lifecycle story with visible before-and-after state                      |

# 19 Risks controls and definition of done

## 19.1 Implementation risks

| **Risk**                    | **Early warning**                       | **Control**                                                           |
|-----------------------------|-----------------------------------------|-----------------------------------------------------------------------|
| Scope growth                | New branches or integrations added      | Treat the frozen scope as a change-control boundary.                  |
| RAG instability             | Correct policy missing from top results | Build the evaluation set in Stage 1 and tune retrieval before graphs. |
| LLM schema failures         | Repeated validation errors              | Use strict Pydantic output, concise prompts, and one repair only.     |
| n8n debugging consumes time | Actions cannot be reproduced by curl    | Implement and test mock endpoints before n8n.                         |
| LANL data overload          | Memory or disk pressure                 | Stream input and aggregate before training.                           |
| Frontend starts too early   | API fields change repeatedly            | Do not generate React until Stage 2 contracts are frozen.             |
| Live demo network failure   | Model or deployment latency             | Prepare seeded results and a local fallback demo path.                |

## 19.2 Global definition of done

> \[ \] The product definition, scope, workflows, and architecture still match this plan book.
>
> \[ \] All three workflows and four branches work through the final interface.
>
> \[ \] PostgreSQL remains the source of truth and Qdrant contains only current or approved searchable knowledge.
>
> \[ \] Every high-impact AI decision includes evidence and human authorization.
>
> \[ \] Every n8n action is idempotent and independently verified.
>
> \[ \] Every policy update produces a reviewable change analysis and impact list.
>
> \[ \] Every approved lesson is sanitized, scoped, policy-linked, and removable from retrieval when stale.
>
> \[ \] The ML model is trained and evaluated with genuine LANL data and used only for decision support.
>
> \[ \] The entire demonstration can be reset and reproduced from documented commands.
>
> \[ \] The README, environment example, architecture summary, test commands, and demo instructions are complete.

## 19.3 Final decision lock

The implementation should now proceed without reopening the product concept unless a concrete technical test proves that a frozen component is infeasible. When simplification is necessary, preserve the user-visible outcome and remove internal complexity rather than adding services or features.

# 20 Exact implementation conventions and bootstrap

## 20.1 Runtime and development rules

| **Decision** | **Required implementation**                                                                                   |
|--------------|---------------------------------------------------------------------------------------------------------------|
| Python       | Python 3.11 or 3.12 in one virtual environment. Use synchronous def functions throughout application code.    |
| Backend      | One FastAPI process with route modules and service modules. Run with one Uvicorn worker during development.   |
| Database     | PostgreSQL is the source of truth. Use a normal SQLAlchemy Engine, sessionmaker, and one Session per request. |
| Vector store | One synchronous QdrantClient. Store policy chunks and approved memory in two collections.                     |
| LLM          | OpenAI chat model through one adapter. Optional local Qwen fallback must return the same Pydantic contracts.  |
| Automation   | n8n receives only approved actions. All webhook calls use requests.post with a 30 second timeout.             |
| ML           | A joblib artifact containing the feature specification, imputer, IsolationForest, and threshold metadata.     |
| Identifiers  | UUID version 4 strings at system boundaries and PostgreSQL UUID columns internally.                           |
| Time         | UTC only. API timestamps use ISO 8601 with Z. Never store local time without an offset.                       |

## 20.2 Required local software

- Git, Docker Engine with Docker Compose, Python 3.11 or 3.12, and Node.js 20 or newer for the Stage 3 frontend.

- At least 16 GB system RAM and 30 GB free disk for development. Stream the LANL dataset instead of loading it fully into memory.

- An OpenAI API key and either local Qdrant or Qdrant Cloud. The RTX 4070 is optional for the local Qwen fallback and reranker acceleration.

- curl or an equivalent HTTP client. Swagger at /docs and the included demo_cli.py remain the primary Stage 2 interfaces.

## 20.3 Repository bootstrap commands

> git init livingops-ai  
> cd livingops-ai  
> python -m venv .venv  
> source .venv/bin/activate \# Windows PowerShell: .venv\Scripts\Activate.ps1  
> python -m pip install --upgrade pip  
> mkdir -p backend/app/{routes,services,rag,graphs,ml,mock_company}  
> mkdir -p backend/{tests,scripts} n8n frontend data/{seed,lanl} models  
> touch backend/app/\_\_init\_\_.py  
> touch backend/app/routes/\_\_init\_\_.py backend/app/services/\_\_init\_\_.py  
> touch backend/app/rag/\_\_init\_\_.py backend/app/graphs/\_\_init\_\_.py  
> touch backend/app/ml/\_\_init\_\_.py backend/app/mock_company/\_\_init\_\_.py

## 20.4 Backend requirement groups

> \# backend/requirements.in  
> fastapi  
> uvicorn\[standard\]  
> pydantic  
> pydantic-settings  
> python-multipart  
> sqlalchemy  
> psycopg\[binary\]  
> alembic  
> qdrant-client  
> langchain  
> langgraph  
> langchain-openai  
> openai  
> rank-bm25  
> sentence-transformers  
> pymupdf  
> requests  
> tenacity  
> python-dotenv  
> scikit-learn  
> pandas  
> joblib  
> pytest  
> httpx

Install with python -m pip install -r backend/requirements.in. After the Stage 1 smoke tests pass, freeze the exact environment with python -m pip freeze \> backend/requirements-lock.txt. Commit both files. Later installations use requirements-lock.txt; dependency upgrades require rerunning all frozen tests.

## 20.5 Development Docker Compose contract

> \# docker-compose.yml  
> services:  
> postgres:  
> image: postgres:16-alpine  
> environment:  
> POSTGRES_DB: livingops  
> POSTGRES_USER: livingops  
> POSTGRES_PASSWORD: livingops_dev  
> ports: \["5432:5432"\]  
> volumes: \["postgres_data:/var/lib/postgresql/data"\]  
> healthcheck:  
> test: \["CMD-SHELL", "pg_isready -U livingops -d livingops"\]  
> interval: 5s  
> timeout: 3s  
> retries: 15  
> qdrant:  
> image: qdrant/qdrant:latest  
> ports: \["6333:6333", "6334:6334"\]  
> volumes: \["qdrant_data:/qdrant/storage"\]  
> n8n:  
> image: n8nio/n8n:latest  
> ports: \["5678:5678"\]  
> environment:  
> N8N_SECURE_COOKIE: "false"  
> GENERIC_TIMEZONE: UTC  
> volumes: \["n8n_data:/home/node/.n8n"\]  
> volumes:  
> postgres_data:  
> qdrant_data:  
> n8n_data:

The latest tags are acceptable only for the first local smoke test. Immediately record docker image inspect output and replace each latest tag with the tested version or image digest before Stage 2. This preserves reproducibility without guessing a future package version.

## 20.6 Exact environment file

> \# .env.example  
> APP_ENV=development  
> DATABASE_URL=postgresql+psycopg://livingops:livingops_dev@localhost:5432/livingops  
> QDRANT_URL=http://localhost:6333  
> QDRANT_API_KEY=  
> OPENAI_API_KEY=  
> OPENAI_MODEL=gpt-4.1-mini  
> OPENAI_EMBEDDING_MODEL=text-embedding-3-small  
> RERANKER_MODEL=BAAI/bge-reranker-base  
> LOCAL_LLM_ENABLED=false  
> LOCAL_LLM_BASE_URL=http://localhost:11434/v1  
> LOCAL_LLM_MODEL=qwen2.5:8b  
> N8N_PROVISIONING_WEBHOOK=http://localhost:5678/webhook/livingops-provision  
> N8N_OFFBOARDING_WEBHOOK=http://localhost:5678/webhook/livingops-offboard  
> N8N_SHARED_TOKEN=replace-me  
> ML_MODEL_PATH=models/isolation_forest.joblib  
> ANOMALY_THRESHOLD=  
> REQUEST_TIMEOUT_SECONDS=30  
> MAX_ACTION_ATTEMPTS=2  
> FRONTEND_URL=http://localhost:5173

## 20.7 First start and health commands

> cp .env.example .env  
> docker compose up -d postgres qdrant n8n  
> docker compose ps  
> cd backend  
> source ../.venv/bin/activate  
> uvicorn app.main:app --reload --port 8000  
> \# second terminal  
> curl -s http://localhost:8000/health  
> \# expected: {"status":"ok","database":"ok","qdrant":"ok","n8n":"ok","ml":"not_loaded"}

# 21 Exact PostgreSQL model contract

## 21.1 Shared column rules

- Every id is UUID primary key with application default uuid.uuid4. Foreign keys use PostgreSQL UUID.

- Every mutable table has created_at and updated_at as timezone-aware timestamps. audit_events uses occurred_at and is append-only.

- Use JSONB only for structured payloads that vary by action or graph output. Stable relationships remain normal foreign keys.

- Enum values are stored as uppercase strings so API and database states match. Validate enum transitions in services before commit.

- Use server_default now() for creation timestamps and update updated_at in application code on every mutation.

## 21.2 people

| **Column**        | **Type**     | **Null** | **Constraint and meaning**                          |
|-------------------|--------------|----------|-----------------------------------------------------|
| id                | UUID         | No       | Primary key                                         |
| name              | VARCHAR(160) | No       | Display name                                        |
| email             | VARCHAR(255) | No       | Unique lower-case email                             |
| app_role          | VARCHAR(32)  | No       | HR_MANAGER, LINE_MANAGER, IT_OWNER, EMPLOYEE, ADMIN |
| employment_status | VARCHAR(24)  | No       | CANDIDATE, ACTIVE, DEPARTING, INACTIVE              |
| department        | VARCHAR(80)  | No       | Normalized department                               |
| job_title         | VARCHAR(120) | No       | Role title                                          |
| manager_id        | UUID         | Yes      | FK people.id, on delete SET NULL                    |
| created_at        | TIMESTAMPTZ  | No       | Creation time                                       |
| updated_at        | TIMESTAMPTZ  | No       | Last mutation time                                  |

## 21.3 cases

| **Column**        | **Type**    | **Null** | **Constraint and meaning**                                             |
|-------------------|-------------|----------|------------------------------------------------------------------------|
| id                | UUID        | No       | Primary key                                                            |
| case_type         | VARCHAR(24) | No       | ONBOARDING or OFFBOARDING                                              |
| subject_person_id | UUID        | No       | FK people.id, on delete RESTRICT                                       |
| created_by_id     | UUID        | No       | FK people.id, on delete RESTRICT                                       |
| status            | VARCHAR(32) | No       | CaseState; indexed                                                     |
| priority          | VARCHAR(16) | No       | LOW, NORMAL, HIGH                                                      |
| case_facts        | JSONB       | No       | Start or end date, work mode, location, project sensitivity, successor |
| failure_reason    | TEXT        | Yes      | Latest terminal failure summary                                        |
| created_at        | TIMESTAMPTZ | No       | Creation time                                                          |
| updated_at        | TIMESTAMPTZ | No       | Last mutation time                                                     |

## 21.4 case_plans

| **Column**         | **Type**    | **Null** | **Constraint and meaning**                  |
|--------------------|-------------|----------|---------------------------------------------|
| id                 | UUID        | No       | Primary key                                 |
| case_id            | UUID        | No       | FK cases.id, on delete CASCADE              |
| revision           | INTEGER     | No       | Unique with case_id; begins at 1            |
| status             | VARCHAR(32) | No       | PlanState; indexed                          |
| plan_data          | JSONB       | No       | Validated OnboardingPlan or OffboardingPlan |
| summary            | TEXT        | No       | Human-readable short summary                |
| parent_plan_id     | UUID        | Yes      | Self FK, on delete SET NULL                 |
| correction_summary | TEXT        | Yes      | Manager reason for revision                 |
| created_at         | TIMESTAMPTZ | No       | Creation time                               |
| updated_at         | TIMESTAMPTZ | No       | Last mutation time                          |

## 21.5 case_actions

| **Column**        | **Type**     | **Null** | **Constraint and meaning**                                |
|-------------------|--------------|----------|-----------------------------------------------------------|
| id                | UUID         | No       | Primary key                                               |
| case_id           | UUID         | No       | FK cases.id, on delete CASCADE                            |
| plan_id           | UUID         | No       | FK case_plans.id, on delete RESTRICT                      |
| action_type       | VARCHAR(40)  | No       | CREATE, ASSIGN, DISABLE, REVOKE, REASSIGN, REQUEST_RETURN |
| resource_type     | VARCHAR(40)  | No       | Allow-listed ResourceType                                 |
| requested_data    | JSONB        | No       | Exact approved action input                               |
| status            | VARCHAR(32)  | No       | ActionState; indexed                                      |
| idempotency_key   | VARCHAR(120) | No       | Unique immutable key                                      |
| n8n_execution_id  | VARCHAR(120) | Yes      | Returned execution identifier                             |
| attempt_count     | INTEGER      | No       | Default 0, check 0 to 2                                   |
| result_data       | JSONB        | Yes      | n8n response                                              |
| verification_data | JSONB        | Yes      | Independent resource query                                |
| error_message     | TEXT         | Yes      | Sanitized failure                                         |
| created_at        | TIMESTAMPTZ  | No       | Creation time                                             |
| updated_at        | TIMESTAMPTZ  | No       | Last mutation time                                        |

## 21.6 approvals

| **Column**   | **Type**    | **Null** | **Constraint and meaning**                   |
|--------------|-------------|----------|----------------------------------------------|
| id           | UUID        | No       | Primary key                                  |
| target_type  | VARCHAR(32) | No       | PLAN, LEARNING, POLICY_IMPACT, HANDOVER      |
| target_id    | UUID        | No       | Application-validated polymorphic identifier |
| requested_by | UUID        | No       | FK people.id, on delete RESTRICT             |
| assigned_to  | UUID        | No       | FK people.id, on delete RESTRICT             |
| status       | VARCHAR(24) | No       | PENDING, APPROVED, REJECTED                  |
| comment      | TEXT        | Yes      | Required for rejection or revision           |
| requested_at | TIMESTAMPTZ | No       | Request time                                 |
| decided_at   | TIMESTAMPTZ | Yes      | Decision time                                |
| created_at   | TIMESTAMPTZ | No       | Creation time                                |

## 21.7 policy_versions

| **Column**     | **Type**     | **Null** | **Constraint and meaning**       |
|----------------|--------------|----------|----------------------------------|
| id             | UUID         | No       | Primary key                      |
| policy_code    | VARCHAR(50)  | No       | Stable logical code              |
| title          | VARCHAR(180) | No       | Policy title                     |
| version_number | INTEGER      | No       | Unique with policy_code          |
| status         | VARCHAR(16)  | No       | DRAFT, CURRENT, ARCHIVED         |
| department     | VARCHAR(80)  | No       | GLOBAL or department             |
| effective_from | DATE         | No       | Start date                       |
| content_text   | TEXT         | No       | Normalized authoritative text    |
| content_hash   | CHAR(64)     | No       | Unique SHA-256 per policy code   |
| uploaded_by    | UUID         | No       | FK people.id, on delete RESTRICT |
| created_at     | TIMESTAMPTZ  | No       | Upload time                      |

## 21.8 policy_links

| **Column**        | **Type**    | **Null** | **Constraint and meaning**                           |
|-------------------|-------------|----------|------------------------------------------------------|
| id                | UUID        | No       | Primary key                                          |
| policy_version_id | UUID        | No       | FK policy_versions.id, on delete RESTRICT; indexed   |
| subject_type      | VARCHAR(24) | No       | PLAN or LEARNING                                     |
| subject_id        | UUID        | No       | Application-validated target                         |
| use_reason        | VARCHAR(80) | No       | Equipment, access, training, handover, or validation |
| evidence_ids      | JSONB       | No       | List of Qdrant chunk identifiers                     |
| created_at        | TIMESTAMPTZ | No       | Creation time                                        |

## 21.9 learning_records

| **Column**      | **Type**    | **Null** | **Constraint and meaning**                     |
|-----------------|-------------|----------|------------------------------------------------|
| id              | UUID        | No       | Primary key                                    |
| source_case_id  | UUID        | No       | FK cases.id, on delete RESTRICT                |
| source_plan_id  | UUID        | No       | FK case_plans.id, on delete RESTRICT           |
| trigger_type    | VARCHAR(32) | No       | PLAN_CORRECTION or HANDOVER                    |
| status          | VARCHAR(24) | No       | PENDING_APPROVAL, APPROVED, REJECTED, STALE    |
| candidate_data  | JSONB       | No       | Full validated candidate                       |
| memory_text     | TEXT        | No       | Sanitized text sent to Qdrant                  |
| scope           | JSONB       | No       | case_types, departments, roles and sensitivity |
| qdrant_point_id | UUID        | Yes      | Present only after indexing                    |
| stale_reason    | TEXT        | Yes      | Reason retrieval was disabled                  |
| content_hash    | CHAR(64)    | No       | Normalized duplicate check                     |
| created_at      | TIMESTAMPTZ | No       | Creation time                                  |
| updated_at      | TIMESTAMPTZ | No       | Last mutation time                             |

## 21.10 policy_changes

| **Column**     | **Type**    | **Null** | **Constraint and meaning**                          |
|----------------|-------------|----------|-----------------------------------------------------|
| id             | UUID        | No       | Primary key                                         |
| policy_code    | VARCHAR(50) | No       | Compared policy                                     |
| old_version_id | UUID        | No       | FK policy_versions.id, on delete RESTRICT           |
| new_version_id | UUID        | No       | FK policy_versions.id, on delete RESTRICT           |
| diff_data      | JSONB       | No       | Deterministic line diff plus structured LLM summary |
| overall_risk   | VARCHAR(16) | No       | LOW, MEDIUM, HIGH                                   |
| status         | VARCHAR(24) | No       | ANALYZED, REVIEWED, RESOLVED                        |
| created_at     | TIMESTAMPTZ | No       | Analysis time                                       |
| updated_at     | TIMESTAMPTZ | No       | Last mutation time                                  |

## 21.11 policy_impacts

| **Column**         | **Type**    | **Null** | **Constraint and meaning**                     |
|--------------------|-------------|----------|------------------------------------------------|
| id                 | UUID        | No       | Primary key                                    |
| policy_change_id   | UUID        | No       | FK policy_changes.id, on delete CASCADE        |
| target_type        | VARCHAR(24) | No       | PLAN, CASE, LEARNING                           |
| target_id          | UUID        | No       | Application-validated target                   |
| risk_level         | VARCHAR(16) | No       | LOW, MEDIUM, HIGH                              |
| explanation        | TEXT        | No       | Evidence-based reason                          |
| recommended_action | VARCHAR(40) | No       | REGENERATE, REVIEW, MARK_STALE, NO_ACTION      |
| status             | VARCHAR(24) | No       | OPEN, ACCEPTED, REMEDIATING, RESOLVED, IGNORED |
| resolved_by        | UUID        | Yes      | FK people.id, on delete SET NULL               |
| created_at         | TIMESTAMPTZ | No       | Creation time                                  |
| updated_at         | TIMESTAMPTZ | No       | Last mutation time                             |

## 21.12 audit_events

| **Column**     | **Type**    | **Null** | **Constraint and meaning**        |
|----------------|-------------|----------|-----------------------------------|
| id             | UUID        | No       | Primary key                       |
| occurred_at    | TIMESTAMPTZ | No       | Indexed event time                |
| actor_type     | VARCHAR(24) | No       | USER, SYSTEM, LLM, N8N, ML        |
| actor_id       | UUID        | Yes      | User ID when applicable           |
| event_type     | VARCHAR(80) | No       | Stable event name                 |
| entity_type    | VARCHAR(32) | No       | Affected domain type              |
| entity_id      | UUID        | No       | Affected identifier               |
| before_data    | JSONB       | Yes      | Sanitized prior state             |
| after_data     | JSONB       | Yes      | Sanitized new state               |
| evidence_data  | JSONB       | Yes      | Policy IDs, verification or score |
| correlation_id | UUID        | No       | Indexed journey identifier        |

## 21.13 company_resources

| **Column**       | **Type**     | **Null** | **Constraint and meaning**                                                    |
|------------------|--------------|----------|-------------------------------------------------------------------------------|
| id               | UUID         | No       | Primary key                                                                   |
| person_id        | UUID         | No       | FK people.id, on delete CASCADE                                               |
| resource_type    | VARCHAR(40)  | No       | EMAIL_ACCOUNT, GITHUB_ACCESS, LAPTOP, TRAINING, WORK_ITEM, KNOWLEDGE_DOCUMENT |
| resource_key     | VARCHAR(160) | No       | Unique external-like key                                                      |
| status           | VARCHAR(32)  | No       | ResourceState                                                                 |
| details_data     | JSONB        | No       | Type-specific values                                                          |
| source_action_id | UUID         | Yes      | FK case_actions.id, on delete SET NULL                                        |
| idempotency_key  | VARCHAR(120) | No       | Unique creation or mutation key                                               |
| created_at       | TIMESTAMPTZ  | No       | Creation time                                                                 |
| updated_at       | TIMESTAMPTZ  | No       | Last mutation time                                                            |

## 21.14 access_events

| **Column**     | **Type**     | **Null** | **Constraint and meaning**                    |
|----------------|--------------|----------|-----------------------------------------------|
| id             | UUID         | No       | Primary key                                   |
| person_id      | UUID         | No       | FK people.id, on delete CASCADE               |
| event_time     | TIMESTAMPTZ  | No       | Indexed source event time                     |
| source         | VARCHAR(120) | No       | Source computer or system                     |
| destination    | VARCHAR(120) | No       | Destination computer or service               |
| event_type     | VARCHAR(40)  | No       | Authentication event type                     |
| success        | BOOLEAN      | No       | Authentication outcome                        |
| features_data  | JSONB        | No       | Exact model feature vector                    |
| anomaly_score  | FLOAT        | No       | Normalized 0 to 1 risk score                  |
| alert_status   | VARCHAR(24)  | No       | NONE, OPEN, CONFIRMED, FALSE_POSITIVE, CLOSED |
| reviewed_by    | UUID         | Yes      | FK people.id, on delete SET NULL              |
| review_comment | TEXT         | Yes      | Human conclusion                              |
| created_at     | TIMESTAMPTZ  | No       | Ingestion time                                |
| updated_at     | TIMESTAMPTZ  | No       | Last review time                              |

## 21.15 Relationships and deletion policy

| **Parent**      | **Child**         | **Cardinality and deletion**                                                       |
|-----------------|-------------------|------------------------------------------------------------------------------------|
| people          | cases             | One person has many subject and creator cases; RESTRICT deletion while referenced. |
| cases           | case_plans        | One to many; delete plans with a deleted demo case.                                |
| case_plans      | case_actions      | One to many; approved plan cannot be deleted while actions exist.                  |
| policy_versions | policy_links      | One to many; policy versions are archived, never deleted.                          |
| cases and plans | learning_records  | One to many source relationship; retain source evidence.                           |
| policy_changes  | policy_impacts    | One to many; impacts follow their comparison record.                               |
| people          | company_resources | One to many; demo reset may cascade resources.                                     |
| people          | access_events     | One to many; demo reset may cascade events.                                        |

# 22 State machines roles and transaction rules

## 22.0 Exact enum registry

> AppRole = HR_MANAGER \| LINE_MANAGER \| IT_OWNER \| EMPLOYEE \| ADMIN  
> EmploymentStatus = CANDIDATE \| ACTIVE \| DEPARTING \| INACTIVE  
> CaseType = ONBOARDING \| OFFBOARDING  
> CaseState = NEW \| PLANNING \| PENDING_APPROVAL \| APPROVED \| EXECUTING \| COMPLETED \| FAILED \| HUMAN_REVIEW \| PAUSED \| CANCELLED  
> PlanState = DRAFT \| PENDING_APPROVAL \| APPROVED \| REJECTED \| SUPERSEDED \| STALE  
> ActionState = PENDING \| DISPATCHED \| SUCCEEDED \| VERIFIED \| FAILED \| RETRYING \| HUMAN_REVIEW \| SKIPPED  
> ApprovalState = PENDING \| APPROVED \| REJECTED  
> PolicyState = DRAFT \| CURRENT \| ARCHIVED  
> LearningState = PENDING_APPROVAL \| APPROVED \| REJECTED \| STALE  
> ImpactState = OPEN \| ACCEPTED \| REMEDIATING \| RESOLVED \| IGNORED  
> ResourceState = ACTIVE \| ASSIGNED \| DISABLED \| REVOKED \| RETURN_REQUESTED \| RETURNED \| REASSIGNED  
> AlertState = NONE \| OPEN \| CONFIRMED \| FALSE_POSITIVE \| CLOSED

## 22.1 Required state transitions

| **Object**     | **Allowed transitions**                                                                                                                                                                                                                                            |
|----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Case           | NEW -\> PLANNING -\> PENDING_APPROVAL -\> APPROVED -\> EXECUTING -\> COMPLETED. Any active state may move to FAILED or HUMAN_REVIEW. PENDING_APPROVAL or APPROVED may move to PAUSED after a relevant policy change. PAUSED returns to PLANNING after remediation. |
| Plan           | DRAFT -\> PENDING_APPROVAL -\> APPROVED or REJECTED. A manager revision makes the parent SUPERSEDED and creates a new PENDING_APPROVAL revision. A policy change may move PENDING_APPROVAL or APPROVED to STALE.                                                   |
| Action         | PENDING -\> DISPATCHED -\> SUCCEEDED -\> VERIFIED. Failure moves DISPATCHED to RETRYING and then DISPATCHED. A second failure moves to HUMAN_REVIEW. SKIPPED is allowed only after approved plan revision.                                                         |
| Approval       | PENDING -\> APPROVED or REJECTED. Decisions are immutable; a changed target creates a new approval.                                                                                                                                                                |
| Policy         | DRAFT -\> CURRENT -\> ARCHIVED. Exactly one CURRENT version exists per policy_code.                                                                                                                                                                                |
| Learning       | PENDING_APPROVAL -\> APPROVED or REJECTED. APPROVED -\> STALE after conflicting policy change. STALE cannot return to APPROVED; create a replacement record.                                                                                                       |
| Policy impact  | OPEN -\> ACCEPTED -\> REMEDIATING -\> RESOLVED. OPEN may move to IGNORED only with a comment and audit event.                                                                                                                                                      |
| Security alert | NONE -\> OPEN when threshold is crossed. OPEN -\> CONFIRMED or FALSE_POSITIVE. Either review state may move to CLOSED.                                                                                                                                             |

## 22.2 Role authorization matrix

| **Operation**                         | **Allowed roles**                          |
|---------------------------------------|--------------------------------------------|
| Create onboarding or offboarding case | HR_MANAGER, ADMIN                          |
| Generate plan                         | HR_MANAGER, LINE_MANAGER, ADMIN            |
| Approve or revise normal plan         | Assigned LINE_MANAGER or ADMIN             |
| Approve sensitive access              | Assigned IT_OWNER or ADMIN                 |
| Execute approved plan                 | HR_MANAGER, IT_OWNER, ADMIN                |
| Upload policy version                 | IT_OWNER, ADMIN                            |
| Approve learning record               | IT_OWNER or designated LINE_MANAGER; ADMIN |
| Resolve policy impact                 | IT_OWNER, ADMIN                            |
| Review access anomaly                 | IT_OWNER, ADMIN                            |
| Read audit events                     | HR_MANAGER for own cases, IT_OWNER, ADMIN  |

## 22.3 Demo authentication contract

The hackathon version uses an X-Demo-User-Id request header. A dependency loads the person, rejects inactive users, and makes the actor available to route services. This is intentionally not production authentication. Stage 3 must label the selector as Demo Role and keep the dependency isolated so a real identity provider can replace it later.

> def get_current_actor(  
> x_demo_user_id: UUID = Header(...),  
> db: Session = Depends(get_db),  
> ) -\> Person:  
> actor = db.get(Person, x_demo_user_id)  
> if actor is None or actor.employment_status == 'INACTIVE':  
> raise HTTPException(status_code=403, detail='Invalid demo actor')  
> return actor

## 22.4 Transaction boundaries

> 1\. Validate authorization and current state before mutation.
>
> 2\. Begin one database transaction for the local state change and its audit event. Commit them together.
>
> 3\. Never keep a database transaction open during an OpenAI, Qdrant, or n8n network call.
>
> 4\. Before an external call, store an immutable request and DISPATCHED state. Commit. Call the external service. Open a new transaction to store its result.
>
> 5\. Verification is a separate read of company_resources. Only VERIFIED actions count toward case completion.
>
> 6\. Use the same idempotency_key for every retry. Never create a replacement key for the same approved action.

## 22.5 Standard service result and error

> \# success envelope  
> {  
> "data": {"id":"88888888-8888-4888-8888-888888888888","status":"PENDING_APPROVAL"},  
> "next_action": "approve_plan",  
> "correlation_id": "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"  
> }  
>   
> \# error envelope  
> {  
> "error": {  
> "code": "INVALID_STATE",  
> "message": "Plan must be approved before execution",  
> "details": {"current_state": "PENDING_APPROVAL"}  
> },  
> "correlation_id": "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"  
> }

# 23 File by file backend implementation

## 23.1 Application files

| **Path**            | **Required public objects**                                                     |
|---------------------|---------------------------------------------------------------------------------|
| app/config.py       | Settings and get_settings. Read environment once with lru_cache.                |
| app/database.py     | engine, SessionLocal, Base, get_db, init_db. No AsyncSession.                   |
| app/enums.py        | All enum classes named in Section 22.                                           |
| app/models.py       | The 13 SQLAlchemy models in Section 21 and relationships.                       |
| app/schemas.py      | Pydantic request, response, graph output, pagination, and error models.         |
| app/main.py         | FastAPI app, CORS, exception handlers, routers, startup model loading, /health. |
| app/dependencies.py | get_current_actor, require_roles, correlation ID dependency.                    |

## 23.2 Route files

| **Path**               | **Responsibility**                                               |
|------------------------|------------------------------------------------------------------|
| routes/people.py       | POST and GET people.                                             |
| routes/cases.py        | Case CRUD, generate, revise, approve, execute, aggregate detail. |
| routes/policies.py     | Policy upload, versions, change detail, impact remediation.      |
| routes/learning.py     | Candidate creation, listing, approval and rejection.             |
| routes/security.py     | Access-event scoring, alert listing, human review.               |
| routes/audit.py        | Correlation and entity timeline queries.                         |
| routes/mock_company.py | Development-only resource mutation and verification endpoints.   |

## 23.3 Service files

| **Path**                      | **Required functions**                                                               |
|-------------------------------|--------------------------------------------------------------------------------------|
| services/case_service.py      | create_case, get_case_detail, transition_case, all_required_actions_verified         |
| services/plan_service.py      | save_plan_revision, validate_plan_authority, approve_plan, reject_plan, revise_plan  |
| services/execution_service.py | build_actions, dispatch_action, verify_action, retry_or_escalate, execute_case       |
| services/policy_service.py    | ingest_policy, activate_version, archive_previous, link_evidence                     |
| services/learning_service.py  | build_candidate, sanitize_candidate, approve_candidate, reject_candidate, mark_stale |
| services/guardian_service.py  | compare_versions, find_dependencies, create_impacts, apply_impact_resolution         |
| services/audit_service.py     | append_audit_event and list_timeline                                                 |
| services/resource_service.py  | create_or_update_resource, verify_resource_state, inventory_person                   |

## 23.4 AI retrieval and ML files

| **Path**              | **Required functions**                                                                  |
|-----------------------|-----------------------------------------------------------------------------------------|
| rag/ingest.py         | extract_text, normalize_text, split_policy, upsert_policy_chunks, delete_version_chunks |
| rag/bm25_index.py     | rebuild_bm25, lexical_search                                                            |
| rag/retrieval.py      | dense_search, reciprocal_rank_fusion, apply_authority_rules, retrieve_context           |
| rag/reranker.py       | load_reranker, rerank                                                                   |
| graphs/contracts.py   | TypedDict states and Pydantic output contracts                                          |
| graphs/onboarding.py  | build_onboarding_graph                                                                  |
| graphs/offboarding.py | build_offboarding_graph                                                                 |
| graphs/learning.py    | build_learning_graph                                                                    |
| graphs/guardian.py    | build_guardian_graph                                                                    |
| ml/features.py        | LANL schema, aggregate_windows, transform_single_event                                  |
| ml/train.py           | train, evaluate, save_bundle                                                            |
| ml/inference.py       | load_bundle, score_event                                                                |

## 23.5 Script and test files

| **Path**                   | **Purpose**                                                     |
|----------------------------|-----------------------------------------------------------------|
| scripts/init_db.py         | Create development schema and Qdrant collections.               |
| scripts/seed_demo.py       | Reset and insert the exact Nexora Labs data in Section 30.      |
| scripts/rebuild_indexes.py | Rebuild both Qdrant collections and BM25 from PostgreSQL.       |
| scripts/train_qa.py        | Run frozen RAG questions and emit metrics JSON.                 |
| scripts/demo_cli.py        | Execute the complete Stage 2 judge path.                        |
| tests/conftest.py          | Isolated database, fake LLM responses, fake n8n, seeded actors. |
| tests/test_states.py       | State and permission tests.                                     |
| tests/test_rag.py          | Authority, RRF, citations, stale filters.                       |
| tests/test_workflows.py    | Three end-to-end workflow tests.                                |
| tests/test_guardian.py     | Version impact and remediation tests.                           |
| tests/test_ml.py           | Feature, model-load, threshold and alert tests.                 |

# 24 Exact REST API and payload contracts

## 24.1 Endpoint implementation matrix

| **Endpoint**                      | **Request to response**                           | **Success and state**                             |
|-----------------------------------|---------------------------------------------------|---------------------------------------------------|
| POST /people                      | PersonCreate -\> PersonRead                       | 201; person created                               |
| GET /people                       | Filters -\> list PersonRead                       | 200                                               |
| POST /cases                       | CaseCreate -\> CaseRead                           | 201; NEW                                          |
| GET /cases                        | Filters -\> CaseList                              | 200                                               |
| GET /cases/{id}                   | None -\> CaseDetail                               | 200; aggregate view                               |
| POST /cases/{id}/generate-plan    | PlanGenerateRequest -\> PlanRead                  | 201; PENDING_APPROVAL or HUMAN_REVIEW             |
| POST /plans/{id}/approve          | DecisionRequest -\> PlanRead                      | 200; APPROVED                                     |
| POST /plans/{id}/reject           | DecisionRequest -\> PlanRead                      | 200; REJECTED                                     |
| POST /plans/{id}/revise           | PlanRevisionRequest -\> PlanRead                  | 201; new revision PENDING_APPROVAL                |
| GET /approvals                    | status and target filters -\> list ApprovalRead   | 200; actor-scoped queue                           |
| POST /cases/{id}/execute          | ExecuteRequest -\> ExecutionSummary               | 200 or 207; EXECUTING, COMPLETED, or HUMAN_REVIEW |
| POST /policies                    | multipart file plus metadata -\> PolicyRead       | 201; first CURRENT version                        |
| POST /policies/{code}/versions    | multipart file plus metadata -\> PolicyChangeRead | 201; new CURRENT version and impacts              |
| GET /policy-changes/{id}          | None -\> PolicyChangeDetail                       | 200                                               |
| POST /policy-impacts/{id}/resolve | ImpactResolution -\> ImpactRead                   | 200                                               |
| POST /learning/from-case/{id}     | LearningCreateRequest -\> LearningRead            | 201; PENDING_APPROVAL                             |
| POST /learning/{id}/approve       | DecisionRequest -\> LearningRead                  | 200; APPROVED and indexed                         |
| POST /access-events               | AccessEventCreate -\> AccessEventRead             | 201; score and possible OPEN alert                |
| POST /access-events/{id}/review   | AlertReview -\> AccessEventRead                   | 200; reviewed                                     |

## 24.2 Create person and case examples

> POST /people  
> {  
> "name": "Amina Rahman",  
> "email": "amina.rahman@nexora.demo",  
> "app_role": "EMPLOYEE",  
> "employment_status": "CANDIDATE",  
> "department": "ENGINEERING",  
> "job_title": "AI Engineer",  
> "manager_id": "22222222-2222-4222-8222-222222222222"  
> }  
>   
> POST /cases  
> {  
> "case_type": "ONBOARDING",  
> "subject_person_id": "44444444-4444-4444-8444-444444444444",  
> "priority": "HIGH",  
> "case_facts": {  
> "start_date": "2026-10-01",  
> "work_mode": "HYBRID",  
> "location": "Dhaka",  
> "project_sensitivity": "CONFIDENTIAL"  
> }  
> }

## 24.3 Onboarding plan response contract

> {  
> "id": "88888888-8888-4888-8888-888888888888",  
> "case_id": "77777777-7777-4777-8777-777777777777",  
> "revision": 1,  
> "status": "PENDING_APPROVAL",  
> "plan_data": {  
> "equipment": \[{"catalog_key":"LAPTOP-ENG","reason":"Development work","evidence_refs":\["POL-EQUIPMENT-V1-C1"\]}\],  
> "accounts": \[{"resource_type":"EMAIL_ACCOUNT","level":"STANDARD","evidence_refs":\["POL-ACCESS-V1-C1"\]}\],  
> "access": \[{"resource_key":"github:project-aurora","level":"RESTRICTED","requires_it_approval":true,"evidence_refs":\["POL-ACCESS-V1-C3"\]}\],  
> "training": \[{"catalog_key":"SECURITY-CONFIDENTIAL","due_days":3,"evidence_refs":\["POL-ACCESS-V1-C4"\]}\],  
> "restrictions": \["No production access before security training"\],  
> "confidence": 0.88,  
> "needs_human_review": false  
> },  
> "summary": "Restricted confidential-project onboarding plan"  
> }

## 24.4 Approval revision and execution examples

> POST /plans/{plan_id}/approve  
> {"comment":"Approved for restricted repository access only"}  
>   
> POST /plans/{plan_id}/revise  
> {  
> "correction_summary": "Remove production access and require security training first",  
> "plan_data": {  
> "equipment":\[{"resource_type":"LAPTOP","catalog_key":"LAPTOP-ENG","reason":"Engineering work","evidence_refs":\["POL-EQUIPMENT-V1-C1"\]}\],  
> "accounts":\[{"resource_type":"EMAIL_ACCOUNT","catalog_key":"EMAIL-STANDARD","reason":"Company communication","evidence_refs":\["POL-ACCESS-V1-C1"\]}\],  
> "access":\[{"resource_type":"GITHUB_ACCESS","catalog_key":"GITHUB-AURORA-READ","level":"RESTRICTED","reason":"Confidential project","requires_it_approval":true,"evidence_refs":\["POL-ACCESS-V1-C3"\]}\],  
> "training":\[{"resource_type":"TRAINING","catalog_key":"SECURITY-CONFIDENTIAL","reason":"Required before confidential write access","evidence_refs":\["POL-ACCESS-V1-C4"\]}\],  
> "restrictions":\["No production access during onboarding"\],"confidence":0.91,"needs_human_review":false  
> }  
> }  
>   
> POST /cases/{case_id}/execute  
> {"dry_run":false}  
>   
> \# ExecutionSummary  
> {  
> "case_id":"77777777-7777-4777-8777-777777777777",  
> "case_status":"COMPLETED",  
> "total_actions":4,  
> "verified_actions":4,  
> "human_review_actions":0,  
> "next_action":"create_learning_candidate",  
> "correlation_id":"bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"  
> }

## 24.5 Policy upload and impact examples

> POST /policies/ACCESS/versions \# multipart/form-data  
> file=@data/seed/access_policy_v2.md  
> version_number=2  
> department=GLOBAL  
> effective_from=2026-10-15  
>   
> \# PolicyChangeDetail  
> {  
> "policy_code":"ACCESS",  
> "old_version":1,  
> "new_version":2,  
> "overall_risk":"HIGH",  
> "changes":\[{"change_type":"RESTRICTED","old_rule":"Training must be assigned before confidential write access","new_rule":"Training must be completed before confidential write access"}\],  
> "impacts":\[{"target_type":"LEARNING","target_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","recommended_action":"MARK_STALE","status":"OPEN"}\]  
> }

## 24.6 Learning and security examples

> POST /learning/from-case/{case_id}  
> {"trigger_type":"PLAN_CORRECTION"}  
>   
> POST /access-events  
> {  
> "person_id":"44444444-4444-4444-8444-444444444444",  
> "event_time":"2026-10-18T02:13:00Z",  
> "source":"C102",  
> "destination":"C900",  
> "event_type":"NETWORK",  
> "success":false  
> }  
>   
> \# response excerpt  
> {"anomaly_score":0.93,"alert_status":"OPEN","decision":"HUMAN_REVIEW_ONLY"}

## 24.7 Validation and status code rules

- 400 for semantically invalid business input, 403 for role or assignee failure, 404 for missing record, 409 for invalid state or duplicate content, and 422 for Pydantic shape failure.

- Every mutation accepts or creates a correlation_id. Return it in the response and all related audit events.

- Reject unknown JSON keys on graph output and high-impact request models by setting extra to forbid.

- Never return raw policy text, prompts, secrets, local model paths, or internal exception traces to frontend clients.

## 24.8 Pydantic model registry

| **Model**           | **Required fields**                                                                                                          |
|---------------------|------------------------------------------------------------------------------------------------------------------------------|
| PersonCreate        | name, email, app_role, employment_status, department, job_title, manager_id optional                                         |
| PersonRead          | all PersonCreate fields plus id, created_at, updated_at                                                                      |
| CaseCreate          | case_type, subject_person_id, priority default NORMAL, case_facts                                                            |
| CaseRead            | id, creator, subject, status, priority, case_facts, failure_reason, timestamps, next_action                                  |
| CaseDetail          | CaseRead plus plans, actions, approvals, resources, learning_records, policy_impacts, audit_events                           |
| PlanGenerateRequest | force_regenerate default false; reason required when true                                                                    |
| PlanRead            | id, case_id, revision, status, plan_data discriminated by case_type, summary, parent_plan_id, correction_summary, timestamps |
| DecisionRequest     | comment optional for approval and required for rejection                                                                     |
| PlanRevisionRequest | complete replacement plan_data and correction_summary                                                                        |
| ExecuteRequest      | dry_run default false                                                                                                        |
| ActionRead          | id, types, requested_data, state, immutable idempotency_key, attempts, result, verification, error                           |
| ApprovalRead        | id, target, requester, assignee, status, comment, requested_at, decided_at                                                   |
| PolicyRead          | id, code, title, version, state, department, effective_from, content_hash, uploader, timestamps                              |
| ImpactResolution    | resolution_action, comment, replacement_target_id optional                                                                   |
| LearningRead        | id, trigger, state, candidate_data, memory_text, scope, policy links, stale_reason, timestamps                               |
| AccessEventCreate   | person_id, event_time, source, destination, event_type, success                                                              |
| AlertReview         | outcome CONFIRMED or FALSE_POSITIVE, comment                                                                                 |

# 25 Hybrid RAG implementation specification

## 25.1 Qdrant collection creation

| **Collection**              | **Vector and payload contract**                                                                                                                                                                                                   |
|-----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| policy_knowledge            | Cosine dense vector, size 1536 for text-embedding-3-small. UUID point ID. Payload: source_type=POLICY, policy_version_id, policy_code, version_number, status, department, section, chunk_index, evidence_id, content_hash, text. |
| approved_operational_memory | Same vector configuration. Payload: source_type=LEARNING, learning_id, status, trigger_type, case_types, departments, roles, sensitivity, policy_version_ids, evidence_id, content_hash, text.                                    |

Create a payload index for status, department, policy_code, source_type, case_types, departments, roles, and sensitivity. If the embedding model changes, create new collections with a versioned name and rebuild from PostgreSQL; do not mix vector dimensions.

## 25.2 Deterministic evidence identifiers

> policy evidence: POL-{policy_code}-V{version_number}-C{chunk_index}  
> learning evidence: MEM-{learning_id}-C0  
> point UUID: uuid5(NAMESPACE_URL, evidence_id + ':' + content_hash)

The evidence identifier is stable for identical source content. A new policy version receives new evidence identifiers even if some sentences are unchanged. Store every final evidence ID in policy_links.evidence_ids and in the plan field it supports.

## 25.3 Policy ingestion algorithm

> 1\. Read uploaded bytes and reject files larger than 10 MB or extensions outside PDF, MD, and TXT.
>
> 2\. Extract text with PyMuPDF for PDF and UTF-8 decoding for Markdown or text. Reject encrypted, empty, or image-only files in the MVP.
>
> 3\. Normalize line endings, collapse repeated spaces, preserve headings, and compute SHA-256 over normalized text.
>
> 4\. Inside one PostgreSQL transaction, create the policy version as DRAFT and reject duplicate policy_code plus version_number or content_hash.
>
> 5\. Split by headings when possible, then RecursiveCharacterTextSplitter with chunk_size 800 and chunk_overlap 120. Drop chunks shorter than 80 characters unless they contain a heading plus rule.
>
> 6\. Embed batches of at most 64 chunks. Upsert deterministic Qdrant points with status DRAFT.
>
> 7\. Activate the new version and archive the old version in one database transaction. Update Qdrant status payloads only after the commit succeeds.
>
> 8\. If Qdrant update fails, keep PostgreSQL authoritative, record an audit failure, and run scripts/rebuild_indexes.py before further planning.
>
> 9\. Rebuild the in-memory BM25 corpus from PostgreSQL CURRENT policy text and APPROVED, non-stale learning records.

## 25.4 BM25 corpus and tokenization

> TOKEN_PATTERN = r'\[A-Za-z0-9\_./:-\]+'  
>   
> def tokenize(text: str) -\> list\[str\]:  
> return re.findall(TOKEN_PATTERN, text.lower())  
>   
> \# Keep one corpus entry per Qdrant point.  
> \# CorpusEntry fields: evidence_id, source_type, text, payload.  
> \# Rebuild at startup, policy activation, learning approval, and stale invalidation.

## 25.5 Reciprocal rank fusion and reranking

> def rrf(dense, lexical, k=60, limit=10):  
> scores = {}  
> records = {}  
> for ranking in (dense, lexical):  
> for rank, item in enumerate(ranking, start=1):  
> key = item.evidence_id  
> scores\[key\] = scores.get(key, 0.0) + 1.0 / (k + rank)  
> records\[key\] = item  
> ordered = sorted(scores, key=scores.get, reverse=True)\[:limit\]  
> return \[records\[key\] for key in ordered\]  
>   
> \# CrossEncoder input pairs: \[query, candidate.text\]  
> \# Rerank fused top 10 and retain top 4 policy chunks plus top 2 memories.

## 25.6 Exact retrieval procedure

> 1\. Build one query from case type, department, job title, sensitivity, and the planning question. Do not ask the LLM to generate extra queries.
>
> 2\. Dense-search policy_knowledge for top 10 with status CURRENT and department in GLOBAL or the case department.
>
> 3\. Dense-search approved_operational_memory for top 6 with status APPROVED and compatible scope.
>
> 4\. Run BM25 over the same eligible corpus and take top 10.
>
> 5\. Fuse dense and lexical rankings with RRF k=60, deduplicate by evidence_id, and keep 10.
>
> 6\. Rerank with BAAI/bge-reranker-base. Select at most four policy chunks and two learning records. Policy always precedes memory in the prompt.
>
> 7\. If no policy evidence supports a mandatory decision category, set needs_human_review true. Never replace missing policy with a learning record.
>
> 8\. Return RetrievalBundle with query, policy_evidence, memory_evidence, discarded_conflicts, and retrieval_trace.

## 25.7 Retrieval data contract

> class EvidenceItem(BaseModel):  
> evidence_id: str  
> source_type: Literal\['POLICY', 'LEARNING'\]  
> source_id: UUID  
> title: str  
> text: str  
> score: float  
> policy_version_ids: list\[UUID\]  
>   
> class RetrievalBundle(BaseModel):  
> query: str  
> policy_evidence: list\[EvidenceItem\]  
> memory_evidence: list\[EvidenceItem\]  
> discarded_conflicts: list\[str\]  
> retrieval_trace: dict\[str, Any\]

## 25.8 Policy precedence check

- A learning item is eligible only when every linked policy version is CURRENT or the item has been explicitly revalidated against the replacement version.

- If memory recommends broader access, weaker training, or a longer revocation period than current policy, discard it and audit MEMORY_POLICY_CONFLICT.

- Evidence support is field-level. Each equipment, account, access, training, revocation, and handover item carries at least one evidence reference.

- The final validator loads referenced policy_versions from PostgreSQL and rejects archived, missing, or wrong-department evidence even if Qdrant returned it.

## 25.9 RAG evaluation set

| **Query**                                                         | **Required evidence**                            |
|-------------------------------------------------------------------|--------------------------------------------------|
| What laptop should an AI engineer receive                         | Equipment Policy V1 engineering equipment clause |
| Can a new confidential-project employee receive production access | Access Policy restriction and training clauses   |
| Which training is required before repository access               | Access Policy training clause                    |
| When must a departing employee lose access                        | Offboarding Policy revocation clause             |
| How should unfinished work be reassigned                          | Offboarding Policy work ownership clause         |
| May an old manager exception override Access Policy V2            | V2 current policy; stale memory excluded         |

# 26 LangGraph workflows prompts and validators

## 26.1 Common graph rule

Use StateGraph for bounded workflows with predetermined nodes. Nodes return state updates; they do not commit arbitrary data. Network and database access occur through injected service functions. Compile each graph once at application startup and call graph.invoke(initial_state) synchronously.

> class BaseGraphState(TypedDict, total=False):  
> correlation_id: str  
> case_id: str  
> case_facts: dict  
> resources: list\[dict\]  
> retrieval: dict  
> draft: dict  
> validation_errors: list\[str\]  
> repair_count: int  
> final_output: dict  
> terminal_state: str

## 26.2 Onboarding graph

| **Node**         | **Input to output**                                                   |
|------------------|-----------------------------------------------------------------------|
| load_case        | case_id -\> authorized case facts and employee profile                |
| retrieve_context | facts -\> RetrievalBundle                                             |
| generate_plan    | facts plus evidence -\> OnboardingPlan draft                          |
| validate_plan    | draft -\> errors or final_output                                      |
| repair_plan      | draft plus errors and same evidence -\> corrected draft; maximum once |
| finish_review    | terminal_state NEEDS_HUMAN_REVIEW when validation still fails         |

> START -\> load_case -\> retrieve_context -\> generate_plan -\> validate_plan  
> validate_plan(valid) -\> END  
> validate_plan(invalid and repair_count == 0) -\> repair_plan -\> validate_plan  
> validate_plan(invalid and repair_count == 1) -\> finish_review -\> END

## 26.3 Onboarding output model

> class EvidenceRef(BaseModel):  
> evidence_id: str  
> reason: str  
>   
> class PlannedItem(BaseModel):  
> resource_type: ResourceType  
> catalog_key: str  
> level: str \| None = None  
> reason: str  
> evidence_refs: list\[EvidenceRef\]  
> requires_it_approval: bool = False  
>   
> class OnboardingPlan(BaseModel):  
> equipment: list\[PlannedItem\]  
> accounts: list\[PlannedItem\]  
> access: list\[PlannedItem\]  
> training: list\[PlannedItem\]  
> restrictions: list\[str\]  
> confidence: float = Field(ge=0, le=1)  
> needs_human_review: bool  
> review_reason: str \| None = None

## 26.4 Onboarding system prompt

> You are the LivingOps onboarding planner. Produce only the requested structured object.  
> POLICY EVIDENCE is authoritative. APPROVED MEMORY is advisory and must never weaken policy.  
> Choose only catalog keys supplied in AVAILABLE CATALOG. Cite evidence for every planned item.  
> Do not invent company rules, resources, or approvals. If evidence is missing or conflicting, set  
> needs_human_review=true and explain the missing decision. Confidential and production access  
> requires IT approval. Return no prose outside the schema.  
>   
> Inputs: CASE_FACTS, AVAILABLE_CATALOG, POLICY_EVIDENCE, APPROVED_MEMORY.

## 26.5 Onboarding deterministic validator

> 1\. Parse with OnboardingPlan.model_validate and reject extra fields.
>
> 2\. Confirm every catalog_key exists and its resource_type matches the catalog.
>
> 3\. Resolve every evidence_id from the supplied RetrievalBundle and PostgreSQL policy version.
>
> 4\. Require current policy evidence for each item. Learning-only support is invalid.
>
> 5\. Require IT approval for CONFIDENTIAL sensitivity, production access, admin roles, and security systems.
>
> 6\. Reject direct production access when mandatory training is not also in the plan.
>
> 7\. Limit total items to 25 and explanation length to 500 characters per item.

## 26.6 Offboarding graph and output

> START -\> load_case -\> inventory_resources -\> retrieve_context -\> generate_plan  
> -\> validate_plan -\> generate_questions -\> validate_questions -\> END  
> \# One repair is permitted at either validation boundary, not one per boundary.
>
> class OffboardingPlan(BaseModel):  
> revocations: list\[PlannedItem\]  
> asset_returns: list\[PlannedItem\]  
> reassignments: list\[PlannedItem\]  
> notifications: list\[PlannedItem\]  
> handover_topics: list\[str\]  
> targeted_questions: list\[str\]  
> evidence_refs: list\[EvidenceRef\]  
> needs_human_review: bool

The offboarding prompt receives only approved resource metadata: type, key, status, owner, due date, and title. It must not receive private message bodies, passwords, personal files, or unrelated content. Validators require an action for every ACTIVE account or access resource, a return request for each assigned laptop, and a reassignment for every open work item.

## 26.7 Learning graph

> START -\> load_completed_case -\> compare_revisions -\> retrieve_current_policy  
> -\> draft_candidate -\> sanitize -\> validate_scope -\> END or NEEDS_HUMAN_REVIEW
>
> class LearningCandidate(BaseModel):  
> situation: str  
> conditions: list\[str\]  
> recommended_action: str  
> rationale: str  
> scope: dict\[str, list\[str\] \| str\]  
> policy_refs: list\[str\]  
> source_evidence: list\[str\]  
> sensitive_data_removed: bool  
> confidence: float = Field(ge=0, le=1)

## 26.8 Learning prompt

> Convert one verified manager correction or approved handover into a reusable operational  
> lesson. Preserve the decision pattern, not names or private facts. Current policy is authoritative.  
> Do not generalize beyond the observed role, department, case type, and sensitivity. Remove names,  
> emails, IDs, dates that identify a person, secrets, and customer data. If the correction conflicts  
> with current policy, do not create a lesson; request human review. Return only the schema.

## 26.9 Policy Guardian graph

> START -\> load_exact_versions -\> deterministic_diff -\> explain_changes  
> -\> load_policy_links -\> classify_impacts -\> validate_impacts -\> persist_result -\> END
>
> class PolicyChangeItem(BaseModel):  
> change_type: Literal\['ADDED','REMOVED','RESTRICTED','RELAXED','CLARIFIED'\]  
> old_rule: str \| None  
> new_rule: str \| None  
> affected_areas: list\[str\]  
> risk_level: Literal\['LOW','MEDIUM','HIGH'\]  
> explanation: str  
>   
> class PolicyChangeAnalysis(BaseModel):  
> policy_code: str  
> old_version_id: UUID  
> new_version_id: UUID  
> changes: list\[PolicyChangeItem\]  
> overall_risk: Literal\['LOW','MEDIUM','HIGH'\]

## 26.10 Guardian prompt and validation

> Compare ONLY OLD_POLICY and NEW_POLICY supplied below. Do not retrieve or assume other  
> policy text. Explain operational meaning without legal claims. Mark access expansion, revocation  
> delay, approval removal, or training removal as HIGH risk. Quote no more than the necessary rule  
> fragment. Return only PolicyChangeAnalysis with the exact version IDs supplied.

- The code computes a line-level unified diff before the LLM call and stores it even if the LLM fails.

- The validator checks exact old and new version IDs, nonempty changes when hashes differ, and risk consistency.

- Affected targets come only from policy_links. The LLM explains impact but cannot invent target IDs.

## 26.11 LLM adapter and fallback

> def structured_call(prompt, schema):  
> try:  
> return openai_model.with_structured_output(schema).invoke(prompt)  
> except Exception as primary_error:  
> if not settings.local_llm_enabled:  
> raise  
> raw = local_openai_compatible_client.chat.completions.create(  
> model=settings.local_llm_model,  
> messages=\[{"role":"user","content":prompt}\],  
> temperature=0, response_format={"type":"json_object"}  
> )  
> return schema.model_validate_json(raw.choices\[0\].message.content)  
>   
> \# The adapter returns a validated model or raises AIOutputError.  
> \# It never changes graph state directly and never performs retries beyond one repair node.

# 27 n8n and mock company execution manual

## 27.1 Provisioning webhook request

> POST /webhook/livingops-provision  
> Authorization: Bearer \${N8N_SHARED_TOKEN}  
> {  
> "action_id":"99999999-9999-4999-8999-999999999999",  
> "case_id":"77777777-7777-4777-8777-777777777777",  
> "person_id":"44444444-4444-4444-8444-444444444444",  
> "action_type":"CREATE",  
> "resource_type":"EMAIL_ACCOUNT",  
> "resource_key":"email:amina.rahman",  
> "requested_data":{"address":"amina.rahman@nexora.demo"},  
> "idempotency_key":"case:77777777:plan:1:email:amina.rahman",  
> "callback_base_url":"http://backend:8000"  
> }

## 27.2 Provisioning workflow nodes

| **Order** | **n8n node**          | **Configuration and result**                                                                         |
|-----------|-----------------------|------------------------------------------------------------------------------------------------------|
| 1         | Webhook               | POST livingops-provision; respond through Respond to Webhook.                                        |
| 2         | IF Validate token     | Compare Authorization header to environment token. False -\> 401 response.                           |
| 3         | Code Validate payload | Require action_id, person_id, action_type, resource_type, resource_key, idempotency_key.             |
| 4         | Switch resource_type  | EMAIL_ACCOUNT, GITHUB_ACCESS, LAPTOP, TRAINING; unsupported -\> 400.                                 |
| 5         | HTTP Request          | POST callback_base_url/mock/resources/apply with the unchanged approved payload; timeout 20 seconds. |
| 6         | Set response          | Normalize execution_id, resource_id, resource_key, resource_status, already_existed.                 |
| 7         | Respond to Webhook    | 200 for applied or idempotent replay, 400 validation, 502 downstream failure.                        |

## 27.3 Offboarding workflow nodes

| **Order** | **n8n node**       | **Configuration and result**                                          |
|-----------|--------------------|-----------------------------------------------------------------------|
| 1         | Webhook            | POST livingops-offboard and validate shared token.                    |
| 2         | Split Out          | Process the supplied approved actions in order.                       |
| 3         | Switch action_type | DISABLE, REVOKE, REASSIGN, REQUEST_RETURN.                            |
| 4         | HTTP Request       | POST /mock/resources/apply once per item with idempotency key.        |
| 5         | Aggregate          | Collect per-action success or failure without hiding partial failure. |
| 6         | Respond to Webhook | Return actions array and execution_id. FastAPI performs verification. |

## 27.4 n8n response contract

> {  
> "execution_id": "n8n-demo-0001",  
> "status": "SUCCEEDED",  
> "actions": \[{  
> "action_id": "99999999-9999-4999-8999-999999999999",  
> "resource_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",  
> "resource_key": "email:amina.rahman",  
> "resource_status": "ACTIVE",  
> "already_existed": false,  
> "error": null  
> }\]  
> }

## 27.5 Mock company endpoints

| **Method and path**                    | **Behavior**                                                                                               |
|----------------------------------------|------------------------------------------------------------------------------------------------------------|
| POST /mock/resources/apply             | Insert or update by idempotency_key. Map action type to resource state. Return existing result for replay. |
| GET /mock/resources/{resource_key}     | Return authoritative mock resource for verification.                                                       |
| GET /mock/people/{person_id}/resources | Return complete resource inventory.                                                                        |
| POST /mock/failures                    | Configure a resource type to fail the next N calls for retry tests.                                        |
| DELETE /mock/reset                     | Development-only reset used by seed script; ADMIN demo role only.                                          |

## 27.6 Action to expected resource state

| **Action**       | **Expected state and verification**                        |
|------------------|------------------------------------------------------------|
| CREATE or ASSIGN | Resource exists for person and status ACTIVE or ASSIGNED.  |
| DISABLE          | Account status DISABLED.                                   |
| REVOKE           | Access status REVOKED.                                     |
| REASSIGN         | Resource person_id equals successor and status REASSIGNED. |
| REQUEST_RETURN   | Laptop status RETURN_REQUESTED with due_date.              |

## 27.7 Retry and partial failure algorithm

> 1\. Persist DISPATCHED and increment attempt_count before the HTTP call.
>
> 2\. Call n8n with a 30 second timeout. Treat timeout, connection failure, non-2xx, malformed JSON, and missing action result as failure.
>
> 3\. After success, persist SUCCEEDED, then query the mock resource endpoint. Persist VERIFIED only when expected state matches.
>
> 4\. On first failure, set RETRYING, audit, and repeat once with the same idempotency key.
>
> 5\. On second failure or failed verification, set HUMAN_REVIEW. Do not roll back already verified actions and do not mark the case completed.
>
> 6\. Return HTTP 207 with a per-action summary when the case has mixed verified and review states.

# 28 Approved learning and Policy Guardian algorithms

## 28.1 Learning candidate eligibility

> \[ \] The source case is COMPLETED and every required action is VERIFIED.
>
> \[ \] The trigger is an approved plan revision or approved handover; ordinary unedited plans do not create learning.
>
> \[ \] The correction changes an operational choice, not only wording, formatting, or a personal preference.
>
> \[ \] All cited policy versions are CURRENT when the candidate is created.
>
> \[ \] The source contains no unresolved security incident, failed action, or pending approval.

## 28.2 Revision comparison

> 1\. Load the earliest AI-generated plan and the final approved plan for the case.
>
> 2\. Canonicalize JSON by sorting object keys and sorting item lists by resource_type plus catalog_key.
>
> 3\. Calculate added, removed, and changed items. Ignore summary text, confidence, timestamps, and evidence ordering.
>
> 4\. If the semantic action set is unchanged, return 409 NO_REUSABLE_CORRECTION.
>
> 5\. Pass only the structured difference, current policies, case scope, and verified outcome to the learning graph.

## 28.3 Sanitization and scope

- Deterministically replace email addresses, UUIDs, phone-like strings, employee names, and customer identifiers with neutral labels before the LLM call.

- After the LLM returns, scan memory_text again. Reject a record that contains a known person name, email domain other than nexora.demo, secret-like token, or source resource key.

- Default scope is the exact case_type, department, job_title family, and project sensitivity. A reviewer may narrow scope but cannot broaden it without creating a new reviewed candidate.

- Compute content_hash from normalized memory_text plus canonical scope. An exact duplicate returns the existing learning ID.

- Cosine similarity above 0.92 against another approved memory creates a DUPLICATE_REVIEW warning; it does not automatically merge records.

## 28.4 Approval and indexing

> 1\. Create learning_records as PENDING_APPROVAL and create an approval assigned to IT Owner for access lessons or Line Manager for process handovers.
>
> 2\. On approval, recheck source completion, current policy status, sanitization, and duplicate warning.
>
> 3\. In one PostgreSQL transaction, mark APPROVED, create policy_links, and append LEARNING_APPROVED audit evidence.
>
> 4\. After commit, embed memory_text and upsert its Qdrant point with status APPROVED. Save qdrant_point_id in a new transaction.
>
> 5\. If indexing fails, retain the approved PostgreSQL record with null qdrant_point_id, audit INDEX_FAILED, and repair with rebuild_indexes.py. Retrieval requires both APPROVED and a present point ID.

## 28.5 Policy activation sequence

> 1\. Validate the proposed version number is exactly current version plus one and content_hash differs.
>
> 2\. Store the new version as DRAFT and index its chunks as DRAFT.
>
> 3\. Run deterministic diff and Guardian explanation against exact old and new texts.
>
> 4\. Inside one transaction, archive the old version, activate the new version, save policy_change, and create policy_impacts for every old-version policy_link.
>
> 5\. For linked learning records, immediately mark APPROVED records STALE. For linked PENDING_APPROVAL or APPROVED plans, mark STALE and pause their active cases.
>
> 6\. Commit, update Qdrant payload status, remove stale memory points, and rebuild BM25.
>
> 7\. If vector maintenance fails, block plan generation until rebuild_indexes.py makes Qdrant match PostgreSQL.

## 28.6 Impact classification rules

| **Target and condition**                                  | **Risk** | **Automatic safe action**                   | **Human remediation**                         |
|-----------------------------------------------------------|----------|---------------------------------------------|-----------------------------------------------|
| Approved memory linked to old policy                      | HIGH     | Mark STALE and remove from retrieval        | Review and create replacement lesson if valid |
| Pending or approved plan with unexecuted sensitive access | HIGH     | Mark plan STALE and pause case              | Regenerate and approve under V2               |
| Pending normal equipment or training plan                 | MEDIUM   | Pause only when changed clause affects item | Review or regenerate                          |
| Completed case                                            | LOW      | Keep historical record; no reversal         | Optional retrospective review                 |
| Open action already DISPATCHED                            | HIGH     | Do not issue new action; set HUMAN_REVIEW   | IT confirms external state and remediation    |

## 28.7 Impact resolution actions

| **Resolution** | **Required behavior**                                                                                                               |
|----------------|-------------------------------------------------------------------------------------------------------------------------------------|
| REGENERATE     | Create a new plan revision from current policy, supersede stale plan, request new approval, and unpause case only after validation. |
| MARK_STALE     | Confirm learning record remains STALE and its Qdrant point is absent.                                                               |
| REVALIDATE     | Run the learning graph against current policy and create a new candidate; never reactivate the old record.                          |
| NO_ACTION      | Allowed only for completed historical cases or a proven false impact; require comment and audit evidence.                           |

# 29 ML training evaluation and serving manual

## 29.1 Dataset and ethical use

Use the Los Alamos National Laboratory Comprehensive Multi-Source Cyber-Security Events dataset. It contains 58 consecutive days of de-identified enterprise events and a separate list of known red-team authentication events. Request auth.txt.gz and redteam.txt.gz from https://csr.lanl.gov/data/cyber1/ and keep the compressed files under data/lanl, excluded from Git.

The model is decision support only. A high score opens an IT review and must never automatically block access, punish an employee, or determine employment status. Report results as evaluation on a public research dataset, not performance on a real customer company.

## 29.2 Official file schemas

> \# auth.txt.gz, no header  
> time,src_user,dst_user,src_computer,dst_computer,auth_type,logon_type,orientation,outcome  
>   
> \# redteam.txt.gz, no header  
> time,user,src_computer,dst_computer  
>   
> \# LANL missing values are '?'; time is seconds from dataset epoch 1.

## 29.3 Feature window

Aggregate authentication events into one-hour windows per source user. Exclude computer-account users ending with \$ and well-known service identities for the first version. Map Success to 1 and Failure to 0. Join red-team labels when user, source computer, destination computer, and time match.

| **Feature**           | **Definition**                                                                                          |
|-----------------------|---------------------------------------------------------------------------------------------------------|
| event_count           | Authentication rows in the user-hour window                                                             |
| failure_count         | Rows with outcome Failure                                                                               |
| failure_ratio         | failure_count divided by max event_count, 1                                                             |
| unique_src_computers  | Distinct source computers                                                                               |
| unique_dst_computers  | Distinct destination computers                                                                          |
| unique_dst_users      | Distinct destination users                                                                              |
| unique_auth_types     | Distinct authentication types                                                                           |
| unique_logon_types    | Distinct logon types                                                                                    |
| new_destination_ratio | Destinations not observed for that user in preceding training history divided by destinations in window |
| rare_source_ratio     | Source computers seen in fewer than 0.1 percent of that user's training events                          |
| failure_burst         | Maximum failures in any five-minute bucket inside the hour                                              |

## 29.4 Streaming preparation pseudocode

> AUTH_COLS = \['time','src_user','dst_user','src_computer','dst_computer',  
> 'auth_type','logon_type','orientation','outcome'\]  
> for chunk in pd.read_csv('data/lanl/auth.txt.gz', names=AUTH_COLS,  
> chunksize=1_000_000, na_values='?'):  
> chunk = chunk\[~chunk.src_user.str.endswith('\$', na=False)\]  
> chunk\['hour'\] = chunk.time // 3600  
> \# update per-user baseline sets and grouped counters  
> \# write aggregated rows to data/lanl/features.parquet in partitions  
> \# Never concatenate all raw chunks in memory.

## 29.5 Leakage-safe split

- Training: days 1 through 21, excluding any row matched to redteam.txt.gz.

- Validation: days 22 through 35, used to select the review threshold and alert budget.

- Test: days 36 through 58, untouched until final evaluation.

- Build destination novelty using only history available before each split. Never calculate global frequencies from test data.

- If feature generation is too slow, use a documented subset of users but retain every red-team user and report the sampling rule.

## 29.6 Training configuration

> FEATURES = \[  
> 'event_count','failure_count','failure_ratio','unique_src_computers',  
> 'unique_dst_computers','unique_dst_users','unique_auth_types',  
> 'unique_logon_types','new_destination_ratio','rare_source_ratio','failure_burst'  
> \]  
> model = Pipeline(\[  
> ('imputer', SimpleImputer(strategy='median')),  
> ('detector', IsolationForest(  
> n_estimators=300, max_samples=min(10000, len(train)),  
> contamination='auto', random_state=42, n_jobs=-1  
> ))  
> \])  
> model.fit(train\[FEATURES\])

## 29.7 Score calibration and artifact

> 1\. Compute raw anomaly as negative decision_function so larger means more unusual.
>
> 2\. Save the 1st and 99th percentiles of validation raw scores. Convert product risk to clip((raw-p01)/(p99-p01), 0, 1).
>
> 3\. Choose the alert threshold as the larger of validation 99.5th percentile risk or the value that limits alerts to five per thousand validation windows.
>
> 4\. Evaluate threshold once on the test split. Report PR-AUC, red-team recall, precision at top K, and alerts per thousand windows.
>
> 5\. Save a dictionary with model, feature_names, p01, p99, threshold, training_period, dataset_name, and code_version using joblib.

## 29.8 Product inference behavior

The POST /access-events endpoint creates a one-event approximation of the same feature schema using recent access_events for the person. It loads the saved bundle once at startup, computes risk, stores features and score, and opens an alert when risk is at or above the saved threshold. If the artifact is missing or incompatible, /health reports ML degraded and the endpoint returns 503 without inventing a score.

## 29.9 Training and evaluation commands

> cd backend  
> python -m app.ml.features --auth ../data/lanl/auth.txt.gz \\  
> --redteam ../data/lanl/redteam.txt.gz --out ../data/lanl/features  
> python -m app.ml.train --features ../data/lanl/features \\  
> --model-out ../models/isolation_forest.joblib \\  
> --report-out ../models/isolation_forest_metrics.json  
> python -m pytest tests/test_ml.py -q

# 30 Exact Nexora Labs seed package

## 30.1 People

| **Name**        | **Role**           | **Department** | **Purpose**                                            |
|-----------------|--------------------|----------------|--------------------------------------------------------|
| Farhana Islam   | HR_MANAGER         | PEOPLE         | Creates lifecycle cases                                |
| Nabil Chowdhury | LINE_MANAGER       | ENGINEERING    | Approves Amina and Rafi plans                          |
| Tahmid Hasan    | IT_OWNER           | IT_SECURITY    | Approves access, policies, learning, and alerts        |
| Amina Rahman    | EMPLOYEE candidate | ENGINEERING    | Confidential-project onboarding                        |
| Rafi Ahmed      | EMPLOYEE candidate | ENGINEERING    | Similar later onboarding that reuses approved learning |
| Arif Hossain    | EMPLOYEE departing | ENGINEERING    | Offboarding and handover scenario                      |

## 30.2 Resource catalog

| **Catalog key**       | **Type**           | **Default state and rule**                          |
|-----------------------|--------------------|-----------------------------------------------------|
| LAPTOP-ENG            | LAPTOP             | ASSIGNED; standard engineering laptop               |
| EMAIL-STANDARD        | EMAIL_ACCOUNT      | ACTIVE                                              |
| GITHUB-AURORA-READ    | GITHUB_ACCESS      | ACTIVE; confidential read access; IT approval       |
| GITHUB-AURORA-WRITE   | GITHUB_ACCESS      | ACTIVE; allowed only after training and IT approval |
| SECURITY-BASE         | TRAINING           | ASSIGNED; due in seven days                         |
| SECURITY-CONFIDENTIAL | TRAINING           | ASSIGNED; due in three days                         |
| WORK-AURORA-API       | WORK_ITEM          | OPEN; owned by Arif at seed time                    |
| DOC-AURORA-RUNBOOK    | KNOWLEDGE_DOCUMENT | ACTIVE; owned by Arif at seed time                  |

## 30.3 Access Policy V1 seed text

> \# Access Policy  
> Policy code: ACCESS \| Version: 1 \| Department: GLOBAL  
> 1. Every employee receives a standard company email account.  
> 2. Repository access must match the employee's assigned project and role.  
> 3. Confidential-project access is restricted and requires IT Owner approval.  
> 4. Confidential security training must be assigned before confidential write access.  
> 5. Production access is not granted during initial onboarding unless separately approved by IT Owner.  
> 6. Access must be removed no later than the employee's final working day.

## 30.4 Equipment Policy V1 seed text

> \# Equipment Policy  
> Policy code: EQUIPMENT \| Version: 1 \| Department: GLOBAL  
> 1. Engineering employees receive one managed engineering laptop.  
> 2. Equipment must be assigned to a named employee and recorded by asset key.  
> 3. Remote and hybrid employees receive the same managed baseline.  
> 4. Departing employees must receive a return request before the final working day.

## 30.5 Offboarding Policy V1 seed text

> \# Offboarding Policy  
> Policy code: OFFBOARDING \| Version: 1 \| Department: GLOBAL  
> 1. All active accounts and access grants must be disabled or revoked by the final working day.  
> 2. Assigned equipment must be returned or have a documented return request.  
> 3. Open work items and owned operational documents must be reassigned to the named successor or manager.  
> 4. The manager must approve the handover before reusable knowledge is stored.  
> 5. Private messages, passwords, personal files, and unrelated content must not be collected.

## 30.6 Access Policy V2 change

> \# Access Policy  
> Policy code: ACCESS \| Version: 2 \| Department: GLOBAL  
> 1. Every employee receives a standard company email account.  
> 2. Repository access must match the assigned project and role.  
> 3. All confidential repository access, including read access, requires IT Owner approval.  
> 4. Confidential security training must be completed, not only assigned, before confidential write access.  
> 5. Production access is prohibited during the first 30 days of employment.  
> 6. Access must be removed by 18:00 UTC on the employee's final working day.  
> 7. Previously approved exceptions under Version 1 must be reviewed before reuse.

## 30.7 Seeded current resource state

- Arif owns an active email account, Aurora write access, LAPTOP-ARIF-01, WORK-AURORA-API, and DOC-AURORA-RUNBOOK.

- Amina and Rafi have no resources before onboarding. Amina's case facts set project_sensitivity CONFIDENTIAL. Rafi has the same department and role family but begins only after a learning record is approved.

- Configure one optional failure injection: the next LAPTOP action fails twice. Use it only for the retry demonstration and clear it during normal reset.

## 30.8 Seed command contract

> cd backend  
> python -m app.scripts.seed_demo --reset  
> \# The command must print stable names plus generated UUIDs and write  
> \# data/seed/demo_ids.json, which is ignored by Git. Re-running it must  
> \# produce one clean organization without duplicates.

# 31 Complete test and evaluation catalog

## 31.1 Test isolation rules

- Unit tests use no network. Replace the LLM, embeddings, Qdrant, and n8n clients with deterministic fakes.

- Integration tests run against dedicated PostgreSQL and Qdrant test instances or uniquely named test collections.

- Every test creates its own correlation_id and cleans up its records. Do not depend on test execution order.

- Store representative valid and invalid graph outputs under backend/tests/fixtures. Do not call paid models in the default pytest command.

- The optional live test suite is marked live and runs only with RUN_LIVE_AI_TESTS=true.

## 31.2 Required test cases

| **ID** | **Area**    | **Input or action**                    | **Required assertion**                            |
|--------|-------------|----------------------------------------|---------------------------------------------------|
| T01    | Database    | Create all 13 tables                   | Expected tables and unique constraints exist      |
| T02    | People      | Duplicate lower-case email             | 409 and one person                                |
| T03    | Case        | Employee attempts to create case       | 403; no case                                      |
| T04    | State       | Execute PENDING_APPROVAL plan          | 409 INVALID_STATE                                 |
| T05    | RAG         | Current Access V1 query                | Required clause appears in final context          |
| T06    | RAG         | Archived policy is highly similar      | Archived chunk excluded                           |
| T07    | RAG         | Stale learning is highly similar       | Stale memory excluded                             |
| T08    | RAG         | Dense and BM25 duplicate               | One fused evidence record                         |
| T09    | Plan        | Valid confidential onboarding          | IT approval flag and training present             |
| T10    | Plan        | Unknown catalog key                    | One repair; then human review if repeated         |
| T11    | Plan        | Memory weakens current policy          | Memory discarded and audit warning                |
| T12    | Approval    | Wrong manager approves                 | 403; approval remains pending                     |
| T13    | Revision    | Manager changes access                 | New revision and old plan superseded              |
| T14    | n8n         | Duplicate idempotency key              | One resource and same resource ID                 |
| T15    | n8n         | First call fails then succeeds         | Two attempts and VERIFIED                         |
| T16    | n8n         | Two failures                           | HUMAN_REVIEW and case incomplete                  |
| T17    | Verify      | n8n claims success but resource absent | Action not VERIFIED                               |
| T18    | Learning    | No semantic plan correction            | 409 NO_REUSABLE_CORRECTION                        |
| T19    | Learning    | Approved correction                    | Qdrant point and policy_links created             |
| T20    | Learning    | PII remains after sanitization         | Candidate rejected                                |
| T21    | Guardian    | Access V2 upload                       | Old V1 archived; V2 current                       |
| T22    | Guardian    | V1-linked memory                       | Marked STALE and removed from retrieval           |
| T23    | Guardian    | V1-linked pending plan                 | Plan STALE and case PAUSED                        |
| T24    | Guardian    | Regenerate resolution                  | New V2-linked plan and approval                   |
| T25    | Offboarding | Arif lifecycle                         | Access revoked, work reassigned, return requested |
| T26    | Handover    | Private field in input                 | Field absent from approved memory                 |
| T27    | ML          | Saved bundle reload                    | Same features produce same score                  |
| T28    | ML          | Score below threshold                  | alert_status NONE                                 |
| T29    | ML          | Score at threshold                     | OPEN alert; no automatic block                    |
| T30    | Audit       | Complete onboarding                    | Ordered correlated evidence timeline              |

## 31.3 Test commands

> cd backend  
> python -m pytest -q  
> python -m pytest tests/test_rag.py -q  
> python -m pytest tests/test_workflows.py tests/test_guardian.py -q  
> python -m pytest tests/test_ml.py -q  
> RUN_LIVE_AI_TESTS=true python -m pytest -m live -q  
>   
> \# coverage is recommended after the suite is stable  
> python -m pip install coverage  
> coverage run -m pytest -q  
> coverage report -m

## 31.4 Evaluation report files

| **File**                      | **Required fields**                                                                               |
|-------------------------------|---------------------------------------------------------------------------------------------------|
| reports/rag_metrics.json      | query_count, recall_at_4, reranker_hit_rate, archived_hits, stale_memory_hits                     |
| reports/workflow_metrics.json | scenario, schema_valid, evidence_supported, verified_actions, retries, duration_seconds           |
| reports/guardian_metrics.json | seeded_impacts, detected_impacts, false_impacts, stale_exclusion_rate                             |
| reports/ml_metrics.json       | split periods, sample counts, PR_AUC, recall_at_k, precision_at_k, alerts_per_thousand, threshold |

## 31.5 Release gates

> \[ \] All default tests pass without OpenAI network access.
>
> \[ \] The six frozen RAG queries return the expected current evidence and zero archived or stale items.
>
> \[ \] Every workflow scenario can be reset and repeated three times with the same state outcomes.
>
> \[ \] No action is marked complete solely from an n8n response; verification data exists.
>
> \[ \] No high-score access event changes an employee or resource state automatically.
>
> \[ \] All reported metrics are generated by committed scripts and stored with configuration metadata.

# 32 Stage 3 frontend implementation specification

## 32.1 Frontend stack and structure

> frontend/  
> src/  
> api/client.ts  
> api/types.ts  
> components/{AppShell,StatusBadge,DataTable,ApprovalPanel,AuditTimeline}.tsx  
> pages/{Dashboard,Cases,CaseDetails,ApprovalsLearning,PolicyGuardian,Security}.tsx  
> hooks/useDemoActor.ts  
> routes.tsx  
> main.tsx  
> .env.example  
> package.json  
> vite.config.ts

Use React, TypeScript, Vite, React Router, and one small styling approach such as Tailwind or CSS modules. Do not add Redux, a component framework, real-time sockets, or a second backend-for-frontend. Fetch data with the browser fetch API or one lightweight client.

## 32.2 Global interaction rules

- The header contains product name, Demo Role selector, backend health indicator, and Reset Demo action visible only to ADMIN.

- The selected actor ID is sent as X-Demo-User-Id on every API request. Correlation IDs are shown in detail and error views.

- Every page implements loading, empty, success, permission-denied, invalid-state, and network-error states.

- Buttons are disabled when the backend state does not allow their action. Backend validation remains authoritative.

- Never display raw prompts or chain-of-thought. Display short decision explanations, policy evidence, verification, and audit events.

## 32.3 Six-page data contract

| **Page**               | **Initial API calls**                              | **Primary actions**                                               |
|------------------------|----------------------------------------------------|-------------------------------------------------------------------|
| Dashboard              | GET /cases, /learning, /policies, /security/alerts | Open pending plan, impact, failure, or alert                      |
| Cases                  | GET /cases and /people                             | Create case; filter by type, status, subject                      |
| Case Details           | GET /cases/{id}                                    | Generate, revise, approve, execute; inspect evidence and timeline |
| Approvals and Learning | GET /approvals and /learning                       | Approve or reject assigned plan, learning, or handover            |
| Policy Guardian        | GET /policies and selected change detail           | Upload version; resolve impact                                    |
| Security               | GET /security/alerts                               | Submit demo event; confirm false positive or incident; close      |

## 32.4 Case Details tabs

| **Tab**   | **Visible evidence**                                                                   |
|-----------|----------------------------------------------------------------------------------------|
| Overview  | Subject, case facts, current state, next action and failure reason                     |
| Plan      | Revision selector, structured sections, current or stale state                         |
| Evidence  | Policy title, version, section, evidence ID, source authority; memory shown separately |
| Approvals | Assignee, state, comment, requested and decided timestamps                             |
| Actions   | Attempt count, n8n result, independent verification, error                             |
| Resources | Before and after resource inventory                                                    |
| Handover  | Targeted questions, draft, approval and memory status                                  |
| Audit     | Chronological event timeline filtered by correlation ID                                |

## 32.5 AI frontend generation prompt

> Build the LivingOps AI React TypeScript frontend from the supplied OpenAPI JSON and sample  
> payloads. Implement exactly six routes: Dashboard, Cases, Case Details, Approvals and Learning,  
> Policy Guardian, and Security. Use the backend as the only source of state. Send X-Demo-User-Id  
> on every request. Implement typed API functions and loading, empty, error, permission, and invalid-state  
> views. Show policy evidence separately from approved memory. Show n8n result separately from independent  
> verification. Do not add authentication, chat, WebSockets, Redux, mock data, or new product features.  
> Return code in the requested file structure and explain any OpenAPI ambiguity before assuming a field.

## 32.6 Frontend completion checklist

> \[ \] npm run build finishes with no TypeScript errors.
>
> \[ \] All six routes work after a browser refresh and use real API data.
>
> \[ \] Every mutation displays its returned next_action or a clear error.
>
> \[ \] A stale plan cannot show an enabled Execute button.
>
> \[ \] A judge can see policy version, learning approval, action verification, anomaly review, and audit evidence without opening developer tools.
>
> \[ \] Desktop layout is polished at 1366 by 768 and remains usable at 1024 pixels wide.

# 33 Deployment operations and recovery

## 33.1 Deployment architecture

Deploy the final hackathon system on one Docker-capable Linux host to minimize operational complexity. Run FastAPI, PostgreSQL, Qdrant, n8n, and a static frontend behind one HTTPS reverse proxy. Persist the three stateful volumes. Do not expose PostgreSQL or Qdrant publicly, and do not expose the n8n editor to judges.

> Internet  
> -\> HTTPS reverse proxy  
> / -\> frontend static files  
> /api/\* -\> FastAPI:8000  
> /automation/\* -\> n8n webhook endpoint only  
> -\> private Docker network  
> PostgreSQL:5432, Qdrant:6333, n8n:5678

## 33.2 Backend Dockerfile

> \# backend/Dockerfile  
> FROM python:3.12-slim  
> WORKDIR /app  
> COPY requirements-lock.txt .  
> RUN pip install --no-cache-dir -r requirements-lock.txt  
> COPY app ./app  
> CMD \["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1"\]

## 33.3 Frontend Dockerfile

> \# frontend/Dockerfile  
> FROM node:20-alpine AS build  
> WORKDIR /app  
> COPY package\*.json ./  
> RUN npm ci  
> COPY . .  
> RUN npm run build  
> FROM nginx:alpine  
> COPY --from=build /app/dist /usr/share/nginx/html  
> COPY nginx.conf /etc/nginx/conf.d/default.conf

## 33.4 Production configuration rules

- Use non-default database and n8n credentials stored outside Git. Rotate the Stage 1 shared token before deployment.

- Allow CORS only from the deployed frontend origin. Limit uploaded policy files to 10 MB and PDF, MD, or TXT.

- Make /health public but return only component states. Protect Swagger or disable it after judging if the URL becomes public.

- Mount PostgreSQL, Qdrant, n8n, and model artifacts on persistent volumes. Back up PostgreSQL before policy demonstrations.

- Set restart unless-stopped, memory limits where available, and health checks for backend, PostgreSQL, Qdrant, and frontend.

- Use HTTPS. Keep the n8n editor private; expose only required production webhook paths through the reverse proxy.

## 33.5 Deployment procedure

> 1\. Provision the Linux host, install Docker and Compose, open only ports 80 and 443, and configure DNS.
>
> 2\. Clone the repository and copy .env.production from a secure local source. Never commit it.
>
> 3\. Build immutable images with docker compose -f docker-compose.prod.yml build.
>
> 4\. Start databases first and confirm health. Run the Alembic baseline migration and Qdrant collection initializer.
>
> 5\. Import and activate the two reviewed n8n workflows. Confirm the production webhook URLs.
>
> 6\. Start backend and frontend, then run the smoke suite against the public HTTPS URL.
>
> 7\. Seed the demo only in the hackathon environment. Capture a database backup and Qdrant snapshot after the known-good seed.
>
> docker compose -f docker-compose.prod.yml up -d postgres qdrant n8n  
> docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head  
> docker compose -f docker-compose.prod.yml run --rm backend python -m app.scripts.init_qdrant  
> docker compose -f docker-compose.prod.yml up -d backend frontend proxy  
> curl -fsS https://livingops.example.com/api/health  
> python backend/scripts/smoke_public.py --base-url https://livingops.example.com/api

## 33.6 Backup reset and recovery

| **Situation**         | **Procedure**                                                                                                    |
|-----------------------|------------------------------------------------------------------------------------------------------------------|
| Normal demo reset     | Run seed_demo --reset, rebuild indexes, clear n8n failure injection, and verify /health.                         |
| LLM unavailable       | Use deterministic saved valid graph fixtures only for the fallback demonstration and clearly label the fallback. |
| Qdrant drift          | Block generation, run rebuild_indexes.py from PostgreSQL, rerun six RAG queries.                                 |
| n8n unavailable       | Show approved plan and recorded fallback execution video; never pretend actions executed.                        |
| PostgreSQL corruption | Stop writes, restore the pre-demo backup, rebuild Qdrant and BM25, then rerun smoke tests.                       |
| Frontend failure      | Use Swagger and demo_cli.py against the deployed backend; Stage 2 remains a complete backup product.             |

# 34 Solo execution schedule and handoff

## 34.1 Dependency order

> Schema and seed  
> -\> policy ingestion and retrieval  
> -\> mock resources and n8n smoke  
> -\> onboarding planning and approval  
> -\> verified provisioning  
> -\> offboarding and handover  
> -\> approved learning  
> -\> policy Guardian  
> -\> anomaly model  
> -\> complete backend tests  
> -\> freeze API  
> -\> frontend  
> -\> deployment and final demo

## 34.2 Solo work schedule

| **Period** | **Focus**                                                   | **Exit evidence**                       |
|------------|-------------------------------------------------------------|-----------------------------------------|
| Week 1     | Repository, Docker services, synchronous FastAPI, 13 models | Health, schema, resettable seed         |
| Week 2     | Policy ingestion, Qdrant, BM25, RRF, reranker               | Six-query retrieval report              |
| Week 3     | Mock company, n8n provisioning, audit helper                | Idempotent verified resource smoke      |
| Week 4     | Onboarding graph, validators, approval and revision         | Valid current-policy plan from terminal |
| Week 5     | Provisioning execution and full failure handling            | Complete onboarding plus retry demo     |
| Week 6     | Offboarding graph, execution, targeted handover             | Complete Arif scenario                  |
| Week 7     | Approved Learning and Policy Guardian                       | Correction reuse and V2 invalidation    |
| Week 8     | LANL features, Isolation Forest, product scoring            | Saved model and metrics report          |
| Week 9     | Backend test suite, demo_cli, API freeze                    | Stage 2 release tag                     |
| Week 10    | React foundation and six pages                              | All pages on real APIs                  |
| Week 11    | Deployment, end-to-end tests, fallback path                 | Public Stage 3 release candidate        |
| Week 12    | Judge flow, metrics, recording and polish                   | Repeatable six-minute final demo        |

## 34.3 Daily implementation loop

> 1\. Select one numbered work package and restate its required result.
>
> 2\. Write or update its tests first for state, authority, and failure behavior.
>
> 3\. Implement the smallest synchronous path that passes the tests.
>
> 4\. Run the affected tests and one upstream smoke test.
>
> 5\. Update README commands and the demo reset if behavior changed.
>
> 6\. Commit with the work-package ID, for example 2.4 verified provisioning.
>
> 7\. Do not begin a dependent package until its predecessor exit evidence is reproducible.

## 34.4 Stage release tags

> git tag stage-1-foundation  
> git tag stage-2-backend-product  
> git tag stage-3-event-ready  
>   
> \# Tag only after its checklist passes. Include reports, OpenAPI JSON,  
> \# requirements lock, image digests, and demo instructions in each release.

## 34.5 Final repository handoff checklist

> \[ \] README begins with one-command local start, sample actors, demo flow, test commands, and architecture summary.
>
> \[ \] .env.example contains every variable and no secret; .gitignore excludes .env, LANL files, generated IDs, caches, and model experiments.
>
> \[ \] OpenAPI JSON, requirements lock, Docker image versions, n8n exports, Alembic migration, and model metrics are committed.
>
> \[ \] The seed policies and demo data are reproducible and clearly labeled as fictional company data.
>
> \[ \] Source citations and model limitations are visible in README and presentation material.
>
> \[ \] A fresh-machine rehearsal succeeds without manually editing the database, Qdrant, or n8n execution data.

# 35 Troubleshooting and authoritative references

## 35.1 Troubleshooting matrix

| **Symptom**                       | **Likely cause**                                   | **Required fix**                                                             |
|-----------------------------------|----------------------------------------------------|------------------------------------------------------------------------------|
| /health database failed           | PostgreSQL not ready or bad URL                    | Check docker compose ps, pg_isready, and DATABASE_URL.                       |
| Qdrant dimension error            | Collection created with another embedding model    | Create versioned collection and rebuild all vectors.                         |
| Correct policy not retrieved      | Wrong status or department payload                 | Inspect PostgreSQL truth, point payload, filters, then rerun evaluation.     |
| Archived policy appears           | Index drift or missing validator                   | Block generation, rebuild Qdrant, and enforce PostgreSQL evidence check.     |
| LLM returns invalid JSON          | Prompt or provider output failure                  | Use structured output, run one repair, then HUMAN_REVIEW.                    |
| Duplicate resource                | New retry key was generated                        | Reuse the original immutable idempotency_key and add uniqueness test.        |
| n8n says success but action fails | Mock state differs                                 | Keep action unverified and inspect independent resource query.               |
| Learning not retrieved            | Not approved, stale, wrong scope, or missing point | Inspect record state and qdrant_point_id; rebuild if required.               |
| Guardian finds no impact          | policy_links were not stored                       | Reject plan persistence without current policy links and backfill demo data. |
| LANL processing exhausts RAM      | Raw chunks accumulated                             | Aggregate each chunk and write partitions; never concatenate raw data.       |
| Frontend action receives 409      | Stale client state                                 | Refresh CaseDetail, show next_action, and keep backend authoritative.        |

## 35.2 Authoritative technical references

- LANL Comprehensive Multi-Source Cyber-Security Events dataset and file schemas: https://csr.lanl.gov/data/cyber1/

- LangGraph Graph API concepts and State, Nodes, and Edges: https://docs.langchain.com/oss/python/langgraph/graph-api

- LangGraph workflows and agents patterns: https://docs.langchain.com/oss/python/langgraph/workflows-agents

- Qdrant documentation and Query API: https://qdrant.tech/documentation/ and https://qdrant.tech/documentation/search/search/

- n8n Webhook and Respond to Webhook nodes: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.respondtowebhook/

- FastAPI documentation: https://fastapi.tiangolo.com/

- SQLAlchemy ORM documentation: https://docs.sqlalchemy.org/en/20/orm/

- scikit-learn IsolationForest documentation: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html

## 35.3 Implementation sufficiency test

This manual is sufficient only when a developer can answer each of the following without redesigning the product: which table owns a state, which transition is allowed, which role authorizes it, which evidence supports an AI field, which graph node runs next, which external action is sent, how success is verified, which test proves it, and which stage gate accepts it. Sections 20 through 35 provide those answers while Sections 1 through 19 preserve the product rationale and scope.

## 35.4 Final build command sequence

> \# Foundation  
> docker compose up -d postgres qdrant n8n  
> cd backend && python -m app.scripts.init_db  
> python -m app.scripts.seed_demo --reset  
> python -m pytest -q  
>   
> \# Stage 2 product  
> uvicorn app.main:app --reload --port 8000  
> python -m app.scripts.demo_cli --scenario full  
>   
> \# Stage 3 product  
> cd ../frontend && npm ci && npm run build  
> cd .. && docker compose -f docker-compose.prod.yml build  
> \# deploy, run smoke_public.py, then rehearse the six-minute judge flow
