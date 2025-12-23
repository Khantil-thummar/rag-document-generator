"""
Application configuration settings.
Loads environment variables and provides centralized config access.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_llm_model: str = "gpt-4o-mini"
    
    # Qdrant Configuration
    qdrant_path: str = "./qdrant_data"  # Local persistent storage path
    qdrant_collection_name: str = "documents"
    
    # Embedding Configuration
    embedding_dimension: int = 1536  # text-embedding-3-small dimension
    
    # Chunking Configuration
    chunk_size: int = 500  # tokens
    chunk_overlap: int = 50  # tokens
    
    # Retrieval Configuration
    top_k: int = 5  # Number of chunks to retrieve
    similarity_threshold: float = 0.3  # Minimum similarity score
    
    # LLM Configuration
    max_context_tokens: int = 4000  # Max tokens for context in prompt
    temperature: float = 0.3  # Lower temperature for more factual responses
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

