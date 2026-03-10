#!/bin/bash
# JARVIS Comprehensive Test Runner
# Runs all tests with coverage and generates reports

set -e

echo "╔═══════════════════════════════════════╗"
echo "║      JARVIS Test Suite Runner         ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Not in virtual environment${NC}"
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install test dependencies
echo "Installing test dependencies..."
pip install pytest pytest-cov pytest-asyncio pytest-mock -q

# Create test results directory
mkdir -p test_results

# Run tests
echo ""
echo "Running comprehensive test suite..."
echo "═══════════════════════════════════════"

pytest tests/test_comprehensive.py \
    -v \
    --tb=short \
    --maxfail=5 \
    --cov=modules \
    --cov=plugins \
    --cov=tools \
    --cov=jarvis \
    --cov-report=html:test_results/coverage \
    --cov-report=xml:test_results/coverage.xml \
    --junitxml=test_results/junit.xml \
    --html=test_results/report.html \
    --self-contained-html \
    -n auto || true

echo ""
echo "═══════════════════════════════════════"
echo ""

# Check test results
if [ -f "test_results/junit.xml" ]; then
    # Parse results
    TOTAL=$(grep -o 'tests="[0-9]*"' test_results/junit.xml | head -1 | grep -o '[0-9]*')
    FAILURES=$(grep -o 'failures="[0-9]*"' test_results/junit.xml | head -1 | grep -o '[0-9]*')
    ERRORS=$(grep -o 'errors="[0-9]*"' test_results/junit.xml | head -1 | grep -o '[0-9]*')
    
    echo "Test Results:"
    echo "  Total:  $TOTAL"
    echo "  Failed: $FAILURES"
    echo "  Errors: $ERRORS"
    echo ""
    
    if [ "$FAILURES" -eq 0 ] && [ "$ERRORS" -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        echo ""
        echo "Reports generated:"
        echo "  - HTML Report: test_results/report.html"
        echo "  - Coverage:    test_results/coverage/index.html"
        echo "  - JUnit XML:   test_results/junit.xml"
        exit 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        echo ""
        echo "Check test_results/report.html for details"
        exit 1
    fi
else
    echo -e "${RED}✗ Test execution failed${NC}"
    exit 1
fi
