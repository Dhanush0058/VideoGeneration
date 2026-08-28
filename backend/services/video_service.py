import os
import uuid
import asyncio
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from backend.config import settings
from backend.models.job import JobModel
from backend.models.script import ScriptModel
from backend.models.scene import SceneModel
from backend.services.llm_service import LLMService
from backend.services.tts_service import TTSService
from backend.services.image_service import ImageService
from backend.services.subtitle_service import SubtitleService
from backend.video.renderer import VideoRenderer

class VideoService:
    # Class-level job store to persist status in memory across API requests
    _jobs: Dict[str, JobModel] = {}
    _executor = ThreadPoolExecutor(max_workers=3)

    def __init__(self):
        self.llm = LLMService()
        self.tts = TTSService()
        self.image_service = ImageService()

    def get_job(self, job_id: str) -> Optional[JobModel]:
        return self._jobs.get(job_id)

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()
        job = JobModel(
            job_id=job_id,
            status="queued",
            progress=0,
            current_stage="Queued",
            created_at=now,
            updated_at=now,
            logs=["Job initialized and queued."]
        )
        self._jobs[job_id] = job
        return job_id

    def update_job(self, job_id: str, **kwargs):
        job = self._jobs.get(job_id)
        if job:
            for key, val in kwargs.items():
                setattr(job, key, val)
            if "logs" in kwargs:
                # Append instead of overwrite if list is provided
                pass
            job.updated_at = datetime.utcnow().isoformat()

    def add_log(self, job_id: str, log_message: str):
        job = self._jobs.get(job_id)
        if job:
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            job.logs.append(f"[{timestamp}] {log_message}")
            job.updated_at = datetime.utcnow().isoformat()
            print(f"[JOB-{job_id}] {log_message}")

    def start_generation_task(
        self, 
        job_id: str, 
        document_text: str, 
        duration: int, 
        difficulty: str, 
        style: str, 
        topic: str = ""
    ):
        """Spawns the background video generator task."""
        asyncio.create_task(
            self._run_generation_pipeline(
                job_id, document_text, duration, difficulty, style, topic
            )
        )

    async def _run_generation_pipeline(
        self, 
        job_id: str, 
        document_text: str, 
        duration: int, 
        difficulty: str, 
        style: str, 
        topic: str
    ):
        self.update_job(job_id, status="generating", current_stage="Analyzing document", progress=5)
        self.add_log(job_id, "Starting analysis and script generation...")

        # Setup paths
        job_dir = os.path.join(settings.STORAGE_PATH, "jobs", job_id)
        os.makedirs(job_dir, exist_ok=True)
        temp_dir = os.path.join(job_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # 1. Script Generation
            self.update_job(job_id, current_stage="Creating script", progress=10)
            script = await self.llm.generate_script(document_text, duration, difficulty, style, topic)
            self.update_job(job_id, script=script)
            self.add_log(job_id, f"Script generated: '{script.title}' with {len(script.scenes)} scenes.")

            # 2. Scene Media Generation Loop (TTS + Image + Scene Render)
            self.update_job(job_id, current_stage="Planning scenes", progress=15, total_scenes=len(script.scenes))
            clip_paths = []
            
            scenes_weight = 70.0
            scenes_start_progress = 15.0

            for i, scene in enumerate(script.scenes):
                scene_num = i + 1
                self.update_job(job_id, current_scene=scene_num, current_stage=f"Generating scene {scene_num} of {len(script.scenes)}")
                
                # Calculate individual step progress
                base_progress = scenes_start_progress + (i * (scenes_weight / len(script.scenes)))
                self.update_job(job_id, progress=int(base_progress))

                # A. TTS Audio
                self.add_log(job_id, f"Generating narration audio for scene {scene_num}...")
                audio_path = os.path.join(temp_dir, f"scene_{scene_num:03d}.wav")
                actual_duration = await self.tts.generate_narration(scene.narration, audio_path)
                scene.audio_path = audio_path
                scene.actual_duration = actual_duration
                self.add_log(job_id, f"Scene {scene_num} audio generated (duration: {actual_duration:.2f}s).")

                # B. Image Generation
                self.add_log(job_id, f"Generating visual slide for scene {scene_num}...")
                image_path = os.path.join(temp_dir, f"scene_{scene_num:03d}.png")
                await self.image_service.generate_image(
                    scene.visual_prompt, image_path, title=scene.title, on_screen_text=scene.on_screen_text
                )
                scene.image_path = image_path
                self.add_log(job_id, f"Scene {scene_num} visual slide created.")

                # C. Scene clip compilation
                self.add_log(job_id, f"Rendering video clip for scene {scene_num}...")
                clip_path = VideoRenderer.render_scene_clip(scene, temp_dir)
                clip_paths.append(clip_path)
                
                # Progress update post scene
                post_scene_progress = base_progress + (scenes_weight / len(script.scenes))
                self.update_job(job_id, progress=int(post_scene_progress))

            # 3. Concatenation & Subtitles
            self.update_job(job_id, current_stage="Rendering video", progress=88)
            self.add_log(job_id, "Stitching scene clips together...")
            
            final_video_filename = f"final_output_{job_id}.mp4"
            final_video_path = os.path.join(job_dir, final_video_filename)
            VideoRenderer.concatenate_clips(clip_paths, final_video_path)
            
            # Generate subtitle files (VTT for HTML5 frontend player, SRT for local file availability)
            self.add_log(job_id, "Compiling subtitles...")
            vtt_path = os.path.join(job_dir, f"subtitles_{job_id}.vtt")
            srt_path = os.path.join(job_dir, f"subtitles_{job_id}.srt")
            SubtitleService.generate_webvtt(script.scenes, vtt_path)
            SubtitleService.generate_srt(script.scenes, srt_path)

            # Finalize
            self.update_job(job_id, current_stage="Finalizing", progress=95)
            self.add_log(job_id, "Finalizing files and cleaning up temp data...")
            
            # Expose paths as download links
            video_url = f"/api/video/{job_id}/download"
            self.update_job(
                job_id, 
                status="completed", 
                progress=100, 
                current_stage="Completed", 
                video_url=video_url
            )
            self.add_log(job_id, "Educational video compilation complete!")

        except Exception as e:
            self.update_job(job_id, status="failed", current_stage="Failed", error_message=str(e))
            self.add_log(job_id, f"CRITICAL ERROR in generation pipeline: {str(e)}")
            import traceback
            traceback.print_exc()

    async def regenerate_single_scene(
        self, 
        job_id: str, 
        scene_id: int, 
        title: str,
        narration: str, 
        visual_prompt: str, 
        on_screen_text: List[str]
    ) -> JobModel:
        """
        Regenerates visual or narration for a single scene and compiles the video again.
        Saves time by avoiding full script and static media regeneration for untouched scenes.
        """
        job = self._jobs.get(job_id)
        if not job or job.status != "completed":
            raise ValueError("Job not found or not in completed state.")

        script = job.script
        if not script or scene_id < 1 or scene_id > len(script.scenes):
            raise ValueError("Invalid scene ID.")

        job_dir = os.path.join(settings.STORAGE_PATH, "jobs", job_id)
        temp_dir = os.path.join(job_dir, "temp")

        # Set job status back to compiling
        self.update_job(job_id, status="generating", current_stage=f"Regenerating Scene {scene_id}", progress=50)
        self.add_log(job_id, f"Scene Editor: Regenerating scene {scene_id}...")

        # Update scene metadata in-memory
        scene = script.scenes[scene_id - 1]
        scene.title = title
        scene.narration = narration
        scene.visual_prompt = visual_prompt
        scene.on_screen_text = on_screen_text

        # Regenerate TTS Audio
        self.add_log(job_id, f"Scene Editor: Updating narration audio for scene {scene_id}...")
        audio_path = os.path.join(temp_dir, f"scene_{scene_id:03d}.wav")
        # Ensure old files are cleaned
        if os.path.exists(audio_path):
            os.remove(audio_path)
        actual_duration = await self.tts.generate_narration(scene.narration, audio_path)
        scene.audio_path = audio_path
        scene.actual_duration = actual_duration

        # Regenerate Slide Image
        self.add_log(job_id, f"Scene Editor: Updating visual diagram for scene {scene_id}...")
        image_path = os.path.join(temp_dir, f"scene_{scene_id:03d}.png")
        if os.path.exists(image_path):
            os.remove(image_path)
        await self.image_service.generate_image(
            scene.visual_prompt, image_path, title=scene.title, on_screen_text=scene.on_screen_text
        )
        scene.image_path = image_path

        # Re-render affected MP4 clip
        self.add_log(job_id, f"Scene Editor: Re-compiling clip for scene {scene_id}...")
        clip_path = os.path.join(temp_dir, f"scene_{scene_id:03d}.mp4")
        if os.path.exists(clip_path):
            os.remove(clip_path)
        VideoRenderer.render_scene_clip(scene, temp_dir)

        # Re-concatenate all clips (fast!)
        self.update_job(job_id, current_stage="Stitching clips together", progress=85)
        self.add_log(job_id, "Scene Editor: Re-stitching all video clips...")
        
        clip_paths = []
        for s in script.scenes:
            c_path = os.path.join(temp_dir, f"scene_{s.id:03d}.mp4")
            clip_paths.append(c_path)

        final_video_path = os.path.join(job_dir, f"final_output_{job_id}.mp4")
        VideoRenderer.concatenate_clips(clip_paths, final_video_path)

        # Re-compile Subtitles
        self.add_log(job_id, "Scene Editor: Re-compiling subtitles...")
        vtt_path = os.path.join(job_dir, f"subtitles_{job_id}.vtt")
        srt_path = os.path.join(job_dir, f"subtitles_{job_id}.srt")
        SubtitleService.generate_webvtt(script.scenes, vtt_path)
        SubtitleService.generate_srt(script.scenes, srt_path)

        # Restore Completed Status
        self.update_job(job_id, status="completed", progress=100, current_stage="Completed")
        self.add_log(job_id, f"Scene Editor: Scene {scene_id} regenerated and video re-rendered successfully!")

        return job
