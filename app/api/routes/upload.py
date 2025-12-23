"""
Document upload endpoint.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Annotated

from app.models.schemas import DocumentUploadResponse, UploadedFileInfo
from app.services.document_processor import get_document_processor

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    files: Annotated[list[UploadFile], File(description="One or more .txt files to upload")]
) -> DocumentUploadResponse:
    """
    Upload one or more text documents.
    
    The documents will be:
    1. Chunked into smaller pieces for better retrieval
    2. Embedded using OpenAI's text-embedding-3-small model
    3. Stored in Qdrant vector database with metadata
    
    Supported format: .txt files only
    
    **Example using curl:**
    ```
    curl -X POST "http://localhost:8000/upload" \\
      -F "files=@document1.txt" \\
      -F "files=@document2.txt"
    ```
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    document_processor = get_document_processor()
    
    uploaded_files = []
    successful = 0
    failed = 0
    
    for file in files:
        # Validate file type
        if not file.filename or not file.filename.endswith(".txt"):
            uploaded_files.append(UploadedFileInfo(
                filename=file.filename or "unknown",
                document_id="",
                chunks_created=0,
                status=f"failed: Only .txt files are supported"
            ))
            failed += 1
            continue
        
        # Read file content
        try:
            content = await file.read()
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            uploaded_files.append(UploadedFileInfo(
                filename=file.filename,
                document_id="",
                chunks_created=0,
                status="failed: File is not valid UTF-8 text"
            ))
            failed += 1
            continue
        except Exception as e:
            uploaded_files.append(UploadedFileInfo(
                filename=file.filename,
                document_id="",
                chunks_created=0,
                status=f"failed: Could not read file - {str(e)}"
            ))
            failed += 1
            continue
        
        # Check if content is empty
        if not text_content.strip():
            uploaded_files.append(UploadedFileInfo(
                filename=file.filename,
                document_id="",
                chunks_created=0,
                status="failed: File is empty"
            ))
            failed += 1
            continue
        
        # Process the document
        try:
            result = await document_processor.process_document(
                filename=file.filename,
                content=text_content
            )
            
            if result["success"]:
                uploaded_files.append(UploadedFileInfo(
                    filename=file.filename,
                    document_id=result["document_id"],
                    chunks_created=result["chunks_created"],
                    status="success"
                ))
                successful += 1
            else:
                uploaded_files.append(UploadedFileInfo(
                    filename=file.filename,
                    document_id="",
                    chunks_created=0,
                    status=f"failed: {result.get('error', 'Unknown error')}"
                ))
                failed += 1
                
        except Exception as e:
            uploaded_files.append(UploadedFileInfo(
                filename=file.filename,
                document_id="",
                chunks_created=0,
                status=f"failed: {str(e)}"
            ))
            failed += 1
    
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
        files=uploaded_files
    )

