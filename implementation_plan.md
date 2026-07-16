# Implementation Plan - Decoupling LLM Integration

This plan details how to refactor the LLM communication layer in the DataTrust backend to be completely provider-agnostic. Instead of hardcoding Ollama-specific endpoints, we will introduce an abstraction layer supporting both **Ollama** and **OpenRouter** (or any OpenAI-compatible endpoint) dynamically based on the environment configuration.

---

## Proposed Changes

We will group our refactoring into three components:
1. **Config Layer**: Adding OpenRouter properties to settings.
2. **LLM Abstraction Layer**: Creating provider interfaces and concrete implementations.
3. **Service & Router Layer**: Updating `generation_service.py` and `chat.py` to use the vendor-agnostic client and names.

---

### 1. Configuration Layer

#### [MODIFY] [config.py](file:///c:/Users/ARSHAN/Desktop/RagTrust/DataTrust_Project/backend/app/core/config.py)
* Add `OPENROUTER_API_KEY` (string, default `""`).
* Add `OPENROUTER_MODEL` (string, default `"meta-llama/llama-3-8b-instruct:free"`).
* Modify default `OLLAMA_MODEL` to fallback dynamically if needed.

---

### 2. LLM Abstraction Layer

#### [NEW] [llm_client.py](file:///c:/Users/ARSHAN/Desktop/RagTrust/DataTrust_Project/backend/app/services/llm_client.py)
Create a new abstraction module defining an `LLMProvider` interface and concrete implementations:
* **`LLMProvider` (ABC)**: Defines `generate(prompt, model_name, **kwargs) -> str` and `stream(prompt, model_name, **kwargs) -> Iterator[str]`.
* **`OllamaProvider`**: Implements the local Ollama `/api/generate` endpoint payload/response.
* **`OpenRouterProvider`**: Implements the standard OpenAI `/v1/chat/completions` API structure using OpenRouter's URL and bearer authorization headers.
* **`get_llm_provider()`**: Factory function returning an instance of the provider based on the presence of `OPENROUTER_API_KEY`.

---

### 3. Service and Router Refactoring

#### [MODIFY] [generation_service.py](file:///c:/Users/ARSHAN/Desktop/RagTrust/DataTrust_Project/backend/app/services/generation_service.py)
* Replace all direct `requests.post(f"{settings.LLM_URL}/api/generate", ...)` calls with calls to the provider retrieved from `get_llm_provider()`.
* Rename service functions to be vendor-agnostic:
  * `generate_answer_with_ollama` ➡️ `generate_answer`
  * `stream_answer_with_ollama` ➡️ `stream_answer`
  * `generate_general_answer_with_ollama` ➡️ `generate_general_answer`
  * `stream_general_answer_with_ollama` ➡️ `stream_general_answer`
* Automatically map model names based on the selected provider (e.g. if using OpenRouter, fall back from local model tags like `phi3:latest` to the specified `OPENROUTER_MODEL`).

#### [MODIFY] [chat.py](file:///c:/Users/ARSHAN/Desktop/RagTrust/DataTrust_Project/backend/app/routers/chat.py)
* Update imports from `app.services.generation_service` to use the new agnostic function names (`generate_answer`, `stream_answer`, etc.).
* Replace all calls inside `guarded_chat` and `guarded_chat_stream` with their agnostic counterparts.

#### [MODIFY] [main.py](file:///c:/Users/ARSHAN/Desktop/RagTrust/DataTrust_Project/backend/app/main.py)
* Update startup LLM warm-up function to use the provider factory to test connection status (either warming up local Ollama or sending a small test check to OpenRouter).

---

## Verification Plan

### Manual Verification
1. **With OpenRouter**:
   * Add `OPENROUTER_API_KEY=your_key` to `.env`.
   * Start backend (`uvicorn app.main:app`).
   * Trigger chat queries from Swagger UI and verify responses are fetched from OpenRouter.
2. **With Ollama (Local Fallback)**:
   * Keep `OPENROUTER_API_KEY` blank or unset.
   * Verify that the client falls back to local Ollama.
