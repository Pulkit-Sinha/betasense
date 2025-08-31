from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
import asyncio
import os
from dotenv import load_dotenv
from services.websearch_service import WebSearchService
from services.llm_service import LLMService
from services.hybrid_search_service import HybridSearchService
from services.indexing_service import IndexingService
from constants import LLMModel

# Load environment variables
load_dotenv()

app = FastAPI()

@app.middleware("http")
async def log_requests(request, call_next):
    print(f"Request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")
    response = await call_next(request)
    print(f"Response status: {response.status_code}")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
websearch_service = WebSearchService()
llm_service = LLMService()
hybrid_search_service = HybridSearchService()
indexing_service = IndexingService()

class QueryRequest(BaseModel):
    question: str
    sources: Dict[str, Any]
    enable_web_search: bool = False

def map_source_selection_to_filters(sources: Dict[str, Any]) -> Dict[str, List[str]]:
    """Convert frontend source selection to search filters"""
    categories = []
    subcategories = []
    
    for category, config in sources.items():
        if config.get('enabled', False):
            if category == 'brokerResearch':
                categories.append('broker_research')
                for sub, enabled in config.get('subcategories', {}).items():
                    if enabled:
                        subcategories.append(sub)
            elif category == 'companyDocs':
                categories.append('company_docs')
                for sub, enabled in config.get('subcategories', {}).items():
                    if enabled:
                        subcategories.append(sub)
    
    return {'categories': categories, 'subcategories': subcategories}

@app.get("/")
def read_root():
    return {"message": "BetaSense Backend API"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from FastAPI!"}


@app.post("/api/query")
async def query_documents(request: QueryRequest):
    print(f"POST request received: {request.question[:50]}...")
    print(f"Web search enabled: {request.enable_web_search}")
    try:
        response_data = {
            "answer": "",
            "sources_used": [],
            "web_results": []
        }
        
        # If web search is enabled, perform web search first
        if request.enable_web_search:
            web_results = await websearch_service.search_web(request.question)
            response_data["web_results"] = web_results
            
            if web_results:
                # Enhance query with web context
                enhanced_answer = await websearch_service.enhance_query_with_web_context(
                    request.question, 
                    web_results
                )
                response_data["answer"] = enhanced_answer
            else:
                # Fallback to basic Claude response
                system_prompt = "You are a financial AI assistant. Answer the user's question accurately and professionally."
                basic_answer = llm_service.execute_prompt(system_prompt, request.question)
                response_data["answer"] = basic_answer or "I couldn't generate a response to your question."
        else:
            # Use local document search with source filtering
            filters = map_source_selection_to_filters(request.sources)
            print(f"Source filters: categories={filters['categories']}, subcategories={filters['subcategories']}")
            
            local_results = hybrid_search_service.search_documents(
                query=request.question,
                categories=filters['categories'] if filters['categories'] else None,
                subcategories=filters['subcategories'] if filters['subcategories'] else None,
                max_results=5
            )
            
            if local_results:
                # Prepare context from search results
                context = "\n\n".join([
                    f"Source: {result['source_file']}\n{result['text']}"
                    for result in local_results[:3]
                ])
                
                system_prompt = """You are a financial AI assistant analyzing documents. Answer the user's question based on the provided document excerpts. Always cite your sources."""
                
                user_prompt = f"""Question: {request.question}

Relevant document excerpts:
{context}

Please provide a comprehensive answer based on these documents."""
                
                local_answer = llm_service.execute_prompt(system_prompt, user_prompt)
                response_data["answer"] = local_answer or "I couldn't generate a response based on the documents."
                response_data["sources_used"] = [
                    {"file": result['source_file'], "score": result['combined_score']}
                    for result in local_results[:3]
                ]
            else:
                response_data["answer"] = "I couldn't find relevant information in the local documents."
        
        return response_data
        
    except Exception as e:
        print(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/status")
async def get_status():
    """Get system status and indexing statistics"""
    try:
        stats = indexing_service.get_index_stats()
        search_stats = hybrid_search_service.get_search_stats()
        
        return {
            "system_status": "online",
            "indexing_stats": stats,
            "search_stats": search_stats
        }
    except Exception as e:
        print(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail="Error getting system status")

@app.post("/api/reindex")
async def reindex_documents():
    """Trigger document reindexing"""
    try:
        results = indexing_service.index_all_documents(clear_existing=True)
        return {
            "status": "completed" if not results['errors'] else "completed_with_errors",
            "results": results
        }
    except Exception as e:
        print(f"Error reindexing documents: {e}")
        raise HTTPException(status_code=500, detail="Error reindexing documents")

@app.post("/api/search_test")
async def test_search_filtering(request: QueryRequest):
    """Test search filtering without LLM processing"""
    try:
        filters = map_source_selection_to_filters(request.sources)
        
        local_results = hybrid_search_service.search_documents(
            query=request.question,
            categories=filters['categories'] if filters['categories'] else None,
            subcategories=filters['subcategories'] if filters['subcategories'] else None,
            max_results=10
        )
        
        return {
            "query": request.question,
            "filters_applied": filters,
            "results_count": len(local_results),
            "results": local_results[:5]  # Return first 5 for testing
        }
    except Exception as e:
        print(f"Error in search test: {e}")
        raise HTTPException(status_code=500, detail="Error testing search")