# LivingOps MCP Access Gateway

A thin MCP server (Python MCP SDK 2.x, Streamable HTTP) that lets any
standard MCP agent ask LivingOps for time-limited access. It holds no state
and makes no decisions: each tool forwards the agent's `X-Agent-Key` header to
the backend, which authenticates the agent by key hash, applies the
deterministic risk tier, runs approval, execution and verification, and
audits everything.

| Tool | Backend |
| --- | --- |
| `whoami` | `GET /agent-identity` |
| `request_access(resource, permission, duration_minutes, reason, system="github")` | `POST /access-requests` |
| `check_request(request_id)` | `GET /access-requests/{id}` |
| `list_my_access` | `GET /access-grants/mine` |
| `release_access(grant_key)` | `POST /access-grants/{grant_key}/release` |

## Run

From the project root, with the backend running on port 8000:

```powershell
pip install -r mcp_server/requirements.txt
python -m mcp_server
```

Settings: `LIVINGOPS_BACKEND_URL` (default `http://127.0.0.1:8000`),
`MCP_HOST` (`127.0.0.1`), `MCP_PORT` (`8765`). The endpoint is
`http://127.0.0.1:8765/mcp`.

## Demo scene 5

1. Put a random `AURORA_BOT_MCP_KEY` in `.env` and re-seed
   (`python -m app.scripts.reset_demo --yes` in `backend/`): only its hash is
   stored on Aurora Release Bot.
2. `python -m mcp_server.demo_client --low` plays the bot: `whoami`, a LOW
   read request on `helios` (approved by the rules at once), then a HIGH
   request for two hours of write on `aurora`, which waits.
3. Tahmid approves it on the Approvals page; the client sees `ACTIVE` with
   the expiry time. `--release` gives the access back at the end.

Any other MCP client (e.g. Claude Desktop) can connect to the same URL with
an `X-Agent-Key` header.
