import logging
from typing import List, Dict, Any

try:
    import faiss
except ImportError:
    raise ImportError("FAISS is not installed. Please install it with 'pip install faiss-cpu'.")

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise ImportError("SentenceTransformer is not installed. Please install it with 'pip install sentence-transformers'.")

from utils.text_processor import TextProcessor

class RAGSystem:
    """Retrieval-Augmented Generation system using FAISS for vector storage"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.logger = logging.getLogger(__name__)
        self.text_processor = TextProcessor()
        
        
        if SentenceTransformer:
            try:
                self.embedding_model = SentenceTransformer(model_name)
                self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            except Exception as e:
                self.logger.warning(f"Failed to load SentenceTransformer: {e}")
                self.embedding_model = None
                self.embedding_dim = 384  
        else:
            self.embedding_model = None
            self.embedding_dim = 384
        
        
        if faiss and self.embedding_model:
            self.index = faiss.IndexFlatIP(self.embedding_dim)  
            self.document_chunks = []
            self.chunk_metadata = []
        else:
            self.index = None
            self.document_chunks = []
            self.chunk_metadata = []
            self.logger.warning("FAISS or SentenceTransformer not available. RAG functionality will be limited.")
    
    def add_documents(self, documents: List[str], metadata: List[Dict[str, Any]] = None):
        """
        Add documents to the vector store
        
        Args:
            documents (List[str]): List of document texts
            metadata (List[Dict]): Optional metadata for each document
        """
        if not self.embedding_model or not self.index:
            self.logger.warning("RAG system not properly initialized")
            return
        
        try:
            
            all_chunks = []
            all_metadata = []
            
            for i, doc in enumerate(documents):
                chunks = self.text_processor.chunk_text(doc)
                doc_metadata = metadata[i] if metadata and i < len(metadata) else {}
                
                for j, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    chunk_meta = doc_metadata.copy()
                    chunk_meta.update({
                        'doc_index': i,
                        'chunk_index': j,
                        'chunk_text': chunk
                    })
                    all_metadata.append(chunk_meta)
            
            if not all_chunks:
                return
            
            
            embeddings = self.embedding_model.encode(all_chunks, convert_to_numpy=True)
            
            
            faiss.normalize_L2(embeddings)
            
            
            self.index.add(embeddings)
            self.document_chunks.extend(all_chunks)
            self.chunk_metadata.extend(all_metadata)
            
            self.logger.info(f"Added {len(all_chunks)} chunks to vector store")
            
        except Exception as e:
            self.logger.error(f"Error adding documents to RAG system: {str(e)}")
            raise
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant documents based on query
        
        Args:
            query (str): Search query
            top_k (int): Number of top results to return
            
        Returns:
            List[Dict]: List of relevant document chunks with metadata
        """
        if not self.embedding_model or not self.index or self.index.ntotal == 0:
            self.logger.warning("RAG system not available or no documents indexed")
            return []
        
        try:
            
            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
            faiss.normalize_L2(query_embedding)
            
            
            scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
            
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx >= 0 and idx < len(self.document_chunks):
                    result = {
                        'text': self.document_chunks[idx],
                        'score': float(score),
                        'rank': i + 1,
                        'metadata': self.chunk_metadata[idx]
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching in RAG system: {str(e)}")
            return []
    
    def get_context_for_query(self, query: str, max_context_length: int = 2000) -> str:
        """
        Get relevant context for a query, concatenated and trimmed to max length
        
        Args:
            query (str): Search query
            max_context_length (int): Maximum length of context to return
            
        Returns:
            str: Concatenated relevant context
        """
        search_results = self.search(query, top_k=5)
        
        if not search_results:
            return ""
        
        
        context_parts = []
        current_length = 0
        
        for result in search_results:
            text = result['text']
            if current_length + len(text) <= max_context_length:
                context_parts.append(text)
                current_length += len(text)
            else:
                
                remaining_space = max_context_length - current_length
                if remaining_space > 100:  
                    context_parts.append(text[:remaining_space] + "...")
                break
        
        return "\n\n".join(context_parts)
    
    def build_job_requirements_index(self, job_description: str):
        """
        Build a specialized index for job requirements
        
        Args:
            job_description (str): Job description text
        """
        
        sections = self.text_processor.extract_job_sections(job_description)
        
        
        documents = []
        metadata = []
        
        for section_name, section_text in sections.items():
            if section_text.strip():
                documents.append(section_text)
                metadata.append({
                    'type': 'job_requirement',
                    'section': section_name,
                    'source': 'job_description'
                })
        
        
        documents.append(job_description)
        metadata.append({
            'type': 'job_description',
            'section': 'full',
            'source': 'job_description'
        })
        
        if documents:
            self.add_documents(documents, metadata)
    
    def clear_index(self):
        """Clear the vector store index"""
        if self.index:
            self.index.reset()
        self.document_chunks.clear()
        self.chunk_metadata.clear()
        self.logger.info("Vector store index cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        return {
            'total_chunks': len(self.document_chunks),
            'index_size': self.index.ntotal if self.index else 0,
            'embedding_dimension': self.embedding_dim,
            'model_available': self.embedding_model is not None,
            'faiss_available': faiss is not None
        }
