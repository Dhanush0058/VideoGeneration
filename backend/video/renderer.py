import os
import subprocess
from typing import List
from backend.models.scene import SceneModel

class VideoRenderer:
    @staticmethod
    def render_scene_clip(scene: SceneModel, temp_dir: str) -> str:
        """
        Renders a single scene into an MP4 clip with audio and optional zoom/pan animations.
        """
        img_path = scene.image_path
        audio_path = scene.audio_path
        duration = scene.actual_duration or scene.duration
        
        output_clip_path = os.path.join(temp_dir, f"scene_{scene.id:03d}.mp4")
        
        # Ensure input files exist
        if not img_path or not os.path.exists(img_path):
            raise FileNotFoundError(f"Scene image not found: {img_path}")
        if not audio_path or not os.path.exists(audio_path):
            raise FileNotFoundError(f"Scene audio not found: {audio_path}")

        # Choose FFmpeg command based on animation setting
        animation = scene.animation or "none"
        
        # Define base video filters for Ken Burns effect
        # zoompan filter requires specific formatting. We wrap it in a fallback to guarantee completion.
        filter_str = None
        if animation == "zoom_in":
            # Scale slightly larger, then zoom in towards center
            filter_str = f"scale=2048:1152,zoompan=z='min(zoom+0.0006,1.15)':d={int(duration * 25)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080,format=yuv420p"
        elif animation == "zoom_out":
            # Scale and zoom out
            filter_str = f"scale=2048:1152,zoompan=z='max(1.15-0.0006*on,1.0)':d={int(duration * 25)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080,format=yuv420p"
        elif animation == "pan_left":
            # Pan left to right
            filter_str = f"scale=2048:1152,zoompan=z=1.15:d={int(duration * 25)}:x='(1-on/{int(duration * 25)})*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':s=1920x1080,format=yuv420p"
        elif animation == "pan_right":
            # Pan right to left
            filter_str = f"scale=2048:1152,zoompan=z=1.15:d={int(duration * 25)}:x='(on/{int(duration * 25)})*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':s=1920x1080,format=yuv420p"

        # Construct FFmpeg command
        if filter_str:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-framerate", "25",
                "-i", img_path,
                "-i", audio_path,
                "-vf", filter_str,
                "-c:v", "libx264",
                "-t", str(duration),
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                output_clip_path
            ]
        else:
            # Static fallback command
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-framerate", "25",
                "-i", img_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-t", str(duration),
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                output_clip_path
            ]

        try:
            print(f"Rendering scene {scene.id} clip (Animation: {animation})...")
            # Run FFmpeg command
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Ken Burns rendering failed for scene {scene.id}: {e.stderr.decode('utf-8', errors='ignore')}")
            print("Retrying with static fallback command...")
            
            # Static fallback attempt
            fallback_cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-framerate", "25",
                "-i", img_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-t", str(duration),
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                output_clip_path
            ]
            subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            
        return output_clip_path

    @staticmethod
    def concatenate_clips(clip_paths: List[str], output_path: str) -> str:
        """
        Concatenates multiple scene MP4 files together into a single MP4 video file.
        Uses stream copy for fast compilation.
        """
        temp_dir = os.path.dirname(output_path)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Write list of clips to a text file for FFmpeg's concat demuxer
        concat_file_path = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_file_path, "w", encoding="utf-8") as f:
            for path in clip_paths:
                # FFmpeg concat demuxer requires absolute paths with forward slashes on Windows
                abs_path = os.path.abspath(path)
                safe_path = abs_path.replace("\\", "/")
                f.write(f"file '{safe_path}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file_path,
            "-c", "copy",
            output_path
        ]

        try:
            print("Concatenating all clips...")
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Fast concatenation failed: {e.stderr.decode('utf-8', errors='ignore')}")
            raise ValueError(f"Failed to concatenate scene clips: {str(e)}")
        finally:
            # Clean up the temp concat list file
            if os.path.exists(concat_file_path):
                os.remove(concat_file_path)

        return output_path
