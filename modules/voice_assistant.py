"""
Voice Assistant - WITH INTERRUPT CAPABILITY
Orchestrates wake word, STT, and TTS with intelligent response formatting
"""

import logging
import threading
import random
import time
from typing import Callable, Optional
from .wake_word_detector import SimpleWakeWordDetector
from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech
from .voice_response_formatter import VoiceResponseFormatter

logger = logging.getLogger(__name__)


class VoiceAssistant:
    """
    Complete voice assistant system with interrupt capability

    Flow:
    1. Listen for wake word ("Hey JARVIS")
    2. Play acknowledgment sound
    3. Listen for command
    4. Convert speech to text
    5. Process command (external handler)
    6. Convert response to speech
    7. Return to wake word listening
    
    NEW: Can be interrupted while speaking!
    """

    def __init__(
        self,
        command_handler: Callable[[str], str],
        llm_client=None,  # For response summarization (optional)
        wake_phrase: str = "hey jarvis",
        whisper_model: str = "tiny",  # Use tiny for faster loading
        speech_rate: str = "+0%",  # Edge TTS uses percentage string
        voice: str = "en-GB-RyanNeural"  # British male voice
    ):
        """
        Initialize voice assistant

        Args:
            command_handler: Function that processes commands and returns responses
            llm_client: LLM instance for response formatting
            wake_phrase: Wake word/phrase to activate
            whisper_model: Whisper model size
            speech_rate: TTS speech rate
            voice: TTS voice to use
        """
        self.command_handler = command_handler

        # Initialize components
        logger.info("Initializing voice assistant...")

        try:
            self.wake_detector = SimpleWakeWordDetector(wake_phrase=wake_phrase)
        except Exception as e:
            logger.error(f"Wake detector failed: {e}")
            raise

        try:
            self.stt = SpeechToText(model_size="base", language="en")  # Changed from "tiny" to "base"
        except Exception as e:
            logger.error(f"STT failed: {e}")
            raise

        try:
            self.tts = TextToSpeech(rate=speech_rate, voice=voice)
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            raise

        # Response formatter for intelligent summarization
        self.formatter = VoiceResponseFormatter(llm_client)

        logger.info("✓ Voice assistant ready (UK accent optimized, interrupt enabled)")

        self.is_running = False
        self.is_speaking = False  # Track if currently speaking
        self.listen_thread = None
        self.interrupt_event = threading.Event()  # For interrupting speech

    def start(self):
        """Start voice assistant in background thread"""
        if self.is_running:
            logger.warning("Voice assistant already running")
            return

        self.is_running = True
        self.interrupt_event.clear()

        # Start wake word detection in thread
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()

        logger.info("🎤 Voice assistant started (interrupt enabled)")
        self.tts.speak("Voice assistant online. Say the wake word to begin.", wait=False)

    def _listen_loop(self):
        """Main listening loop"""
        try:
            self.wake_detector.start_listening(callback=self._on_wake_word_detected)
        except Exception as e:
            logger.error(f"Listen loop error: {str(e)}", exc_info=True)
            self.is_running = False

    def _on_wake_word_detected(self):
        """Called when wake word is detected"""
        logger.info("Wake word detected!")

        # If currently speaking, interrupt!
        if self.is_speaking:
            logger.info("Interrupting current speech...")
            self.interrupt_event.set()  # Signal to stop speaking
            time.sleep(0.2)  # Brief pause
            self.interrupt_event.clear()

        # Choose random witty acknowledgment
        responses = [
            "Yes?",
            "At your service.",
            "Listening.",
            "Ready when you are.",
            "All ears.",
            "Go ahead, I'm listening.",
            "What can I do for you?",
            "Your wish?",
            "Online and ready.",
            "How may I assist?",
        ]
        response = random.choice(responses)
        self.tts.speak(response)

        # Listen for command
        try:
            command_text = self.stt.listen_for_command()

            if not command_text:
                self.tts.speak("I didn't catch that. Please try again.")
                return

            logger.info(f"Command: {command_text}")

            # Process command
            raw_response = self.command_handler(command_text)

            # Format response for speech using intelligent formatter
            voice_response = self.formatter.format_for_voice(
                raw_response,
                context=command_text
            )

            logger.info(f"Voice response: {voice_response[:100]}...")

            # Speak formatted response (can be interrupted)
            self._speak_with_interrupt(voice_response)

        except Exception as e:
            logger.error(f"Command processing error: {str(e)}")
            self.tts.speak("Sorry, I encountered an error processing that command.")

    def _speak_with_interrupt(self, text: str):
        """
        Speak text with ability to be interrupted
        
        Args:
            text: Text to speak
        """
        self.is_speaking = True
        self.interrupt_event.clear()

        try:
            # Speak in chunks to allow interruption
            sentences = text.split('.')
            
            for i, sentence in enumerate(sentences):
                # Check if interrupt was triggered
                if self.interrupt_event.is_set():
                    logger.info("Speech interrupted by user")
                    self.interrupt_event.clear()
                    break
                
                sentence = sentence.strip()
                if sentence:
                    # Add period back except for last sentence
                    if i < len(sentences) - 1:
                        sentence += "."
                    
                    self.tts.speak(sentence, wait=True)
                    
                    # Small pause between sentences for natural flow
                    if i < len(sentences) - 1:
                        time.sleep(0.3)
        
        finally:
            self.is_speaking = False

    def stop(self):
        """Stop voice assistant"""
        logger.info("Stopping voice assistant...")

        self.is_running = False
        self.interrupt_event.set()  # Stop any ongoing speech
        self.wake_detector.stop_listening()

        if self.listen_thread:
            self.listen_thread.join(timeout=2)

        self.is_speaking = False
        logger.info("Voice assistant stopped")

    def speak(self, text: str):
        """Manually speak text"""
        self.tts.speak(text)

    def cleanup(self):
        """Clean up all resources"""
        self.stop()
        self.wake_detector.cleanup()
        self.stt.cleanup()
        self.tts.cleanup()
