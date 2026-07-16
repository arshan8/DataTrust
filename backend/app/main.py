from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.analyze import router as analyze_router
from app.routers.retrieval import router as retrieval_router
from app.routers.ingestion import router as ingestion_router
from app.routers.verification import router as verification_router
from app.routers.chat import router as chat_router  
from app.routers.debug import router as debug_router
from app.routers.local_ingestion import router as local_ingestion_router
from app.routers.admin import router as admin_router
import requests
from app.core.config import settings
from app.services.embedding_service import generate_embedding
from app.routers.data_quality import router as data_quality_router
#from app.routers.github_connect import router as github_connector_router
from app.routers.confluence_ingest import router as confluence_connector_router
#from app.routers.google_drive_ingest import router as google_drive_connector_router
from app.routers.github_ingest import router as github_ingest_router
from app.routers.google_drive_ingest import router as google_drive_ingest_router
from app.routers import chat_history

app = FastAPI(title="DataTrust Backend")

@app.on_event("startup")
def warm_up_models():
    try:
        generate_embedding("warm up")
        print("Embedding model warmed up")
    except Exception as e:
        print(f"Embedding warm-up failed: {e}")

    if settings.OPENROUTER_API_KEY:
        print("Using OpenRouter (skipping local LLM warm-up)")
    else:
        try:
            requests.post(
                f"{settings.LLM_URL}/api/generate",
                json={
                    "model": "phi3:latest",
                    "prompt": "hello",
                    "stream": False,
                    "options": {"num_predict": 10},
                },
                timeout=60,
            )
            print("LLM warm-up completed")
        except Exception as e:
            print(f"LLM warm-up failed: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://136.111.123.202",
        "http://136.111.123.202.nip.io",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5173/admin"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(analyze_router, tags=["policy"])
app.include_router(retrieval_router, tags=["retrieval"])
app.include_router(ingestion_router, tags=["ingestion"])
app.include_router(verification_router, tags=["verification"])
app.include_router(chat_router, tags=["chat"])
app.include_router(debug_router, tags=["debug"])
app.include_router(local_ingestion_router, tags=["local-ingestion"])
app.include_router(admin_router, tags=["admin"])
app.include_router(data_quality_router, tags=["verification"])
app.include_router(confluence_connector_router, tags=["confluence"])
app.include_router(github_ingest_router, tags=["github-ingestion"])
app.include_router(google_drive_ingest_router, tags=["google-drive-ingestion"])
app.include_router(chat_history.router)
