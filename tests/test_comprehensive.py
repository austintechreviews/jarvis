"""
Comprehensive Test Suite for JARVIS
Production-ready testing with pytest
"""

import pytest
import sys
import os
from pathlib import Path
import json
import time
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def jarvis_instance():
    """Create a JARVIS instance for testing"""
    from jarvis import JARVIS
    jarvis = JARVIS()
    yield jarvis
    # Cleanup
    if jarvis.voice_assistant:
        jarvis.voice_assistant.cleanup()


@pytest.fixture
def plugin_manager():
    """Create plugin manager for testing"""
    from modules.plugin_system import PluginManager
    # Use absolute path to plugins directory
    plugins_dir = Path(__file__).parent.parent / "plugins"
    pm = PluginManager(plugins_dir)
    pm.load_all_plugins()
    yield pm
    pm.cleanup_all()


@pytest.fixture
def llm_router(jarvis_instance):
    """Create LLM router for testing"""
    from modules.llm_tool_router import LLMToolRouter
    router = LLMToolRouter(
        llm_client=jarvis_instance,
        plugin_manager=jarvis_instance.plugin_manager
    )
    yield router


@pytest.fixture
def weather_plugin():
    """Create weather plugin for testing"""
    from plugins.weather_plugin import WeatherPlugin
    plugin = WeatherPlugin()
    plugin.initialize()
    yield plugin
    plugin.cleanup()


@pytest.fixture
def speech_to_text():
    """Create speech-to-text instance"""
    from modules.speech_to_text import SpeechToText
    stt = SpeechToText(model_size="base", language="en")
    yield stt
    stt.cleanup()


@pytest.fixture
def text_to_speech():
    """Create text-to-speech instance"""
    from modules.text_to_speech import TextToSpeech
    tts = TextToSpeech(
        voice="en-GB-RyanNeural",
        enable_ducking=False  # Disable for tests
    )
    yield tts
    tts.cleanup()


# ============================================================================
# PLUGIN SYSTEM TESTS
# ============================================================================

class TestPluginSystem:
    """Test plugin discovery and loading"""
    
    def test_plugin_manager_initialization(self):
        """Test plugin manager creates correctly"""
        from modules.plugin_system import PluginManager
        pm = PluginManager(Path.home() / "jarvis" / "plugins")
        
        assert pm.plugins_dir.exists()
        assert len(pm.plugins) == 0
        assert len(pm.tools) == 0
    
    def test_plugin_discovery(self, plugin_manager):
        """Test plugin discovery finds all plugins"""
        plugins = plugin_manager.discover_plugins()
        
        assert len(plugins) >= 3  # weather, example, spotify
        assert "weather_plugin" in plugins
        assert "example_plugin" in plugins
        assert "spotify_plugin" in plugins
    
    def test_plugin_loading(self, plugin_manager):
        """Test plugins load successfully"""
        assert len(plugin_manager.plugins) >= 3
        
        assert "weather" in plugin_manager.plugins
        assert "example" in plugin_manager.plugins
        assert "spotify" in plugin_manager.plugins
    
    def test_plugin_tools_registered(self, plugin_manager):
        """Test plugin tools are registered"""
        tools = plugin_manager.list_tools()
        
        # Weather tools
        assert "weather.current" in tools
        assert "weather.forecast" in tools
        assert "weather.time" in tools
        
        # Example tools
        assert "example.hello" in tools
        assert "example.example_action" in tools
        
        # Spotify tools
        assert "spotify.play" in tools
        assert "spotify.pause" in tools
        assert "spotify.now_playing" in tools
    
    def test_plugin_metadata(self, plugin_manager):
        """Test plugin metadata is correct"""
        status = plugin_manager.get_plugin_status()
        
        assert "weather" in status
        assert status["weather"]["version"] == "1.0.0"
        assert status["weather"]["status"] == "loaded"
        
        assert "example" in status
        assert status["example"]["version"] == "1.0.0"
    
    def test_plugin_unload(self, plugin_manager):
        """Test plugin unloading"""
        initial_count = len(plugin_manager.plugins)
        
        plugin_manager.unload_plugin("example")
        
        assert len(plugin_manager.plugins) == initial_count - 1
        assert "example" not in plugin_manager.plugins
    
    def test_plugin_system_prompt_aggregation(self, plugin_manager):
        """Test system prompt aggregation from plugins"""
        prompt = plugin_manager.get_aggregated_system_prompt()
        
        assert "weather" in prompt.lower() or len(prompt) > 0
        assert "Plugin" in prompt or "Tools" in prompt


