"""
Application Launcher Module
Launch desktop applications by name
"""

import subprocess
import shutil
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ApplicationLauncher:
    """Launch desktop applications by name"""
    
    COMMON_APPS = {
        "chrome": ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"],
        "chromium": ["chromium", "chromium-browser", "google-chrome-stable"],
        "firefox": ["firefox"],
        "vscode": ["code", "code-oss"],
        "code": ["code", "code-oss"],
        "terminal": ["kitty", "alacritty", "gnome-terminal", "konsole", "xfce4-terminal"],
        "files": ["nautilus", "thunar", "dolphin", "pcmanfm"],
        "file manager": ["nautilus", "thunar", "dolphin", "pcmanfm"],
        "editor": ["code", "vim", "nano", "gedit"],
        "browser": ["firefox", "google-chrome-stable", "chromium"],
        "calculator": ["gnome-calculator", "kcalc"],
        "settings": ["gnome-control-center", "systemsettings"],
        "terminal file manager": ["ranger", "nnn", "lf"],
        "music": ["spotify", "rhythmbox", "audacious"],
        "video": ["vlc", "mpv"],
        "image viewer": ["eog", "gwenview", "feh"],
        "pdf": ["evince", "okular", "zathura"],
        "text editor": ["gedit", "mousepad", "leafpad", "vim", "nano"],
    }
    
    def __init__(self):
        """Initialize application launcher"""
        self.launched_apps: Dict[str, int] = {}  # Track launched apps by name -> PID
    
    def launch(self, app_name: str) -> Dict[str, Any]:
        """
        Launch application by common name
        
        Args:
            app_name: Common application name (e.g., "chrome", "firefox", "vscode")
        
        Returns:
            {"success": bool, "message": str, "pid": int}
        """
        app_lower = app_name.lower().strip()
        
        # Check if it's a known app
        if app_lower in self.COMMON_APPS:
            commands = self.COMMON_APPS[app_lower]
        else:
            # Try exact command
            commands = [app_name]
        
        # Try each command variant
        for cmd in commands:
            if shutil.which(cmd):  # Check if command exists
                try:
                    process = subprocess.Popen(
                        [cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    
                    # Track launched app
                    self.launched_apps[app_lower] = process.pid
                    
                    logger.info(f"Launched {cmd} (PID: {process.pid})")
                    return {
                        "success": True,
                        "message": f"Launched {app_name}",
                        "pid": process.pid,
                        "command": cmd
                    }
                except Exception as e:
                    logger.error(f"Failed to launch {cmd}: {str(e)}")
                    continue
        
        return {
            "success": False,
            "message": f"Application '{app_name}' not found. Tried: {commands}",
            "pid": None,
            "command": None
        }
    
    def is_running(self, app_name: str) -> bool:
        """Check if an application is running"""
        app_lower = app_name.lower().strip()
        
        # Check if we launched it
        if app_lower in self.launched_apps:
            pid = self.launched_apps[app_lower]
            try:
                # Check if process is still running
                import os
                os.kill(pid, 0)  # Signal 0 doesn't kill, just checks existence
                return True
            except (ProcessLookupError, PermissionError):
                return False
        
        # Check by process name
        if app_lower in self.COMMON_APPS:
            commands = self.COMMON_APPS[app_lower]
            for cmd in commands:
                try:
                    result = subprocess.run(
                        ["pgrep", "-x", cmd],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        return True
                except Exception:
                    continue
        
        return False
    
    def close(self, app_name: str) -> Dict[str, Any]:
        """Close an application"""
        app_lower = app_name.lower().strip()
        
        # Check if we launched it
        if app_lower in self.launched_apps:
            pid = self.launched_apps[app_lower]
            try:
                import os
                import signal
                os.killpg(pid, signal.SIGTERM)
                del self.launched_apps[app_lower]
                return {"success": True, "message": f"Closed {app_name}"}
            except Exception as e:
                return {"success": False, "message": f"Failed to close: {str(e)}"}
        
        # Try to kill by process name
        if app_lower in self.COMMON_APPS:
            commands = self.COMMON_APPS[app_lower]
            for cmd in commands:
                try:
                    subprocess.run(["pkill", cmd], capture_output=True)
                    return {"success": True, "message": f"Closed {app_name}"}
                except Exception:
                    continue
        
        return {"success": False, "message": f"Application '{app_name}' not found running"}
    
    def list_running(self) -> list:
        """List applications we've launched that are still running"""
        running = []
        for app_name, pid in list(self.launched_apps.items()):
            if self.is_running(app_name):
                running.append({"name": app_name, "pid": pid})
        return running
