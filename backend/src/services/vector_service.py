import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import json


class VectorService:
    def __init__(self, collection_name: str = "betasense_docs"):
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"Using existing ChromaDB collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"Created new ChromaDB collection: {collection_name}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text"""
        return self.embedding_model.encode(text).tolist()
    
    def add_document(self, doc_data: Dict[str, Any]) -> bool:
        """Add a single document to the vector database"""
        try:
            # Generate embedding
            embedding = self.generate_embedding(doc_data['text'])
            
            # Prepare metadata
            metadata = {
                'source_file': doc_data['source_file'],
                'category': doc_data['category'],
                'subcategory': doc_data['subcategory'],
                'chunk_index': doc_data['chunk_index'],
                'total_chunks': doc_data['total_chunks'],
                'file_path': doc_data.get('file_path', '')
            }
            
            # Add to collection
            self.collection.add(
                embeddings=[embedding],
                documents=[doc_data['text']],
                metadatas=[metadata],
                ids=[doc_data['chunk_id']]
            )
            
            return True
        except Exception as e:
            print(f"Error adding document {doc_data['chunk_id']} to ChromaDB: {e}")
            return False
    
    def add_documents_batch(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """Add multiple documents in batches"""
        added_count = 0
        
        try:
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # Prepare batch data
                embeddings = []
                texts = []
                metadatas = []
                ids = []
                
                for doc_data in batch:
                    # Generate embedding
                    embedding = self.generate_embedding(doc_data['text'])
                    embeddings.append(embedding)
                    
                    texts.append(doc_data['text'])
                    ids.append(doc_data['chunk_id'])
                    
                    metadata = {
                        'source_file': doc_data['source_file'],
                        'category': doc_data['category'],
                        'subcategory': doc_data['subcategory'],
                        'chunk_index': doc_data['chunk_index'],
                        'total_chunks': doc_data['total_chunks'],
                        'file_path': doc_data.get('file_path', '')
                    }
                    metadatas.append(metadata)
                
                # Add batch to collection
                self.collection.add(
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )
                
                added_count += len(batch)
                print(f"Added batch {i//batch_size + 1}: {len(batch)} documents to ChromaDB")
            
            print(f"Successfully added {added_count} documents to ChromaDB")
            return added_count
            
        except Exception as e:
            print(f"Error in batch adding documents to ChromaDB: {e}")
            return added_count
    
    def search_similar(self, query: str, 
                      categories: Optional[List[str]] = None,
                      subcategories: Optional[List[str]] = None,
                      max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            # Build where clause for filtering
            where_clause = None
            if categories and subcategories:
                # Both filters - use $and
                where_clause = {
                    "$and": [
                        {"category": {"$in": categories}},
                        {"subcategory": {"$in": subcategories}}
                    ]
                }
            elif categories:
                # Only category filter
                where_clause = {"category": {"$in": categories}}
            elif subcategories:
                # Only subcategory filter
                where_clause = {"subcategory": {"$in": subcategories}}
            
            # Search
            search_params = {
                'query_embeddings': [query_embedding],
                'n_results': max_results
            }
            
            if where_clause:
                search_params['where'] = where_clause
            
            results = self.collection.query(**search_params)
            
            # Format results
            formatted_results = []
            if results['documents'] and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    result = {
                        'chunk_id': results['ids'][0][i],
                        'text': doc,
                        'similarity_score': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'source_file': results['metadatas'][0][i]['source_file'],
                        'category': results['metadatas'][0][i]['category'],
                        'subcategory': results['metadatas'][0][i]['subcategory'],
                        'chunk_index': results['metadatas'][0][i]['chunk_index']
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching ChromaDB: {e}")
            return []
    
    def clear_collection(self) -> bool:
        """Clear all documents from the collection"""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name=self.collection.name)
            self.collection = self.client.create_collection(
                name=self.collection.name,
                metadata={"hnsw:space": "cosine"}
            )
            print("ChromaDB collection cleared")
            return True
        except Exception as e:
            print(f"Error clearing ChromaDB collection: {e}")
            return False
    
    def get_document_count(self) -> int:
        """Get total number of documents in the collection"""
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Error getting document count: {e}")
            return 0