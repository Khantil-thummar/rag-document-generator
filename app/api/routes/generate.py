"""
Content generation endpoint.
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import GenerateRequest, GenerateResponse
from app.services.llm_service import get_llm_service

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate_content(request: GenerateRequest) -> GenerateResponse:
    """
    Generate new content based on existing documents.
    
    This endpoint uses RAG (Retrieval-Augmented Generation) to:
    1. Search for relevant document chunks using semantic similarity
    2. Use retrieved context to ground the LLM's response
    3. Generate content that is factually based on source documents
    4. Return the generated content with full source attribution
    
    **Generation Types:**
    - `faq`: Generate a FAQ document with Q&A format
    - `summary`: Create a concise summary of the topic
    - `blog`: Write an engaging blog post
    - `report`: Generate a formal report
    - `general`: General content generation (default)
    
    **Example Request:**
    ```json
    {
        "query": "Create a FAQ about the company's remote work policy",
        "generation_type": "faq",
        "filters": {
            "filenames": ["remote_work"]
        }
    }
    ```
    
    **Metadata Filtering:**
    You can filter which documents to search using:
    - `document_ids`: List of specific document IDs
    - `filenames`: List of filename patterns (partial match)
    
    **Source Attribution:**
    Every response includes:
    - List of source documents used
    - Relevance score for each source
    - Excerpt from each source
    - Explanation of why each source was relevant
    """
    llm_service = get_llm_service()
    
    try:
        response = await llm_service.generate(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Generation failed: {str(e)}"
        )

