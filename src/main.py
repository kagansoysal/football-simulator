from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.api.endpoints import router as api_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="UEFA Şampiyonlar Ligi, Avrupa Ligi ve Konferans Ligi için Monte Carlo & Dixon-Coles Analitik API'si",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS ayarları (React/Next.js frontend hazır olduğunda sorunsuz bağlanması için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }
