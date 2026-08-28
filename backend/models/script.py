from typing import List
from pydantic import BaseModel, Field
from backend.models.scene import SceneModel

class ScriptModel(BaseModel):
    title: str = Field(..., description="Main title of the educational video overview")
    summary: str = Field(..., description="Brief educational summary of the content")
    target_duration: int = Field(default=300, description="Overall targeted duration of the video in seconds")
    scenes: List[SceneModel] = Field(..., description="Ordered list of visual and spoken scenes composing the video")
