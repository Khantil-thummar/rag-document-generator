"""
RAG Document Generator - FastAPI Application

A backend service that generates new textual documents using existing documents
as the source of truth. The generated content is grounded, transparent, and explainable.

Production-ready with async support for parallel request processing.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.config import get_settings
from app.services.vector_store import get_vector_store, close_vector_store
from app.services.embedding_service import close_embedding_service
from app.services.llm_service import close_llm_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Initializes services on startup and cleans up on shutdown.
    """
    # Startup
    print("🚀 Starting RAG Document Generator...")
    
    # Initialize vector store (ensures collection exists)
    try:
        vector_store = get_vector_store()
        stats = await vector_store.get_collection_stats()
        print(f"✅ Qdrant initialized - {stats.get('total_chunks', 0)} chunks in store")
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize Qdrant: {e}")
    
    # Verify OpenAI API key
    settings = get_settings()
    if settings.openai_api_key:
        print("✅ OpenAI API key configured")
    else:
        print("❌ OpenAI API key not configured!")
    
    print("✅ Service ready! (Async mode enabled for parallel processing)")
    print("📚 API docs available at /docs")
    
    yield
    
    # Shutdown - Clean up async clients
    print("👋 Shutting down RAG Document Generator...")
    
    await close_vector_store()
    await close_embedding_service()
    await close_llm_service()
    
    print("✅ All connections closed")


# Create FastAPI application
app = FastAPI(
    title="RAG Document Generator",
    description="""
## AI-Powered Document Generation Service

This service generates new textual documents using existing documents as the source of truth.
The generated content is **grounded**, **transparent**, and **explainable**.

### Features

- **Document Ingestion**: Upload text, PDF, and DOCX documents
- **Semantic Search**: Find relevant content using vector similarity
- **Grounded Generation**: Generate FAQs, summaries, blogs, and reports based on source documents
- **Source Attribution**: Every generated response includes citations to source documents
- **Parallel Processing**: Async architecture for handling concurrent requests

### Transparency

All generated content includes:
- Which source documents were used
- Relevance scores for each source
- Excerpts from relevant sections
- Explanation of why sources were selected

### Anti-Hallucination Measures

- LLM is strictly instructed to only use provided context
- Low-relevance sources trigger warnings
- Missing sources result in clear error messages
""",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirects to docs."""
    return {
        "message": "RAG Document Generator API",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
