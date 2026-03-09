# JARVIS - Desktop Control AI Assistant

An intelligent desktop automation assistant for Arch Linux with **conversation memory** and **LLM tool calling**, powered by local LLMs and SearXNG.

## ✨ Features

### Core Capabilities
- **💬 Conversation Memory** - Remembers context across messages (15 exchange history)
- **🧠 LLM Tool Calling** - LLM can parse and call tools automatically via JSON
- **🔍 Web Search** - SearXNG integration (your server: 192.168.1.248:8090)
- **🌐 Browser Automation** - Playwright-based navigation and interaction
- **📁 File Management** - CRUD operations with automatic backups
- **🚀 App Launcher** - Open Chrome, Firefox, VS Code, Terminal, etc.
- **🖱️ Desktop Control** - Mouse/keyboard automation via PyAutoGUI
- **⚡ Terminal Commands** - Direct execution for common commands
- **🛡️ Safety System** - Risk assessment for destructive commands
- **📝 Audit Logging** - Complete conversation and command logs

### Smart Features
- **Compound Command Parsing** - "open youtube.com in chrome" → 2 steps
- **URL Extraction** - "navigate to youtube" → youtube.com
- **News Search** - "latest news" → uses news search category
- **Context Commands** - `clear`, `compact` to manage memory

## 🚀 Quick Start

### Prerequisites
```bash
# System dependencies
sudo pacman -S --needed python python-pip xdotool xclip scrot firefox

# Ollama with model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:3b
```

### Installation
```bash
cd ~/Documents/jarvis

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright (optional)
playwright install chromium
```

### Run JARVIS
```bash
python jarvis.py
```

## 💬 Example Commands

### Application Launch
```
• "Open Chrome"
• "Launch Firefox"
• "Open VS Code"
• "open youtube.com in chrome"  ← Compound command!
```

### Browser Navigation
```
• "Navigate to youtube.com"
• "Go to github"  ← Auto-adds .com!
• "Visit reddit"
• "browse to wikipedia"
```

### Web Search (SearXNG)
```
• "Search for Python tutorials"
• "What is the latest news"  ← Uses news category
• "Find machine learning resources"
• "What is quantum computing"
```

### File Operations
```
• "List files in Downloads"
• "Show files in Documents"
• "What files are in root folder"
```

### System Commands
```
• "What time is it"
• "run whoami"
• "Take a screenshot"
```

### Context Management
```
• "My name is Austin"  ← Stored in memory
• "What's my name?"  ← Remembers!
• "clear"  ← Reset conversation
• "compact"  ← Summarize context
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    JARVIS Core                           │
│  (Orchestration + Conversation Memory + LLM Tool Call)  │
└────┬──────────────────────────────────────────┬─────────┘
     │                                          │
┌────▼───────┐                          ┌──────▼────────┐
│ LLM Brain  │                          │ Tool Router   │
│ qwen2.5-   │◄──── Conversation ──────►│ + Parser      │
│ coder:3B   │      Memory (15)         │               │
└────┬───────┘                          └──────┬────────┘
     │                                          │
     └──────────────────┬───────────────────────┘
                        │
     ┌──────────────────┼───────────────────┐
     │                  │                   │
┌────▼────┐      ┌─────▼─────┐      ┌──────▼──────┐
│ Web     │      │ Browser   │      │ File        │
│ Search  │      │ Controller│      │ Manager     │
│SearXNG  │      │Playwright │      │             │
└─────────┘      └───────────┘      └─────────────┘
     │                  │                   │
┌────▼──────┐   ┌──────▼──────┐   ┌────────▼───────┐
│App        │   │ Desktop     │   │ Terminal       │
│Launcher   │   │ Control     │   │ Executor       │
└───────────┘   └─────────────┘   └────────────────┘
```

## 📁 Project Structure

```
jarvis/
├── jarvis.py                    # Main orchestrator
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── config/
│   ├── system_prompt.txt        # LLM instructions
│   └── modelfile                # Ollama config
├── modules/
│   ├── __init__.py
│   ├── safety_validator.py      # Safety system
│   ├── file_manager.py          # File operations
│   ├── web_search.py            # SearXNG search
│   └── browser_controller.py    # Browser automation
├── tools/
│   ├── __init__.py
│   ├── desktop_control.py       # Desktop automation
│   └── app_launcher.py          # App launcher
├── tests/
│   └── test_jarvis.py           # Test suite
└── logs/                        # Auto-created logs
```

## 🔧 Configuration

### SearXNG Server
Edit `modules/web_search.py` to change your SearXNG URL:
```python
self.searxng_url = "http://192.168.1.248:8090"
```

### LLM Model
Edit `jarvis.py` to change the model:
```python
self.llm_model = "qwen2.5-coder:3b"  # or "llama3.2:3b", etc.
```

### Conversation Memory Size
```python
self.max_history_pairs = 15  # Keep last 15 exchanges
```

## 🧪 Testing

```bash
# Run test suite
python -m pytest tests/test_jarvis.py -v

# Expected: 14/15 pass (1 requires X display)
```

## 🛠️ Development

### Adding New Tools

1. Create tool method in `jarvis.py`:
```python
def execute_my_tool(self, param: str) -> str:
    """Execute my custom tool"""
    # Implementation
    return result
```

2. Add to `execute_tool()`:
```python
elif tool_name == "my_tool":
    return self.execute_my_tool(tool_call.get("param"))
```

3. Update system prompt with tool description

### Debugging

Enable verbose logging:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

Add debug command in interaction loop:
```python
if user_input.lower() == "debug":
    console.print(f"History: {len(self.conversation_history)}")
    console.print(f"Browser: {self.browser.is_running}")
```

## 📊 Performance

| Operation | Time | Notes |
|-----------|------|-------|
| LLM Response | 2-4s | qwen2.5-coder:3b on CPU |
| Web Search | 0.5-2s | Depends on SearXNG |
| Browser Nav | 1-3s | Page load time |
| File Ops | <0.1s | Instant |
| App Launch | <1s | System dependent |

## 🔒 Security

- **Safety Validator** - Confirms destructive commands
- **Audit Logging** - All commands logged to `logs/audit.log`
- **File Backups** - Automatic backups before modifications
- **Sandboxed Execution** - Commands run with timeout and output capture

## 📝 License

MIT License

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

---

**JARVIS Online** 🚀

*Last Updated: March 2026*
