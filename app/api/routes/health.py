"""
Health check endpoint.
"""

from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse
from app.services.vector_store import get_vector_store

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns the status of the service including:
    - Overall service status
    - Qdrant connection status
    - OpenAI configuration status
    - Document and chunk counts
    """
    settings = get_settings()
    vector_store = get_vector_store()
    
    # Check Qdrant connection (async)
    qdrant_connected = await vector_store.is_connected()
    
    # Check if OpenAI API key is configured
    openai_configured = bool(settings.openai_api_key)
    
    # Get collection stats (async)
    stats = await vector_store.get_collection_stats()
    
    # Get document count (async)
    documents = await vector_store.get_all_documents()
    
    # Determine overall status
    if qdrant_connected and openai_configured:
        status = "healthy"
    elif qdrant_connected or openai_configured:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        qdrant_connected=qdrant_connected,
        openai_configured=openai_configured,
        total_documents=len(documents),
        total_chunks=stats.get("total_chunks", 0)
    )
