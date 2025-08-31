from .pdf_service import PDFService
from .solr_service import SolrService
from .vector_service import VectorService
from typing import List, Dict, Any
import time


class IndexingService:
    def __init__(self, data_directory: str = "../data"):
        self.pdf_service = PDFService(data_directory)
        self.solr_service = SolrService()
        self.vector_service = VectorService()
        
    def check_services(self) -> Dict[str, bool]:
        """Check if all services are ready"""
        return {
            'solr': self.solr_service.test_connection(),
            'chromadb': True,  # ChromaDB is always available locally
            'data_directory_exists': len(self.pdf_service.get_all_pdfs()) > 0
        }
    
    def index_all_documents(self, clear_existing: bool = False) -> Dict[str, Any]:
        """Index all PDF documents to both Solr and ChromaDB"""
        
        start_time = time.time()
        results = {
            'total_pdfs': 0,
            'total_chunks': 0,
            'solr_indexed': 0,
            'vector_indexed': 0,
            'errors': [],
            'processing_time': 0
        }
        
        try:
            # Clear existing indices if requested
            if clear_existing:
                print("Clearing existing indices...")
                self.solr_service.clear_index()
                self.vector_service.clear_collection()
            
            # Process all PDFs
            print("Processing PDF documents...")
            all_chunks = self.pdf_service.process_all_pdfs()
            
            results['total_pdfs'] = len(self.pdf_service.get_all_pdfs())
            results['total_chunks'] = len(all_chunks)
            
            if not all_chunks:
                results['errors'].append("No PDF documents found or processed")
                return results
            
            print(f"Found {len(all_chunks)} chunks from {results['total_pdfs']} PDFs")
            
            # Index to Solr
            print("Indexing to Solr...")
            solr_count = self.solr_service.index_documents_batch(all_chunks)
            results['solr_indexed'] = solr_count
            
            # Index to ChromaDB
            print("Indexing to ChromaDB (this may take a while for embeddings)...")
            vector_count = self.vector_service.add_documents_batch(all_chunks)
            results['vector_indexed'] = vector_count
            
            results['processing_time'] = time.time() - start_time
            
            print(f"Indexing completed in {results['processing_time']:.2f} seconds")
            print(f"Solr: {solr_count} documents, ChromaDB: {vector_count} documents")
            
        except Exception as e:
            results['errors'].append(str(e))
            print(f"Error during indexing: {e}")
        
        return results
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about current indices"""
        return {
            'services_status': self.check_services(),
            'solr_document_count': self.solr_service.get_document_count(),
            'vector_document_count': self.vector_service.get_document_count(),
            'available_pdfs': len(self.pdf_service.get_all_pdfs()),
            'pdf_categories': self._get_pdf_categories()
        }
    
    def _get_pdf_categories(self) -> Dict[str, int]:
        """Get count of PDFs by category"""
        pdfs = self.pdf_service.get_all_pdfs()
        categories = {}
        
        for pdf in pdfs:
            category = pdf['category']
            if category in categories:
                categories[category] += 1
            else:
                categories[category] = 1
        
        return categories


def main():
    """Main function for running indexing from command line"""
    print("Starting document indexing process...")
    
    indexing_service = IndexingService()
    
    # Check services
    print("Checking services...")
    status = indexing_service.check_services()
    print(f"Service status: {status}")
    
    if not status['solr']:
        print("ERROR: Solr is not running. Please start Solr with:")
        print("docker run -d -p 8983:8983 --name solr solr:9")
        print("docker exec -it solr solr create_collection -c betasense_docs")
        return
    
    if not status['data_directory_exists']:
        print("ERROR: No PDF files found in data directory")
        return
    
    # Start indexing
    print("Starting indexing process...")
    results = indexing_service.index_all_documents(clear_existing=True)
    
    print("\n" + "="*50)
    print("INDEXING RESULTS")
    print("="*50)
    print(f"Total PDFs processed: {results['total_pdfs']}")
    print(f"Total chunks created: {results['total_chunks']}")
    print(f"Solr documents indexed: {results['solr_indexed']}")
    print(f"Vector documents indexed: {results['vector_indexed']}")
    print(f"Processing time: {results['processing_time']:.2f} seconds")
    
    if results['errors']:
        print(f"Errors encountered: {results['errors']}")
    
    # Show final stats
    print("\n" + "="*50)
    print("FINAL INDEX STATISTICS")
    print("="*50)
    stats = indexing_service.get_index_stats()
    print(f"Solr document count: {stats['solr_document_count']}")
    print(f"Vector document count: {stats['vector_document_count']}")
    print(f"PDF categories: {stats['pdf_categories']}")
    

if __name__ == "__main__":
    main()