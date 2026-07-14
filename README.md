# AI-First CRM — HCP Module

Two folders, matching the required stack:

```
hcp-crm/
  frontend/   React + Redux Toolkit (Vite)
  backend/    FastAPI + LangGraph + Groq
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```
Opens on `http://localhost:5173`. It's a pixel-level replica of the provided
mock: the two-panel `Log HCP Interaction` screen, with the structured form
on the left (Redux-backed via `src/store/interactionSlice.js`) and the AI
Assistant chat panel on the right. Typing in the chat and hitting **Log**
calls the backend's `/api/interactions/chat` endpoint and hydrates the form
fields from the agent's response — chat and form are two views of the same
Redux state, not two separate features.

## Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env            # then add your GROQ_API_KEY
uvicorn app.main:app --reload --port 8000
```

Get a Groq API key at [console.groq.com](https://console.groq.com). By
default the backend uses a local SQLite file (`hcp_crm.db`) so it runs
out of the box with zero setup — swap `DATABASE_URL` in `.env` for a
Postgres/MySQL connection string when you're ready for a real database.

Key files:
- `app/langgraph_agent.py` — the agent graph and all 5 tools (`get_hcp_context`,
  `recommend_compliant_content`, `log_interaction`, `edit_interaction`,
  `schedule_followup_task`)
- `app/routers/chat.py` — `POST /api/interactions/chat`, the conversational path
- `app/routers/interactions.py` — plain REST CRUD, the structured-form path
- `app/routers/hcps.py` — `GET /api/hcps?q=` for the HCP search field
- `app/models.py` / `app/database.py` — SQLAlchemy models + session setup

API docs are auto-generated at `http://localhost:8000/docs` once the
server is running.

## Running both together

Start the backend first (port 8000), then the frontend (port 5173) — CORS
is already configured in `app/main.py` to allow the Vite dev origin.

## Design doc

The fuller architecture writeup — tool rationale, state schema, LangGraph
concepts explained from scratch — is in
`AI-First-CRM-HCP-Module-Design.md` from earlier in this conversation.
