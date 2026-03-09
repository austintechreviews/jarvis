#!/bin/bash
# JARVIS Setup Script for Arch Linux
# Automates installation of all dependencies

set -e  # Exit on error

echo "╔═══════════════════════════════════════╗"
echo "║     JARVIS Installation Script        ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Arch Linux
if [ ! -f /etc/arch-release ]; then
    log_warn "This script is designed for Arch Linux."
    log_warn "Some commands may not work on other distributions."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: System update
log_info "Step 1: Updating system packages..."
#sudo pacman -Syu --noconfirm

# Step 2: Install base dependencies
log_info "Step 2: Installing base dependencies..."
sudo pacman -S --needed --noconfirm \
    python python-pip \
    python-venv \
    git base-devel \
    xdotool \
    xclip \
    scrot \
    firefox

# Step 3: Check/install Ollama
log_info "Step 3: Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    log_info "Ollama is already installed"
    ollama --version
else
    log_info "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Start Ollama service
    systemctl --user enable ollama
    systemctl --user start ollama
fi

# Step 4: Create Python virtual environment
log_info "Step 4: Setting up Python virtual environment..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    log_info "Virtual environment already exists"
else
    python -m venv venv
    log_info "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip setuptools wheel --quiet

# Step 5: Install Python dependencies
log_info "Step 5: Installing Python dependencies..."
pip install -r requirements.txt

# Step 6: Install Playwright browsers
log_info "Step 6: Installing Playwright browsers..."
playwright install chromium

# Step 7: Download LLM model
log_info "Step 7: Setting up LLM model..."
if ollama list | grep -q "qwen2.5-coder"; then
    log_info "Qwen2.5-Coder model already exists"
else
    log_info "Downloading Qwen2.5-Coder-3B model (this may take a while)..."
    ollama pull qwen2.5-coder:3b
fi

# Create custom model
if ollama list | grep -q "jarvis-brain"; then
    log_info "JARVIS brain model already exists"
else
    log_info "Creating JARVIS brain model..."
    ollama create jarvis-brain -f config/modelfile
fi

# Step 8: Create necessary directories
log_info "Step 8: Creating directories..."
mkdir -p logs backups data

# Step 9: Set permissions
log_info "Step 9: Setting permissions..."
chmod +x jarvis.py

# Step 10: Run tests (optional)
log_info "Step 10: Running basic tests..."
if python -m pytest tests/test_jarvis.py -v --tb=short; then
    log_info "All tests passed!"
else
    log_warn "Some tests failed. You can still use JARVIS."
fi

# Final summary
echo ""
echo "╔═══════════════════════════════════════╗"
echo "║     Installation Complete!            ║"
echo "╚═══════════════════════════════════════╝"
echo ""
echo "To start JARVIS:"
echo "  1. Activate virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Run JARVIS:"
echo "     python jarvis.py"
echo ""
echo "Or use the quick start script:"
echo "     ./start.sh"
echo ""
log_info "Happy automating! 🚀"
