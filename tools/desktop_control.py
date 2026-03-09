"""
Desktop automation using xdotool and PyAutoGUI
"""

import os
import logging
import subprocess
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Try to import pyautogui, handle case when no display is available
try:
    import pyautogui
    # Prevent PyAutoGUI from pausing
    pyautogui.PAUSE = 0.1
    PYAUTOGUI_AVAILABLE = True
except Exception as e:
    logger.warning(f"PyAutoGUI not available (no display?): {e}")
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None


class DesktopController:
    """Desktop GUI automation"""
    
    def __init__(self):
        """Initialize desktop controller"""
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required tools are installed"""
        try:
            subprocess.run(["which", "xdotool"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            logger.warning("xdotool not installed. Install with: sudo pacman -S xdotool")
    
    def execute(self, instruction: str) -> str:
        """Execute desktop automation task"""
        instruction_lower = instruction.lower()
        
        # Mouse operations
        if "click" in instruction_lower:
            x, y = self._extract_coordinates(instruction)
            if x and y:
                return self.click(x, y)
            else:
                return self.click()  # Click current position
        
        if "move mouse" in instruction_lower or "move to" in instruction_lower:
            x, y = self._extract_coordinates(instruction)
            if x and y:
                return self.move_mouse(x, y)
        
        # Keyboard operations
        if "type" in instruction_lower:
            text = self._extract_text_to_type(instruction)
            if text:
                return self.type_text(text)
        
        # Key press
        if "press" in instruction_lower and "key" in instruction_lower:
            key = self._extract_key(instruction)
            if key:
                return self.press_key(key)
        
        # Hotkey
        if "hotkey" in instruction_lower or "press" in instruction_lower and ("ctrl" in instruction_lower or "alt" in instruction_lower or "shift" in instruction_lower):
            keys = self._extract_hotkey_keys(instruction)
            if keys:
                return self.hotkey(*keys)
        
        # Screenshot
        if "screenshot" in instruction_lower:
            return self.screenshot()
        
        return "Unknown desktop operation"
    
    def move_mouse(self, x: int, y: int, duration: float = 0.5) -> str:
        """Move mouse to coordinates"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: PyAutoGUI not available (no X display)"
        try:
            pyautogui.moveTo(x, y, duration=duration)
            logger.info(f"Mouse moved to ({x}, {y})")
            return f"Mouse moved to ({x}, {y})"
        except Exception as e:
            logger.error(f"Move mouse error: {str(e)}")
            return f"Error: {str(e)}"
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> str:
        """Click at coordinates or current position"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: PyAutoGUI not available (no X display)"
        try:
            if x and y:
                pyautogui.click(x, y, button=button)
                logger.info(f"Clicked at ({x}, {y})")
                return f"Clicked at ({x}, {y})"
            else:
                pyautogui.click(button=button)
                logger.info("Clicked at current position")
                return "Clicked at current position"
        except Exception as e:
            logger.error(f"Click error: {str(e)}")
            return f"Error: {str(e)}"
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Double-click at coordinates or current position"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: PyAutoGUI not available (no X display)"
        try:
            if x and y:
                pyautogui.doubleClick(x, y)
                logger.info(f"Double-clicked at ({x}, {y})")
                return f"Double-clicked at ({x}, {y})"
            else:
                pyautogui.doubleClick()
                logger.info("Double-clicked at current position")
                return "Double-clicked at current position"
        except Exception as e:
            logger.error(f"Double-click error: {str(e)}")
            return f"Error: {str(e)}"
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Right-click at coordinates or current position"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: PyAutoGUI not available (no X display)"
        try:
            if x and y:
                pyautogui.rightClick(x, y)
                logger.info(f"Right-clicked at ({x}, {y})")
                return f"Right-clicked at ({x}, {y})"
            else:
                pyautogui.rightClick()
                logger.info("Right-clicked at current position")
                return "Right-clicked at current position"
        except Exception as e:
            logger.error(f"Right-click error: {str(e)}")
            return f"Error: {str(e)}"
    
    def type_text(self, text: str, interval: float = 0.05) -> str:
        """Type text at current cursor position"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: PyAutoGUI not available (no X display)"
        try:
            pyautogui.write(text, interval=interval)
            logger.info(f"Typed: {text[:50]}...")
            return f"Typed: {text}"
        except Exception as e:
            logger.error(f"Type error: {str(e)}")
            return f"Error: {str(e)}"
    
    def press_key(self, key: str) -> str:
        """Press a keyboard key"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: PyAutoGUI not available (no X display)"
        try:
            pyautogui.press(key)
            logger.info(f"Pressed key: {key}")
            return f"Pressed key: {key}"
        except Exception as e:
            logger.error(f"Key press error: {str(e)}")
            return f"Error: {str(e)}"
    
    def hotkey(self, *keys: str) -> str:
        """Press key combination (e.g., Ctrl+C)"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: PyAutoGUI not available (no X display)"
        try:
            pyautogui.hotkey(*keys)
            logger.info(f"Pressed hotkey: {'+'.join(keys)}")
            return f"Pressed hotkey: {'+'.join(keys)}"
        except Exception as e:
            logger.error(f"Hotkey error: {str(e)}")
            return f"Error: {str(e)}"
    
    def screenshot(self, save_path: Optional[str] = None) -> str:
        """Take screenshot of entire screen"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: PyAutoGUI not available (no X display)"
        try:
            if not save_path:
                timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"/home/{os.getenv('USER')}/jarvis/data/screenshot_{timestamp}.png"
            
            screenshot = pyautogui.screenshot()
            screenshot.save(save_path)
            logger.info(f"Screenshot saved: {save_path}")
            return f"Screenshot saved: {save_path}"
        except Exception as e:
            logger.error(f"Screenshot error: {str(e)}")
            return f"Error: {str(e)}"
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen resolution"""
        if not PYAUTOGUI_AVAILABLE:
            return (0, 0)
        return pyautogui.size()
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position"""
        if not PYAUTOGUI_AVAILABLE:
            return (0, 0)
        return pyautogui.position()
    
    def scroll(self, amount: int, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Scroll mouse wheel"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: PyAutoGUI not available (no X display)"
        try:
            if x and y:
                pyautogui.scroll(amount, x=x, y=y)
                logger.info(f"Scrolled {amount} at ({x}, {y})")
                return f"Scrolled {amount} at ({x}, {y})"
            else:
                pyautogui.scroll(amount)
                logger.info(f"Scrolled {amount}")
                return f"Scrolled {amount}"
        except Exception as e:
            logger.error(f"Scroll error: {str(e)}")
            return f"Error: {str(e)}"
    
    def drag_to(self, x: int, y: int, duration: float = 0.5) -> str:
        """Drag mouse to coordinates"""
        if not PYAUTOGUI_AVAILABLE:
            return "Error: PyAutoGUI not available (no X display)"
        try:
            pyautogui.dragTo(x, y, duration=duration)
            logger.info(f"Dragged to ({x}, {y})")
            return f"Dragged to ({x}, {y})"
        except Exception as e:
            logger.error(f"Drag error: {str(e)}")
            return f"Error: {str(e)}"
    
    def _extract_coordinates(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract (x, y) coordinates from text"""
        import re
        # Look for patterns like "100 200", "100, 200", "(100, 200)"
        pattern = r'(\d+)\s*,?\s*(\d+)'
        match = re.search(pattern, text)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None, None
    
    def _extract_text_to_type(self, instruction: str) -> Optional[str]:
        """Extract text to type from instruction"""
        import re
        
        # Look for text in quotes
        pattern = r'["\'](.+?)["\']'
        match = re.search(pattern, instruction)
        if match:
            return match.group(1)
        
        # Otherwise, take everything after "type"
        parts = instruction.lower().split("type")
        if len(parts) > 1:
            return parts[1].strip()
        
        return None
    
    def _extract_key(self, instruction: str) -> Optional[str]:
        """Extract key name from instruction"""
        import re
        
        # Common keys
        keys = ['enter', 'tab', 'escape', 'backspace', 'delete', 'home', 'end', 
                'pageup', 'pagedown', 'up', 'down', 'left', 'right', 'f1', 'f2', 
                'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12']
        
        instruction_lower = instruction.lower()
        for key in keys:
            if key in instruction_lower:
                return key
        
        # Look for key in quotes
        pattern = r'["\'](.+?)["\']'
        match = re.search(pattern, instruction)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_hotkey_keys(self, instruction: str) -> Optional[list]:
        """Extract keys for hotkey combination"""
        import re
        
        keys_map = {
            'ctrl': 'ctrl',
            'control': 'ctrl',
            'alt': 'alt',
            'shift': 'shift',
            'win': 'command',
            'super': 'command',
            'command': 'command',
        }
        
        keys = []
        instruction_lower = instruction.lower()
        
        # Look for modifier keys
        for keyword, key in keys_map.items():
            if keyword in instruction_lower:
                keys.append(key)
        
        # Look for the final key (in quotes or after modifiers)
        pattern = r'["\'](.+?)["\']'
        match = re.search(pattern, instruction)
        if match:
            keys.append(match.group(1))
        else:
            # Try to find common keys
            common_keys = ['c', 'v', 'x', 'z', 'a', 's', 'w', 't', 'r', 'f', 'q']
            for k in common_keys:
                if f" {k}" in instruction_lower or instruction_lower.endswith(f" {k}"):
                    keys.append(k)
                    break
        
        return keys if len(keys) >= 2 else None
