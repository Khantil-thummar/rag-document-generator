"""
Vector store service using Qdrant with persistent disk storage.
"""

import uuid
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import get_settings


class VectorStoreService:
    """Service for managing document vectors in Qdrant."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize Qdrant client with persistent disk storage
        self.client = QdrantClient(path=self.settings.qdrant_path)
        self.collection_name = self.settings.qdrant_collection_name
        
        # Ensure collection exists
        self._ensure_collection()
    
    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        try:
            self.client.get_collection(self.collection_name)
        except (UnexpectedResponse, ValueError):
            # Collection doesn't exist, create it
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.settings.embedding_dimension,
                    distance=models.Distance.COSINE
                )
            )
            
            # Create payload indices for efficient filtering
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="filename",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
    
    def is_connected(self) -> bool:
        """Check if Qdrant connection is healthy."""
        try:
            self.client.get_collection(self.collection_name)
            return True
        except Exception:
            return False
    
    def get_collection_stats(self) -> dict:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "total_chunks": info.points_count,
                "vectors_count": info.vectors_count
            }
        except Exception:
            return {"total_chunks": 0, "vectors_count": 0}
    
    def add_chunks(
        self,
        document_id: str,
        filename: str,
        chunks: list[str],
        embeddings: list[list[float]],
        uploaded_at: str
    ) -> int:
        """
        Add document chunks with their embeddings to the vector store.
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            chunks: List of text chunks
            embeddings: List of embedding vectors
            uploaded_at: ISO format timestamp
            
        Returns:
            Number of chunks added
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        total_chunks = len(chunks)
        
        points = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": idx,
                        "total_chunks": total_chunks,
                        "chunk_text": chunk,
                        "uploaded_at": uploaded_at
                    }
                )
            )
        
        # Batch upsert for efficiency
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        return len(points)
    
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        score_threshold: float = 0.3,
        document_ids: list[str] | None = None,
        filenames: list[str] | None = None
    ) -> list[dict]:
        """
        Search for similar chunks with optional metadata filtering.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            document_ids: Optional filter by document IDs
            filenames: Optional filter by filenames
            
        Returns:
            List of matching chunks with metadata and scores
        """
        # Build filter conditions
        filter_conditions = []
        
        if document_ids:
            filter_conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchAny(any=document_ids)
                )
            )
        
        if filenames:
            # For partial filename matching, we use multiple conditions
            filename_conditions = [
                models.FieldCondition(
                    key="filename",
                    match=models.MatchText(text=fname)
                )
                for fname in filenames
            ]
            if filename_conditions:
                filter_conditions.append(
                    models.Filter(should=filename_conditions)
                )
        
        # Construct the final filter
        query_filter = None
        if filter_conditions:
            query_filter = models.Filter(must=filter_conditions)
        
        # Perform search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=query_filter,
            with_payload=True
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "document_id": result.payload.get("document_id"),
                "filename": result.payload.get("filename"),
                "chunk_index": result.payload.get("chunk_index"),
                "total_chunks": result.payload.get("total_chunks"),
                "chunk_text": result.payload.get("chunk_text"),
                "uploaded_at": result.payload.get("uploaded_at"),
                "score": result.score
            })
        
        return formatted_results
    
    def get_all_documents(self) -> list[dict]:
        """
        Get list of all unique documents with metadata.
        
        Returns:
            List of document info dictionaries
        """
        # Scroll through all points to get unique documents
        documents = {}
        offset = None
        
        while True:
            results, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            for point in results:
                doc_id = point.payload.get("document_id")
                if doc_id and doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "filename": point.payload.get("filename"),
                        "total_chunks": point.payload.get("total_chunks"),
                        "uploaded_at": point.payload.get("uploaded_at")
                    }
            
            if offset is None:
                break
        
        return list(documents.values())
    
    def document_exists(self, filename: str) -> bool:
        """Check if a document with the given filename already exists."""
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="filename",
                        match=models.MatchValue(value=filename)
                    )
                ]
            ),
            limit=1,
            with_payload=False,
            with_vectors=False
        )
        return len(results) > 0
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete all chunks belonging to a document.
        
        Args:
            document_id: Document identifier to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id)
                            )
                        ]
                    )
                )
            )
            return True
        except Exception:
            return False


# Singleton instance
_vector_store: VectorStoreService | None = None


def get_vector_store() -> VectorStoreService:
    """Get or create vector store singleton."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store

