from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, List
import asyncio
import os
from dotenv import load_dotenv
from src.services.websearch_service import WebSearchService
from src.services.llm_service import LLMService
from src.services.hybrid_search_service import HybridSearchService
from src.services.indexing_service import IndexingService
from src.services.comprehensive_report_service import ComprehensiveReportService
from src.constants import LLMModel

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
comprehensive_report_service = ComprehensiveReportService()

class QueryRequest(BaseModel):
    question: str
    sources: Dict[str, Any]
    enable_web_search: bool = False

class ReportRequest(BaseModel):
    topic: str
    sources: Dict[str, Any]
    enable_web_search: bool = False
    domain_context: str = "financial analysis"

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


@app.post("/api/report-structure")
async def generate_report_structure(request: ReportRequest):
    """Generate report structure and research plan (preview mode)"""
    print(f"Report structure request: {request.topic}")
    try:
        # Generate structure and research plan only
        report_structure = comprehensive_report_service.structure_service.generate_report_structure(
            request.topic, request.domain_context
        )
        research_plan = comprehensive_report_service.research_service.generate_research_plan(
            report_structure
        )
        
        return {
            "success": True,
            "structure": report_structure.to_dict(),
            "research_plan": {
                "topic": research_plan.topic,
                "search_strategy": research_plan.search_strategy,
                "research_queries": [
                    {
                        "section_title": rq.section_title,
                        "search_queries": rq.search_queries,
                        "key_concepts": rq.key_concepts,
                        "search_priority": rq.search_priority
                    }
                    for rq in research_plan.research_queries
                ]
            }
        }
        
    except Exception as e:
        print(f"Error generating report structure: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating structure: {str(e)}")

@app.post("/api/comprehensive-report")
async def generate_comprehensive_report(request: ReportRequest):
    """Generate a comprehensive structured report based on research plan"""
    print(f"Comprehensive report request: {request.topic}")
    try:
        report_content = await comprehensive_report_service.generate_comprehensive_report(
            topic=request.topic,
            sources=request.sources,
            enable_web_search=request.enable_web_search,
            domain_context=request.domain_context
        )
        
        return {
            "success": True,
            "report": report_content.to_dict()
        }
        
    except Exception as e:
        print(f"Error generating comprehensive report: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

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
        
        # Always search local documents first - get top 10 from each engine
        filters = map_source_selection_to_filters(request.sources)
        print(f"Source filters: categories={filters['categories']}, subcategories={filters['subcategories']}")
        
        local_results = hybrid_search_service.search_documents_expanded(
            query=request.question,
            categories=filters['categories'] if filters['categories'] else None,
            subcategories=filters['subcategories'] if filters['subcategories'] else None,
            keyword_count=10,
            vector_count=10
        )
        
        # Prepare local context from all deduplicated results
        local_context = ""
        if local_results:
            # Use all chunks after deduplication (no artificial limit)
            local_context = "\n\n".join([
                f"Source: {result['source_file']} (Score: {result['combined_score']:.3f}, Type: {result['search_type']})\n{result['text']}"
                for result in local_results
            ])
            
            # Include all sources in response metadata
            response_data["sources_used"] = [
                {
                    "file": result['source_file'], 
                    "score": result['combined_score'],
                    "search_type": result['search_type'],
                    "chunk_id": result['chunk_id']
                }
                for result in local_results
            ]
        
        # If web search is enabled, also perform web search
        if request.enable_web_search:
            web_results = await websearch_service.search_and_scrape_web(request.question)
            response_data["web_results"] = web_results
            
            # Combine local and web context
            if web_results or local_results:
                enhanced_answer = await websearch_service.enhance_query_with_combined_context(
                    request.question, 
                    local_context,
                    web_results
                )
                response_data["answer"] = enhanced_answer
            else:
                # Fallback to basic Claude response
                system_prompt = "You are a financial AI assistant. Answer the user's question accurately and professionally."
                basic_answer = llm_service.execute_prompt(system_prompt, request.question)
                response_data["answer"] = basic_answer or "I couldn't generate a response to your question."
        else:
            # Use only local document search
            if local_results:
                system_prompt = """You are a financial AI assistant analyzing documents. Answer the user's question based on the provided document excerpts. Always cite your sources."""
                
                user_prompt = f"""Question: {request.question}

Relevant document excerpts:
{local_context}

Please provide a comprehensive answer based on these documents."""
                
                local_answer = llm_service.execute_prompt(system_prompt, user_prompt)
                response_data["answer"] = local_answer or "I couldn't generate a response based on the documents."
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

@app.get("/api/pdf/{filename:path}")
async def serve_pdf(filename: str):
    """Serve PDF files for citation links"""
    try:
        # Construct the data directory path (one level up)
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        data_dir_abs = os.path.abspath(data_dir)
        
        # First try direct path (in case filename includes subdirectory)
        pdf_path = os.path.join(data_dir, filename)
        full_path = os.path.abspath(pdf_path)
        
        # Security check - ensure the file is within the data directory
        if not full_path.startswith(data_dir_abs):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # If direct path exists, return it
        if os.path.exists(full_path):
            return FileResponse(
                full_path,
                media_type="application/pdf",
                headers={"Content-Disposition": f"inline; filename={os.path.basename(filename)}"}
            )
        
        # If direct path doesn't exist, search recursively for the filename
        import glob
        search_pattern = os.path.join(data_dir, "**", os.path.basename(filename))
        matches = glob.glob(search_pattern, recursive=True)
        
        if matches:
            # Use the first match found
            found_path = matches[0]
            # Double-check security constraint
            found_path_abs = os.path.abspath(found_path)
            if not found_path_abs.startswith(data_dir_abs):
                raise HTTPException(status_code=403, detail="Access denied")
            
            return FileResponse(
                found_path,
                media_type="application/pdf",
                headers={"Content-Disposition": f"inline; filename={os.path.basename(filename)}"}
            )
        
        # File not found anywhere
        raise HTTPException(status_code=404, detail="PDF not found")
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"Error serving PDF: {e}")
        raise HTTPException(status_code=500, detail="Error serving PDF")

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