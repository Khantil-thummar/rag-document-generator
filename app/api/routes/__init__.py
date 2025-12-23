"""
API routes aggregation.
"""

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.upload import router as upload_router
from app.api.routes.documents import router as documents_router
from app.api.routes.generate import router as generate_router

# Create main router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(upload_router, tags=["Documents"])
api_router.include_router(documents_router, tags=["Documents"])
api_router.include_router(generate_router, tags=["Generation"])

