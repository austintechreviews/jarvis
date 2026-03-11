"""
Comprehensive Unit Tests for JARVIS Fine-Tuning Framework
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from finetuning.data_collector import DataCollector
from finetuning.tools.prepare_training_data import DatasetPreparator, DataAugmenter, DatasetAnalyzer
from finetuning.tools.deploy_model import ModelDeployer


class TestDataCollector(unittest.TestCase):
    """Tests for DataCollector class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.collector = DataCollector(self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def test_init_creates_directories(self):
        """Test that initialization creates log directory"""
        self.assertTrue(self.test_dir.exists())
    
    def test_log_interaction(self):
        """Test logging an interaction"""
        interaction_id = self.collector.log_interaction(
            user_input="List files",
            assistant_response="ls -la",
            tool_used="terminal",
            success=True,
            execution_time=0.5
        )
        
        self.assertIsNotNone(interaction_id)
        self.assertTrue(self.collector.conversation_log.exists())
        
        # Verify log content
        with open(self.collector.conversation_log, 'r') as f:
            entry = json.loads(f.readline())
            self.assertEqual(entry['user'], "List files")
            self.assertEqual(entry['assistant'], "ls -la")
            self.assertTrue(entry['metadata']['success'])
    
    def test_log_user_correction(self):
        """Test logging a user correction"""
        correction_id = self.collector.log_user_correction(
            original_command="Delete files",
            assistant_attempt="rm -rf /",
            user_correction="rm *.txt",
            correction_type="command"
        )
        
        self.assertIsNotNone(correction_id)
        self.assertTrue(self.collector.feedback_log.exists())
        
        with open(self.collector.feedback_log, 'r') as f:
            entry = json.loads(f.readline())
            self.assertEqual(entry['correction'], "rm *.txt")
            self.assertEqual(entry['correction_type'], "command")
    
    def test_log_successful_pattern(self):
        """Test logging a successful pattern"""
        pattern_id = self.collector.log_successful_pattern(
            command="List Python files",
            execution="find . -name '*.py'",
            outcome="Found 5 files",
            frequency=3
        )
        
        self.assertIsNotNone(pattern_id)
        self.assertTrue(self.collector.patterns_log.exists())
    
    def test_get_stats(self):
        """Test getting statistics"""
        # Log some interactions
        self.collector.log_interaction("test1", "response1", success=True)
        self.collector.log_interaction("test2", "response2", success=False)
        self.collector.log_user_correction("orig", "attempt", "correction")
        
        stats = self.collector.get_stats()
        
        self.assertEqual(stats['total_interactions'], 2)
        self.assertEqual(stats['successful'], 1)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['corrections'], 1)
    
    def test_export_for_training(self):
        """Test exporting data for training"""
        self.collector.log_interaction("test1", "response1", success=True)
        self.collector.log_interaction("test2", "response2", success=True)
        self.collector.log_interaction("test3", "response3", success=False)
        
        output_file = self.test_dir / "export.jsonl"
        count, stats = self.collector.export_for_training(
            output_file,
            exclude_errors=True
        )
        
        self.assertEqual(count, 2)  # Only successful
        self.assertTrue(output_file.exists())
    
    def test_categorize_interaction(self):
        """Test interaction categorization"""
        categories = [
            ("List files", "file_ops"),
            ("Search for Python", "web_search"),
            ("Open Firefox", "browser"),
            ("Run install command", "terminal"),
            ("Take screenshot", "desktop"),
            ("Write Python script", "code"),
            ("Unknown thing", "other"),
        ]
        
        for input_text, expected in categories:
            result = self.collector._categorize_interaction(input_text)
            self.assertEqual(result, expected, f"Failed for: {input_text}")
    
    def test_quality_report(self):
        """Test quality report generation"""
        for i in range(150):
            self.collector.log_interaction(f"test{i}", f"response{i}", success=True)
        
        report = self.collector.get_quality_report()
        
        self.assertIn('statistics', report)
        self.assertIn('quality_metrics', report)
        self.assertIn('readiness', report)
        self.assertTrue(report['readiness']['ready'])
        self.assertEqual(report['readiness']['level'], 'good')


