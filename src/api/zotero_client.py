import requests
from typing import List, Optional, Tuple, Dict, Any
from src.api.models import Article

ZOTERO_BASE_URL = "https://api.zotero.org"

class ZoteroClient:
    """Client for interacting with Zotero Web API v3."""

    def __init__(self, user_id: str = "", api_key: str = "", timeout: int = 15):
        self.user_id = user_id.strip()
        self.api_key = api_key.strip()
        self.timeout = timeout

    def set_credentials(self, user_id: str, api_key: str):
        self.user_id = user_id.strip()
        self.api_key = api_key.strip()

    def verify_credentials(self, user_id: Optional[str] = None, api_key: Optional[str] = None) -> Tuple[bool, str]:
        """Verify if Zotero User ID and API Key are valid."""
        uid = (user_id if user_id is not None else self.user_id).strip()
        key = (api_key if api_key is not None else self.api_key).strip()

        if not uid or not key:
            return False, "Se requiere proporcionar tanto el User ID como la API Key de Zotero."

        headers = {
            "Zotero-API-Key": key,
            "Zotero-API-Version": "3"
        }
        url = f"{ZOTERO_BASE_URL}/users/{uid}/items"
        params = {"limit": 1}

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return True, f"¡Conexión exitosa con Zotero! (User ID: {uid})"
            elif resp.status_code == 403 or resp.status_code == 401:
                return False, "API Key o User ID inválidos o sin permisos de lectura en Zotero."
            else:
                return False, f"Respuesta inesperada de Zotero (Código HTTP {resp.status_code})"
        except Exception as e:
            return False, f"Error al conectar con Zotero: {str(e)}"

    def article_to_zotero_item(self, article: Article) -> Dict[str, Any]:
        """Convert SearchForLens Article object into Zotero journalArticle schema."""
        creators = []
        for author in article.authors:
            author_clean = author.strip()
            parts = author_clean.split()
            if len(parts) > 1:
                creators.append({
                    "creatorType": "author",
                    "firstName": " ".join(parts[:-1]),
                    "lastName": parts[-1]
                })
            elif author_clean:
                creators.append({
                    "creatorType": "author",
                    "name": author_clean
                })

        if not creators:
            creators = [{"creatorType": "author", "name": "Autor Desconocido"}]

        year = article.pub_date[:4] if len(article.pub_date) >= 4 else ""

        extra_lines = []
        if article.arxiv_id:
            extra_lines.append(f"arXiv: {article.arxiv_id}")
        if article.bibcode:
            extra_lines.append(f"Bibcode: {article.bibcode}")
        if article.inspire_id:
            extra_lines.append(f"INSPIRE: {article.inspire_id}")
        if article.citations:
            extra_lines.append(f"Citations: {article.citations}")

        item = {
            "itemType": "journalArticle",
            "title": article.title,
            "creators": creators,
            "abstractNote": article.abstract or "",
            "publicationTitle": article.journal or f"Preprint ({article.source})",
            "date": year,
            "DOI": article.doi or "",
            "url": article.url or article.pdf_url or "",
            "extra": "\n".join(extra_lines)
        }

        return item

    def create_item(
        self,
        article: Article,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post a single Article to Zotero library."""
        uid = (user_id if user_id is not None else self.user_id).strip()
        key = (api_key if api_key is not None else self.api_key).strip()

        if not uid or not key:
            raise ValueError("User ID y API Key de Zotero son requeridos. Configure sus credenciales en Ajustes.")

        item_data = self.article_to_zotero_item(article)
        headers = {
            "Zotero-API-Key": key,
            "Zotero-API-Version": "3",
            "Content-Type": "application/json"
        }
        url = f"{ZOTERO_BASE_URL}/users/{uid}/items"

        resp = requests.post(url, headers=headers, json=[item_data], timeout=self.timeout)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Error al guardar en Zotero (HTTP {resp.status_code}): {resp.text}")

        res_json = resp.json()
        successful_items = res_json.get("success", {})
        if successful_items:
            item_key = list(successful_items.values())[0] if isinstance(successful_items, dict) else "item"
            return {"status": "success", "key": item_key, "title": article.title}
        else:
            return {"status": "success", "raw": res_json, "title": article.title}

    def create_items_batch(
        self,
        articles: List[Article],
        user_id: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post multiple articles to Zotero library in batches of up to 50 items."""
        uid = (user_id if user_id is not None else self.user_id).strip()
        key = (api_key if api_key is not None else self.api_key).strip()

        if not uid or not key:
            raise ValueError("User ID y API Key de Zotero son requeridos. Configure sus credenciales en Ajustes.")

        if not articles:
            return {"status": "empty", "count": 0}

        headers = {
            "Zotero-API-Key": key,
            "Zotero-API-Version": "3",
            "Content-Type": "application/json"
        }
        url = f"{ZOTERO_BASE_URL}/users/{uid}/items"

        batch_size = 50
        created_count = 0

        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            items_payload = [self.article_to_zotero_item(a) for a in batch]

            resp = requests.post(url, headers=headers, json=items_payload, timeout=self.timeout)
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Error en lote de Zotero (HTTP {resp.status_code}): {resp.text}")

            res_json = resp.json()
            succ = res_json.get("success", {})
            created_count += len(succ) if isinstance(succ, dict) else len(batch)

        return {"status": "success", "count": created_count}
