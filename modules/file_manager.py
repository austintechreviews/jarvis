"""
Comprehensive file management system
Handles CRUD operations with backup and safety features
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
import hashlib
import json

logger = logging.getLogger(__name__)


class FileManager:
    """Handles all file system operations"""
    
    def __init__(self, backup_enabled: bool = True):
        """
        Initialize file manager
        
        Args:
            backup_enabled: Create backups before destructive operations
        """
        self.backup_enabled = backup_enabled
        self.backup_dir = Path.home() / "jarvis" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Operation log
        self.operation_log = Path.home() / "jarvis" / "logs" / "file_operations.jsonl"
        
    def _log_operation(self, operation: str, path: str, success: bool, details: str = ""):
        """Log file operation"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "path": str(path),
            "success": success,
            "details": details
        }
        with open(self.operation_log, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """Create backup of file before modification"""
        if not self.backup_enabled or not file_path.exists():
            return None
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return None
    
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Read file contents
        
        Returns:
            {"success": bool, "content": str, "error": str}
        """
        path = Path(file_path).expanduser()
        
        try:
            if not path.exists():
                return {"success": False, "content": "", "error": "File not found"}
            
            if not path.is_file():
                return {"success": False, "content": "", "error": "Path is not a file"}
            
            content = path.read_text()
            self._log_operation("read", path, True)
            
            return {
                "success": True,
                "content": content,
                "error": "",
                "size": len(content),
                "lines": content.count('\n') + 1
            }
        
        except Exception as e:
            self._log_operation("read", path, False, str(e))
            return {"success": False, "content": "", "error": str(e)}
    
    def write_file(self, file_path: str, content: str, mode: str = "w") -> Dict[str, Any]:
        """
        Write content to file
        
        Args:
            file_path: Path to file
            content: Content to write
            mode: 'w' (overwrite), 'a' (append)
            
        Returns:
            {"success": bool, "error": str, "backup": str}
        """
        path = Path(file_path).expanduser()
        backup_path = None
        
        try:
            # Create backup if file exists
            if path.exists():
                backup_path = self._create_backup(path)
            
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            if mode == "a":
                with open(path, "a") as f:
                    f.write(content)
            else:
                path.write_text(content)
            
            self._log_operation("write", path, True, f"mode={mode}")
            
            return {
                "success": True,
                "error": "",
                "backup": str(backup_path) if backup_path else None,
                "size": len(content)
            }
        
        except Exception as e:
            self._log_operation("write", path, False, str(e))
            return {"success": False, "error": str(e), "backup": None}
    
    def delete_file(self, file_path: str, confirm: bool = True) -> Dict[str, Any]:
        """
        Delete file with optional confirmation
        
        Args:
            file_path: Path to file
            confirm: If True, create backup before deletion
            
        Returns:
            {"success": bool, "error": str, "backup": str}
        """
        path = Path(file_path).expanduser()
        backup_path = None
        
        try:
            if not path.exists():
                return {"success": False, "error": "File not found", "backup": None}
            
            # Create backup if requested
            if confirm and self.backup_enabled:
                backup_path = self._create_backup(path)
            
            # Delete file
            path.unlink()
            self._log_operation("delete", path, True)
            
            return {
                "success": True,
                "error": "",
                "backup": str(backup_path) if backup_path else None
            }
        
        except Exception as e:
            self._log_operation("delete", path, False, str(e))
            return {"success": False, "error": str(e), "backup": None}
    
    def move_file(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Move or rename file
        
        Returns:
            {"success": bool, "error": str, "new_path": str}
        """
        src_path = Path(source).expanduser()
        dst_path = Path(destination).expanduser()
        
        try:
            if not src_path.exists():
                return {"success": False, "error": "Source file not found", "new_path": ""}
            
            # Ensure destination directory exists
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(str(src_path), str(dst_path))
            self._log_operation("move", src_path, True, f"to={dst_path}")
            
            return {
                "success": True,
                "error": "",
                "new_path": str(dst_path)
            }
        
        except Exception as e:
            self._log_operation("move", src_path, False, str(e))
            return {"success": False, "error": str(e), "new_path": ""}
    
    def copy_file(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Copy file to new location
        
        Returns:
            {"success": bool, "error": str, "new_path": str}
        """
        src_path = Path(source).expanduser()
        dst_path = Path(destination).expanduser()
        
        try:
            if not src_path.exists():
                return {"success": False, "error": "Source file not found", "new_path": ""}
            
            # Ensure destination directory exists
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(str(src_path), str(dst_path))
            self._log_operation("copy", src_path, True, f"to={dst_path}")
            
            return {
                "success": True,
                "error": "",
                "new_path": str(dst_path)
            }
        
        except Exception as e:
            self._log_operation("copy", src_path, False, str(e))
            return {"success": False, "error": str(e), "new_path": ""}
    
    def list_directory(self, dir_path: str, pattern: str = "*") -> Dict[str, Any]:
        """
        List files in directory with optional pattern matching
        
        Args:
            dir_path: Directory to list
            pattern: Glob pattern (e.g., "*.py", "test_*")
            
        Returns:
            {"success": bool, "files": List[str], "error": str}
        """
        # Handle special folder names
        dir_path_lower = dir_path.lower().strip()
        if dir_path_lower in ["root", "root folder", "/"]:
            path = Path("/")
        elif dir_path_lower in ["home", "~", "home folder"]:
            path = Path.home()
        elif dir_path_lower in ["downloads", "download folder"]:
            path = Path.home() / "Downloads"
        elif dir_path_lower in ["documents", "documents folder"]:
            path = Path.home() / "Documents"
        elif dir_path_lower in ["desktop"]:
            path = Path.home() / "Desktop"
        elif dir_path_lower in ["pictures", "photos"]:
            path = Path.home() / "Pictures"
        elif dir_path_lower in ["music"]:
            path = Path.home() / "Music"
        elif dir_path_lower in ["videos"]:
            path = Path.home() / "Videos"
        else:
            path = Path(dir_path).expanduser()
        
        try:
            if not path.exists():
                return {"success": False, "files": [], "error": "Directory not found"}
            
            if not path.is_dir():
                return {"success": False, "files": [], "error": "Path is not a directory"}
            
            # List files matching pattern
            files = [str(f) for f in path.glob(pattern)]
            files.sort()
            
            self._log_operation("list", path, True, f"pattern={pattern}")
            
            return {
                "success": True,
                "files": files,
                "error": "",
                "count": len(files)
            }
        
        except Exception as e:
            self._log_operation("list", path, False, str(e))
            return {"success": False, "files": [], "error": str(e)}
    
    def search_files(self, root_dir: str, pattern: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        Recursively search for files matching pattern
        
        Args:
            root_dir: Starting directory
            pattern: Glob pattern
            max_depth: Maximum recursion depth
            
        Returns:
            {"success": bool, "files": List[str], "error": str}
        """
        path = Path(root_dir).expanduser()
        
        try:
            if not path.exists():
                return {"success": False, "files": [], "error": "Directory not found"}
            
            # Recursive search
            files = []
            for f in path.rglob(pattern):
                # Check depth
                relative_depth = len(f.relative_to(path).parts)
                if relative_depth <= max_depth:
                    files.append(str(f))
            
            files.sort()
            self._log_operation("search", path, True, f"pattern={pattern}")
            
            return {
                "success": True,
                "files": files,
                "error": "",
                "count": len(files)
            }
        
        except Exception as e:
            self._log_operation("search", path, False, str(e))
            return {"success": False, "files": [], "error": str(e)}
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get detailed file information
        
        Returns:
            {"success": bool, "info": dict, "error": str}
        """
        path = Path(file_path).expanduser()
        
        try:
            if not path.exists():
                return {"success": False, "info": {}, "error": "File not found"}
            
            stat = path.stat()
            
            # Calculate file hash for integrity
            file_hash = ""
            if path.is_file() and stat.st_size < 10 * 1024 * 1024:  # < 10MB
                file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            
            info = {
                "path": str(path),
                "name": path.name,
                "size": stat.st_size,
                "size_human": self._human_readable_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
                "extension": path.suffix,
                "hash": file_hash
            }
            
            return {"success": True, "info": info, "error": ""}
        
        except Exception as e:
            return {"success": False, "info": {}, "error": str(e)}
    
    def _human_readable_size(self, size: int) -> str:
        """Convert bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    def create_directory(self, dir_path: str) -> Dict[str, Any]:
        """
        Create directory (including parent directories)
        
        Returns:
            {"success": bool, "error": str}
        """
        path = Path(dir_path).expanduser()
        
        try:
            path.mkdir(parents=True, exist_ok=True)
            self._log_operation("mkdir", path, True)
            
            return {"success": True, "error": ""}
        
        except Exception as e:
            self._log_operation("mkdir", path, False, str(e))
            return {"success": False, "error": str(e)}
