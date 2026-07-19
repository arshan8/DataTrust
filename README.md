# DataTrust: Secure Enterprise RAG Gateway

DataTrust is a secure, role-aware Retrieval-Augmented Generation (RAG) backend engine. Unlike standard RAG systems which are blind to user access rights, DataTrust acts as a secure intermediary layer, ensuring users can only retrieve and generate answers from internal data sources they have explicit permission to access.

---

### **1. Input Guardrails**

Before the RAG engine retrieves any documents or calls the LLM, the prompt travels through the input validation pipeline:

```mermaid
graph TD
    UserPrompt["User Prompt (Raw Text)"] --> UR["understand_request()<br><i>(request_understanding_service.py)</i>"]
    
    UR -->|Extracts| UT["normalized_text<br><i>(Standardized spacing & tokens)</i>"]
    UR -->|Extracts| UC["categories<br><i>(Intent classification e.g., PII_HIGH)</i>"]
    UR -->|Extracts| UA["action<br><i>(e.g., upload_to_external_ai)</i>"]
    UR -->|Extracts| UI["prompt_injection_hits<br><i>(e.g., ignore previous instructions)</i>"]
    
    UT --> AP["analyze_text()<br><i>(policy_service.py)</i>"]
    user_context["user_context<br><i>(department, auth_rank)</i>"] --> AP
    
    AP --> PR["policy_result<br><i>(decision, risk_score, matched_rules)</i>"]
    
    PR --> AS["apply_semantic_policy_overrides()<br><i>(chat.py Router)</i>"]
    UC --> AS
    UA --> AS
    UI --> AS
    
    AS --> UP["Updated policy_result<br><i>(Forces overrides e.g., prompt injections)</i>"]
    
    UP -->|Decision is 'blocked'| Block["Return 403 Response early (API Short-circuit)"]
    UP -->|Decision is 'allowed'| BP["build_policy_response()"]
    
    BP --> Payload["Final 'policy' JSON Payload in Response"]
```


## 🛡️ Architecture & Security Guardrails

DataTrust enforces a strict security boundary around the RAG pipeline. Below is the complete `/chat` request lifecycle, mapping the exact services, functions, and databases involved:

