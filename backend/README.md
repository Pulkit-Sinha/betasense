# BetaSense Backend

A hybrid search system for financial documents using Solr (keyword search) + ChromaDB (vector search) with Claude 4 Sonnet integration.

## Quick Start

```bash
./startup.sh
```

This single command will:
- ✅ Check and start Docker + Solr
- ✅ Create Solr collection
- ✅ Set up Python environment
- ✅ Install dependencies
- ✅ Check for document changes
- ✅ Index documents if needed
- ✅ Start the backend server

## Manual Setup

If you prefer manual setup:

### 1. Start Solr
```bash
docker run -d -p 8983:8983 --name solr solr:9
docker exec -it solr solr create_collection -c betasense_docs
```

### 2. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Index Documents
```bash
python -m services.indexing_service
```

### 4. Start Server
```bash
uvicorn main:app --reload --port 8000
```

## API Endpoints

### Core Endpoints
- `POST /api/query` - Query documents with optional web search
- `GET /api/status` - System health and indexing stats
- `POST /api/reindex` - Trigger document reindexing

### Query Format
```json
{
  "question": "What is Jio Financial's revenue?",
  "sources": {
    "brokerResearch": {"enabled": true},
    "companyDocs": {"enabled": true}
  },
  "enable_web_search": false
}
```

### Response Format
```json
{
  "answer": "Based on the documents...",
  "sources_used": [
    {"file": "document.pdf", "score": 0.95}
  ],
  "web_results": []
}
```

## Architecture

### Hybrid Search System
- **Solr**: Keyword search for financial terms, company names, dates
- **ChromaDB**: Vector search for semantic/conceptual queries
- **Weighted Scoring**: Combines both results (60% keyword, 40% vector)

### Document Processing
- **PDF Extraction**: Text extraction from all PDFs in `/data`
- **Chunking**: Documents split into 1000-char chunks with 200-char overlap
- **Metadata**: Category, subcategory, source file tracking

### Services Architecture
```
services/
├── pdf_service.py          # PDF text extraction & chunking
├── solr_service.py         # Keyword search via Solr
├── vector_service.py       # Vector search via ChromaDB
├── hybrid_search_service.py # Combines both searches
├── llm_service.py          # Claude 4 Sonnet integration
└── websearch_service.py    # Web search functionality
```

## Data Structure

Your PDFs should be organized like:
```
data/
├── broker_research/
│   ├── jefferies_research/
│   ├── ubs_research/
│   └── ...
└── company_docs/
    ├── presentations/
    ├── major_filings/
    └── event_transcripts/
```

## Configuration

### Environment Variables (.env)
```bash
ENABLE_LLM_SERVICE=true
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_SESSION_TOKEN=your_aws_session_token
```

### Document Change Detection
The system automatically detects when PDFs have been modified and triggers reindexing:
- Creates `.last_index_time` timestamp file
- Compares PDF modification times
- Only reindexes if documents are newer

## Monitoring

### System Status
```bash
curl http://localhost:8000/api/status
```

### Solr Admin Interface
http://localhost:8983/solr

### API Documentation
http://localhost:8000/docs

## Troubleshooting

### Common Issues

**Solr not starting:**
```bash
docker ps -a  # Check container status
docker logs solr  # Check logs
```

**ChromaDB issues:**
```bash
rm -rf chroma_db/  # Reset vector database
python indexing_service.py  # Reindex
```

**AWS/Bedrock errors:**
- Check your AWS credentials in `.env`
- Ensure you have Bedrock access permissions
- Verify the correct region (us-west-2)

**No search results:**
```bash
curl http://localhost:8000/api/status  # Check document counts
curl -X POST http://localhost:8000/api/reindex  # Force reindex
```

## Development

### Adding New Document Sources
1. Update source categories in frontend
2. Modify PDF processing logic in `pdf_service.py`
3. Update search filters in query endpoint

### Tuning Search Relevance
Adjust weights in `hybrid_search_service.py`:
```python
# Current: 60% keyword, 40% vector
keyword_weight: float = 0.6
vector_weight: float = 0.4
```

### Adding New LLM Models
Update `constants.py` and `llm_service.py` to support additional models.