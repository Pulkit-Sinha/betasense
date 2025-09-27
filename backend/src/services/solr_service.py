import pysolr
from typing import List, Dict, Any, Optional
import json


class SolrService:
    def __init__(self, solr_url: str = "http://localhost:8983/solr/betasense_docs"):
        self.solr = pysolr.Solr(solr_url, always_commit=True, timeout=10)
        
    def test_connection(self) -> bool:
        """Test if Solr is accessible"""
        try:
            self.solr.ping()
            return True
        except Exception as e:
            print(f"Solr connection failed: {e}")
            return False
    
    def index_document(self, doc_data: Dict[str, Any]) -> bool:
        """Index a single document in Solr"""
        try:
            # Prepare document for Solr
            solr_doc = {
                'id': doc_data['chunk_id'],
                'text': doc_data['text'],
                'source_file': doc_data['source_file'],
                'category': doc_data['category'],
                'subcategory': doc_data['subcategory'],
                'chunk_index': doc_data['chunk_index'],
                'total_chunks': doc_data['total_chunks']
            }
            
            self.solr.add([solr_doc])
            return True
        except Exception as e:
            print(f"Error indexing document {doc_data['chunk_id']}: {e}")
            return False
    
    def index_documents_batch(self, documents: List[Dict[str, Any]]) -> int:
        """Index multiple documents in batch"""
        try:
            solr_docs = []
            for doc_data in documents:
                solr_doc = {
                    'id': doc_data['chunk_id'],
                    'text': doc_data['text'],
                    'source_file': doc_data['source_file'],
                    'category': doc_data['category'],
                    'subcategory': doc_data['subcategory'],
                    'chunk_index': doc_data['chunk_index'],
                    'total_chunks': doc_data['total_chunks']
                }
                solr_docs.append(solr_doc)
            
            self.solr.add(solr_docs)
            print(f"Successfully indexed {len(solr_docs)} documents in Solr")
            return len(solr_docs)
        except Exception as e:
            print(f"Error batch indexing documents: {e}")
            return 0
    
    def search_documents(self, query: str, 
                        categories: Optional[List[str]] = None,
                        subcategories: Optional[List[str]] = None,
                        max_results: int = 10) -> List[Dict[str, Any]]:
        """Search documents using keyword search"""
        try:
            # Build search query
            search_query = f'text:"{query}" OR text:({query})'
            
            # Add filters
            filter_queries = []
            if categories:
                category_query = " OR ".join([f'category:"{cat}"' for cat in categories])
                filter_queries.append(f'({category_query})')
            if subcategories:
                subcategory_query = " OR ".join([f'subcategory:"{sub}"' for sub in subcategories])
                filter_queries.append(f'({subcategory_query})')
            
            # Execute search
            params = {
                'rows': max_results,
                'hl': 'true',  # Enable highlighting
                'hl.fl': 'text',  # Highlight text field
                'hl.simple.pre': '<mark>',
                'hl.simple.post': '</mark>',
                'sort': 'score desc'
            }
            
            if filter_queries:
                params['fq'] = filter_queries
            
            results = self.solr.search(search_query, **params)
            
            # Format results
            formatted_results = []
            for doc in results.docs:
                result = {
                    'chunk_id': doc['id'],
                    'text': doc['text'],
                    'source_file': doc['source_file'],
                    'category': doc['category'],
                    'subcategory': doc['subcategory'],
                    'score': doc.get('score', 0),
                    'highlighted_text': ''
                }
                
                # Add highlighting if available
                if hasattr(results, 'highlighting') and doc['id'] in results.highlighting:
                    highlights = results.highlighting[doc['id']].get('text', [])
                    if highlights:
                        result['highlighted_text'] = ' ... '.join(highlights[:3])
                
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching Solr: {e}")
            return []
    
    def clear_index(self) -> bool:
        """Clear all documents from the index"""
        try:
            self.solr.delete(q='*:*')
            print("Solr index cleared")
            return True
        except Exception as e:
            print(f"Error clearing Solr index: {e}")
            return False
    
    def get_document_count(self) -> int:
        """Get total number of indexed documents"""
        try:
            results = self.solr.search('*:*', rows=0)
            return results.hits
        except Exception as e:
            print(f"Error getting document count: {e}")
            return 0