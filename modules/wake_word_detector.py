"""
Simple wake word detection using speech recognition
No API key required - uses Google's free speech recognition
"""

import logging
import pyaudio
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SimpleWakeWordDetector:
    """
    Simple wake word detection using continuous speech recognition
    No API key required, uses Google's free speech recognition
    """
    
    def __init__(self, wake_phrase: str = "hey jarvis"):
        """
        Initialize simple detector
        
        Args:
            wake_phrase: Phrase to detect (will use speech recognition)
        """
        self.wake_phrase = wake_phrase.lower()
        self.pa = pyaudio.PyAudio()
        self.is_listening = False
        
        # Import speech recognition
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
        except ImportError:
            raise ImportError("Install with: pip install SpeechRecognition")
        
        logger.info(f"Simple wake word detector: '{wake_phrase}'")
    
    def start_listening(self, callback: Callable[[], None]):
        """Start listening for wake phrase"""
        import speech_recognition as sr
        
        self.is_listening = True
        
        with sr.Microphone() as source:
            logger.info(f"Listening for: '{self.wake_phrase}'")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            while self.is_listening:
                try:
                    # Listen for audio (short timeout for responsiveness)
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=2)
                    
                    # Convert to text
                    try:
                        text = self.recognizer.recognize_google(audio).lower()
                        
                        # Check if wake phrase is in text
                        if self.wake_phrase in text:
                            logger.info(f"Wake phrase detected: {text}")
                            callback()
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError as e:
                        logger.debug(f"Recognition service error: {e}")
                        continue
                
                except sr.WaitTimeoutError:
                    continue
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.debug(f"Listen error: {e}")
                    continue
    
    def stop_listening(self):
        """Stop listening"""
        self.is_listening = False
    
    def cleanup(self):
        """Clean up"""
        self.stop_listening()
        if self.pa:
            self.pa.terminate()
