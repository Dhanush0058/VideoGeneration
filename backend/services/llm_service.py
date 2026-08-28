import re
import json
import httpx
from typing import Dict, Any, List, Optional
from backend.config import settings
from backend.models.script import ScriptModel
from backend.models.scene import SceneModel

class LLMService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.upper()
        self.model_name = settings.MODEL_NAME
        self.hf_token = settings.HF_TOKEN

    async def generate_script(
        self, 
        document_text: str, 
        duration: int, 
        difficulty: str, 
        style: str, 
        topic: str = ""
    ) -> ScriptModel:
        """Generates a structured educational video script using the configured LLM provider."""
        
        # If provider is MOCK or no api key is present, use mock service
        if self.provider == "MOCK" or not self._has_api_credentials():
            return self._generate_mock_script(document_text, duration, difficulty, style, topic)
            
        prompt = self._build_prompt(document_text, duration, difficulty, style, topic)
        
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                raw_response = await self._call_llm_api(prompt)
                parsed_json = self._clean_and_parse_json(raw_response)
                
                # Validate with Pydantic
                script = ScriptModel(**parsed_json)
                return script
            except Exception as e:
                print(f"LLM script generation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries:
                    print("All LLM attempts failed. Falling back to structured Mock template.")
                    return self._generate_mock_script(document_text, duration, difficulty, style, topic)
                
                # Feedback loop on error
                prompt = f"{prompt}\n\nERROR ON PREVIOUS ATTEMPT: {str(e)}. Please correct the JSON output format and ensure strict conformance to the schema."

    def _has_api_credentials(self) -> bool:
        if self.provider == "GEMINI" and settings.GEMINI_API_KEY:
            return True
        if self.provider == "GROQ" and settings.GROQ_API_KEY:
            return True
        if self.provider == "OPENAI" and settings.OPENAI_API_KEY:
            return True
        if self.provider == "NVIDIA" and settings.NVIDIA_API_KEY:
            return True
        return False

    def _build_prompt(self, text: str, duration: int, difficulty: str, style: str, topic: str) -> str:
        schema = {
            "title": "Topic Title",
            "summary": "Educational summary detailing main concepts",
            "target_duration": duration,
            "scenes": [
                {
                    "id": 1,
                    "title": "Intro to Concept",
                    "duration": 45,
                    "narration": "Verbal narration spoken by the narrator.",
                    "visual_prompt": "Clean professional modern infographic description explaining the concept visually.",
                    "on_screen_text": ["Key Term 1", "Key Term 2"],
                    "animation": "zoom_in",
                    "transition": "fade"
                }
            ]
        }
        
        prompt = f"""
You are an expert curriculum designer and educational video scriptwriter. Your goal is to write a script for a video explanation of the content provided.

Target Video Settings:
- Target Duration: Approximately {duration} seconds
- Target Difficulty: {difficulty} (customize terminology, explanations, and depth accordingly)
- Teaching Style: {style}

Input Material / Context:
{f"Target Topic: {topic}" if topic else ""}
Document Context:
{text[:5000]}

Instructions:
1. Divide the material logically into 3 to 8 sequential scenes representing standard pedagogical progress (Introduction, Key Concept 1, Concept 2, Practical Example/Diagram, Summary).
2. For each scene:
   - Provide a "title" representing the chapter/scene.
   - Design a verbal "narration" that reads naturally, feels conversational, and explains the concepts clearly (approx. 130-150 words per minute).
   - Create a detailed "visual_prompt" describing what visual to generate. Focus on clean diagrams, structural infographics, maps, flowcharts, or specific visual scenarios. Do NOT request realistic cinema/movies.
   - List 2 to 4 "on_screen_text" bullet points/keywords.
   - Select an "animation" from: zoom_in, zoom_out, pan_left, pan_right, none.
   - Select a "transition" from: fade, slide, none.
3. You must respond in STRICT VALID JSON format matching the schema below.
4. Do NOT output any conversational text, markdown formatting (other than JSON block wrappers), or trailing text outside of the JSON block.

Required JSON Schema:
{json.dumps(schema, indent=2)}
"""
        return prompt

    async def _call_llm_api(self, prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        timeout = httpx.Timeout(60.0, connect=10.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            if self.provider == "GEMINI":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json" if "flash" in self.model_name.lower() or "pro" in self.model_name.lower() else "text/plain"
                    }
                }
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code != 200:
                    print(f"Gemini API Error: {res.status_code} - {res.text}")
                res.raise_for_status()
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
                
            elif self.provider == "GROQ":
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers["Authorization"] = f"Bearer {settings.GROQ_API_KEY}"
                payload = {
                    "model": self.model_name if self.model_name else "llama-3.1-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "You are a professional educational scriptwriter that returns strict JSON data."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code != 200:
                    print(f"Groq API Error: {res.status_code} - {res.text}")
                res.raise_for_status()
                data = res.json()
                return data["choices"][0]["message"]["content"]
                
            elif self.provider == "OPENAI":
                url = "https://api.openai.com/v1/chat/completions"
                headers["Authorization"] = f"Bearer {settings.OPENAI_API_KEY}"
                payload = {
                    "model": self.model_name if self.model_name else "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that returns JSON structure."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code != 200:
                    print(f"OpenAI API Error: {res.status_code} - {res.text}")
                res.raise_for_status()
                data = res.json()
                return data["choices"][0]["message"]["content"]
                
            elif self.provider == "NVIDIA":
                url = "https://integrate.api.nvidia.com/v1/chat/completions"
                headers["Authorization"] = f"Bearer {settings.NVIDIA_API_KEY}"
                payload = {
                    "model": self.model_name if self.model_name else "meta/llama-3.1-70b-instruct",
                    "messages": [
                        {"role": "system", "content": "You are a professional educational scriptwriter that returns strict JSON data."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code != 200:
                    print(f"Nvidia API Error: {res.status_code} - {res.text}")
                res.raise_for_status()
                data = res.json()
                return data["choices"][0]["message"]["content"]
                
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _clean_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Cleans and extracts JSON content from model output using regex."""
        # Find JSON object boundaries
        cleaned = raw_text.strip()
        
        # Strip markdown ```json ... ``` tags
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned)
            cleaned = re.sub(r"```$", "", cleaned)
            cleaned = cleaned.strip()
            
        # Try regex extract
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)
            
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Try to fix trailing commas or common JSON syntax errors
            # Replacing trailing comma before close brace/bracket
            cleaned_fix = re.sub(r',\s*([}\]])', r'\1', cleaned)
            return json.loads(cleaned_fix)

    def _generate_mock_script(
        self, 
        text: str, 
        duration: int, 
        difficulty: str, 
        style: str, 
        topic: str
    ) -> ScriptModel:
        """Returns structured mock scripts based on keywords in the prompt to allow zero-key operations."""
        combined_prompt_input = (topic + " " + text).lower()
        
        # Check topic keywords
        if "osi" in combined_prompt_input:
            title = "The OSI Model Explained"
            summary = "An educational breakdown of the 7 layers of the Open Systems Interconnection model, demonstrating how data travels across a network."
            scenes = [
                SceneModel(
                    id=1,
                    title="Introduction to the OSI Model",
                    duration=25.0,
                    narration="Have you ever wondered how an email travels from your computer to someone else's across the globe? It relies on a conceptual framework called the OSI Model, which stands for Open Systems Interconnection.",
                    visual_prompt="A clean diagram showing a computer sending an envelope into a cloud, representing data travelling across a network. Flat vector style, clean typography, white background.",
                    on_screen_text=["OSI Model", "Open Systems Interconnection", "7 Layer Framework"],
                    animation="zoom_in",
                    transition="fade"
                ),
                SceneModel(
                    id=2,
                    title="The Application & Presentation Layers",
                    duration=30.0,
                    narration="At the very top, we have Layer 7: the Application Layer, which interacts directly with your web browser. Right below it is the Presentation Layer, which formats, encrypts, and compresses data so it's readable.",
                    visual_prompt="An illustration of a web browser and a lock symbol, showing data encryption. Flat educational infographic style with light blue accents.",
                    on_screen_text=["L7: Application (HTTP, SMTP)", "L6: Presentation (SSL, JSON)", "Data formatting & Encryption"],
                    animation="pan_right",
                    transition="fade"
                ),
                SceneModel(
                    id=3,
                    title="The Lower Layers and Physical Delivery",
                    duration=35.0,
                    narration="Moving down through Session, Transport, and Network layers, we package the data into packets and route it. Finally, the Data Link and Physical layers convert these packets into electrical signals or light pulses to travel across ethernet cables.",
                    visual_prompt="A diagram showing packets breaking into bits (1s and 0s) passing through a fiber optic or copper cable. Modern clean networking diagram.",
                    on_screen_text=["L4: Transport (TCP/UDP)", "L3: Network (IP Routing)", "L1 & L2: Physical Delivery"],
                    animation="zoom_out",
                    transition="none"
                )
            ]
        elif "cpu" in combined_prompt_input or "schedule" in combined_prompt_input:
            title = "Understanding CPU Scheduling"
            summary = "A pedagogical overview of how operating systems allocate central processor time to multiple competing tasks."
            scenes = [
                SceneModel(
                    id=1,
                    title="What is CPU Scheduling?",
                    duration=20.0,
                    narration="The CPU is the brain of your computer. But with dozens of programs running at once, how does it decide which task gets processed first? That is the job of the CPU Scheduler.",
                    visual_prompt="A central processor chip with multiple task lines queuing up to enter it. Minimalist design with distinct color-coded task boxes.",
                    on_screen_text=["CPU Scheduling", "Multitasking OS", "Resource Management"],
                    animation="zoom_in",
                    transition="fade"
                ),
                SceneModel(
                    id=2,
                    title="FIFO and Round Robin Algorithms",
                    duration=35.0,
                    narration="One simple strategy is First-In First-Out, where tasks are processed in the order they arrive. A more dynamic method is Round Robin, which gives each process a tiny slice of CPU time before rotating to the next task.",
                    visual_prompt="A circular conveyor belt icon showing tasks taking turns. Simple vector infographic showing process rotation with clean circular arrows.",
                    on_screen_text=["FIFO: First In First Out", "Round Robin: Time Slicing", "Preemptive vs Non-preemptive"],
                    animation="pan_left",
                    transition="fade"
                )
            ]
        else:
            # General fallback script based on the input text/topic
            resolved_topic = topic if topic else "Your Educational Topic"
            title = f"Demystifying {resolved_topic}"
            summary = f"A high-level educational walkthrough of the core elements surrounding {resolved_topic}."
            scenes = [
                SceneModel(
                    id=1,
                    title=f"Introducing {resolved_topic}",
                    duration=20.0,
                    narration=f"Today, we are going to explore the core concepts of {resolved_topic}. Whether you're a student, a professional, or simply curious, understanding the fundamentals is the first step.",
                    visual_prompt=f"A modern educational illustration featuring books, lightbulbs, and connecting nodes. Minimal, professional flat art style.",
                    on_screen_text=[resolved_topic, "Core Overview", "Key Fundamentals"],
                    animation="zoom_in",
                    transition="fade"
                ),
                SceneModel(
                    id=2,
                    title="Core Principles & Mechanism",
                    duration=30.0,
                    narration="To truly grasp this subject, we must examine how its components interact. By analyzing the structure, we can identify how ideas connect and function together in practical applications.",
                    visual_prompt="A diagram showing three connected gears turning in synchronization, representing system components. Clean professional infographic style.",
                    on_screen_text=["Systemic Connections", "Key Principles", "Functional Mechanism"],
                    animation="pan_right",
                    transition="fade"
                ),
                SceneModel(
                    id=3,
                    title="Key Summary & Takeaways",
                    duration=25.0,
                    narration="In summary, mastering these core rules allows us to analyze complex scenarios and make informed decisions. Remember these foundational concepts as you continue learning.",
                    visual_prompt="A checklist document with check marks next to it, symbolizing review and summary. Flat vector illustration.",
                    on_screen_text=["Key Takeaways", "Summary Review", "Next Steps"],
                    animation="zoom_out",
                    transition="none"
                )
            ]
            
        return ScriptModel(title=title, summary=summary, target_duration=duration, scenes=scenes)
