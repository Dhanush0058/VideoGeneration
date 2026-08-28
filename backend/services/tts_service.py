import os
import asyncio
import subprocess
import wave
import edge_tts
from backend.config import settings

class TTSService:
    def __init__(self):
        self.provider = settings.TTS_PROVIDER.upper()
        self.default_voice = settings.TTS_VOICE

    async def generate_narration(self, text: str, output_path: str, voice: str = None) -> float:
        """
        Generates an audio file from text and returns the actual duration of the audio in seconds.
        """
        voice = voice or self.default_voice
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.provider == "EDGE_TTS":
            await self._generate_edge_tts(text, voice, output_path)
        else:
            self._generate_pyttsx3(text, output_path)

        # Calculate actual audio duration using ffprobe
        duration = self.get_audio_duration(output_path)
        return duration

    async def _generate_edge_tts(self, text: str, voice: str, output_path: str):
        """Generates audio using Microsoft Edge TTS (high quality, free API)."""
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
        except Exception as e:
            print(f"Edge TTS failed: {str(e)}. Falling back to offline local pyttsx3.")
            self._generate_pyttsx3(text, output_path)

    def _generate_pyttsx3(self, text: str, output_path: str):
        """Generates audio using pyttsx3 (fully offline, Windows SAPI5)."""
        try:
            import pyttsx3
            # Initialize pyttsx3 engine
            engine = pyttsx3.init()
            engine.save_to_file(text, output_path)
            engine.runAndWait()
        except Exception as e:
            print(f"pyttsx3 offline TTS failed: {str(e)}. Attempting gTTS fallback.")
            self._generate_gtts(text, output_path)

    def _generate_gtts(self, text: str, output_path: str):
        """Generates audio using gTTS (Google Translate TTS, basic online fallback)."""
        from gtts import gTTS
        tts = gTTS(text=text, lang='en')
        tts.save(output_path)

    def get_audio_duration(self, audio_path: str) -> float:
        """Retrieves exact duration of audio file using ffprobe (via subprocess)."""
        try:
            cmd = [
                "ffprobe", 
                "-v", "error", 
                "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", 
                audio_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            duration_str = result.stdout.strip()
            return float(duration_str)
        except Exception as e:
            print(f"Error measuring audio duration with ffprobe for {audio_path}: {e}")
            
            # Simple fallback for WAV files if ffprobe fails
            try:
                with wave.open(audio_path, 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    return frames / float(rate)
            except Exception:
                # Direct estimate based on word count (~140 words per minute)
                word_count = len(audio_path.split())
                return max(3.0, (word_count / 140.0) * 60.0)