class TestDatasetPreparator(unittest.TestCase):
    """Tests for DatasetPreparator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.prep = DatasetPreparator(self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def test_clean_conversation(self):
        """Test conversation cleaning"""
        import os
        home = os.path.expanduser('~')
        conv = {
            "messages": [
                {"role": "user", "content": f"List files in {home}"},
                {"role": "assistant", "content": f"ls {home}"}
            ]
        }
        
        cleaned = self.prep.clean_conversation(conv)
        
        self.assertIn('~', cleaned['messages'][0]['content'])
        self.assertIn('~', cleaned['messages'][1]['content'])
    
    def test_remove_sensitive_data(self):
        """Test sensitive data removal"""
        text = "password=secret123 email@test.com 192.168.1.1 AKIAIOSFODNN7EXAMPLE"
        cleaned = self.prep._remove_sensitive_data(text)
        
        self.assertNotIn('secret123', cleaned)
        self.assertIn('[REDACTED]', cleaned)
        self.assertIn('[EMAIL]', cleaned)
        self.assertIn('[IP_ADDRESS]', cleaned)
    
    def test_deduplicate(self):
        """Test deduplication"""
        conversations = [
            {"messages": [{"role": "user", "content": "List files"}]},
            {"messages": [{"role": "user", "content": "List files"}]},  # Duplicate
            {"messages": [{"role": "user", "content": "Open file"}]},
        ]
        
        unique = self.prep.deduplicate(conversations)
        self.assertEqual(len(unique), 2)
    
    def test_balance_dataset(self):
        """Test dataset balancing"""
        conversations = [
            {"messages": [{"role": "user", "content": "file1"}], "category": "file_ops"},
            {"messages": [{"role": "user", "content": "file2"}], "category": "file_ops"},
            {"messages": [{"role": "user", "content": "file3"}], "category": "file_ops"},
            {"messages": [{"role": "user", "content": "web1"}], "category": "web_search"},
        ]
        
        balanced = self.prep.balance_dataset(conversations, max_per_category=2)
        file_ops_count = sum(1 for c in balanced if c['category'] == 'file_ops')
        self.assertLessEqual(file_ops_count, 2)


class TestDataAugmenter(unittest.TestCase):
    """Tests for DataAugmenter class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.augmenter = DataAugmenter()
    
    def test_augment_by_paraphrasing(self):
        """Test paraphrase augmentation"""
        conv = {
            "messages": [
                {"role": "user", "content": "List files"},
                {"role": "assistant", "content": "ls -la"}
            ],
            "category": "file_ops"
        }
        
        variations = self.augmenter.augment_by_paraphrasing(conv)
        
        self.assertGreater(len(variations), 0)
        # Check that variations have different user messages
        user_msgs = [v['messages'][0]['content'] for v in variations]
        self.assertNotIn("List files", user_msgs)  # Original should not be in variations
    
    def test_augment_with_context(self):
        """Test context augmentation"""
        conv = {
            "messages": [
                {"role": "user", "content": "Find files"},
                {"role": "assistant", "content": "find . -type f"}
            ],
            "category": "file_ops"
        }
        
        variations = self.augmenter.augment_with_context(conv)
        
        self.assertGreater(len(variations), 0)
        # Check that variations include location context
        for v in variations:
            self.assertIn('in', v['messages'][0]['content'])


class TestDatasetAnalyzer(unittest.TestCase):
    """Tests for DatasetAnalyzer class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.analyzer = DatasetAnalyzer(self.test_dir)
        
        # Create test data
        train_file = self.test_dir / "train.jsonl"
        with open(train_file, 'w') as f:
            for i in range(50):
                conv = {
                    "messages": [
                        {"role": "user", "content": f"Test {i}"},
                        {"role": "assistant", "content": f"Response {i}"}
                    ],
                    "category": "file_ops"
                }
                f.write(json.dumps(conv) + '\n')
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def test_analyze(self):
        """Test dataset analysis"""
        analysis = self.analyzer.analyze()
        
        self.assertIn('train', analysis)
        self.assertEqual(analysis['train']['count'], 50)
        self.assertIn('recommendations', analysis)


class TestModelDeployer(unittest.TestCase):
    """Tests for ModelDeployer class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.deployer = ModelDeployer(self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def test_create_modelfile(self):
        """Test Modelfile creation"""
        gguf_path = Path("/fake/path/model.gguf")
        modelfile_path = self.deployer.create_modelfile(gguf_path, "test-model", "v1")
        
        self.assertTrue(modelfile_path.exists())
        
        content = modelfile_path.read_text()
        self.assertIn("FROM /fake/path/model.gguf", content)
        self.assertIn("TEMPLATE", content)
        self.assertIn("PARAMETER temperature 0.3", content)
    
    def test_registry_operations(self):
        """Test registry save/load"""
        registry = {
            "test:v1": {
                "name": "test",
                "version": "v1",
                "created_at": datetime.now().isoformat()
            }
        }
        self.deployer._save_registry(registry)
        
        loaded = self.deployer._get_registry()
        self.assertIn("test:v1", loaded)


class TestIntegration(unittest.TestCase):
    """Integration tests for the fine-tuning framework"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.logs_dir = self.test_dir / "logs"
        self.data_dir = self.test_dir / "data"
        self.logs_dir.mkdir()
        self.data_dir.mkdir()
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def test_full_pipeline(self):
        """Test complete data collection to export pipeline"""
        # 1. Collect data
        collector = DataCollector(self.logs_dir)
        for i in range(20):
            collector.log_interaction(
                f"Command {i}",
                f"Response {i}",
                tool_used="terminal",
                success=True
            )
        
        # 2. Export for training
        export_file = self.logs_dir / "training.jsonl"
        count, _ = collector.export_for_training(export_file)
        self.assertEqual(count, 20)
        
        # 3. Prepare dataset
        prep = DatasetPreparator(self.logs_dir)
        result = prep.create_training_dataset(
            export_file,
            self.data_dir,
            validation_split=0.2
        )
        
        self.assertGreater(result['train'], 0)
        self.assertGreater(result['val'], 0)
        
        # 4. Analyze dataset
        analyzer = DatasetAnalyzer(self.data_dir)
        analysis = analyzer.analyze()
        
        self.assertIn('train', analysis)
        self.assertIn('val', analysis)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDataCollector))
    suite.addTests(loader.loadTestsFromTestCase(TestDatasetPreparator))
    suite.addTests(loader.loadTestsFromTestCase(TestDataAugmenter))
    suite.addTests(loader.loadTestsFromTestCase(TestDatasetAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestModelDeployer))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
