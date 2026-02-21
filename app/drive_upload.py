# app/drive_upload.py
"""
Upload de PDF para Google Drive e geração de link "Qualquer pessoa com o link pode visualizar".
Requer: GOOGLE_APPLICATION_CREDENTIALS (caminho do JSON da service account) e GOOGLE_DRIVE_FOLDER_ID.
"""
import os.path
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
_DRIVE_SERVICE = None


def _get_drive_service():
    global _DRIVE_SERVICE
    if _DRIVE_SERVICE: return _DRIVE_SERVICE

    BASE_DIR = Path(__file__).resolve().parent
    CLIENT_SECRETS_PATH = BASE_DIR / "client_secrets.json"

    scopes = ["https://www.googleapis.com/auth/drive.file"]
    creds = None
    
    # O arquivo token.json guarda as permissões para não precisar logar toda hora
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', scopes)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_PATH), scopes)
            # Isso abrirá o navegador uma única vez para você autorizar
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    _DRIVE_SERVICE = build("drive", "v3", credentials=creds)
    return _DRIVE_SERVICE


def upload_pdf_and_get_link(pdf_path: Path, filename: Optional[str] = None) -> Optional[str]:
    """
    Envia o PDF para a pasta do Google Drive configurada, define permissão
    "Qualquer pessoa com o link pode visualizar" e retorna o link.

    Args:
        pdf_path: Caminho local do arquivo PDF.
        filename: Nome do arquivo no Drive (opcional; padrão: nome do arquivo local).

    Returns:
        URL do arquivo (webContentLink para download) ou None em caso de erro.
    """
    service = _get_drive_service()
    if service is None:
        return "service not found"
    folder_id = "add it here"
    if not folder_id:
        return "folder_id not found"
    path = Path(pdf_path).resolve()
    if not path.exists():
        return "path not found"
    name = filename or path.name
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        return "error to import googleapiclient.http"
    try:
        file_metadata = {
            "name": name,
            "parents": [folder_id],
            "copyRequiresWriterPermission": True,
            "writersCanShare": True,
        }
        media = MediaFileUpload(str(path), mimetype="application/pdf", resumable=False)
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id", supportsAllDrives=True)
            .execute()
        )
        file_id = file.get("id")
        if not file_id:
            return "file_id not found"
        # Permissão: qualquer pessoa com o link pode visualizar
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()
        # Obter link de visualização/download
        file = (
            service.files()
            .get(fileId=file_id, fields="webViewLink,webContentLink")
            .execute()
        )
        # Preferir webContentLink (download direto); fallback para webViewLink (abre no navegador)
        return file.get("webContentLink") or file.get("webViewLink")
    except Exception as e:
        print(f"Erro detalhado: {e}")
        return f"error to get file: {str(e)}"
