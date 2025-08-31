# BetaSense

A hybrid search system for financial documents using keyword + vector search with Claude 4 Sonnet integration.

## Features

- **Hybrid Search**: Combines Solr (keyword) + ChromaDB (vector) search
- **Source Filtering**: Filter by broker research, company docs, and subcategories  
- **Web Search**: Optional web search integration
- **Claude 4 Sonnet**: AI-powered document analysis and Q&A
- **React Frontend**: Clean interface for document queries

## Quick Setup

### 1. Add Documents
Place your PDFs in the `data/` directory:
```
data/
├── broker_research/
│   ├── jefferies_research/
│   └── ubs_research/
└── company_docs/
    ├── presentations/
    ├── major_filings/
    └── event_transcripts/
```

### 2. Configure AWS Credentials
Create `backend/.env` with your AWS Bedrock credentials:
```bash
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_SESSION_TOKEN=your_aws_session_token  # If using temporary credentials
```

**Required AWS Permissions:**
- `bedrock:InvokeModel` for Claude 4 Sonnet
- Access to model: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- Region: `us-west-2`

### 3. Start Backend
```bash
cd backend
./startup.sh
```

The startup script automatically:
- Starts Docker + Solr
- Sets up Python environment 
- Installs dependencies
- Indexes your documents
- Launches the API server on port 8000

### 4. Start Frontend
```bash
cd frontend
npm install
npm start
```

Frontend launches on http://localhost:3000

## Usage

1. **Add Documents**: Drop PDFs into appropriate `data/` subdirectories
2. **Query**: Use the web interface to ask questions about your documents
3. **Filter Sources**: Select specific document categories and subcategories
4. **Web Search**: Toggle web search for external information

## Requirements

- **Docker**: For Solr search engine
- **Python 3.8+**: For backend services
- **Node.js**: For React frontend
- **AWS Account**: With Bedrock access for Claude 4 Sonnet

## API Endpoints

- `POST /api/query` - Query documents
- `GET /api/status` - System health check
- `POST /api/reindex` - Force document reindexing

## Architecture

- **Backend**: FastAPI + hybrid search (Solr + ChromaDB)
- **Frontend**: React with source filtering
- **AI**: Claude 4 Sonnet via AWS Bedrock
- **Search**: 60% keyword, 40% vector weighted scoring