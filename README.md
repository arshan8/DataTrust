# DataTrust

Secure enterprise assistant for guarded internal data access and policy-enforced LLM assistance.

## Project overview

- Backend: FastAPI service that implements a deterministic policy engine, retrieval orchestration, ingestion utilities, and LLM generation with streaming support.
- Frontend: React + Vite UI that provides guarded chat and admin views.
- Integrations: Supabase (metadata, auth, audit), Postgres (vector store / pgvector), MongoDB (health checks), and a local LLM endpoint (via LLM_URL).

## Key features

- Deterministic policy engine detecting PII, secrets, data-exfil and scope/auth violations (allow / redact / review / block).
- Retrieval orchestration that selects CONFLUENCE / GITHUB / GDRIVE based on query semantics and user resource scopes.
- Vector retrieval over authorized document chunks (uses sentence-transformers embeddings and Postgres + pgvector).
- Guarded prompt construction and LLM streaming with output validation before returning answers.
- Mock ingestion utilities (mock GitHub) for local testing and audit/sync logging to Supabase.

## Quick start (local)

1. Copy environment variables
   - Create `backend/.env` (or use the provided `.env` file) and set the following at minimum:
     - LLM_URL (e.g. `http://localhost:11434`)
     - OLLAMA_MODEL (model id used by your LLM service)
     - SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY
     - SUPABASE_DB_URL (Postgres connection for vector queries)
     - MONGODB_URI
     - JWT_SECRET

2. Install backend dependencies and start server
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r backend/requirements.txt
   - Start dev server with reload:
     - uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

3. Start frontend
   - cd frontend
   - npm install
   - set `frontend/src/services/api.ts` BACKEND_URL to `"http://localhost:8000"`
   - npm run dev (Vite)

4. Test endpoints
   - Health: `curl http://localhost:8000/health`
   - Login: `POST /auth/login` (Supabase-backed)
   - Chat (simple): `POST /chat` with header `X-User-Id: <user_id>`
   - Chat (stream): `POST /chat/stream` with header `X-User-Id: <user_id>`

## Notes and requirements

- Supabase: The DB schema expected by the backend includes tables such as `app_users`, `departments`, `auth_levels`, `resource_scopes`, `source_systems`, `documents`, and `document_chunks`. Ensure these exist and keys in `.env` are valid.
- Postgres + pgvector: Vector search uses the `<=>` operator — pgvector and appropriate vector column must be available.
- Embeddings: The backend uses `sentence-transformers/all-MiniLM-L6-v2` by default which will be downloaded at runtime.
- LLM: Configure `LLM_URL` and `OLLAMA_MODEL` to point at a local or network LLM inference service that implements the simple JSON /api/generate interface used in `app/services/generation_service.py`.

## Contributing

- Code is organized under `backend/app` and `frontend/src`. Run linters and tests before submitting PRs.

## License

This repository contains example/demo code. Verify licensing of third-party models and libraries before production use.
