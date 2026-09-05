import os
import mimetypes
from typing import Optional, Tuple, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
# pyrefly: ignore [missing-import]
from google_auth_oauthlib.flow import InstalledAppFlow
# pyrefly: ignore [missing-import]
from googleapiclient.discovery import build
# pyrefly: ignore [missing-import]
from googleapiclient.http import MediaFileUpload

# Allow oauthlib to handle additional openid scope automatically added by Google OAuth
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/userinfo.email'
]

class GDriveClient:
    """Client for authenticating and interacting with the Google Drive API."""

    def __init__(self, credentials_path: str = "", token_path: str = ""):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds: Optional[Credentials] = None
        self.service = None

    def authenticate(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None) -> Tuple[bool, str]:
        """Authenticate with Google Drive using saved token or credentials.json."""
        cred_path = credentials_path or self.credentials_path
        tok_path = token_path or self.token_path

        if tok_path and os.path.exists(tok_path):
            try:
                self.creds = Credentials.from_authorized_user_file(tok_path, SCOPES)
            except Exception as e:
                print(f"Error loading existing token.json: {e}")
                self.creds = None

        # Refresh token if expired
        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                with open(tok_path, 'w') as token_file:
                    token_file.write(self.creds.to_json())
            except Exception as e:
                print(f"Error refreshing Google Drive token: {e}")
                self.creds = None

        # If no valid token exists, initiate OAuth Flow
        if not self.creds or not self.creds.valid:
            client_id = os.getenv("GOOGLE_CLIENT_ID", "")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

            try:
                if cred_path and os.path.exists(cred_path):
                    flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
                elif client_id and client_secret:
                    client_config = {
                        "installed": {
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                        }
                    }
                    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                else:
                    return False, "No se encontró el archivo 'credentials.json' ni la configuración GOOGLE_CLIENT_ID."

                self.creds = flow.run_local_server(port=0)

                # Save token locally for future sessions
                if tok_path:
                    os.makedirs(os.path.dirname(tok_path), exist_ok=True)
                    with open(tok_path, 'w') as token_file:
                        token_file.write(self.creds.to_json())
            except Exception as e:
                return False, f"Error durante el inicio de sesión con Google: {str(e)}"

        try:
            self.service = build('drive', 'v3', credentials=self.creds)
            email = self.get_user_email()
            return True, f"Conectado exitosamente como {email}."
        except Exception as e:
            return False, f"Error al inicializar la API de Google Drive: {str(e)}"

    def is_authenticated(self) -> bool:
        return self.creds is not None and self.creds.valid

    def check_connection(self, token_path: str) -> Tuple[bool, str]:
        """Check if existing token is valid and return connection status."""
        if not token_path or not os.path.exists(token_path):
            return False, "Sin conexión a Google Drive."

        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, 'w') as f:
                    f.write(creds.to_json())

            if creds and creds.valid:
                self.creds = creds
                self.service = build('drive', 'v3', credentials=self.creds)
                email = self.get_user_email()
                return True, f"Conectado a Google Drive como {email}."
        except Exception as e:
            print(f"Error checking GDrive connection: {e}")

        return False, "Token de Google Drive no disponible o expirado."

    def get_user_email(self) -> str:
        """Fetch email of the authenticated Google user."""
        if not self.creds:
            return "Usuario de Google"
        try:
            oauth_service = build('oauth2', 'v2', credentials=self.creds)
            user_info = oauth_service.userinfo().get().execute()
            return user_info.get("email", "Usuario de Google")
        except Exception:
            return "Cuenta de Google"

    def get_or_create_folder(self, folder_name: str = "SearchForLens", parent_id: Optional[str] = None) -> Optional[str]:
        """Find or create a folder in Google Drive and return its folder_id."""
        if not self.service:
            return None

        try:
            # Query existing folder
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"

            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])
            if files:
                return files[0].get('id')

            # Create folder if not found
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                folder_metadata['parents'] = [parent_id]

            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            return folder.get('id')

        except Exception as e:
            print(f"Error getting/creating GDrive folder: {e}")
            return None

    def verify_or_find_folder(self, input_str: str) -> Tuple[Optional[str], str]:
        """
        Verify if input_str is a Folder URL, Folder ID, or Folder Name.
        Returns (folder_id, resolved_name_or_error_msg).
        """
        if not self.service:
            return None, "Google Drive API no está autenticado."

        clean = input_str.strip()
        if not clean:
            clean = "SearchForLens"

        import re
        is_url = "http" in clean or "drive.google.com" in clean or "/" in clean

        folder_id = None

        # Pattern 1: .../folders/FOLDER_ID
        m1 = re.search(r'folders/([a-zA-Z0-9_-]+)', clean)
        if m1:
            folder_id = m1.group(1).split('?')[0]

        # Pattern 2: ...?id=FOLDER_ID or ...&id=FOLDER_ID
        if not folder_id:
            m2 = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', clean)
            if m2:
                folder_id = m2.group(1).split('&')[0]

        # Pattern 3: .../d/FOLDER_ID
        if not folder_id:
            m3 = re.search(r'/d/([a-zA-Z0-9_-]+)', clean)
            if m3:
                folder_id = m3.group(1).split('/')[0]

        # Pattern 4: Raw alphanumeric ID string (e.g. >= 20 chars without spaces or slashes)
        if not folder_id and not is_url and len(clean) >= 20 and " " not in clean and "/" not in clean:
            folder_id = clean

        if folder_id:
            try:
                res = self.service.files().get(
                    fileId=folder_id,
                    fields='id, name, mimeType, trashed',
                    supportsAllDrives=True
                ).execute()

                if res.get('trashed'):
                    return None, "La carpeta indicada está en la papelera."
                if res.get('mimeType') != 'application/vnd.google-apps.folder':
                    return None, f"El objeto especificado ('{res.get('name')}') es un archivo, no una carpeta."

                return res.get('id'), res.get('name', 'Carpeta Drive')
            except Exception as e:
                print(f"Direct ID lookup for '{folder_id}' failed: {e}")
                if is_url or (len(clean) >= 20 and " " not in clean):
                    return None, f"No se pudo acceder a la carpeta de Google Drive (ID: '{folder_id}'). Verifique que pertenezca a la cuenta o tenga permisos."

        # If it was a URL but we couldn't parse or access the ID, do NOT create a folder named after the URL!
        if is_url:
            return None, "El enlace proporcionado no contiene un ID de carpeta de Google Drive válido o accesible."

        # Otherwise treat input_str as a plain Folder Name and find or create it
        fid = self.get_or_create_folder(folder_name=clean)
        if fid:
            return fid, clean
        return None, f"No se pudo encontrar ni crear la carpeta '{clean}'."

    def upload_file(
        self,
        file_path: str,
        folder_id: Optional[str] = None,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a file to Google Drive under folder_id."""
        if not self.service:
            raise RuntimeError("Google Drive API no está autenticado.")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No se encontró el archivo local: {file_path}")

        name = file_name or os.path.basename(file_path)
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'

        file_metadata = {'name': name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        try:
            uploaded_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink'
            ).execute()

            return uploaded_file
        except Exception as e:
            raise RuntimeError(f"Error al subir archivo a Google Drive: {str(e)}")