```mermaid
graph TD
    %% Request Ingress
    Client["Client POST /chat<br>(Prompt Text + X-User-Id header)"] --> AuthDep["get_current_user_id()<br><i>(security.py)</i>"]
    
    %% User context lookup
    AuthDep --> UserContext["get_user_context(user_id)<br><i>(authz_service.py)</i>"]
    UserContext -->|Query app_users joined with departments/auth_levels| PostgresContext[(PostgreSQL / Supabase)]
    PostgresContext -->|Return context dict:<br>user_id, department, auth_rank, is_admin| SecurityChecks{Is User Active?}
    
    SecurityChecks -->|No| BlockInactive["Raise HTTP 403 Forbidden"]
    SecurityChecks -->|Yes| InputGuard["Input Guardrail<br><i>(request_understanding_service.py & policy_service.py)</i>"]
    
    InputGuard --> Overrides["apply_semantic_policy_overrides()<br><i>(chat.py Router)</i>"]
    
    Overrides --> DecisionCheck{Is Status == blocked?}
    
    %% Block Route
    DecisionCheck -->|Yes| LogBlock["log_policy_event('CHAT_BLOCKED_BY_POLICY')<br><i>(audit_service.py)</i>"]
    LogBlock -->|Insert Audit Entry| MongoDBAudit[(MongoDB / audit_logs)]
    LogBlock --> ReturnBlock["Return HTTP 403 Forbidden<br><i>(build_policy_response payload)</i>"]
    
    %% Fast Path Small Talk Check
    DecisionCheck -->|No| SmallTalk{Is normalized prompt<br>in SMALL_TALK_INPUTS?}
    SmallTalk -->|Yes| ReturnGreeting["Return static greeting immediately<br><i>(No DB/LLM calls)</i>"]
    
    %% Query Routing
    SmallTalk -->|No| QueryRouter["decide_query_route(text)<br><i>(query_routing_service.py)</i>"]
    
    %% Route Decisions
    QueryRouter --> RouteCheck{Route Decision?}
    
    %% General Route Path
    RouteCheck -->|general_concept| GenAnswer["generate_general_answer() / stream_general_answer()<br><i>(generation_service.py)</i>"]
    
    %% RAG Route Path
    RouteCheck -->|internal_retrieval| RAGPipeline
    
    subgraph RAG Pipeline
        RAGPipeline --> SelectSources["1. select_sources(query, user_context)<br><i>(orchestrator_service.py)</i>"]
        SelectSources -->|Filter source types based on hints| AllowedScopes["2. get_allowed_resource_scopes(user_context)<br><i>(resource_scope_service.py)</i>"]
        AllowedScopes -->|Identify scopes matching department & rank| RetrieveChunks["3. retrieve_authorized_chunks()<br><i>(vector_retrieval_service.py)</i>"]
        
        %% Database retrieval
        RetrieveChunks -->|Get query vector embedding| Embedding["generate_embedding()<br><i>(embedding_service.py)</i>"]
        Embedding -->|Parameterized SELECT query with pgvector <=> operator| PostgresVector[(PostgreSQL / pgvector)]
        PostgresVector -->|Return authorized text chunks| GenerateAnswer["4. generate_answer() / stream_answer()<br><i>(generation_service.py)</i>"]
    end
    
    %% Generation Call
    GenAnswer --> LLMCall
    GenerateAnswer --> LLMCall["active_provider.generate() / stream()<br><i>(llm_client.py)</i>"]
    LLMCall -->|Call LLM Server| LLMProvider["Ollama (local) / OpenRouter (cloud)"]
    
    %% Output Guardrail
    LLMProvider --> OutputGuard["validate_generated_answer(answer)<br><i>(output_guard_service.py)</i>"]
    
    subgraph Output Guardrail Checks
        OutputGuard --> Scan["scan_output()<br><i>(Detect PII / Private keys)</i>"]
        Scan --> Redact["redact_output()<br><i>(Replace matches with REDACTED label)</i>"]
    end
    
    %% Logging & Return
    Redact --> LogEvent["log_policy_event('CHAT_ALLOWED')<br><i>(audit_service.py)</i>"]
    LogEvent -->|Insert Audit Entry| MongoDBAudit
    LogEvent --> FinalResponse["Stream/Return sanitized answer payload"]
```


* **Context Lookup**: [security.py](backend/app/core/security.py) extracts headers, and [authz_service.py](backend/app/services/authz_service.py) fetches user metadata (`department`, `auth_rank`).
* **Prompt Sanitization**: Raw prompts are normalized using regex inside [request_understanding_service.py](backend/app/services/request_understanding_service.py) to map spelling variations into clean system tokens.
* **Injection Detection**: Scans for common LLM prompt injection patterns (e.g., *"ignore previous instructions"*).
* **Policy Compliance Checks**: The [policy_service.py](backend/app/services/policy_service.py) evaluates the prompt against PII/secret regex patterns, checks for out-of-scope department keywords, matches minimum rank thresholds, and guards against sharing private assets with external AI models.

### **2. Authorized Vector Retrieval (RAG & PGVector)**
* **Platform Source Selection**: [orchestrator_service.py](backend/app/services/orchestrator_service.py) scans prompt keywords to isolate target source platforms (`GITHUB`, `CONFLUENCE`, `GDRIVE`).
* **Access Scope Enforcement**: The [resource_scope_service.py](backend/app/services/resource_scope_service.py) queries PostgreSQL for active scopes matching the user's `department` and `auth_rank`.
* **Semantic Vector Search**: [vector_retrieval_service.py](backend/app/services/vector_retrieval_service.py) runs the similarity lookup using the `sentence-transformers/all-MiniLM-L6-v2` embedding engine ([embedding_service.py](backend/app/services/embedding_service.py)) and executes a raw parameterized PostgreSQL query using the `<=>` cosine distance operator restricted to the allowed scope IDs.

### **3. Output Guardrails**
* **PII & Secret Redaction**: The generated response text is scanned for SSNs, credit cards, emails, or AWS credentials. If found, [output_guard_service.py](backend/app/services/output_guard_service.py) automatically redacts the sensitive substrings before returning the payload.

### **4. Audits & Telemetry**
* **Relational Events**: Policy blocks and sync states are stored in PostgreSQL (`connector_sync_state`).
* **Telemetry Logs**: All security events, policy block payloads, and allowed query sessions are logged to the MongoDB collection (`audit_logs`) via [audit_service.py](backend/app/services/audit_service.py).

