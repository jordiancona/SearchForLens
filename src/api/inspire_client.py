import re
import requests
from typing import List, Optional
from src.api.models import Article

INSPIRE_API_SEARCH_URL = "https://inspirehep.net/api/literature"

class InspireClient:
    """Client for fetching articles and metadata from INSPIRE-HEP REST API."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def build_preset_query(
        self,
        preset_type: str,
        custom_query: str = "",
        author: str = "",
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> str:
        """Construct INSPIRE-HEP API search query string."""
        terms = []

        if preset_type == "strong_lensing":
            terms.append('("strong gravitational lensing" OR "strong lensing")')
        elif preset_type == "ai_lensing":
            lens_q = '("gravitational lensing" OR "strong lensing")'
            ai_q = '("machine learning" OR "deep learning" OR "neural network" OR "artificial intelligence" OR "surrogate model")'
            terms.append(f'({lens_q} AND {ai_q})')
        else:
            if custom_query.strip():
                q_clean = custom_query.strip()
                if " " in q_clean and not (q_clean.startswith('"') and q_clean.endswith('"')):
                    terms.append(f'"{q_clean}"')
                else:
                    terms.append(q_clean)

        if author.strip():
            terms.append(f'author:"{author.strip()}"')

        if start_year and end_year:
            terms.append(f'date:{start_year}->{end_year}')
        elif start_year:
            terms.append(f'date:{start_year}->2026')
        elif end_year:
            terms.append(f'date:1900->{end_year}')

        query_str = " AND ".join(terms) if terms else '"gravitational lensing"'
        return query_str

    def search(
        self,
        query: str,
        max_results: int = 50,
        sort_by: str = "date"  # "date", "citations", "relevance"
    ) -> List[Article]:
        """Perform search request to INSPIRE-HEP API and return list of Article instances."""
        sort_val = "mostrecent"
        if sort_by == "citations":
            sort_val = "mostcited"
        elif sort_by == "relevance":
            sort_val = "ranking"

        params = {
            "q": query,
            "size": max_results,
            "sort": sort_val,
            "format": "json"
        }

        headers = {
            "Accept": "application/json",
            "User-Agent": "SearchForLens/1.0 (Gravitational Lensing Research Tool)"
        }

        try:
            resp = requests.get(INSPIRE_API_SEARCH_URL, headers=headers, params=params, timeout=self.timeout)
            resp.raise_for_status()

            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])

            articles = []
            for hit in hits:
                article = self._parse_hit(hit)
                if article:
                    articles.append(article)
            return articles

        except requests.exceptions.RequestException as req_err:
            raise RuntimeError(f"Error de red al consultar INSPIRE-HEP: {str(req_err)}")
        except Exception as e:
            raise RuntimeError(f"Error al procesar resultados de INSPIRE-HEP: {str(e)}")

    def _parse_hit(self, hit: dict) -> Optional[Article]:
        """Parse raw INSPIRE-HEP hit dict into Article object."""
        try:
            metadata = hit.get("metadata", {})
            control_number = str(metadata.get("control_number") or hit.get("id", ""))
            if not control_number:
                return None

            # Title
            titles = metadata.get("titles", [])
            title = titles[0].get("title", "Sin título") if titles else "Sin título"
            title = re.sub(r'\s+', ' ', title.replace('\n', ' ')).strip()

            # Abstract
            abstracts = metadata.get("abstracts", [])
            abstract = abstracts[0].get("value", "Sin resumen disponible.") if abstracts else "Sin resumen disponible."
            abstract = re.sub(r'\s+', ' ', abstract.replace('\n', ' ')).strip()

            # Authors
            authors = []
            for auth in metadata.get("authors", []):
                full_name = auth.get("full_name")
                if full_name:
                    authors.append(full_name)
                else:
                    first = auth.get("first_name", "")
                    last = auth.get("last_name", "")
                    name = f"{first} {last}".strip()
                    if name:
                        authors.append(name)

            if not authors:
                authors = ["Autor Desconocido"]

            # Publication Date
            earliest_date = metadata.get("earliest_date") or metadata.get("legacy_creation_date") or ""
            pub_date = earliest_date[:10] if earliest_date else ""

            # Citation count
            citations = metadata.get("citation_count", 0) or 0

            # ArXiv ID
            arxiv_id = None
            arxiv_eprints = metadata.get("arxiv_eprints", [])
            if arxiv_eprints:
                arxiv_id = arxiv_eprints[0].get("value")

            # DOI
            doi = None
            dois = metadata.get("dois", [])
            if dois:
                doi = dois[0].get("value")

            # Journal / Publication info
            journal = "INSPIRE-HEP"
            pub_info = metadata.get("publication_info", [])
            if pub_info:
                j_title = pub_info[0].get("journal_title")
                j_volume = pub_info[0].get("journal_volume")
                j_year = pub_info[0].get("year")
                if j_title:
                    journal_parts = [j_title]
                    if j_volume:
                        journal_parts.append(str(j_volume))
                    if j_year:
                        journal_parts.append(f"({j_year})")
                    journal = " ".join(journal_parts)

            # URLs
            url = f"https://inspirehep.net/literature/{control_number}"
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None

            # If document links available in metadata
            documents = metadata.get("documents", [])
            if not pdf_url and documents:
                for doc in documents:
                    doc_url = doc.get("url", "")
                    if doc_url.lower().endswith(".pdf") or "pdf" in doc_url.lower():
                        pdf_url = doc_url
                        break

            return Article(
                id=f"inspire_{control_number}",
                title=title,
                authors=authors,
                abstract=abstract,
                pub_date=pub_date,
                source="INSPIRE-HEP",
                arxiv_id=arxiv_id,
                inspire_id=control_number,
                doi=doi,
                pdf_url=pdf_url,
                url=url,
                citations=citations,
                journal=journal
            )
        except Exception as err:
            print(f"Error parsing INSPIRE-HEP hit: {err}")
            return None
