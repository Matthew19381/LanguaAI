import logging
import os

from backend.config import settings

logger = logging.getLogger(__name__)

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", "gdrive_token.json")
CREDENTIALS_FILE = os.environ.get(
    "GDRIVE_CLIENT_SECRETS_FILE",
    os.path.join(os.path.dirname(__file__), "..", "gdrive_credentials.json")
)
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_auth_url() -> str:
    """Return Google OAuth2 authorization URL."""
    try:
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=f"{settings.BACKEND_URL}/api/settings/gdrive/callback"
        )
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
        return auth_url
    except Exception as e:
        logger.error(f"Error generating auth URL: {e}")
        raise


def save_token_from_code(code: str) -> bool:
    """Exchange OAuth2 code for token and save to file."""
    try:
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=f"{settings.BACKEND_URL}/api/settings/gdrive/callback"
        )
        flow.fetch_token(code=code)
        creds = flow.credentials

        import json
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        }
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f)
        return True
    except Exception as e:
        logger.error(f"Error saving token: {e}")
        return False


def _get_credentials():
    """Load saved credentials from token file."""
    import json

    from google.oauth2.credentials import Credentials

    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError("Google Drive not authorized. Visit /api/settings/gdrive/auth first.")

    with open(TOKEN_FILE) as f:
        data = json.load(f)

    creds = Credentials(
        token=data["token"],
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", SCOPES),
    )
    return creds


def get_or_create_folder(service, folder_name: str, parent_id: str | None = None) -> str:
    """Get or create a Google Drive folder by name, return its ID."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def upload_to_google_drive(
    file_path: str,
    folder_id: str | None = None,
    subfolder_name: str | None = None,
) -> str:
    """Upload a file to Google Drive and return the file URL.

    If subfolder_name is given (e.g. 'Hiszpanski_A1'), the file is placed
    inside that subfolder (created automatically if needed).
    """
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = _get_credentials()
        service = build("drive", "v3", credentials=creds)

        target_folder_id = folder_id
        if subfolder_name:
            target_folder_id = get_or_create_folder(service, subfolder_name, parent_id=folder_id)

        filename = os.path.basename(file_path)
        file_metadata = {"name": filename}
        if target_folder_id:
            file_metadata["parents"] = [target_folder_id]

        media = MediaFileUpload(file_path, mimetype="text/markdown")
        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,webViewLink"
        ).execute()

        url = uploaded.get("webViewLink", f"https://drive.google.com/file/d/{uploaded['id']}")
        logger.info(f"Uploaded {filename} to Google Drive: {url}")
        return url
    except Exception as e:
        logger.error(f"Google Drive upload failed: {e}")
        raise


def is_authorized() -> bool:
    """Check if Google Drive OAuth token exists."""
    return os.path.exists(TOKEN_FILE)
