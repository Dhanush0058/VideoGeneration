import os
from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from backend.models.script import ScriptModel
from backend.services.video_service import VideoService
from backend.config import settings

router = APIRouter()
video_service = VideoService()

class GenerateVideoRequest(BaseModel):
    text: str
    script: ScriptModel
    difficulty: str = "Intermediate"
    style: str = "Professor"
    topic: Optional[str] = ""

class RegenerateSceneRequest(BaseModel):
    job_id: str
    scene_id: int
    title: str
    narration: str
    visual_prompt: str
    on_screen_text: List[str]

@router.post("/generate-video")
async def generate_video(
    request: GenerateVideoRequest, 
    background_tasks: BackgroundTasks
):
    """
    Submits a video rendering background job.
    Returns the job_id immediately and runs execution asynchronously.
    """
    try:
        # Create a new job tracker in the service
        job_id = video_service.create_job()
        
        # Inject the parsed script directly to bypass re-running script creation
        video_service.update_job(job_id, script=request.script)
        
        # Start the background task pipeline
        video_service.start_generation_task(
            job_id=job_id,
            document_text=request.text,
            duration=request.script.target_duration,
            difficulty=request.difficulty,
            style=request.style,
            topic=request.topic
        )
        
        return {
            "job_id": job_id,
            "status": "queued"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue video generation job: {str(e)}"
        )

@router.get("/{job_id}")
async def get_job_details(job_id: str):
    """Returns the complete job status, including logs and script content."""
    job = video_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found.")
    return job

@router.get("/{job_id}/status")
async def get_job_status(job_id: str):
    """Returns current polling status metrics (progress, scene index, stages)."""
    job = video_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found.")
        
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "current_stage": job.current_stage,
        "current_scene": job.current_scene,
        "total_scenes": job.total_scenes,
        "video_url": job.video_url,
        "error_message": job.error_message
    }

@router.get("/{job_id}/download")
async def download_video(job_id: str):
    """Streams the completed MP4 video file back to the browser."""
    job = video_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Video is not ready. Current status: {job.status}")

    video_path = os.path.join(settings.STORAGE_PATH, "jobs", job_id, f"final_output_{job_id}.mp4")
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file does not exist on disk.")

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"StudyFlowAI_{job_id}.mp4"
    )

@router.post("/scene/regenerate")
async def regenerate_scene(request: RegenerateSceneRequest):
    """
    Regenerates a single scene (visual and voice) and re-concatenates the final video.
    """
    try:
        updated_job = await video_service.regenerate_single_scene(
            job_id=request.job_id,
            scene_id=request.scene_id,
            title=request.title,
            narration=request.narration,
            visual_prompt=request.visual_prompt,
            on_screen_text=request.on_screen_text
        )
        return {
            "status": "success",
            "job": updated_job
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scene regeneration failed: {str(e)}"
        )
