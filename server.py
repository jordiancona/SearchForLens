from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from src.api.service import SearchService

app = FastAPI(
    title="SearchForLens REST API",
    description="Backend API for Strong Gravitational Lensing research across arXiv, NASA ADS & INSPIRE-HEP",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

search_service = SearchService()

@app.get("/")
def read_root():
    return {"status": "online", "app": "SearchForLens API"}

@app.get("/api/search")
def search_articles(
    preset_type: str = Query("strong_lensing", description="Preset query type: strong_lensing, ai_lensing, custom"),
    custom_query: str = Query("", description="Custom search query string"),
    author: str = Query("", description="Author name filter"),
    start_year: Optional[int] = Query(None, description="Start publication year"),
    end_year: Optional[int] = Query(None, description="End publication year"),
    source: str = Query("all", description="Data source: all, arxiv, ads, inspire, both"),
    ads_api_key: str = Query("", description="NASA ADS API Key"),
    max_results: int = Query(50, description="Max results limit"),
    sort_by: str = Query("date", description="Sort order: date, citations, relevance")
):
    try:
        service = SearchService(ads_api_key=ads_api_key)
        articles, errors, source_summary = service.execute_search(
            preset_type=preset_type,
            custom_query=custom_query,
            author=author,
            start_year=start_year,
            end_year=end_year,
            source=source,
            max_results=max_results,
            sort_by=sort_by
        )
        return {
            "articles": [a.to_dict() for a in articles],
            "errors": errors,
            "source_summary": source_summary,
            "total": len(articles)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