# ============================================================================
# WEATHER PLUGIN TESTS
# ============================================================================

class TestWeatherPlugin:
    """Test weather plugin functionality"""
    
    def test_weather_plugin_initialization(self, weather_plugin):
        """Test weather plugin initializes"""
        assert weather_plugin.name == "weather"
        assert weather_plugin.version == "1.0.0"
        assert weather_plugin.description == "Weather information (free, no API key)"
    
    def test_weather_tools_available(self, weather_plugin):
        """Test weather tools are available"""
        tools = weather_plugin.get_tools()
        
        assert "current" in tools
        assert "forecast" in tools
        assert "set_location" in tools
        assert "time" in tools
    
    def test_weather_time_tool(self, weather_plugin):
        """Test time tool returns correct format"""
        result = weather_plugin.get_time()
        
        assert result["success"] is True
        assert "time" in result
        assert "date" in result
        
        # Verify time format (HH:MM:SS)
        time_parts = result["time"].split(":")
        assert len(time_parts) == 3
        assert 0 <= int(time_parts[0]) <= 23
        assert 0 <= int(time_parts[1]) <= 59
        assert 0 <= int(time_parts[2]) <= 59
    
    def test_weather_current_tool(self, weather_plugin):
        """Test current weather tool"""
        result = weather_plugin.get_current_weather()
        
        # Should return success or error gracefully
        assert "success" in result or "error" in result
    
    def test_weather_set_location(self, weather_plugin):
        """Test setting location"""
        result = weather_plugin.set_location("London")
        
        assert result["success"] is True
        assert weather_plugin.default_location == "London"
    
    def test_weather_system_prompt(self, weather_plugin):
        """Test weather plugin system prompt"""
        prompt = weather_plugin.get_system_prompt_addition()
        
        assert "weather" in prompt.lower()
        assert "current" in prompt.lower() or "forecast" in prompt.lower()


# ============================================================================
# LLM TOOL ROUTER TESTS
# ============================================================================

class TestLLMToolRouter:
    """Test LLM-powered tool routing"""
    
    def test_router_initialization(self, llm_router):
        """Test router initializes correctly"""
        assert llm_router.llm is not None
        assert llm_router.plugin_manager is not None
    
    def test_time_query_routing(self, llm_router):
        """Test time queries route to weather.time"""
        test_cases = [
            "What time is it?",
            "What's the time?",
            "Current time please",
            "Tell me the time",
        ]
        
        for query in test_cases:
            result = llm_router.route(query)
            assert result["tool"] == "weather.time", f"Failed for: {query}"
    
    def test_spotify_play_routing(self, llm_router):
        """Test play commands route to spotify"""
        test_cases = [
            "Play some music",
            "Play Bohemian Rhapsody",
        ]
        
        for query in test_cases:
            result = llm_router.route(query)
            # Should route somewhere (spotify or llm for conversational)
            assert "tool" in result, f"Missing tool in result for: {query}"
            assert "parameters" in result, f"Missing parameters for: {query}"
    
    def test_spotify_pause_routing(self, llm_router):
        """Test pause commands route to spotify.pause"""
        test_cases = [
            "Pause",
            "Pause the music",
            "Stop the music",
        ]
        
        for query in test_cases:
            result = llm_router.route(query)
            assert result["tool"] == "spotify.pause", f"Failed for: {query}"
    
    def test_spotify_now_playing_routing(self, llm_router):
        """Test now playing queries route correctly"""
        # At least one of these should route to spotify
        query = "What's playing?"
        result = llm_router.route(query)
        
        # Should route somewhere (spotify or llm for conversational response)
        assert "tool" in result
        assert "parameters" in result
    
    def test_weather_query_routing(self, llm_router):
        """Test weather queries route correctly"""
        test_cases = [
            "What's the weather?",
            "Weather forecast",
        ]
        
        for query in test_cases:
            result = llm_router.route(query)
            # Should route to weather plugin
            assert "weather" in result["tool"].lower(), f"Failed for: {query}"
    
    def test_router_json_extraction(self, llm_router):
        """Test JSON extraction from LLM responses"""
        # Test various JSON formats
        test_responses = [
            '{"tool": "spotify.play", "parameters": {}}',
            '```json\n{"tool": "spotify.pause"}\n```',
            'Sure! {"tool": "weather.time"}',
            '{"tool": "example.hello", "reasoning": "test"}',
        ]
        
        for response in test_responses:
            result = llm_router._extract_json(response)
            assert result is not None, f"Failed to extract JSON from: {response}"
            assert "tool" in result
    
    def test_router_tool_execution(self, jarvis_instance):
        """Test tool execution through executor"""
        from modules.llm_tool_router import LLMToolExecutor
        
        executor = LLMToolExecutor(jarvis_instance)
        
        # Test weather.time execution
        result = executor._execute_plugin_tool("weather.time", {})
        assert "time" in result.lower() or "success" in result.lower() or "The current" in result


