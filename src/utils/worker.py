from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Optional, Set
from src.api.models import Article
from src.api.arxiv_client import ArxivClient
from src.api.ads_client import AdsClient
from src.api.inspire_client import InspireClient
from src.api.service import SearchService

class SearchWorker(QThread):
    """Worker thread for non-blocking execution of arXiv, NASA ADS, and INSPIRE-HEP search queries."""

    # Signals
    status_updated = pyqtSignal(str)              # Status message e.g. "Buscando en arXiv..."
    results_ready = pyqtSignal(list, str)         # (List[Article], source_summary)
    error_occurred = pyqtSignal(str)              # Error description message

    def __init__(
        self,
        preset_type: str,
        custom_query: str,
        author: str,
        start_year: Optional[int],
        end_year: Optional[int],
        source: str,            # "all", "arxiv", "ads", "inspire", or "both"
        ads_api_key: str,
        max_results: int = 50,
        sort_by: str = "date"   # "date", "citations", "relevance"
    ):
        super().__init__()
        self.preset_type = preset_type
        self.custom_query = custom_query
        self.author = author
        self.start_year = start_year
        self.end_year = end_year
        self.source = source
        self.ads_api_key = ads_api_key
        self.max_results = max_results
        self.sort_by = sort_by

        self.service = SearchService(ads_api_key=self.ads_api_key)

    def run(self):
        merged_articles, errors, source_str = self.service.execute_search(
            preset_type=self.preset_type,
            custom_query=self.custom_query,
            author=self.author,
            start_year=self.start_year,
            end_year=self.end_year,
            source=self.source,
            max_results=self.max_results,
            sort_by=self.sort_by,
            status_callback=lambda msg: self.status_updated.emit(msg)
        )

        if errors and not merged_articles:
            self.error_occurred.emit("\n".join(errors))
        else:
            self.results_ready.emit(merged_articles, source_str)

    def _deduplicate(self, articles: List[Article]) -> List[Article]:
        """Merge identical articles from arXiv, ADS, & INSPIRE-HEP into unified records."""
        unique_map = {}
        source_tracker = {}

        for article in articles:
            # Create a key derived from arXiv ID, Bibcode, DOI, or Title
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

                # Merge highest citation count
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

        # Consolidate source badges
        for key, article in unique_map.items():
            sources = source_tracker[key]
            if len(sources) > 1:
                # Custom ordering: arXiv, NASA ADS, INSPIRE-HEP
                ordered_sources = []
                for s in ["arXiv", "NASA ADS", "INSPIRE-HEP"]:
                    if s in sources:
                        ordered_sources.append(s)
                article.source = " + ".join(ordered_sources)

        return list(unique_map.values())

    def _filter_by_year(self, articles: List[Article]) -> List[Article]:
        filtered = []
        for a in articles:
            if not a.pub_date or len(a.pub_date) < 4:
                filtered.append(a)
                continue
            try:
                year = int(a.pub_date[:4])
                if self.start_year and year < self.start_year:
                    continue
                if self.end_year and year > self.end_year:
                    continue
                filtered.append(a)
            except ValueError:
                filtered.append(a)
        return filtered

    def _sort_articles(self, articles: List[Article]) -> List[Article]:
        if self.sort_by == "citations":
            return sorted(articles, key=lambda x: x.citations, reverse=True)
        elif self.sort_by == "date":
            return sorted(articles, key=lambda x: x.pub_date or "", reverse=True)
        return articles
