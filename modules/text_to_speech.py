"""
Text-to-speech using Microsoft Edge TTS
Natural, human-like voices powered by Azure
"""

import logging
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TextToSpeech:
    """
    Convert text to speech using Microsoft Edge TTS
    
    Voices available (free, no API key):
    - en-US-JennyNeural (Female, warm, friendly)
    - en-US-GuyNeural (Male, professional)
    - en-US-AriaNeural (Female, expressive)
    - en-US-DavisNeural (Male, warm)
    - en-GB-SoniaNeural (British Female)
    - en-GB-RyanNeural (British Male)
    """
    
    def __init__(
        self,
        voice: str = "en-US-JennyNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz"
    ):
        """
        Initialize text-to-speech
        
        Args:
            voice: Voice name (see list above)
            rate: Speech rate (+50% faster, -50% slower)
            volume: Volume (+50% louder, -50% quieter)
            pitch: Pitch (+50Hz higher, -50Hz lower)
        """
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        
        logger.info(f"✓ Edge TTS initialized with voice: {voice}")
    
    def speak(self, text: str, wait: bool = True):
        """
        Speak text using Edge TTS

        Args:
            text: Text to speak
            wait: Block until speech finishes
        """
        logger.info(f"Speaking: {text[:50]}...")

        # Create temp file for audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        try:
            # Generate speech using edge-tts
            logger.info("Generating speech with Edge TTS...")
            asyncio.run(self._generate_speech(text, temp_path))
            
            # Check if file was created
            import os
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise Exception("Edge TTS generated empty or missing file")
            
            logger.info(f"Audio generated: {os.path.getsize(temp_path)} bytes")

            # Play audio using system player
            if wait:
                logger.info("Playing audio...")
                self._play_audio(temp_path)
            else:
                # Non-blocking
                subprocess.Popen(["ffplay", "-nodisp", "-autoexit", temp_path],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)

        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            logger.info("Falling back to pyttsx3...")
            # Fallback to pyttsx3 if available
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 175)
                engine.say(text)
                engine.runAndWait()
            except Exception as fallback_error:
                logger.error(f"Fallback TTS also failed: {fallback_error}")
                print(f"JARVIS: {text}")  # Just print to console

        finally:
            # Clean up temp file
            try:
                Path(temp_path).unlink()
            except:
                pass
    
    async def _generate_speech(self, text: str, output_path: str):
        """Generate speech using Edge TTS"""
        import edge_tts
        
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch
        )
        
        await communicate.save(output_path)
    
    def _play_audio(self, audio_path: str):
        """Play audio file using system player"""
        # Try different players
        players = [
            ["ffplay", "-nodisp", "-autoexit", audio_path],
            ["aplay", audio_path],
            ["paplay", audio_path],
        ]
        
        for player_cmd in players:
            try:
                subprocess.run(player_cmd, check=True, 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             timeout=30)
                return
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        logger.error("No audio player found. Install: sudo pacman -S mpv or ffmpeg")
    
    def speak_async(self, text: str):
        """Speak without blocking"""
        self.speak(text, wait=False)
    
    def list_voices(self):
        """List available Edge TTS voices"""
        voices = [
            ("en-US-JennyNeural", "Female, US, Warm & Friendly"),
            ("en-US-GuyNeural", "Male, US, Professional"),
            ("en-US-AriaNeural", "Female, US, Expressive"),
            ("en-US-DavisNeural", "Male, US, Warm"),
            ("en-GB-SoniaNeural", "Female, British, Professional"),
            ("en-GB-RyanNeural", "Male, British, Professional"),
            ("en-AU-NatashaNeural", "Female, Australian"),
            ("en-AU-WilliamNeural", "Male, Australian"),
        ]
        
        print("\nAvailable Edge TTS Voices:")
        print("=" * 50)
        for voice, desc in voices:
            print(f"  {voice}")
            print(f"    → {desc}")
        print()
    
    def set_voice(self, voice: str):
        """Change voice"""
        self.voice = voice
        logger.info(f"Voice changed to: {voice}")
    
    def set_rate(self, rate_percent: int):
        """Change speech rate"""
        if rate_percent > 0:
            self.rate = f"+{rate_percent}%"
        else:
            self.rate = f"{rate_percent}%"
    
    def set_pitch(self, pitch_hz: int):
        """Change pitch"""
        if pitch_hz > 0:
            self.pitch = f"+{pitch_hz}Hz"
        else:
            self.pitch = f"{pitch_hz}Hz"
    
    def cleanup(self):
        """Clean up (nothing to clean for Edge TTS)"""
        pass


# Test TTS
if __name__ == "__main__":
    tts = TextToSpeech(voice="en-US-JennyNeural")
    tts.list_voices()
    tts.speak("Hello, I am JARVIS. Your intelligent assistant. How may I help you today?")
