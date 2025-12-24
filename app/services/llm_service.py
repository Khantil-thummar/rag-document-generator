"""
LLM service for content generation using OpenAI GPT-4o-mini.
"""

import time

from openai import OpenAI

from app.config import get_settings
from app.services.embedding_service import get_embedding_service
from app.services.vector_store import get_vector_store
from app.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    SourceDocument,
)


class LLMService:
    """Service for generating content using LLM with RAG."""
    
    # System prompts for different generation types
    GENERATION_PROMPTS = {
        "faq": """You are a helpful assistant that creates FAQ documents based on provided source material.
Create a well-structured FAQ with clear questions and concise answers.
Format each Q&A pair clearly with "Q:" and "A:" prefixes.
IMPORTANT: Only use information from the provided context. Do not invent or assume any facts.""",
        
        "summary": """You are a helpful assistant that creates concise summaries of documents.
Create a clear, well-organized summary that captures the key points.
Use bullet points or numbered lists where appropriate.
IMPORTANT: Only use information from the provided context. Do not invent or assume any facts.""",
        
        "blog": """You are a helpful assistant that creates engaging blog posts based on provided source material.
Write in a professional yet approachable tone.
Include an introduction, main points, and conclusion.
IMPORTANT: Only use information from the provided context. Do not invent or assume any facts.""",
        
        "report": """You are a helpful assistant that creates formal reports based on provided source material.
Structure the report with clear sections and professional language.
Include relevant details and maintain a formal tone.
IMPORTANT: Only use information from the provided context. Do not invent or assume any facts.""",
        
        "general": """You are a helpful assistant that generates content based on provided source material.
Respond to the user's request accurately and helpfully.
Structure your response appropriately for the type of content requested.
IMPORTANT: Only use information from the provided context. Do not invent or assume any facts."""
    }
    
    def __init__(self):
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
    
    def _build_context(self, chunks: list[dict]) -> str:
        """Build context string from retrieved chunks."""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {i}: {chunk['filename']}]\n{chunk['chunk_text']}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def _create_source_documents(self, chunks: list[dict]) -> list[SourceDocument]:
        """Create source document objects from chunks."""
        sources = []
        
        for chunk in chunks:
            score = chunk.get("score", 0)
            
            # Create human-readable reason
            if score >= 0.8:
                reason = f"Very high semantic similarity ({score:.0%}) - directly relevant to your query"
            elif score >= 0.6:
                reason = f"High semantic similarity ({score:.0%}) - contains relevant information"
            elif score >= 0.4:
                reason = f"Moderate semantic similarity ({score:.0%}) - contains related context"
            else:
                reason = f"Lower semantic similarity ({score:.0%}) - may contain tangentially related information"
            
            # Truncate excerpt if too long
            excerpt = chunk.get("chunk_text", "")
            if len(excerpt) > 500:
                excerpt = excerpt[:497] + "..."
            
            sources.append(SourceDocument(
                document_id=chunk.get("document_id", ""),
                filename=chunk.get("filename", ""),
                relevance_score=round(score, 4),
                excerpt=excerpt,
                chunk_index=chunk.get("chunk_index", 0),
                reason=reason
            ))
        
        return sources
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """
        Generate content based on user request and retrieved documents.
        
        Args:
            request: Generation request with query and optional filters
            
        Returns:
            Generated response with content and source attribution
        """
        # Determine number of chunks to retrieve
        top_k = request.top_k or self.settings.top_k
        
        # Generate query embedding
        query_embedding = self.embedding_service.get_embedding(request.query)
        
        # Extract filters
        document_ids = None
        filenames = None
        if request.filters:
            document_ids = request.filters.document_ids
            filenames = request.filters.filenames
        
        # Search for relevant chunks with timing
        search_start = time.perf_counter()
        chunks = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            score_threshold=self.settings.similarity_threshold,
            document_ids=document_ids,
            filenames=filenames
        )
        db_search_time = round(time.perf_counter() - search_start, 4)
        
        # Handle case with no or weak sources
        warning = None
        if not chunks:
            warning = "No relevant source documents found. Cannot generate grounded content."
            return GenerateResponse(
                generated_content="I cannot generate this content because no relevant source documents were found in the knowledge base. Please ensure relevant documents have been uploaded, or try rephrasing your query.",
                sources=[],
                db_search_time=db_search_time,
                warning=warning
            )
        
        # Check if sources are weak (low relevance)
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
        if avg_score < 0.4:
            warning = f"Source documents have low relevance (avg: {avg_score:.0%}). Generated content may not fully address your query."
        
        # Build context from chunks
        context = self._build_context(chunks)
        
        # Get appropriate system prompt
        generation_type = request.generation_type or "general"
        system_prompt = self.GENERATION_PROMPTS.get(
            generation_type, 
            self.GENERATION_PROMPTS["general"]
        )
        
        # Create user prompt
        user_prompt = f"""Based on the following source documents, {request.query}

SOURCE DOCUMENTS:
{context}

INSTRUCTIONS:
1. Only use information from the source documents above
2. If the sources don't contain enough information, acknowledge this limitation
3. Do not make up or assume any facts not present in the sources
4. Structure your response appropriately for the requested content type

Please generate the requested content:"""
        
        # Call LLM
        response = self.client.chat.completions.create(
            model=self.settings.openai_llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.settings.temperature,
            max_tokens=2000
        )
        
        generated_content = response.choices[0].message.content
        
        # Create source documents
        sources = self._create_source_documents(chunks)
        
        return GenerateResponse(
            generated_content=generated_content,
            sources=sources,
            db_search_time=db_search_time,
            warning=warning
        )


# Singleton instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

