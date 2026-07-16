import io
import csv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from app.core.config import settings


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=creds)


def list_files_in_folder(folder_id: str) -> list[dict]:
    service = get_drive_service()

    query = f"'{folder_id}' in parents and trashed=false"

    res = service.files().list(
        q=query,
        fields="files(id,name,mimeType,modifiedTime,webViewLink)",
        pageSize=100,
    ).execute()

    return res.get("files", [])


def download_file_text(file_id: str, mime_type: str) -> str:
    service = get_drive_service()

    if mime_type == "text/csv":
        request = service.files().get_media(fileId=file_id)
    elif mime_type == "application/vnd.google-apps.spreadsheet":
        request = service.files().export_media(
            fileId=file_id,
            mimeType="text/csv",
        )
    elif mime_type == "application/vnd.google-apps.document":
        request = service.files().export_media(
            fileId=file_id,
            mimeType="text/plain",
        )
    else:
        return ""

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    raw = fh.getvalue().decode("utf-8", errors="ignore")

    if mime_type in ["text/csv", "application/vnd.google-apps.spreadsheet"]:
        return csv_to_text(raw)

    return raw


def csv_to_text(raw_csv: str) -> str:
    reader = csv.DictReader(io.StringIO(raw_csv))
    rows = []

    for idx, row in enumerate(reader, start=1):
        line = f"Row {idx}: " + "; ".join(
            f"{k}={v}" for k, v in row.items() if v is not None
        )
        rows.append(line)

    return "\n".join(rows)