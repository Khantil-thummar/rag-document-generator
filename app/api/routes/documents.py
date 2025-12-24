"""
Document listing endpoint.
"""

from fastapi import APIRouter

from app.models.schemas import DocumentListResponse, DocumentInfo
from app.services.vector_store import get_vector_store

router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """
    List all documents in the knowledge base.
    
    Returns a list of all uploaded documents with their metadata including:
    - Document ID (unique identifier)
    - Filename (original upload name)
    - Number of chunks
    - Upload timestamp
    
    **Example response:**
    ```json
    {
        "total_documents": 2,
        "documents": [
            {
                "document_id": "abc123...",
                "filename": "remote_work_policy.txt",
                "total_chunks": 8,
                "uploaded_at": "2025-12-24T10:00:00Z"
            }
        ]
    }
    ```
    """
    vector_store = get_vector_store()
    
    # Get all documents from vector store (async)
    documents = await vector_store.get_all_documents()
    
    # Convert to response model
    document_infos = [
        DocumentInfo(
            document_id=doc["document_id"],
            filename=doc["filename"],
            total_chunks=doc["total_chunks"],
            uploaded_at=doc["uploaded_at"]
        )
        for doc in documents
    ]
    
    # Sort by upload time (newest first)
    document_infos.sort(key=lambda x: x.uploaded_at, reverse=True)
    
    return DocumentListResponse(
        total_documents=len(document_infos),
        documents=document_infos
    )
