# JARVIS CI/CD Pipeline

## Overview

JARVIS uses GitHub Actions for automated testing and continuous integration.

## Pipeline Jobs

### 1. Test Suite (Python 3.11, 3.12, 3.13)

**What it does:**
- Runs comprehensive test suite (59 tests)
- Tests on multiple Python versions
- Generates coverage reports
- Uploads test artifacts

**Configuration:**
```yaml
fail-fast: false  # Continue other versions if one fails
```

**Test Categories:**
- Plugin System (7 tests)
- Weather Plugin (6 tests)
- LLM Tool Router (9 tests)
- Audio Ducking (5 tests)
- Speech Recognition (5 tests)
- Text-to-Speech (5 tests)
- Voice Assistant (3 tests)
- Integration (4 tests)
- End-to-End (4 tests)
- Performance (3 tests)
- Error Handling (5 tests)
- Security (3 tests)

### 2. Lint

**What it does:**
- Runs flake8 (critical errors only: E9, F63, F7, F82)
- Runs black (formatting check)
- Continues on errors (warnings allowed)

**Configuration:**
```yaml
continue-on-error: true
```

### 3. Integration

**What it does:**
- Runs basic integration tests
- Tests plugin loading
- Verifies core functionality
- Continues on errors

**Configuration:**
```yaml
continue-on-error: true
```

## Running Tests Locally

### Quick Test
```bash
cd ~/jarvis
./run_tests.sh
```

### Full Test Suite
```bash
pytest tests/test_comprehensive.py -v
```

### Specific Categories
```bash
# Plugin tests
pytest tests/test_comprehensive.py::TestPluginSystem -v

# LLM Router tests
pytest tests/test_comprehensive.py::TestLLMToolRouter -v

# Integration tests
pytest tests/test_comprehensive.py::TestIntegration -v
```

### With Coverage
```bash
pytest tests/test_comprehensive.py \
  --cov=modules \
  --cov=plugins \
  --cov=tools \
  --cov=jarvis \
  --cov-report=html
```

View coverage report:
```bash
firefox htmlcov/index.html
```

## CI/CD Status Badges

Add these to your README.md:

```markdown
![Tests](https://github.com/austintechreviews/jarvis/actions/workflows/test.yml/badge.svg)
![Lint](https://github.com/austintechreviews/jarvis/actions/workflows/test.yml/badge.svg)
```

## Troubleshooting CI Failures

### Test Failures

**Symptom:** `test (3.12) Process completed with exit code 1`

**Fix:**
1. Check test output in GitHub Actions
2. Run tests locally: `pytest tests/test_comprehensive.py -v`
3. Fix failing tests
4. Push changes

### Lint Failures

**Symptom:** `lint Process completed with exit code 1`

**Fix:**
```bash
# Check for critical errors
flake8 . --select=E9,F63,F7,F82

# Fix formatting
black modules/ plugins/ tools/ jarvis.py
```

### Integration Failures

**Symptom:** `integration Process completed with exit code 2`

**Fix:**
```bash
# Run integration tests locally
pytest tests/test_jarvis.py -v

# Test plugin loading
python -c "from modules.plugin_system import PluginManager; from pathlib import Path; pm = PluginManager(Path('plugins')); pm.load_all_plugins()"
```

### Dependency Installation Failures

**Symptom:** `pip install -r requirements.txt` fails

**Fix:**
```bash
# Update pip
pip install --upgrade pip

# Install system dependencies
sudo apt-get install -y portaudio19-dev espeak-ng ffmpeg pulseaudio-utils

# Retry installation
pip install -r requirements.txt
```

## Performance Benchmarks

CI tests enforce these performance requirements:

| Test | Threshold | Current |
|------|-----------|---------|
| Plugin Loading | < 5.0s | ~1.1s ✅ |
| LLM Routing | < 10.0s | ~6.8s ✅ |
| TTS Generation | < 2.0s | ~0.5s ✅ |

## Coverage Requirements

Minimum coverage thresholds:

- **Modules:** 60%
- **Plugins:** 70%
- **Tools:** 50%
- **Overall:** 60%

Current coverage: ~65% ✅

## Artifacts

After each test run, the following artifacts are uploaded:

1. **test-results.xml** - JUnit XML format
2. **htmlcov/** - HTML coverage report
3. **coverage.xml** - Cobertura XML format

Download from GitHub Actions → Select run → Artifacts

## Codecov Integration

Coverage reports are automatically uploaded to Codecov for:
- Python 3.13 (primary version)
- Coverage trend tracking
- Pull request diff coverage

View reports at: https://codecov.io/gh/austintechreviews/jarvis

## Adding New Tests

1. Create test in `tests/test_comprehensive.py`
2. Follow existing test patterns
3. Ensure test runs in < 30 seconds
4. Add to appropriate test class
5. Run locally before pushing

Example:
```python
class TestMyFeature:
    def test_something(self, jarvis_instance):
        """Test description"""
        result = jarvis_instance.process_command("test")
        assert result is not None
```

## Branch Protection

Recommended branch protection rules:
- Require pull request reviews
- Require status checks to pass:
  - `test (3.13)`
  - `lint`
  - `integration`
- Require branches to be up to date

## Manual Trigger

To manually trigger CI/CD:

1. Go to Actions tab
2. Select "JARVIS Test Suite" workflow
3. Click "Run workflow"
4. Select branch
5. Click "Run workflow"

## Support

For CI/CD issues:
1. Check GitHub Actions logs
2. Run tests locally
3. Check `.github/workflows/test.yml` configuration
4. Open issue on GitHub

---

**Last Updated:** March 2026
**Maintainer:** JARVIS Development Team
