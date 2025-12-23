"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ==================== Health Endpoint ====================

class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(..., description="Service status")
    qdrant_connected: bool = Field(..., description="Qdrant connection status")
    openai_configured: bool = Field(..., description="OpenAI API key configured")
    total_documents: int = Field(0, description="Total documents in the system")
    total_chunks: int = Field(0, description="Total chunks in vector store")


# ==================== Upload Endpoint ====================

class UploadedFileInfo(BaseModel):
    """Information about a single uploaded file."""
    filename: str
    document_id: str
    chunks_created: int
    status: str


class DocumentUploadResponse(BaseModel):
    """Response model for document upload endpoint."""
    message: str
    total_files: int
    successful_uploads: int
    failed_uploads: int
    files: list[UploadedFileInfo]


# ==================== Documents List Endpoint ====================

class DocumentInfo(BaseModel):
    """Information about a stored document."""
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    total_chunks: int = Field(..., description="Number of chunks")
    uploaded_at: str = Field(..., description="Upload timestamp")


class DocumentListResponse(BaseModel):
    """Response model for list documents endpoint."""
    total_documents: int
    documents: list[DocumentInfo]


# ==================== Generate Endpoint ====================

class MetadataFilter(BaseModel):
    """Optional metadata filters for document retrieval."""
    document_ids: Optional[list[str]] = Field(None, description="Filter by specific document IDs")
    filenames: Optional[list[str]] = Field(None, description="Filter by filenames (partial match)")


class GenerateRequest(BaseModel):
    """Request model for content generation."""
    query: str = Field(
        ..., 
        description="The user's request (e.g., 'Create a FAQ about remote work policy')",
        min_length=10,
        max_length=2000
    )
    generation_type: Optional[str] = Field(
        "general",
        description="Type of content to generate: 'faq', 'summary', 'blog', 'report', 'general'"
    )
    filters: Optional[MetadataFilter] = Field(
        None,
        description="Optional metadata filters to narrow down source documents"
    )
    top_k: Optional[int] = Field(
        None,
        description="Number of source chunks to retrieve (default from config)"
    )


class SourceDocument(BaseModel):
    """Information about a source document used in generation."""
    document_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Source filename")
    relevance_score: float = Field(..., description="Similarity score (0-1)")
    excerpt: str = Field(..., description="Relevant text excerpt from the chunk")
    chunk_index: int = Field(..., description="Chunk position in document")
    reason: str = Field(..., description="Why this source was relevant")


class GenerationMetadata(BaseModel):
    """Metadata about the generation process."""
    query: str
    generation_type: str
    total_sources_used: int
    average_relevance: float
    model_used: str
    generated_at: str


class GenerateResponse(BaseModel):
    """Response model for content generation."""
    generated_content: str = Field(..., description="The generated text content")
    sources: list[SourceDocument] = Field(..., description="Source documents used")
    metadata: GenerationMetadata = Field(..., description="Generation metadata")
    warning: Optional[str] = Field(None, description="Warning if sources are weak or missing")

