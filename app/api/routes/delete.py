"""
Document deletion endpoint.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.vector_store import get_vector_store

router = APIRouter()


class DeleteResponse(BaseModel):
    """Response model for document deletion."""
    message: str
    document_id: str
    success: bool


@router.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str) -> DeleteResponse:
    """
    Delete a document and all its chunks from the knowledge base.
    
    **Parameters:**
    - `document_id`: The unique identifier of the document to delete
      (obtained from `/documents` or `/upload` response)
    
    **Example:**
    ```bash
    curl -X DELETE "http://localhost:8000/documents/abc123-def456-..."
    ```
    
    **Note:** This action is irreversible. The document and all its 
    embeddings will be permanently removed from the vector store.
    """
    vector_store = get_vector_store()
    
    # Check if document exists first
    documents = vector_store.get_all_documents()
    doc_exists = any(doc["document_id"] == document_id for doc in documents)
    
    if not doc_exists:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{document_id}' not found"
        )
    
    # Delete the document
    success = vector_store.delete_document(document_id)
    
    if success:
        return DeleteResponse(
            message=f"Document successfully deleted",
            document_id=document_id,
            success=True
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document '{document_id}'"
        )

