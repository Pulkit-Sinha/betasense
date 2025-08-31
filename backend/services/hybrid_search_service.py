from typing import List, Dict, Any, Optional
from .solr_service import SolrService
from .vector_service import VectorService


class HybridSearchService:
    def __init__(self):
        try:
            self.solr_service = SolrService()
        except Exception as e:
            print(f"Solr not available: {e}")
            self.solr_service = None
        self.vector_service = VectorService()
        
    def test_connections(self) -> Dict[str, bool]:
        """Test both Solr and ChromaDB connections"""
        return {
            'solr': self.solr_service.test_connection(),
            'chromadb': True  # ChromaDB is always available locally
        }
    
    def search_documents(self, 
                        query: str,
                        categories: Optional[List[str]] = None,
                        subcategories: Optional[List[str]] = None,
                        max_results: int = 10,
                        keyword_weight: float = 0.6,
                        vector_weight: float = 0.4) -> List[Dict[str, Any]]:
        """
        Hybrid search combining keyword (Solr) and vector (ChromaDB) results
        """
        
        # Perform searches (fallback to vector-only if Solr unavailable)
        keyword_results = []
        if self.solr_service:
            print(f"🔍 Performing Solr keyword search for: '{query}'")
            keyword_results = self.solr_service.search_documents(
                query=query,
                categories=categories,
                subcategories=subcategories,
                max_results=max_results * 2
            )
            print(f"📊 Solr returned {len(keyword_results)} keyword results")
        else:
            print("⚠️ Solr service not available, using vector search only")
        
        print(f"🧠 Performing ChromaDB vector search for: '{query}'")
        vector_results = self.vector_service.search_similar(
            query=query,
            categories=categories,
            subcategories=subcategories,
            max_results=max_results * 2 if not keyword_results else max_results
        )
        print(f"📊 ChromaDB returned {len(vector_results)} vector results")
        
        # Combine and rank results
        print(f"🔄 Combining results with weights: keyword={keyword_weight}, vector={vector_weight}")
        combined_results = self._combine_results(
            keyword_results, 
            vector_results, 
            keyword_weight, 
            vector_weight
        )
        
        print(f"✅ Final hybrid results: {len(combined_results)} documents")
        if combined_results:
            print(f"🏆 Top result: {combined_results[0]['source_file']} (score: {combined_results[0]['combined_score']:.3f})")
        
        # Return top results
        return combined_results[:max_results]
    
    def _combine_results(self, 
                        keyword_results: List[Dict[str, Any]], 
                        vector_results: List[Dict[str, Any]],
                        keyword_weight: float,
                        vector_weight: float) -> List[Dict[str, Any]]:
        """
        Combine results from keyword and vector search with weighted scoring
        """
        
        # Create a dictionary to store combined results by chunk_id
        combined_dict = {}
        
        # Process keyword results
        max_keyword_score = max([r.get('score', 0) for r in keyword_results]) if keyword_results else 1
        for result in keyword_results:
            chunk_id = result['chunk_id']
            normalized_score = (result.get('score', 0) / max_keyword_score) if max_keyword_score > 0 else 0
            
            combined_dict[chunk_id] = {
                'chunk_id': chunk_id,
                'text': result['text'],
                'source_file': result['source_file'],
                'category': result['category'],
                'subcategory': result['subcategory'],
                'keyword_score': normalized_score,
                'vector_score': 0,
                'combined_score': normalized_score * keyword_weight,
                'highlighted_text': result.get('highlighted_text', ''),
                'search_type': 'keyword'
            }
        
        # Process vector results
        max_vector_score = max([r.get('similarity_score', 0) for r in vector_results]) if vector_results else 1
        for result in vector_results:
            chunk_id = result['chunk_id']
            normalized_score = (result.get('similarity_score', 0) / max_vector_score) if max_vector_score > 0 else 0
            
            if chunk_id in combined_dict:
                # Update existing result
                combined_dict[chunk_id]['vector_score'] = normalized_score
                combined_dict[chunk_id]['combined_score'] = (
                    combined_dict[chunk_id]['keyword_score'] * keyword_weight +
                    normalized_score * vector_weight
                )
                combined_dict[chunk_id]['search_type'] = 'hybrid'
            else:
                # Add new result from vector search only
                combined_dict[chunk_id] = {
                    'chunk_id': chunk_id,
                    'text': result['text'],
                    'source_file': result['source_file'],
                    'category': result['category'],
                    'subcategory': result['subcategory'],
                    'keyword_score': 0,
                    'vector_score': normalized_score,
                    'combined_score': normalized_score * vector_weight,
                    'highlighted_text': '',
                    'search_type': 'vector'
                }
        
        # Sort by combined score
        combined_results = list(combined_dict.values())
        combined_results.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return combined_results
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get statistics about indexed documents"""
        return {
            'solr_documents': self.solr_service.get_document_count(),
            'vector_documents': self.vector_service.get_document_count(),
            'connections': self.test_connections()
        }
    
    def clear_all_indices(self) -> Dict[str, bool]:
        """Clear both Solr and ChromaDB indices"""
        return {
            'solr_cleared': self.solr_service.clear_index(),
            'vector_cleared': self.vector_service.clear_collection()
        }