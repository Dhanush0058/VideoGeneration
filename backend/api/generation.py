from fastapi import APIRouter, HTTPException, Body
from typing import Optional, List
from pydantic import BaseModel
from backend.services.llm_service import LLMService
from backend.models.script import ScriptModel

router = APIRouter()
llm = LLMService()

class AnalyzeRequest(BaseModel):
    text: str

class ScriptRequest(BaseModel):
    text: str
    duration: int = 300
    difficulty: str = "Intermediate"
    style: str = "Professor"
    topic: Optional[str] = ""

@router.post("/analyze")
async def analyze_content(request: AnalyzeRequest):
    """
    Analyzes document text content to extract learning metadata.
    Uses LLM or falls back to basic heuristics.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Document text cannot be empty.")
        
    try:
        # Prompt the LLM specifically for metadata analysis, or run mock parser
        prompt = f"""
Analyze the following educational text and return a JSON structure with these keys:
- "topic": The main subject topic (string)
- "key_concepts": List of key technical concepts/headings (list of strings)
- "learning_objectives": What a viewer will learn (list of strings)
- "suggested_duration": Recommended explainer video duration in seconds (int)
- "difficulty": Beginner, Intermediate, or Advanced (string)

Text:
{request.text[:4000]}
"""
        
        # Simpler request for quick analysis
        if llm.provider == "MOCK" or not llm._has_api_credentials():
            # Mock analysis response based on text keywords
            lower_text = request.text.lower()
            if "osi" in lower_text:
                analysis = {
                    "topic": "The OSI Model",
                    "key_concepts": ["Layered architecture", "Data Encapsulation", "Physical vs Logical addressing"],
                    "learning_objectives": ["Understand the 7 layers of OSI", "Differentiate transport protocols like TCP/UDP", "Trace physical bits across ethernet"],
                    "suggested_duration": 180,
                    "difficulty": "Intermediate"
                }
            elif "cpu" in lower_text or "scheduling" in lower_text:
                analysis = {
                    "topic": "CPU Scheduling Algorithms",
                    "key_concepts": ["Process queues", "Time quanta", "Context switching", "Round robin"],
                    "learning_objectives": ["Define CPU scheduling", "Contrast FIFO and Round Robin", "Compare CPU utilization metrics"],
                    "suggested_duration": 150,
                    "difficulty": "Intermediate"
                }
            else:
                analysis = {
                    "topic": "General Educational Topic",
                    "key_concepts": ["Foundational basics", "Component relationships", "Summary takeaways"],
                    "learning_objectives": ["Identify main topic elements", "Understand systemic connections", "Recite key takeaways"],
                    "suggested_duration": 120,
                    "difficulty": "Beginner"
                }
        else:
            # Hit LLM for actual JSON structure
            response = await llm._call_llm_api(prompt)
            analysis = llm._clean_and_parse_json(response)
            
        return {
            "status": "success",
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during content analysis: {str(e)}"
        )

@router.post("/generate-script")
async def generate_script(request: ScriptRequest):
    """
    Generates a structured scene-by-scene script JSON.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Document text cannot be empty.")
        
    try:
        script = await llm.generate_script(
            document_text=request.text,
            duration=request.duration,
            difficulty=request.difficulty,
            style=request.style,
            topic=request.topic
        )
        return {
            "status": "success",
            "script": script
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Script generation failed: {str(e)}"
        )
