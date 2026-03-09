"""
Speech-to-text using Faster-Whisper
Converts your voice to text commands
Faster and more efficient than OpenAI Whisper
"""

import logging
import pyaudio
import wave
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SpeechToText:
    """
    Convert speech to text using Faster-Whisper
    
    Models available:
    - tiny: Fastest, least accurate (~500MB RAM)
    - base: Fast, good accuracy (~500MB RAM)
    - small: Balanced (~1GB RAM)
    - medium: High accuracy (~3GB RAM)
    - large: Best accuracy (~5GB RAM)
    """
    
    def __init__(
        self,
        model_size: str = "tiny",
        language: str = "en-GB"  # UK English accent
    ):
        """
        Initialize speech-to-text

        Args:
            model_size: Faster-Whisper model size
            language: Language code (en-GB for UK accent)
        """
        self.model_size = model_size
        self.language = language

        # Load Faster-Whisper model
        logger.info(f"Loading Faster-Whisper model: {model_size}")
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            logger.info("✓ Faster-Whisper model loaded (optimized for UK accent)")
        except Exception as e:
            logger.error(f"Failed to load Faster-Whisper: {e}")
            raise

        # Audio settings
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000

        self.pa = pyaudio.PyAudio()
    
    def listen_for_command(
        self,
        duration: Optional[int] = None,
        silence_threshold: int = 500,
        silence_duration: float = 1.5
    ) -> str:
        """
        Listen for voice command with automatic silence detection
        
        Args:
            duration: Maximum recording duration (None = unlimited)
            silence_threshold: Audio energy threshold for silence
            silence_duration: Seconds of silence before stopping
            
        Returns:
            Transcribed text
        """
        logger.info("🎤 Listening for command...")
        
        # Open audio stream
        stream = self.pa.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        frames = []
        silent_chunks = 0
        max_silent_chunks = int((self.RATE / self.CHUNK) * silence_duration)
        
        recording = True
        while recording:
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # Check audio energy
            audio_data = sum(abs(int.from_bytes(data[i:i+2], 'little', signed=True)) 
                           for i in range(0, len(data), 2))
            
            if audio_data < silence_threshold * self.CHUNK:
                silent_chunks += 1
            else:
                silent_chunks = 0
            
            # Stop if silent too long
            if silent_chunks > max_silent_chunks:
                logger.info("Silence detected, processing...")
                recording = False
            
            # Stop if max duration reached
            if duration and len(frames) > (self.RATE / self.CHUNK) * duration:
                recording = False
        
        stream.stop_stream()
        stream.close()
        
        # Save audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        
        wf = wave.open(temp_path, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.pa.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        # Transcribe with Faster-Whisper
        logger.info("Processing speech...")
        segments, info = self.model.transcribe(
            temp_path,
            language=self.language,
            vad_filter=True  # Voice activity detection
        )
        
        text = " ".join([segment.text for segment in segments]).strip()
        logger.info(f"Transcribed: {text}")
        
        # Clean up temp file
        Path(temp_path).unlink()
        
        return text
    
    def transcribe_file(self, audio_path: str) -> str:
        """
        Transcribe audio file
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text
        """
        segments, info = self.model.transcribe(audio_path, language=self.language)
        return " ".join([segment.text for segment in segments]).strip()
    
    def cleanup(self):
        """Clean up resources"""
        if self.pa:
            self.pa.terminate()
