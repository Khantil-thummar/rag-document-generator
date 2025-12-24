"""
Embedding service using OpenAI's text-embedding-3-small model.
Async implementation for production-ready parallel processing.
"""

from openai import AsyncOpenAI
from app.config import get_settings


class EmbeddingService:
    """Async service for generating text embeddings using OpenAI."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.model = self.settings.openai_embedding_model
    
    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        # Clean and prepare text
        text = text.replace("\n", " ").strip()
        if not text:
            raise ValueError("Cannot generate embedding for empty text")
        
        response = await self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in a single API call.
        More efficient for batch processing.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # Clean texts
        cleaned_texts = [t.replace("\n", " ").strip() for t in texts]
        
        # Filter empty texts and track indices
        non_empty_indices = [i for i, t in enumerate(cleaned_texts) if t]
        non_empty_texts = [cleaned_texts[i] for i in non_empty_indices]
        
        if not non_empty_texts:
            raise ValueError("All texts are empty")
        
        response = await self.client.embeddings.create(
            model=self.model,
            input=non_empty_texts
        )
        
        # Map embeddings back to original indices
        embeddings = [None] * len(texts)
        for idx, embedding_data in zip(non_empty_indices, response.data):
            embeddings[idx] = embedding_data.embedding
        
        return embeddings
    
    async def close(self):
        """Close the async client."""
        await self.client.close()


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


async def close_embedding_service():
    """Close the embedding service client."""
    global _embedding_service
    if _embedding_service is not None:
        await _embedding_service.close()
        _embedding_service = None