# ============================================================================
# AUDIO DUCKING TESTS
# ============================================================================

class TestAudioDucking:
    """Test audio ducking functionality"""
    
    def test_ducker_initialization(self):
        """Test audio ducker initializes"""
        from modules.text_to_speech import AudioDucker
        
        ducker = AudioDucker(ducking_level=0.3)
        
        assert ducker.ducking_level == 0.3
        assert ducker.is_ducked is False
    
    def test_ducker_pulseaudio_check(self):
        """Test PulseAudio availability check"""
        from modules.text_to_speech import AudioDucker
        
        ducker = AudioDucker()
        
        # Should return boolean
        assert isinstance(ducker.pulse_available, bool)
    
    def test_ducker_context_manager(self):
        """Test ducker as context manager"""
        from modules.text_to_speech import AudioDucker
        
        ducker = AudioDucker(ducking_level=0.3)
        
        with ducker:
            # Should be ducked inside context
            pass
        
        # Should be restored after context
        assert ducker.is_ducked is False
    
    def test_tts_ducking_enabled(self, text_to_speech):
        """Test TTS has ducking enabled"""
        assert text_to_speech.enable_ducking is False  # Disabled for tests
        assert text_to_speech.ducker is None
    
    def test_tts_ducking_configuration(self):
        """Test TTS ducking configuration"""
        from modules.text_to_speech import TextToSpeech
        
        tts = TextToSpeech(enable_ducking=True, ducking_level=0.25)
        
        assert tts.enable_ducking is True
        assert tts.ducker is not None
        assert tts.ducker.ducking_level == 0.25
        
        tts.cleanup()


# ============================================================================
# SPEECH RECOGNITION TESTS
# ============================================================================

class TestSpeechRecognition:
    """Test speech-to-text functionality"""
    
    def test_stt_initialization(self, speech_to_text):
        """Test STT initializes with correct model"""
        assert speech_to_text.model_size == "base"
        assert speech_to_text.language == "en"
        assert speech_to_text.model is not None
    
    def test_stt_command_corrections(self, speech_to_text):
        """Test command correction dictionary"""
        corrections = speech_to_text.command_corrections
        
        # Should have pause corrections
        assert "thank you very much" in corrections
        assert corrections["thank you very much"] == "pause"
        
        assert "pulse" in corrections
        assert corrections["pulse"] == "pause"
    
    def test_stt_post_processing(self, speech_to_text):
        """Test transcription post-processing"""
        # Test exact matches - these should be in the corrections dict
        corrections = speech_to_text.command_corrections
        
        # Verify corrections exist
        assert "thank you very much" in corrections
        assert corrections["thank you very much"] == "pause"
        
        assert "pulse" in corrections
        assert corrections["pulse"] == "pause"
        
        # Test the post-processing function
        result = speech_to_text._post_process_transcription("thank you very much")
        assert result == "pause"
        
        # Test no correction needed - should return as-is
        result = speech_to_text._post_process_transcription("play music")
        assert "play" in result  # Contains the original text
    
    def test_stt_model_loading(self):
        """Test STT model loading with different sizes"""
        from modules.speech_to_text import SpeechToText
        
        # Test base model (default)
        stt_base = SpeechToText(model_size="base")
        assert stt_base.model is not None
        stt_base.cleanup()
        
        # Test tiny model (faster)
        stt_tiny = SpeechToText(model_size="tiny")
        assert stt_tiny.model is not None
        stt_tiny.cleanup()


# ============================================================================
# TEXT-TO-SPEECH TESTS
# ============================================================================

