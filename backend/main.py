import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.api import upload, generation, video

app = FastAPI(
    title="StudyFlow AI Backend",
    description="AI-powered educational video generator inspired by NotebookLM Video Overviews",
    version="1.0.0"
)

# Configure CORS for local development (allows Vite UI to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify front-end origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include endpoint routers
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(generation.router, prefix="/api", tags=["Generation"])
# Include video endpoints under /api/video to match requested structure
app.include_router(video.router, prefix="/api/video", tags=["Video"])

# Mount storage directory statically to serve rendered mp4 files and WebVTT tracks
app.mount("/static", StaticFiles(directory=settings.STORAGE_PATH), name="static")

@app.get("/")
async def root():
    return {
        "app": "StudyFlow AI Backend",
        "status": "healthy",
        "low_resource_mode": settings.LOW_RESOURCE
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
