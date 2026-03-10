"""
Text-to-speech using Microsoft Edge TTS
Natural, human-like voices powered by Azure

Features:
- Multiple voice options
- Audio ducking (reduces background audio when speaking)
- Volume control
"""

import logging
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AudioDucker:
    """
    Manages audio ducking - reduces background audio when JARVIS speaks
    """
    
    def __init__(self, ducking_level: float = 0.3):
        """
        Initialize audio ducker
        
        Args:
            ducking_level: Volume level during ducking (0.0-1.0)
                          0.3 = 30% volume during JARVIS speech
        """
        self.ducking_level = ducking_level
        self.original_volume = 1.0
        self.is_ducked = False
        self.pulse_available = self._check_pulseaudio()
        
    def _check_pulseaudio(self) -> bool:
        """Check if PulseAudio is available"""
        try:
            result = subprocess.run(
                ["pactl", "info"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def duck(self):
        """Reduce background audio volume"""
        if self.is_ducked:
            return
        
        try:
            if self.pulse_available:
                # Get current volume
                result = subprocess.run(
                    ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # Parse volume (format: "Volume: front-left: 65536 / 100%")
                if "100%" in result.stdout or "65536" in result.stdout:
                    self.original_volume = 1.0
                elif "%" in result.stdout:
                    vol_str = result.stdout.split("%")[0].split("/")[-1].strip()
                    self.original_volume = float(vol_str) / 100.0
                else:
                    self.original_volume = 1.0
                
                # Set reduced volume
                ducked_vol = int(self.ducking_level * 65536)
                subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{ducked_vol}"],
                    capture_output=True,
                    timeout=5
                )
                
                self.is_ducked = True
                logger.debug(f"Audio ducked to {self.ducking_level * 100}%")
            
        except Exception as e:
            logger.debug(f"Audio ducking failed: {str(e)}")
    
    def restore(self):
        """Restore original audio volume"""
        if not self.is_ducked:
            return
        
        try:
            if self.pulse_available:
                # Restore original volume
                original_vol = int(self.original_volume * 65536)
                subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{original_vol}"],
                    capture_output=True,
                    timeout=5
                )
                
                self.is_ducked = False
                logger.debug(f"Audio restored to {self.original_volume * 100}%")
            
        except Exception as e:
            logger.debug(f"Audio restore failed: {str(e)}")
    
    def __enter__(self):
        """Context manager entry"""
        self.duck()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.restore()


class TextToSpeech:
    """
    Convert text to speech using Microsoft Edge TTS

    Voices available (free, no API key):
    - en-GB-RyanNeural (Female, warm, friendly)
    - en-US-GuyNeural (Male, professional)
    - en-US-AriaNeural (Female, expressive)
    - en-US-DavisNeural (Male, warm)
    - en-GB-SoniaNeural (British Female)
    - en-GB-RyanNeural (British Male)
    """

    def __init__(
        self,
        voice: str = "en-GB-RyanNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        enable_ducking: bool = True,
        ducking_level: float = 0.3
    ):
        """
        Initialize text-to-speech

        Args:
            voice: Voice name (see list above)
            rate: Speech rate (+50% faster, -50% slower)
            volume: Volume (+50% louder, -50% quieter)
            pitch: Pitch (+50Hz higher, -50Hz lower)
            enable_ducking: Reduce background audio when speaking
            ducking_level: Volume during ducking (0.0-1.0)
        """
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        
        # Audio ducking
        self.enable_ducking = enable_ducking
        self.ducker = AudioDucker(ducking_level=ducking_level) if enable_ducking else None
        
        logger.info(f"✓ Edge TTS initialized with voice: {voice}")
        if enable_ducking:
            logger.info(f"✓ Audio ducking enabled (level: {ducking_level * 100}%)")

    def speak(self, text: str, wait: bool = True, duck_audio: bool = True):
        """
        Speak text using Edge TTS

        Args:
            text: Text to speak
            wait: Block until speech finishes
            duck_audio: Reduce background audio while speaking
        """
        logger.info(f"Speaking: {text[:50]}...")

        # Create temp file for audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        try:
            # Duck audio before generating speech
            if duck_audio and self.ducker:
                self.ducker.duck()

            # Generate speech using edge-tts
            asyncio.run(self._generate_speech(text, temp_path))

            # Check if file was created
            if not Path(temp_path).exists() or Path(temp_path).stat().st_size == 0:
                raise Exception("Edge TTS generated empty file")

            logger.info(f"Audio generated: {Path(temp_path).stat().st_size} bytes")

            # Play audio using system player
            if wait:
                logger.info("Playing audio...")
                self._play_audio(temp_path)
            else:
                # Non-blocking
                subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", temp_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

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
            # Restore audio volume after speaking
            if duck_audio and self.ducker:
                # Small delay to ensure speech finishes
                import time
                time.sleep(0.3)
                self.ducker.restore()
            
            # Clean up temp file
            try:
                Path(temp_path).unlink()
            except:
                pass

    async def _generate_speech(self, text: str, output_path: str):
        """Generate speech using Edge TTS"""
        import edge_tts

        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(str(output_path))

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
                subprocess.run(
                    player_cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30
                )
                return
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue

        logger.error("No audio player found. Install: sudo pacman -S ffmpeg")

    def speak_async(self, text: str, duck_audio: bool = True):
        """Speak without blocking"""
        self.speak(text, wait=False, duck_audio=duck_audio)

    def list_voices(self):
        """List available Edge TTS voices"""
        voices = [
            ("en-GB-RyanNeural", "Female, US, Warm & Friendly"),
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

    def set_ducking(self, enabled: bool, level: float = 0.3):
        """
        Enable/disable audio ducking
        
        Args:
            enabled: Enable ducking
            level: Volume level during ducking (0.0-1.0)
        """
        self.enable_ducking = enabled
        if enabled:
            self.ducker = AudioDucker(ducking_level=level)
            logger.info(f"Audio ducking enabled (level: {level * 100}%)")
        else:
            self.ducker = None
            logger.info("Audio ducking disabled")

    def cleanup(self):
        """Clean up (nothing to clean for Edge TTS)"""
        # Ensure audio is restored
        if self.ducker and self.ducker.is_ducked:
            self.ducker.restore()
