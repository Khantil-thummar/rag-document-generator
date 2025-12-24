"""
Document upload endpoint.
Supports concurrent file processing for better performance.
"""

import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Annotated

from app.models.schemas import DocumentUploadResponse, UploadedFileInfo
from app.services.document_processor import get_document_processor
from app.services.file_parser import (
    is_supported_file,
    extract_text,
    SUPPORTED_EXTENSIONS
)

router = APIRouter()


async def process_single_file(
    file: UploadFile,
    supported_formats: str
) -> UploadedFileInfo:
    """
    Process a single file: validate, extract text, and store.
    Returns UploadedFileInfo with the result.
    """
    document_processor = get_document_processor()
    
    # Validate file type
    if not file.filename or not is_supported_file(file.filename):
        return UploadedFileInfo(
            filename=file.filename or "unknown",
            document_id="",
            chunks_created=0,
            status=f"failed: Unsupported file type. Supported: {supported_formats}"
        )
    
    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        return UploadedFileInfo(
            filename=file.filename,
            document_id="",
            chunks_created=0,
            status=f"failed: Could not read file - {str(e)}"
        )
    
    # Extract text from file
    try:
        text_content = extract_text(file.filename, content)
    except ValueError as e:
        return UploadedFileInfo(
            filename=file.filename,
            document_id="",
            chunks_created=0,
            status=f"failed: {str(e)}"
        )
    except Exception as e:
        return UploadedFileInfo(
            filename=file.filename,
            document_id="",
            chunks_created=0,
            status=f"failed: Could not extract text - {str(e)}"
        )
    
    # Check if content is empty
    if not text_content.strip():
        return UploadedFileInfo(
            filename=file.filename,
            document_id="",
            chunks_created=0,
            status="failed: No text content found in file"
        )
    
    # Process the document
    try:
        result = await document_processor.process_document(
            filename=file.filename,
            content=text_content
        )
        
        if result["success"]:
            return UploadedFileInfo(
                filename=file.filename,
                document_id=result["document_id"],
                chunks_created=result["chunks_created"],
                status="success"
            )
        else:
            return UploadedFileInfo(
                filename=file.filename,
                document_id="",
                chunks_created=0,
                status=f"failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        return UploadedFileInfo(
            filename=file.filename,
            document_id="",
            chunks_created=0,
            status=f"failed: {str(e)}"
        )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    files: Annotated[list[UploadFile], File(description="One or more documents to upload (.txt, .pdf, .docx)")]
) -> DocumentUploadResponse:
    """
    Upload one or more documents to the knowledge base.
    
    Files are processed **concurrently** for optimal performance.
    
    The documents will be:
    1. Text extracted (for PDF/DOCX)
    2. Chunked into smaller pieces for better retrieval
    3. Embedded using OpenAI's text-embedding-3-small model
    4. Stored in Qdrant vector database with metadata
    
    **Supported formats:** `.txt`, `.pdf`, `.docx`
    
    **Example using curl:**
    ```
    curl -X POST "http://localhost:8000/upload" \\
      -F "files=@document.txt" \\
      -F "files=@report.pdf" \\
      -F "files=@policy.docx"
    ```
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    supported_formats = ", ".join(SUPPORTED_EXTENSIONS)
    
    # Process all files concurrently
    tasks = [process_single_file(file, supported_formats) for file in files]
    uploaded_files = await asyncio.gather(*tasks)
    
    # Count successes and failures
    successful = sum(1 for f in uploaded_files if f.status == "success")
    failed = len(uploaded_files) - successful
    
    # Determine overall message
    if failed == 0:
        message = f"Successfully uploaded {successful} document(s)"
    elif successful == 0:
        message = f"Failed to upload all {failed} document(s)"
    else:
        message = f"Uploaded {successful} document(s), {failed} failed"
    
    return DocumentUploadResponse(
        message=message,
        total_files=len(files),
        successful_uploads=successful,
        failed_uploads=failed,
        files=list(uploaded_files)
    )
