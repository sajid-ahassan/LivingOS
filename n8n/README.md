# LivingOps n8n workflows

Three workflows, exported without credentials. n8n only executes approved
actions and forwards messages; every decision stays in the backend, and the
backend verifies GitHub results itself with its own read-only token.

| File | Trigger | Does |
| --- | --- | --- |
| `livingops-executor.json` | Webhook `POST /webhook/livingops-executor` | Checks the shared header token. `target = github`: lists deploy keys, plans the calls (idempotent), calls the GitHub REST API. `target = mock`: calls the backend `/mock/resources/apply`. Answers `{status: "SUCCEEDED", execution_id, external_ref, details}`. Any failed node makes n8n answer non-2xx, which the backend treats as a failure. |
| `livingops-notifier.json` | Webhook `POST /webhook/livingops-notifier` | Formats an approval / Guardian message and posts it to a Slack channel (incoming webhook). |
| `livingops-expiry-sweeper.json` | Every 5 minutes | Calls the backend `POST /access-grants/expire-due` (added in W5); the backend finds expired grants and revokes them through the executor. |

Written for n8n 1.x node versions; adjust after import if your instance
reports a different version.

## Import steps

1. In n8n, create three **Header Auth** credentials (names must match):
   - `LivingOps shared token`: header `Authorization`, value = `N8N_SHARED_TOKEN`
     from the backend `.env` (exact value).
   - `LivingOps GitHub write token`: header `Authorization`, value
     `Bearer <fine-grained token with Administration (deploy keys) and
     collaborators write on the demo repo>`. This write token exists only here.
   - `LivingOps service token`: header `Authorization`, value =
     `MCP_SERVICE_TOKEN` from the backend `.env`.
2. Import the three JSON files, open each node that shows a credential warning
   and select the matching credential.
3. In each **Config** node replace the `REPLACE-WITH-...` placeholder:
   backend URL (executor, sweeper) and the Slack incoming webhook URL (notifier).
4. Activate the executor and notifier. Activate the sweeper only once the
   backend is reachable from Render (deployed, or a tunnel).
5. Put the production webhook URLs in the backend `.env` as
   `N8N_PROVISIONING_WEBHOOK` and `N8N_NOTIFIER_WEBHOOK`.

Never paste tokens into these JSON files or commit an export that contains
credential data.
