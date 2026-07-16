# DataTrust: Secure Enterprise RAG Gateway

DataTrust is a secure, role-aware Retrieval-Augmented Generation (RAG) backend engine. Unlike standard RAG systems which are blind to user access rights, DataTrust acts as a secure intermediary layer, ensuring users can only retrieve and generate answers from internal data sources they have explicit permission to access.

---

## 🛡️ Architecture & Security Guardrails

The application enforces a **double-sided security boundary** (Input Guards & Output Guards) around the core retrieval engine:

```mermaid
graph TD
    A[Client Request /chat] --> B[Get User Auth Context]
    B --> C[Analyze & Classify Input Policy]
    C -->|Violated| D[Log & Return Blocked Response]
    C -->|Allowed| E[Determine Query Route]
    E -->|General Concept| F[Direct LLM Answer]
    E -->|Data Query| G[Source Systems Selection Orchestrator]
    G --> H[Retrieve Authorized Chunks]
    H --> I[Generate Answer using LLM Context]
    I --> J[Run Output Validation & Redaction]
    J --> K[Log Event & Stream/Return Result]
```

### **1. Input Guardrails**
* **Prompt Sanitization**: Raw prompts are normalized using regex inside [request_understanding_service.py](backend/app/services/request_understanding_service.py) to map spelling variations into clean system tokens.
* **Injection Detection**: Scans for common LLM prompt injection patterns (e.g., *"ignore previous instructions"*).
* **Policy Compliance Checks**: The [policy_service.py](backend/app/services/policy_service.py) evaluates the prompt against blacklist keywords and verifies that the user's home department matches the document domain. A Finance user, for example, is blocked from querying engineering repositories.

### **2. Authorized Vector Retrieval (PGVector)**
* **Semantic Vector Search**: Chunks are embedded using `sentence-transformers/all-MiniLM-L6-v2` into 384-dimensional dense vectors.
* **Access Scope Enforcement**: The [vector_retrieval_service.py](backend/app/services/vector_retrieval_service.py) queries PostgreSQL using the Cosine Distance operator (`<=>`). Crucially, the query contains SQL constraints mapping `resource_scopes` directly to the user's `department` and `auth_rank`, completely isolating data access in the database.

### **3. Output Guardrails**
* **PII & Secret Redaction**: The generated response text is scanned for SSNs, credit cards, emails, or AWS credentials. If found, [output_guard_service.py](backend/app/services/output_guard_service.py) automatically redacts the sensitive substrings before returning the payload.

### **4. Audits & Telemetry**
* **Relational Events**: Policy blocks and errors are stored in PostgreSQL (`policy_events`).
* **Telemetry Logs**: Complete prompt payloads, matched rules, categories, risk scores, and process timings are logged into MongoDB collections (`audit_logs`, `prompt_logs`, `system_events`).

---

## 🗄️ Database Design

The system relies on a dual-database design:
1. **Supabase / PostgreSQL** (Relational & Vector Store):
   * `departments`: Defines business units (e.g., `TECH`, `HR`, `FINANCE`).
   * `auth_levels`: Defines hierarchical ranks (e.g., `L1` rank 1, `L2` rank 2, `L3` rank 3).
   * `app_users`: Mapped corporate users.
   * `auth_identity_map`: Maps external JWT Auth0 subjects to internal user IDs.
   * `resource_scopes`: Security containers (folders/repositories) defining access requirements.
   * `documents` & `document_chunks`: Extracted text items with their `VECTOR(384)` embeddings.
2. **MongoDB** (JSON Audit Logging):
   * Schema-less repository for logging full prompt payload histories.

---

## 🚀 Quick Start (Local Setup)

### **1. Environment Variables**
Create a new file named `.env` in the `backend/` directory and configure the following parameters:

```ini
ENV=development
JWT_SECRET=your_development_jwt_secret_key_123

# Local LLM Server (Ollama endpoint)
LLM_URL=http://localhost:11434
OLLAMA_MODEL=phi3:latest

# Supabase Configurations
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY

# Direct PostgreSQL Connection URL (for pgvector lookups)
SUPABASE_DB_URL=postgresql://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres

# MongoDB Configurations
MONGODB_URI=mongodb://localhost:27017
```

### **2. Install Dependencies & Start Server**
Navigate to the root directory in your PowerShell terminal and run:

```powershell
# Create and activate Python virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install requirements
pip install -r backend/requirements.txt

# Start Uvicorn development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On a successful build, the terminal will confirm the server is listening:
```text
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
Embedding model warmed up
LLM warm-up completed
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 🧪 Testing the APIs
1. Open your browser and navigate to the Swagger docs: `http://localhost:8000/docs`.
2. Select `POST /chat` or `POST /debug/retrieve`.
3. Set the development authorization header: `X-User-Id: dev_user_123` (this bypasses external Auth0 requirement for fast local debugging).
4. Run requests to test policies:
   * Ask: *"Show HR Salaries"* (Blocked if user is not in HR).
   * Ask: *"Summarize mock backend code"* (Allowed if user is L2/L3 in TECH).

