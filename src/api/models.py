from dataclasses import dataclass, field
from typing import List, Optional
import json

@dataclass
class Article:
    """Unified article representation across arXiv and NASA ADS APIs."""
    id: str
    title: str
    authors: List[str]
    abstract: str
    pub_date: str  # YYYY-MM-DD or YYYY
    source: str    # "arXiv", "NASA ADS", or "Both"
    arxiv_id: Optional[str] = None
    bibcode: Optional[str] = None
    inspire_id: Optional[str] = None
    doi: Optional[str] = None
    pdf_url: Optional[str] = None
    url: Optional[str] = None
    citations: int = 0
    journal: Optional[str] = None
    raw_bibtex: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "pub_date": self.pub_date,
            "source": self.source,
            "arxiv_id": self.arxiv_id,
            "bibcode": self.bibcode,
            "inspire_id": self.inspire_id,
            "doi": self.doi,
            "pdf_url": self.pdf_url,
            "url": self.url,
            "citations": self.citations,
            "journal": self.journal,
            "raw_bibtex": self.raw_bibtex,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            abstract=data.get("abstract", ""),
            pub_date=data.get("pub_date", ""),
            source=data.get("source", "Unknown"),
            arxiv_id=data.get("arxiv_id"),
            bibcode=data.get("bibcode"),
            inspire_id=data.get("inspire_id"),
            doi=data.get("doi"),
            pdf_url=data.get("pdf_url"),
            url=data.get("url"),
            citations=data.get("citations", 0),
            journal=data.get("journal"),
            raw_bibtex=data.get("raw_bibtex"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Article":
        return cls.from_dict(json.loads(json_str))

    def generate_bibtex(self) -> str:
        """Generate standard BibTeX string if raw_bibtex is not available."""
        if self.raw_bibtex:
            return self.raw_bibtex
        
        # Create citation key
        first_author = self.authors[0].split()[-1] if self.authors else "Unknown"
        year = self.pub_date[:4] if len(self.pub_date) >= 4 else "2026"
        key = f"{first_author}{year}{self.id.replace('/', '_').replace('.', '_')}"
        
        authors_str = " and ".join(self.authors)
        bib = f"@article{{{key},\n"
        bib += f"  title = {{{self.title}}},\n"
        bib += f"  author = {{{authors_str}}},\n"
        bib += f"  year = {{{year}}},\n"
        if self.journal:
            bib += f"  journal = {{{self.journal}}},\n"
        if self.eprint_or_arxiv():
            bib += f"  eprint = {{{self.arxiv_id}}},\n"
            bib += f"  archivePrefix = {{arXiv}},\n"
        if self.doi:
            bib += f"  doi = {{{self.doi}}},\n"
        if self.url:
            bib += f"  url = {{{self.url}}},\n"
        bib += "}"
        return bib

    def eprint_or_arxiv(self) -> Optional[str]:
        return self.arxiv_id
