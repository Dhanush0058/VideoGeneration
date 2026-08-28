import os
from typing import List
from backend.models.scene import SceneModel

class SubtitleService:
    @staticmethod
    def generate_webvtt(scenes: List[SceneModel], output_path: str):
        """
        Generates a standard WebVTT subtitle file.
        Splits scene narration into readable timed blocks and writes to output_path.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        vtt_content = ["WEBVTT\n"]
        current_time = 0.0

        for index, scene in enumerate(scenes):
            duration = scene.actual_duration or scene.duration
            narration = scene.narration
            
            # Split narration into smaller readable lines (approx. 8-12 words per slide)
            chunks = SubtitleService._split_into_chunks(narration)
            if not chunks:
                continue

            chunk_duration = duration / len(chunks)

            for c_idx, chunk in enumerate(chunks):
                start_val = current_time + (c_idx * chunk_duration)
                end_val = start_val + chunk_duration

                start_str = SubtitleService._format_timestamp(start_val)
                end_str = SubtitleService._format_timestamp(end_val)

                # WebVTT block
                vtt_content.append(f"{index + 1}_{c_idx + 1}")
                vtt_content.append(f"{start_str} --> {end_str}")
                vtt_content.append(f"{chunk.strip()}\n")

            current_time += duration

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(vtt_content))

    @staticmethod
    def generate_srt(scenes: List[SceneModel], output_path: str):
        """
        Generates a standard SRT subtitle file (typically for burning into video via FFmpeg).
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        srt_content = []
        current_time = 0.0
        counter = 1

        for scene in scenes:
            duration = scene.actual_duration or scene.duration
            narration = scene.narration
            
            chunks = SubtitleService._split_into_chunks(narration)
            if not chunks:
                continue

            chunk_duration = duration / len(chunks)

            for c_idx, chunk in enumerate(chunks):
                start_val = current_time + (c_idx * chunk_duration)
                end_val = start_val + chunk_duration

                start_str = SubtitleService._format_timestamp_srt(start_val)
                end_str = SubtitleService._format_timestamp_srt(end_val)

                srt_content.append(str(counter))
                srt_content.append(f"{start_str} --> {end_str}")
                srt_content.append(f"{chunk.strip()}\n")
                counter += 1

            current_time += duration

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))

    @staticmethod
    def _split_into_chunks(text: str, max_words: int = 10) -> List[str]:
        """Splits narration into readable phrases of around max_words length."""
        # Simple splitting by sentence endings or comma pauses first
        parts = re.split(r'(?<=[,.;!?])\s+', text)
        chunks = []
        
        for part in parts:
            words = part.split()
            if not words:
                continue
            
            # If a part is too long, chunk it by word count
            for i in range(0, len(words), max_words):
                chunk_words = words[i:i+max_words]
                chunks.append(" ".join(chunk_words))
                
        return chunks

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Formats seconds into WebVTT timestamp: HH:MM:SS.mmm"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        mils = int((seconds % 1) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{mils:03d}"

    @staticmethod
    def _format_timestamp_srt(seconds: float) -> str:
        """Formats seconds into SRT timestamp: HH:MM:SS,mmm"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        mils = int((seconds % 1) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{mils:03d}"

import re
