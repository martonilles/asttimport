from pathlib import Path
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from asttimport.utils import info, error

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SERVICE_ACCOUNT_PATH = Path("service_account.json").resolve()


def authenticate():
    if not SERVICE_ACCOUNT_PATH.exists():
        error(f"Error: {SERVICE_ACCOUNT_PATH.as_posix()} not found!")
        error("\nCreate service account at Google Cloud Console")
        error("Then share the sheet with the service account email")
        return None

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH.as_posix(), scopes=SCOPES
    )

    return build("drive", "v3", credentials=credentials)


def get_timetable_excel(service, name, file_id):
    try:
        request = service.files().export_media(
            fileId=file_id,
            mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        info(f"Downloading {name} ({file_id})...")
        while not done:
            status, done = downloader.next_chunk()
            if status:
                info(f"Progress: {int(status.progress() * 100)}%")

        fh.seek(0)
        return fh

    except Exception as e:
        error(f"Error downloading: {e}")