### **5. Scope Stamping on Document Ingestion**
During document sync (e.g. from GitHub, Confluence, Google Drive, or Local file upload), files are mapped to resource scopes (containers) defining their security properties before they are chunked and indexed. If a security definition does not exist in the database, the ingestion pipeline aborts to prevent security leaks:

```mermaid
graph TD
    SourceSync["Connector Sync / Local File Upload"] --> Crawl["Crawl Resource Path / Load File Parameters"]
    Crawl --> Classify["Classify Security Context<br><i>(source_manifest.py)</i>"]
    
    Classify --> Mapped["Mapped Security Tuple<br><i>(department, rank, scope_external_id)</i>"]
    
    Mapped --> Lookup["Resolve Relational IDs in DB<br><i>(ingestion_common_service.py)</i>"]
    
    Lookup --> CheckScope{Are matching rows found in DB?}
    
    CheckScope -->|No| Abort["Raise ValueError (Abort Sync & block file ingestion)"]
    CheckScope -->|Yes| SaveDoc["Save/Update Document mapped to resource_scope_id<br><i>(document_service.py)</i>"]
    
    SaveDoc --> SplitChunks["Split Text and Generate Vector Embeddings"]
    SplitChunks --> SaveChunks["Save Chunks stamped with resource_scope_id<br><i>(document_chunks table)</i>"]
```

---

## 🗄️ Database Design

The system relies on a dual-database design:
1. **Supabase / PostgreSQL** (Relational & Vector Store):
   * `departments`: Defines corporate business units (e.g., `TECH`, `HR`, `FINANCE`).
   * `auth_levels`: Defines hierarchical security ranks (e.g., `L1` rank 1, `L2` rank 2, `L3` rank 3).
   * `app_users`: Mapped corporate user accounts.
   * `source_systems`: Defines connected external systems (e.g., `GITHUB`, `CONFLUENCE`, `GDRIVE`).
   * `resource_scopes`: Security containers (folders/repositories) defining access permissions.
   * `auth_identity_map`: Maps external JWT Auth0 subjects to internal user IDs.
   * `documents`: Extracted documents with metadata and sync statuses.
   * `document_chunks`: Text chunks with their 384-dimensional pgvector embeddings (`VECTOR(384)`).
   * `connector_sync_state`: Tracks synchronization state and metadata for external files.
   * `policy_events`: Auditable logs of policy access evaluations and blocks.
2. **MongoDB** (JSON Audit Logging & Sessions):
   * `audit_logs`: Detailed JSON log records of blocked prompts, matched rules, and compliance events.
   * `system_events`: Telemetry records of background synchronization jobs and connector activity.
   * `prompt_logs`: Logs of general conversational user queries.
   * `chat_sessions`: Persistent histories of user chat sessions and historical context.

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

# Cloud LLM Server (Optional - OpenRouter)
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=openrouter/auto

# Supabase Configurations
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY

# Direct PostgreSQL Connection URL (for pgvector lookups)
SUPABASE_DB_URL=postgresql://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres

# MongoDB Configurations
MONGODB_URI=mongodb://localhost:27017

# --- Optional Integrations ---
# GitHub Sync Credentials
GITHUB_TOKEN=your_github_token
GITHUB_OWNER=your_github_username_or_org
GITHUB_REPO=your_repo_name
GITHUB_BRANCH=main

# Confluence Sync Credentials
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_EMAIL=your_confluence_email
CONFLUENCE_API_TOKEN=your_confluence_api_token
CONFLUENCE_SPACE_KEY=your_space_key

# Google Drive Sync Credentials
GOOGLE_APPLICATION_CREDENTIALS=path_to_service_account_json
GOOGLE_DRIVE_HR_L1_FOLDER_ID=folder_id
GOOGLE_DRIVE_HR_L2_FOLDER_ID=folder_id
GOOGLE_DRIVE_HR_L3_FOLDER_ID=folder_id

# Auth0 Authentication Credentials
AUTH0_DOMAIN=your_auth0_domain
AUTH0_AUDIENCE=your_auth0_audience
AUTH0_ISSUER=your_auth0_issuer
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

