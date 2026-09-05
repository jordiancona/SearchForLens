from typing import List, Optional, Tuple, Callable
from src.api.models import Article
from src.api.arxiv_client import ArxivClient
from src.api.ads_client import AdsClient
from src.api.inspire_client import InspireClient

class SearchService:
    """
    Pure Python search and consolidation service for SearchForLens.
    Decoupled from any GUI framework (PyQt6/Qt) for cross-platform and mobile backend reusability.
    """

    def __init__(self, ads_api_key: str = ""):
        self.ads_api_key = ads_api_key
        self.arxiv_client = ArxivClient()
        self.ads_client = AdsClient(api_key=ads_api_key)
        self.inspire_client = InspireClient()

    def set_ads_api_key(self, api_key: str) -> None:
        self.ads_api_key = api_key
        self.ads_client.set_api_key(api_key)

    def execute_search(
        self,
        preset_type: str = "custom",
        custom_query: str = "",
        author: str = "",
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        source: str = "all",           # "all", "arxiv", "ads", "inspire", or "both"
        max_results: int = 50,
        sort_by: str = "date",         # "date", "citations", "relevance"
        status_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[List[Article], List[str], str]:
        """
        Execute search across arXiv, NASA ADS, and INSPIRE-HEP.
        Returns (merged_articles, errors_list, sources_summary_string).
        """
        articles: List[Article] = []
        errors: List[str] = []

        query_arxiv = source in ("arxiv", "both", "all")
        query_ads = source in ("ads", "both", "all")
        query_inspire = source in ("inspire", "both", "all")

        def notify(msg: str):
            if status_callback:
                status_callback(msg)

        # 1. Query arXiv
        if query_arxiv:
            notify("Buscando en arXiv API...")
            try:
                arxiv_q = self.arxiv_client.build_preset_query(
                    preset_type=preset_type,
                    custom_query=custom_query,
                    author=author,
                    start_year=start_year,
                    end_year=end_year
                )
                sort_order = "submittedDate" if sort_by == "date" else "relevance"
                arxiv_res = self.arxiv_client.search(
                    query=arxiv_q,
                    max_results=max_results,
                    sort_by=sort_order
                )
                articles.extend(arxiv_res)
            except Exception as e:
                errors.append(f"arXiv: {str(e)}")

        # 2. Query NASA ADS
        if query_ads:
            notify("Buscando en NASA ADS API...")
            if not self.ads_api_key:
                errors.append("NASA ADS: Se requiere configurar una API Key en Ajustes.")
            else:
                try:
                    ads_q = self.ads_client.build_preset_query(
                        preset_type=preset_type,
                        custom_query=custom_query,
                        author=author,
                        start_year=start_year,
                        end_year=end_year
                    )
                    ads_sort = "date desc"
                    if sort_by == "citations":
                        ads_sort = "citation_count desc"
                    elif sort_by == "relevance":
                        ads_sort = "score desc"

                    ads_res = self.ads_client.search(
                        query=ads_q,
                        rows=max_results,
                        sort=ads_sort
                    )
                    articles.extend(ads_res)
                except Exception as e:
                    errors.append(f"NASA ADS: {str(e)}")

        # 3. Query INSPIRE-HEP
        if query_inspire:
            notify("Buscando en INSPIRE-HEP API...")
            try:
                inspire_q = self.inspire_client.build_preset_query(
                    preset_type=preset_type,
                    custom_query=custom_query,
                    author=author,
                    start_year=start_year,
                    end_year=end_year
                )
                inspire_res = self.inspire_client.search(
                    query=inspire_q,
                    max_results=max_results,
                    sort_by=sort_by
                )
                articles.extend(inspire_res)
            except Exception as e:
                errors.append(f"INSPIRE-HEP: {str(e)}")

        notify("Procesando y consolidando resultados...")

        merged = self._deduplicate(articles)
        if start_year or end_year:
            merged = self._filter_by_year(merged, start_year, end_year)
        merged = self._sort_articles(merged, sort_by)

        sources_used = []
        if query_arxiv:
            sources_used.append("arXiv")
        if query_ads:
            sources_used.append("NASA ADS")
        if query_inspire:
            sources_used.append("INSPIRE-HEP")

        source_str = " + ".join(sources_used)
        return merged, errors, source_str

    def _deduplicate(self, articles: List[Article]) -> List[Article]:
        unique_map = {}
        source_tracker = {}

        for article in articles:
            key = None
            if article.arxiv_id:
                key = f"arxiv:{article.arxiv_id.split('v')[0].lower()}"
            elif article.bibcode:
                key = f"bibcode:{article.bibcode.lower()}"
            elif article.doi:
                key = f"doi:{article.doi.lower()}"
            elif article.inspire_id:
                key = f"inspire:{article.inspire_id}"
            else:
                key = f"title:{article.title.strip().lower()[:50]}"

            if key not in unique_map:
                unique_map[key] = article
                source_tracker[key] = {article.source}
            else:
                existing = unique_map[key]
                source_tracker[key].add(article.source)

                if article.citations > existing.citations:
                    existing.citations = article.citations
                if article.bibcode and not existing.bibcode:
                    existing.bibcode = article.bibcode
                if article.arxiv_id and not existing.arxiv_id:
                    existing.arxiv_id = article.arxiv_id
                if article.inspire_id and not existing.inspire_id:
                    existing.inspire_id = article.inspire_id
                if article.pdf_url and not existing.pdf_url:
                    existing.pdf_url = article.pdf_url
                if article.doi and not existing.doi:
                    existing.doi = article.doi
                if article.raw_bibtex and not existing.raw_bibtex:
                    existing.raw_bibtex = article.raw_bibtex

        for key, article in unique_map.items():
            sources = source_tracker[key]
            if len(sources) > 1:
                ordered_sources = []
                for s in ["arXiv", "NASA ADS", "INSPIRE-HEP"]:
                    if s in sources:
                        ordered_sources.append(s)
                article.source = " + ".join(ordered_sources)

        return list(unique_map.values())

    def _filter_by_year(self, articles: List[Article], start_year: Optional[int], end_year: Optional[int]) -> List[Article]:
        filtered = []
        for a in articles:
            if not a.pub_date or len(a.pub_date) < 4:
                filtered.append(a)
                continue
            try:
                year = int(a.pub_date[:4])
                if start_year and year < start_year:
                    continue
                if end_year and year > end_year:
                    continue
                filtered.append(a)
            except ValueError:
                filtered.append(a)
        return filtered

    def _sort_articles(self, articles: List[Article], sort_by: str) -> List[Article]:
        if sort_by == "citations":
            return sorted(articles, key=lambda x: x.citations, reverse=True)
        elif sort_by == "date":
            return sorted(articles, key=lambda x: x.pub_date or "", reverse=True)
        return articles
