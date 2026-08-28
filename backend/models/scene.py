from typing import List, Optional
from pydantic import BaseModel, Field

class SceneModel(BaseModel):
    id: int = Field(..., description="Unique sequential ID of the scene starting at 1")
    title: str = Field(..., description="Short descriptive title of the scene")
    duration: float = Field(..., description="Target duration of the scene in seconds")
    narration: str = Field(..., description="Complete verbal narration text for this scene")
    visual_prompt: str = Field(..., description="Highly detailed prompt to generate an educational image/diagram for this scene")
    on_screen_text: List[str] = Field(default=[], description="Bullet points or key terms to display on the screen")
    animation: str = Field(default="zoom_in", description="Animation style: zoom_in, zoom_out, pan_left, pan_right, none")
    transition: str = Field(default="fade", description="Transition style into the next scene: fade, slide, none")
    
    # Optional values calculated at generation runtime
    audio_path: Optional[str] = None
    image_path: Optional[str] = None
    actual_duration: Optional[float] = None
