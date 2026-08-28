from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from backend.models.script import ScriptModel

class JobModel(BaseModel):
    job_id: str
    status: str = "queued" # queued, generating, completed, failed, cancelled
    progress: int = 0
    current_stage: str = "Queued" # Analyzing document, Creating script, Planning scenes, Generating narration, Generating visuals, Rendering video, Finalizing, Completed, Failed
    current_scene: int = 0
    total_scenes: int = 0
    error_message: Optional[str] = None
    script: Optional[ScriptModel] = None
    video_url: Optional[str] = None
    created_at: str
    updated_at: str
    logs: List[str] = []
