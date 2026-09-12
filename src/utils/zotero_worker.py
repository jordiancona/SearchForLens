from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional, List, Dict, Any
from src.api.models import Article
from src.api.zotero_client import ZoteroClient

class ZoteroUploadWorker(QThread):
    """Worker thread for background upload of single articles or article batches to Zotero API."""

    status_updated = pyqtSignal(str)
    upload_complete = pyqtSignal(dict)  # Returns info dict e.g. {"count": 1, "title": ...}
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        user_id: str,
        api_key: str,
        article: Optional[Article] = None,
        articles: Optional[List[Article]] = None
    ):
        super().__init__()
        self.user_id = user_id
        self.api_key = api_key
        self.article = article
        self.articles = articles

        self.zotero_client = ZoteroClient(user_id=user_id, api_key=api_key)

    def run(self):
        try:
            self.status_updated.emit("Verificando conexión con Zotero...")
            valid, msg = self.zotero_client.verify_credentials(self.user_id, self.api_key)
            if not valid:
                self.error_occurred.emit(f"Error de autenticación con Zotero: {msg}")
                return

            if self.article:
                self.status_updated.emit(f"Enviando artículo '{self.article.title[:40]}...' a Zotero...")
                result = self.zotero_client.create_item(self.article, self.user_id, self.api_key)
                self.upload_complete.emit(result)
            elif self.articles:
                self.status_updated.emit(f"Exportando {len(self.articles)} artículos a Zotero...")
                result = self.zotero_client.create_items_batch(self.articles, self.user_id, self.api_key)
                self.upload_complete.emit(result)
            else:
                self.error_occurred.emit("No se especificaron artículos para enviar a Zotero.")

        except Exception as e:
            self.error_occurred.emit(f"Error al comunicar con Zotero: {str(e)}")
