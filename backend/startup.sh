#!/bin/bash

# BetaSense Backend Startup Script
# This script handles Solr setup, dependency installation, document indexing, and server startup

set -e  # Exit on any error

echo "🚀 Starting BetaSense Backend Setup..."
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if Docker is running
print_info "Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi
print_status "Docker is running"

# Check if Solr container exists and is running
print_info "Checking Solr container..."
if docker ps -q -f name=^solr$ | grep -q .; then
    print_status "Solr container is already running"
elif docker ps -aq -f name=^solr$ | grep -q .; then
    print_info "Starting existing Solr container..."
    docker start solr
    sleep 5
    print_status "Solr container started"
else
    print_info "Creating and starting Solr container..."
    docker run -d -p 8983:8983 --name solr solr:9
    sleep 10
    print_status "Solr container created and started"
fi

# Wait for Solr to be ready
print_info "Waiting for Solr to be ready..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s "http://localhost:8983/solr/admin/cores" > /dev/null 2>&1; then
        break
    fi
    echo -n "."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    print_error "Solr failed to start within 60 seconds"
    exit 1
fi
print_status "Solr is ready"

# Check if betasense_docs core exists
print_info "Checking Solr core..."
if curl -s "http://localhost:8983/solr/admin/cores" | grep -q "betasense_docs"; then
    print_status "betasense_docs core already exists"
    
    # Check document count in Solr
    SOLR_DOC_COUNT=$(curl -s "http://localhost:8983/solr/betasense_docs/select?q=*:*&rows=0" | grep -o '"numFound":[0-9]*' | cut -d: -f2 || echo "0")
    print_info "Current Solr document count: $SOLR_DOC_COUNT"
    
    # Count available PDF files
    PDF_COUNT=$(find ../data -name "*.pdf" 2>/dev/null | wc -l | tr -d ' ')
    print_info "Available PDF files: $PDF_COUNT"
    
    # If no documents indexed or PDF count changed significantly, suggest reindexing
    if [ "$SOLR_DOC_COUNT" -lt 10 ] || [ "$PDF_COUNT" -gt $((SOLR_DOC_COUNT / 10)) ]; then
        print_warning "Document counts suggest reindexing may be needed"
        NEED_INDEXING=true
    fi
else
    print_info "Creating betasense_docs core..."
    if docker exec solr solr create_core -c betasense_docs 2>/dev/null; then
        print_status "betasense_docs core created"
    else
        print_warning "Core creation failed (may already exist)"
    fi
    NEED_INDEXING=true
fi

# Check if virtual environment exists
print_info "Checking Python virtual environment..."
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_status "Virtual environment exists"
fi

# Activate virtual environment and install dependencies
print_info "Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1
print_status "Dependencies installed"

# Check if documents need indexing
print_info "Checking document indexing status..."

# Create index timestamp file if it doesn't exist
INDEX_TIMESTAMP_FILE=".last_index_time"
if [ ! -f "$INDEX_TIMESTAMP_FILE" ]; then
    echo "0" > "$INDEX_TIMESTAMP_FILE"
    NEED_INDEXING=true
    print_info "No previous indexing found"
else
    LAST_INDEX_TIME=$(cat "$INDEX_TIMESTAMP_FILE")
    print_info "Last indexing time: $(date -r $LAST_INDEX_TIME 2>/dev/null || echo 'Unknown')"
    
    # Check if any PDF files are newer than last index time
    if find ../data -name "*.pdf" -newer "$INDEX_TIMESTAMP_FILE" | grep -q .; then
        NEED_INDEXING=true
        print_warning "Found PDFs newer than last index time"
    else
        print_status "All documents are up to date"
    fi
fi

# Additional checks for ChromaDB
if [ ! -d "chroma_db" ]; then
    print_info "ChromaDB directory not found - will create during indexing"
    NEED_INDEXING=true
fi

# Check if both indices have documents
if [ "$NEED_INDEXING" = false ]; then
    # Check ChromaDB document count via Python
    CHROMA_DOC_COUNT=$(python3 -c "
import sys, os
sys.path.append('.')
try:
    from src.services.vector_service import VectorService
    vs = VectorService()
    print(vs.get_document_count())
except:
    print('0')
" 2>/dev/null || echo "0")
    
    print_info "Current ChromaDB document count: $CHROMA_DOC_COUNT"
    
    # If either index is empty, reindex
    if [ "$SOLR_DOC_COUNT" -eq 0 ] || [ "$CHROMA_DOC_COUNT" -eq 0 ]; then
        print_warning "One or both search indices are empty - reindexing needed"
        NEED_INDEXING=true
    fi
fi

# Index documents if needed
if [ "$NEED_INDEXING" = true ]; then
    print_info "Starting document indexing..."
    python -m src.services.indexing_service
    
    if [ $? -eq 0 ]; then
        # Update timestamp
        date +%s > "$INDEX_TIMESTAMP_FILE"
        print_status "Document indexing completed successfully"
    else
        print_error "Document indexing failed"
        exit 1
    fi
else
    print_status "Skipping indexing - documents are up to date"
fi

# Get indexing statistics
print_info "Getting system status..."
python3 -c "
import sys
sys.path.append('.')
from src.services.indexing_service import IndexingService
indexing_service = IndexingService()
stats = indexing_service.get_index_stats()
print(f'📊 System Statistics:')
print(f'   • Available PDFs: {stats[\"available_pdfs\"]}')
print(f'   • Solr documents: {stats[\"solr_document_count\"]}')
print(f'   • Vector documents: {stats[\"vector_document_count\"]}')
print(f'   • Categories: {list(stats[\"pdf_categories\"].keys())}')
"

# Start the FastAPI server
print_info "Starting BetaSense Backend Server..."
echo "========================================"
print_status "Backend will be available at: http://localhost:8000"
print_status "API documentation at: http://localhost:8000/docs"
print_status "Solr admin at: http://localhost:8983/solr"
echo ""
print_info "Press Ctrl+C to stop the server"
echo ""

# Start the server
uvicorn src.main:app --reload --port 8000