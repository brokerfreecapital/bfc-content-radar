import io
import os
from typing import Dict, Iterable, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

def get_file_metadata(file_id: str) -> dict:
    service = _drive_service()
    return service.files().get(
        fileId=file_id,
        fields="id,name,mimeType,owners(emailAddress),driveId",
        supportsAllDrives=True,
    ).execute()

def _drive_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=DRIVE_SCOPES,
    )
    return build("drive", "v3", credentials=creds)

def list_child_folders(parent_folder_id: str) -> Dict[str, str]:
    service = _drive_service()
    q = (
        f"'{parent_folder_id}' in parents and "
        "mimeType='application/vnd.google-apps.folder' and trashed=false"
    )

    out: Dict[str, str] = {}
    page_token: Optional[str] = None

    while True:
        resp = service.files().list(
            q=q,
            fields="nextPageToken, files(id, name)",
            pageToken=page_token,
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        for f in resp.get("files", []):
            normalized_name = f["name"].strip().strip("/")
            out[normalized_name] = f["id"]

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return out


def list_txt_files(folder_id: str) -> List[dict]:
    service = _drive_service()
    q = f"'{folder_id}' in parents and mimeType='text/plain' and trashed=false"

    files: List[dict] = []
    page_token: Optional[str] = None

    while True:
        resp = service.files().list(
            q=q,
            fields="nextPageToken, files(id, name, modifiedTime, createdTime, size)",
            pageToken=page_token,
            pageSize=200,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    files.sort(key=lambda x: x.get("modifiedTime", ""), reverse=True)
    return files


def list_files(folder_id: str, mime_types: Optional[Iterable[str]] = None) -> List[dict]:
    """List files in a folder, optionally filtered by mime types."""
    service = _drive_service()
    base_q = f"'{folder_id}' in parents and trashed=false"
    if mime_types:
        mime_parts = [f"mimeType='{m}'" for m in mime_types]
        mime_clause = " or ".join(mime_parts)
        base_q += f" and ({mime_clause})"

    out: List[dict] = []
    page_token: Optional[str] = None

    while True:
        resp = service.files().list(
            q=base_q,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, createdTime, size)",
            pageToken=page_token,
            pageSize=200,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        out.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    out.sort(key=lambda x: x.get("modifiedTime", ""), reverse=True)
    return out


def download_file(file_id: str, destination_path: str) -> None:
    """Download any Drive file to the given local path."""
    service = _drive_service()
    request = service.files().get_media(fileId=file_id)
    with open(destination_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def upload_text_file(folder_id: str, filename: str, content: str) -> dict:
    """Upload a UTF-8 text file into the specified Drive folder."""
    service = _drive_service()
    media_body = MediaIoBaseUpload(io.BytesIO(content.encode("utf-8")), mimetype="text/plain")
    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }
    return service.files().create(
        body=file_metadata,
        media_body=media_body,
        fields="id,name,modifiedTime",
    ).execute()

def download_text(file_id: str) -> str:
    """Download a text/plain file content."""
    service = _drive_service()
    data = service.files().get_media(fileId=file_id).execute()  # bytes
    return data.decode("utf-8", errors="replace")


def load_transcripts_from_root(root_folder_id: str, transcripts_folder_name: str) -> List[dict]:
    """Find transcripts folder by name under root, then download all .txt transcripts."""
    folders = list_child_folders(root_folder_id)
    if transcripts_folder_name not in folders:
        raise RuntimeError(
            f"Transcripts folder '{transcripts_folder_name}' not found under root {root_folder_id}. "
            f"Found folders: {list(folders.keys())}"
        )

    transcripts_id = folders[transcripts_folder_name]
    txt_files = list_txt_files(transcripts_id)

    out: List[dict] = []
    for f in txt_files:
        out.append({
            "id": f["id"],
            "name": f["name"],
            "modifiedTime": f.get("modifiedTime"),
            "text": download_text(f["id"]),
        })
    return out
