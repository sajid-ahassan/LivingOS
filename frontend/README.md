# LivingOps Frontend — Stage 2 UI

Professional zero-build frontend for the LivingOps Stage 2 backend.

## Pages
- `index.html` — Dashboard
- `cases.html` — Cases
- `workspace.html?case=<UUID>` — adaptive Case Workspace
- `guardian.html` — Policy Guardian
- `security.html` — Security monitoring and human review

## Run
Start the FastAPI backend on port 8000:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then from this frontend folder:

```powershell
python serve_frontend.py
```

Open `http://127.0.0.1:5173`.

The frontend server proxies `/api/*` to `http://127.0.0.1:8000`, avoiding browser CORS issues during local development. Override the backend with the `LIVINGOPS_BACKEND` environment variable if needed.

## Security page behavior
The Security page uses the real backend endpoints:
- `POST /access-events`
- `GET /security/alerts`
- `POST /access-events/{event_id}/review`

The backend only exposes **open** alerts through the list endpoint. Completed review responses are therefore retained in browser local storage only so the UI can show recent review history without inventing backend data. The authoritative open-alert queue is always reloaded from FastAPI.

The reviewer offered by this UI is Tahmid Hasan, the deterministic demo `IT_OWNER`.