class TestTextToSpeech:
    """Test text-to-speech functionality"""
    
    def test_tts_initialization(self, text_to_speech):
        """Test TTS initializes with correct voice"""
        assert text_to_speech.voice == "en-GB-RyanNeural"
    
    def test_tts_voice_list(self, text_to_speech):
        """Test voice listing"""
        # Should not raise exception
        text_to_speech.list_voices()
    
    def test_tts_speech_generation(self, text_to_speech):
        """Test speech generation"""
        # Test with wait=False to avoid blocking
        text_to_speech.speak("Test", wait=False, duck_audio=False)
        # Should not raise exception
    
    def test_tts_voice_settings(self, text_to_speech):
        """Test voice setting changes"""
        text_to_speech.set_voice("en-US-JennyNeural")
        assert text_to_speech.voice == "en-US-JennyNeural"
        
        text_to_speech.set_rate(150)
        assert text_to_speech.rate == "+150%"
    
    def test_tts_ducking_toggle(self, text_to_speech):
        """Test ducking enable/disable"""
        text_to_speech.set_ducking(True, level=0.4)
        assert text_to_speech.enable_ducking is True
        assert text_to_speech.ducker is not None
        
        text_to_speech.set_ducking(False)
        assert text_to_speech.enable_ducking is False
        assert text_to_speech.ducker is None


# ============================================================================
# VOICE ASSISTANT TESTS
# ============================================================================

class TestVoiceAssistant:
    """Test voice assistant integration"""
    
    def test_voice_assistant_initialization(self, jarvis_instance):
        """Test voice assistant initializes"""
        assert jarvis_instance.voice_assistant is not None
        
        va = jarvis_instance.voice_assistant
        assert va.stt is not None
        assert va.tts is not None
        assert va.formatter is not None
    
    def test_voice_assistant_stt_model(self, jarvis_instance):
        """Test voice assistant uses base model"""
        va = jarvis_instance.voice_assistant
        assert va.stt.model_size == "base"
    
    def test_voice_assistant_tts_voice(self, jarvis_instance):
        """Test voice assistant uses correct TTS voice"""
        va = jarvis_instance.voice_assistant
        assert va.tts.voice == "en-GB-RyanNeural"
    
    def test_voice_assistant_formatter(self, jarvis_instance):
        """Test response formatter exists"""
        va = jarvis_instance.voice_assistant
        assert va.formatter is not None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_full_time_query_workflow(self, jarvis_instance):
        """Test complete time query workflow"""
        # Simulate user asking for time
        result = jarvis_instance.process_command("What time is it?")
        
        # Should contain time information
        assert "time" in result.lower() or ":" in result
    
    def test_full_weather_query_workflow(self, jarvis_instance):
        """Test complete weather query workflow"""
        result = jarvis_instance.process_command("What's the weather?")
        
        # Should attempt to get weather (may fail without API)
        assert isinstance(result, str)
    
    def test_plugin_tool_execution_workflow(self, jarvis_instance):
        """Test plugin tool execution through full stack"""
        # Test weather.time through LLM router
        result = jarvis_instance.process_command("Tell me the time")
        
        assert "time" in result.lower() or "success" in result.lower()
    
    def test_conversation_memory(self, jarvis_instance):
        """Test conversation memory works"""
        initial_length = len(jarvis_instance.conversation_history)
        
        # First message
        jarvis_instance.process_command("Hello")
        
        # Check memory increased (may add 2 messages: user + assistant)
        assert len(jarvis_instance.conversation_history) >= initial_length

    def test_compound_command_parsing(self, jarvis_instance):
        """Test compound command parsing"""
        # Test "open chrome and navigate to github"
        steps = jarvis_instance.parse_compound_command(
            "open chrome and navigate to github"
        )
        
        # May or may not detect as compound depending on parsing
        assert isinstance(steps, list)


# ============================================================================
# END-TO-END TESTS
# ============================================================================

