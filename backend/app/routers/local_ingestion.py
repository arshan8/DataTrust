from fastapi import APIRouter
from pydantic import BaseModel

from app.services.local_ingestion_service import ingest_local_file

router = APIRouter()


class LocalIngestRequest(BaseModel):
    file_path: str
    source_code: str
    department_code: str
    level_code: str
    resource_scope_external_id: str


@router.post("/ingest/local-file")
def ingest_local_file_route(request: LocalIngestRequest):
    result = ingest_local_file(
        file_path=request.file_path,
        source_code=request.source_code,
        department_code=request.department_code,
        level_code=request.level_code,
        resource_scope_external_id=request.resource_scope_external_id,
    )
    return {
        "status": "success",
        "result": result,
    }