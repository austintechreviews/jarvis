"""
Test suite for JARVIS components
"""

import unittest
from pathlib import Path
import sys
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.safety_validator import SafetyValidator
from modules.file_manager import FileManager
from modules.web_search import WebSearcher


class TestSafetyValidator(unittest.TestCase):
    """Test safety validation system"""
    
    def setUp(self):
        self.validator = SafetyValidator(auto_approve_safe=True)
    
    def test_safe_commands(self):
        """Test that safe commands are classified correctly"""
        safe_commands = [
            "ls -la",
            "cat file.txt",
            "grep 'pattern' file.txt",
            "find . -name '*.py'",
            "pwd",
            "echo 'hello'",
        ]
        
        for cmd in safe_commands:
            risk, reason = self.validator.classify(cmd)
            self.assertEqual(risk, 'safe', f"Command '{cmd}' should be safe")
    
    def test_dangerous_commands(self):
        """Test that dangerous commands are classified correctly"""
        dangerous_commands = [
            "sudo rm -rf /",
            "rm -rf *",
            "chmod 777 /etc/passwd",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
        ]
        
        for cmd in dangerous_commands:
            risk, reason = self.validator.classify(cmd)
            self.assertEqual(risk, 'high', f"Command '{cmd}' should be high risk")
    
    def test_medium_risk_commands(self):
        """Test that potentially modifying commands are medium risk"""
        medium_commands = [
            "python script.py",
            "npm install",
            "make build",
        ]
        
        for cmd in medium_commands:
            risk, reason = self.validator.classify(cmd)
            self.assertEqual(risk, 'medium', f"Command '{cmd}' should be medium risk")


class TestFileManager(unittest.TestCase):
    """Test file management operations"""
    
    def setUp(self):
        self.file_manager = FileManager(backup_enabled=False)
        self.test_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test files"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_create_and_read_file(self):
        """Test file creation and reading"""
        test_file = self.test_dir / "test.txt"
        content = "Hello, JARVIS!"
        
        # Write file
        result = self.file_manager.write_file(str(test_file), content)
        self.assertTrue(result['success'])
        
        # Read file
        result = self.file_manager.read_file(str(test_file))
        self.assertTrue(result['success'])
        self.assertEqual(result['content'], content)
    
    def test_list_directory(self):
        """Test directory listing"""
        # Create test files
        for i in range(3):
            (self.test_dir / f"file{i}.txt").write_text("test")
        
        # List directory
        result = self.file_manager.list_directory(str(self.test_dir))
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 3)
    
    def test_search_files(self):
        """Test file search"""
        # Create test files
        (self.test_dir / "test1.py").write_text("# Python")
        (self.test_dir / "test2.py").write_text("# Python")
        (self.test_dir / "readme.md").write_text("# README")
        
        # Search for Python files
        result = self.file_manager.search_files(str(self.test_dir), "*.py")
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
    
    def test_copy_file(self):
        """Test file copying"""
        src = self.test_dir / "source.txt"
        dst = self.test_dir / "destination.txt"
        src.write_text("Test content")
        
        result = self.file_manager.copy_file(str(src), str(dst))
        self.assertTrue(result['success'])
        self.assertTrue(dst.exists())
        self.assertEqual(dst.read_text(), "Test content")
    
    def test_move_file(self):
        """Test file moving"""
        src = self.test_dir / "source.txt"
        dst = self.test_dir / "destination.txt"
        src.write_text("Test content")
        
        result = self.file_manager.move_file(str(src), str(dst))
        self.assertTrue(result['success'])
        self.assertTrue(dst.exists())
        self.assertFalse(src.exists())
    
    def test_delete_file(self):
        """Test file deletion"""
        test_file = self.test_dir / "to_delete.txt"
        test_file.write_text("Delete me")
        
        result = self.file_manager.delete_file(str(test_file), confirm=False)
        self.assertTrue(result['success'])
        self.assertFalse(test_file.exists())
    
    def test_get_file_info(self):
        """Test file info retrieval"""
        test_file = self.test_dir / "info.txt"
        test_file.write_text("Test content for info")
        
        result = self.file_manager.get_file_info(str(test_file))
        self.assertTrue(result['success'])
        self.assertIn('size', result['info'])
        self.assertIn('modified', result['info'])
        self.assertEqual(result['info']['name'], 'info.txt')
    
    def test_create_directory(self):
        """Test directory creation"""
        new_dir = self.test_dir / "new_folder" / "subfolder"
        
        result = self.file_manager.create_directory(str(new_dir))
        self.assertTrue(result['success'])
        self.assertTrue(new_dir.exists())


class TestWebSearcher(unittest.TestCase):
    """Test web search functionality"""
    
    def setUp(self):
        self.searcher = WebSearcher()
    
    def test_basic_search(self):
        """Test basic web search"""
        results = self.searcher.search("Python programming", max_results=3)
        
        self.assertIsInstance(results, list)
        
        # Check result structure (may be empty if offline)
        for result in results:
            self.assertIn('title', result)
            self.assertIn('snippet', result)
            self.assertIn('link', result)
    
    def test_search_with_max_results(self):
        """Test search respects max_results"""
        results = self.searcher.search("test query", max_results=1)
        
        # Should return at most 1 result
        self.assertLessEqual(len(results), 1)


class TestDesktopController(unittest.TestCase):
    """Test desktop control functionality"""
    
    def setUp(self):
        from tools.desktop_control import DesktopController
        self.controller = DesktopController()
    
    def test_get_screen_size(self):
        """Test screen size retrieval"""
        size = self.controller.get_screen_size()
        self.assertIsInstance(size, tuple)
        self.assertEqual(len(size), 2)
        self.assertGreater(size[0], 0)  # Width
        self.assertGreater(size[1], 0)  # Height
    
    def test_get_mouse_position(self):
        """Test mouse position retrieval"""
        pos = self.controller.get_mouse_position()
        self.assertIsInstance(pos, tuple)
        self.assertEqual(len(pos), 2)


if __name__ == "__main__":
    unittest.main()