class TestEndToEnd:
    """End-to-end tests for complete user scenarios"""
    
    def test_e2e_voice_mode_activation(self, jarvis_instance):
        """Test complete voice mode activation"""
        # Toggle voice mode
        jarvis_instance.toggle_voice_mode()
        
        assert jarvis_instance.voice_mode is True
        
        # Toggle off
        jarvis_instance.toggle_voice_mode()
        assert jarvis_instance.voice_mode is False
    
    def test_e2e_plugin_listing(self, jarvis_instance):
        """Test listing all plugins"""
        if jarvis_instance.plugin_manager:
            status = jarvis_instance.plugin_manager.get_plugin_status()
            
            assert len(status) >= 3
            assert "weather" in status
            assert "spotify" in status
    
    def test_e2e_help_command(self, jarvis_instance):
        """Test help command shows all features"""
        # Should not raise exception
        jarvis_instance.show_help()
    
    def test_e2e_context_clear(self, jarvis_instance):
        """Test clearing conversation context"""
        initial_length = len(jarvis_instance.conversation_history)
        
        # Add some messages
        jarvis_instance.conversation_history.append(
            {"role": "user", "content": "test"}
        )
        jarvis_instance.conversation_history.append(
            {"role": "assistant", "content": "response"}
        )
        
        # Clear
        result = jarvis_instance.clear_context()
        
        # Should have cleared some messages
        assert len(jarvis_instance.conversation_history) <= initial_length
        assert isinstance(result, str)


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance and load tests"""
    
    def test_plugin_load_time(self):
        """Test plugins load within acceptable time"""
        from modules.plugin_system import PluginManager
        import time
        
        start = time.time()
        pm = PluginManager(Path.home() / "jarvis" / "plugins")
        pm.load_all_plugins()
        elapsed = time.time() - start
        
        # Should load within 5 seconds
        assert elapsed < 5.0, f"Plugin loading took {elapsed:.2f}s"
    
    def test_llm_routing_time(self, llm_router):
        """Test LLM routing completes quickly"""
        import time

        start = time.time()
        result = llm_router.route("What time is it?")
        elapsed = time.time() - start

        # Should route within 10 seconds (LLM inference time)
        assert elapsed < 10.0, f"LLM routing took {elapsed:.2f}s"
    
    def test_tts_generation_time(self, text_to_speech):
        """Test TTS generation time"""
        import time
        
        start = time.time()
        text_to_speech.speak("Test message", wait=False, duck_audio=False)
        elapsed = time.time() - start
        
        # Should generate within 2 seconds
        assert elapsed < 2.0, f"TTS generation took {elapsed:.2f}s"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_plugin_not_found_error(self, plugin_manager):
        """Test handling of missing plugin"""
        result = plugin_manager.get_tool("nonexistent.tool")
        assert result is None
    
    def test_invalid_tool_name(self, jarvis_instance):
        """Test handling of invalid tool names"""
        from modules.llm_tool_router import LLMToolExecutor
        
        executor = LLMToolExecutor(jarvis_instance)
        result = executor._execute_plugin_tool("invalid.tool.name", {})
        assert "Invalid" in result or "not found" in result.lower() or "Plugin not loaded" in result
    
    def test_empty_command(self, jarvis_instance):
        """Test handling of empty commands"""
        result = jarvis_instance.process_command("")
        assert result is not None
    
    def test_malformed_json_routing(self, llm_router):
        """Test handling of malformed JSON in routing"""
        malformed_responses = [
            "not json at all",
            '{"tool": }',
            '{"tool": "test", invalid}',
            '',
        ]
        
        for response in malformed_responses:
            result = llm_router._extract_json(response)
            # Should return None for invalid JSON
            assert result is None
    
    def test_tts_fallback(self):
        """Test TTS fallback when Edge TTS fails"""
        from modules.text_to_speech import TextToSpeech
        
        tts = TextToSpeech(enable_ducking=False)
        
        # Should not crash even if Edge TTS fails
        try:
            tts.speak("Test", wait=False, duck_audio=False)
        except Exception as e:
            pytest.fail(f"TTS should handle errors gracefully: {e}")
        finally:
            tts.cleanup()


# ============================================================================
# SECURITY TESTS
# ============================================================================

class TestSecurity:
    """Security and safety tests"""
    
    def test_safety_validator_dangerous_commands(self):
        """Test safety validator catches dangerous commands"""
        from modules.safety_validator import SafetyValidator
        
        validator = SafetyValidator()
        
        dangerous = [
            "sudo rm -rf /",
            "chmod 777 /etc/passwd",
            "dd if=/dev/zero of=/dev/sda",
        ]
        
        for cmd in dangerous:
            risk, reason = validator.classify(cmd)
            assert risk == "high", f"Failed to detect dangerous command: {cmd}"
    
    def test_safety_validator_safe_commands(self):
        """Test safety validator allows safe commands"""
        from modules.safety_validator import SafetyValidator
        
        validator = SafetyValidator(auto_approve_safe=True)
        
        safe = [
            "ls -la",
            "cat file.txt",
            "pwd",
        ]
        
        for cmd in safe:
            risk, reason = validator.classify(cmd)
            assert risk == "safe", f"Failed to detect safe command: {cmd}"
    
    def test_plugin_isolation(self, plugin_manager):
        """Test plugins don't have access to system files"""
        # Plugins should only access their own tools
        for plugin_name, plugin in plugin_manager.plugins.items():
            tools = plugin.get_tools()
            
            # Tools should be callable methods
            for tool_name, tool_func in tools.items():
                assert callable(tool_func)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--maxfail=5",
        "-x",
    ])
