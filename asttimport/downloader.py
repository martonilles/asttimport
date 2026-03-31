from pathlib import Path
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SERVICE_ACCOUNT_PATH = Path("service_account.json").resolve()


def authenticate():
    if not SERVICE_ACCOUNT_PATH.exists():
        print(f"Error: {SERVICE_ACCOUNT_PATH.as_posix()} not found!")
        print("\nCreate service account at Google Cloud Console")
        print("Then share the sheet with the service account email")
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
        print(f"Downloading {name} ({file_id})...")
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Progress: {int(status.progress() * 100)}%")

        fh.seek(0)
        return fh

    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. Spreadsheet ID is correct")
        print("2. Sheet is shared with service account email")
        print("3. File is a Google Sheet (not regular Excel file)")
