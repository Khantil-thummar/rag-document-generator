"""
Document processing service for chunking and ingesting documents.
"""

import uuid
from datetime import datetime, timezone

import tiktoken

from app.config import get_settings
from app.services.embedding_service import get_embedding_service
from app.services.vector_store import get_vector_store


class DocumentProcessor:
    """Service for processing and ingesting documents."""
    
    def __init__(self):
        self.settings = get_settings()
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        
        # Initialize tokenizer for chunking
        self.tokenizer = tiktoken.encoding_for_model("gpt-4o-mini")
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))
    
    def _chunk_text(self, text: str) -> list[str]:
        """
        Split text into chunks based on token count with overlap.
        Uses sentence-aware splitting for better context preservation.
        
        Args:
            text: The text to chunk
            
        Returns:
            List of text chunks
        """
        chunk_size = self.settings.chunk_size
        overlap = self.settings.chunk_overlap
        
        # Split into sentences (simple approach)
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = []  # List of sentences (strings)
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)
            
            # If single sentence exceeds chunk size, split it further
            if sentence_tokens > chunk_size:
                # Flush current chunk if not empty
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split long sentence by words and create complete chunks
                words = sentence.split()
                temp_chunk = []
                temp_tokens = 0
                
                for word in words:
                    word_tokens = self._count_tokens(word + " ")
                    if temp_tokens + word_tokens > chunk_size:
                        if temp_chunk:
                            # Save the word-based chunk as a complete chunk
                            chunks.append(" ".join(temp_chunk))
                        temp_chunk = [word]
                        temp_tokens = word_tokens
                    else:
                        temp_chunk.append(word)
                        temp_tokens += word_tokens
                
                # Any remaining words from the long sentence become a complete chunk
                # Don't carry them forward to avoid mixing words with sentences
                if temp_chunk:
                    chunks.append(" ".join(temp_chunk))
                
                # Reset state - next iteration starts fresh with sentences
                current_chunk = []
                current_tokens = 0
                continue
            
            # Check if adding sentence exceeds chunk size
            if current_tokens + sentence_tokens > chunk_size:
                # Save current chunk
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                
                # Start new chunk with overlap from previous
                if overlap > 0 and current_chunk:
                    # Get last few sentences that fit in overlap
                    overlap_chunk = []
                    overlap_tokens = 0
                    for sent in reversed(current_chunk):
                        sent_tokens = self._count_tokens(sent)
                        if overlap_tokens + sent_tokens <= overlap:
                            overlap_chunk.insert(0, sent)
                            overlap_tokens += sent_tokens
                        else:
                            break
                    current_chunk = overlap_chunk + [sentence]
                    current_tokens = overlap_tokens + sentence_tokens
                else:
                    current_chunk = [sentence]
                    current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences.
        Simple approach that handles common cases.
        """
        # Normalize whitespace
        text = " ".join(text.split())
        
        # Split on sentence boundaries
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in ".!?" and len(current.strip()) > 0:
                # Check if it's actually end of sentence (not abbreviation)
                stripped = current.strip()
                if len(stripped) > 2:  # Avoid splitting on single letters with periods
                    sentences.append(stripped)
                    current = ""
        
        # Add remaining text
        if current.strip():
            sentences.append(current.strip())
        
        # If no sentences found, split by newlines
        if not sentences:
            sentences = [s.strip() for s in text.split("\n") if s.strip()]
        
        return sentences if sentences else [text]
    
    async def process_document(self, filename: str, content: str) -> dict:
        """
        Process a document: chunk it, generate embeddings, and store in vector DB.
        
        Args:
            filename: Original filename
            content: Document text content
            
        Returns:
            Dictionary with processing results
        """
        # Check if document already exists
        if self.vector_store.document_exists(filename):
            return {
                "success": False,
                "filename": filename,
                "error": f"Document '{filename}' already exists. Delete it first to re-upload."
            }
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        uploaded_at = datetime.now(timezone.utc).isoformat()
        
        # Chunk the document
        chunks = self._chunk_text(content)
        
        if not chunks:
            return {
                "success": False,
                "filename": filename,
                "error": "Document produced no valid chunks"
            }
        
        # Generate embeddings for all chunks
        try:
            embeddings = self.embedding_service.get_embeddings_batch(chunks)
        except Exception as e:
            return {
                "success": False,
                "filename": filename,
                "error": f"Failed to generate embeddings: {str(e)}"
            }
        
        # Filter out chunks with None embeddings
        valid_chunks = []
        valid_embeddings = []
        for chunk, embedding in zip(chunks, embeddings):
            if embedding is not None:
                valid_chunks.append(chunk)
                valid_embeddings.append(embedding)
        
        if not valid_chunks:
            return {
                "success": False,
                "filename": filename,
                "error": "No valid embeddings generated"
            }
        
        # Store in vector database
        try:
            chunks_added = self.vector_store.add_chunks(
                document_id=document_id,
                filename=filename,
                chunks=valid_chunks,
                embeddings=valid_embeddings,
                uploaded_at=uploaded_at
            )
        except Exception as e:
            return {
                "success": False,
                "filename": filename,
                "error": f"Failed to store in vector database: {str(e)}"
            }
        
        return {
            "success": True,
            "filename": filename,
            "document_id": document_id,
            "chunks_created": chunks_added,
            "uploaded_at": uploaded_at
        }


# Singleton instance
_document_processor: DocumentProcessor | None = None


def get_document_processor() -> DocumentProcessor:
    """Get or create document processor singleton."""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor

