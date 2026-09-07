import time
import requests
import feedparser
import re
from typing import List, Optional
from src.api.models import Article

ARXIV_API_URLS = [
    "https://export.arxiv.org/api/query",
    "https://api.arxiv.org/query",
    "http://export.arxiv.org/api/query",
]

class ArxivClient:
    """Client for fetching papers from arXiv API."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def build_preset_query(self, preset_type: str, custom_query: str = "", author: str = "", start_year: Optional[int] = None, end_year: Optional[int] = None) -> str:
        """Construct arXiv API search_query string."""
        terms = []

        if preset_type == "strong_lensing":
            base_q = '(ti:"strong gravitational lensing" OR abs:"strong gravitational lensing" OR ti:"strong lensing" OR abs:"strong lensing")'
            terms.append(base_q)
        elif preset_type == "ai_lensing":
            lens_q = '(ti:"gravitational lensing" OR abs:"gravitational lensing" OR ti:"strong lensing" OR abs:"strong lensing")'
            ai_q = '(abs:"machine learning" OR abs:"deep learning" OR abs:"neural network" OR abs:"convolutional" OR abs:"transformer" OR abs:"artificial intelligence" OR abs:"surrogate model")'
            terms.append(f'{lens_q} AND {ai_q}')
        else:
            # Custom search query
            if custom_query.strip():
                # Wrap custom query terms safely
                q_clean = custom_query.strip()
                terms.append(f'(all:"{q_clean}" OR ti:"{q_clean}" OR abs:"{q_clean}")')

        if author.strip():
            terms.append(f'au:"{author.strip()}"')

        # Combine with AND
        query_str = " AND ".join(terms) if terms else 'all:"gravitational lensing"'

        # Category filter for astronomy/astrophysics and ML if desired
        full_query = f'cat:astro-ph* AND {query_str}'
        return full_query

    def search(
        self,
        query: str,
        max_results: int = 50,
        start_index: int = 0,
        sort_by: str = "submittedDate",  # "submittedDate", "relevance", "lastUpdatedDate"
        sort_order: str = "descending"   # "descending", "ascending"
    ) -> List[Article]:
        """Perform search request to arXiv API and return list of Article instances."""
        params = {
            "search_query": query,
            "start": start_index,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }

        headers = {
            "User-Agent": "SearchForLens/1.0 (mailto:researcher@searchforlens.org)"
        }

        last_error = None
        for url in ARXIV_API_URLS:
            for attempt in range(2):
                try:
                    resp = requests.get(url, params=params, headers=headers, timeout=self.timeout)
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.content)

                    articles = []
                    for entry in feed.entries:
                        article = self._parse_entry(entry)
                        if article:
                            articles.append(article)
                    return articles
                except Exception as e:
                    last_error = e
                    print(f"arXiv attempt {attempt + 1} on {url} failed: {e}")
                    time.sleep(1)

        print(f"Error fetching arXiv data after retries: {last_error}")
        return []

    def _parse_entry(self, entry) -> Optional[Article]:
        """Parse feedparser entry into an Article object."""
        try:
            raw_id = entry.id
            # Extract clean arXiv ID e.g., 2305.12345 or astro-ph/0501234
            arxiv_id_match = re.search(r'arxiv\.org/abs/([^/]+(?:v\d+)?)$', raw_id, re.IGNORECASE)
            arxiv_id = arxiv_id_match.group(1) if arxiv_id_match else raw_id.split('/')[-1]

            title = entry.title.replace('\n', ' ').strip()
            # Clean title multiple spaces
            title = re.sub(r'\s+', ' ', title)

            abstract = entry.summary.replace('\n', ' ').strip()
            abstract = re.sub(r'\s+', ' ', abstract)

            authors = [author.name for author in entry.get('authors', [])]
            if not authors and 'author' in entry:
                authors = [entry.author]

            pub_date = entry.published[:10] if 'published' in entry else ""

            # Extract links (web & pdf)
            url = f"https://arxiv.org/abs/{arxiv_id}"
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            doi = entry.get('arxiv_doi', None)

            # Check links list for explicit pdf
            for link in entry.get('links', []):
                if link.get('title') == 'pdf' or link.get('type') == 'application/pdf':
                    pdf_url = link.get('href', pdf_url)
                if link.get('rel') == 'alternate':
                    url = link.get('href', url)

            journal = entry.get('arxiv_journal_ref', 'arXiv preprint')

            return Article(
                id=f"arxiv_{arxiv_id}",
                title=title,
                authors=authors,
                abstract=abstract,
                pub_date=pub_date,
                source="arXiv",
                arxiv_id=arxiv_id,
                doi=doi,
                pdf_url=pdf_url,
                url=url,
                citations=0,
                journal=journal
            )
        except Exception as err:
            print(f"Error parsing arXiv entry: {err}")
            return None
