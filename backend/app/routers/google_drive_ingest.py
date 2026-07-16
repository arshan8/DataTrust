from fastapi import APIRouter
from app.core.config import settings
from app.services.connectors_sources.google_drive_connector import (
    list_files_in_folder,
    download_file_text,
)
from app.services.ingestion_common_service import ingest_text_document

router = APIRouter()


DRIVE_FOLDERS = [
    {
        "folder_id": settings.GOOGLE_DRIVE_HR_L1_FOLDER_ID,
        "folder_name": "hr_data/L1",
        "department_code": "HR",
        "level_code": "L1",
        "scope_external_id": "BC-HR-GDRIVE-L1",
    },
    {
        "folder_id": settings.GOOGLE_DRIVE_HR_L2_FOLDER_ID,
        "folder_name": "hr_data/L2",
        "department_code": "HR",
        "level_code": "L2",
        "scope_external_id": "BC-HR-GDRIVE-L2",
    },
    {
        "folder_id": settings.GOOGLE_DRIVE_HR_L3_FOLDER_ID,
        "folder_name": "hr_data/L3",
        "department_code": "HR",
        "level_code": "L3",
        "scope_external_id": "BC-HR-GDRIVE-L3",
    },
]


@router.get("/debug/google-drive-files")
def debug_google_drive_files():
    output = []

    for folder in DRIVE_FOLDERS:
        if not folder["folder_id"]:
            output.append({
                "folder": folder["folder_name"],
                "error": "missing_folder_id",
            })
            continue

        files = list_files_in_folder(folder["folder_id"])
        output.append({
            "folder": folder["folder_name"],
            "file_count": len(files),
            "files": files,
        })

    return output


@router.post("/ingest/google-drive")
def ingest_google_drive():
    results = []
    skipped = []
    failed = []

    for folder in DRIVE_FOLDERS:
        if not folder["folder_id"]:
            skipped.append({
                "folder": folder["folder_name"],
                "reason": "missing_folder_id",
            })
            continue

        try:
            files = list_files_in_folder(folder["folder_id"])
        except Exception as e:
            failed.append({
                "folder": folder["folder_name"],
                "error": str(e),
            })
            continue

        for file in files:
            try:
                text = download_file_text(file["id"], file["mimeType"])

                if not text.strip():
                    skipped.append({
                        "file": file["name"],
                        "reason": "unsupported_or_empty",
                    })
                    continue

                result = ingest_text_document(
                    source_code="GDRIVE",
                    department_code=folder["department_code"],
                    level_code=folder["level_code"],
                    scope_external_id=folder["scope_external_id"],
                    external_doc_id=f"gdrive:{file['id']}",
                    external_parent_id=folder["folder_id"],
                    title=file["name"],
                    resource_path=f"gdrive://{folder['folder_name']}/{file['name']}",
                    source_url=file.get("webViewLink"),
                    raw_text=text,
                    metadata={
                        "connector": "google_drive",
                        "folder": folder["folder_name"],
                        "file_id": file["id"],
                        "mime_type": file["mimeType"],
                        "modified_time": file.get("modifiedTime"),
                    },
                )

                results.append(result)

            except Exception as e:
                failed.append({
                    "file": file.get("name"),
                    "error": str(e),
                })

    return {
        "status": "completed_with_errors" if failed else "success",
        "ingested_count": len(results),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "results": results,
        "skipped": skipped,
        "failed": failed,
    }