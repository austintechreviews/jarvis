"""
Safety validation system for command execution
Implements whitelist/blacklist approach with risk scoring
"""

import re
import logging
from typing import Tuple, List
from rich.console import Console
from rich.prompt import Confirm

console = Console()
logger = logging.getLogger(__name__)


class SafetyValidator:
    """Validates commands before execution"""
    
    # Commands that ALWAYS require explicit confirmation
    DESTRUCTIVE_PATTERNS = [
        r'\bsudo\b',
        r'\brm\s+.*(-rf|-fr|--recursive.*--force)',
        r'\brm\s+.*\*',  # rm with wildcards
        r'\bchmod\s+(777|666)',
        r'\bchown\s+',
        r'\bmkfs\.',
        r'\bdd\s+if=.*of=/dev/',
        r'\bformat\b',
        r'\bfdisk\b',
        r'\bparted\b',
        r'\bmount\s+.*\s+/',
        r'\bumount\s+/',
        r'\bpacman\s+-R',  # Arch package removal
        r'\bpacman\s+--remove',
        r'\bsystemctl\s+(stop|disable|mask)',
        r'\bkillall\b',
        r'\bpkill\b',
        r'\breboot\b',
        r'\bshutdown\b',
        r'\binit\s+[016]',
        r'\>/dev/(sd[a-z]|nvme|null)',
        r':\(\)\s*\{.*:\|:.*\}',  # Fork bomb pattern
        r'\bcurl\s+.*\|\s*bash',  # Pipe to bash
        r'\bwget\s+.*\|\s*sh',
    ]
    
    # Commands that are ALWAYS safe to auto-execute
    SAFE_PATTERNS = [
        r'^ls(\s|$)',
        r'^ll(\s|$)',
        r'^cat\s+[^|>]+$',  # Cat without pipes/redirects
        r'^head\s+',
        r'^tail\s+',
        r'^grep\s+',
        r'^find\s+',
        r'^locate\s+',
        r'^which\s+',
        r'^whereis\s+',
        r'^pwd$',
        r'^cd\s+',
        r'^echo\s+',
        r'^date$',
        r'^cal$',
        r'^whoami$',
        r'^hostname$',
        r'^uname\s+',
        r'^df\s+-h',
        r'^du\s+-h',
        r'^free\s+-h',
        r'^ps\s+',
        r'^top$',
        r'^htop$',
        r'^history$',
        r'^man\s+',
        r'^file\s+',
        r'^stat\s+',
        r'^wc\s+',
        r'^sort\s+',
        r'^uniq\s+',
    ]
    
    # File extensions that are safe to create/modify
    SAFE_FILE_EXTENSIONS = [
        '.txt', '.md', '.py', '.js', '.json', '.yaml', '.yml',
        '.html', '.css', '.sh', '.bash', '.log', '.csv'
    ]
    
    def __init__(self, auto_approve_safe: bool = True):
        """
        Initialize safety validator
        
        Args:
            auto_approve_safe: If True, auto-execute commands matching SAFE_PATTERNS
        """
        self.auto_approve_safe = auto_approve_safe
        self.command_history: List[str] = []
        
    def classify(self, command: str) -> Tuple[str, str]:
        """
        Classify command risk level
        
        Returns:
            (risk_level, reason)
            risk_level: 'safe' | 'medium' | 'high'
        """
        # Remove leading/trailing whitespace
        command = command.strip()
        
        # Check for empty command
        if not command:
            return ('safe', 'Empty command')
        
        # Check destructive patterns (HIGH RISK)
        for pattern in self.DESTRUCTIVE_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return ('high', f'Matches dangerous pattern: {pattern}')
        
        # Check safe patterns (SAFE)
        for pattern in self.SAFE_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return ('safe', 'Matches safe read-only pattern')
        
        # Check for file operations
        if self._is_safe_file_operation(command):
            return ('safe', 'Safe file operation')
        
        # Check for write operations to home directory (MEDIUM)
        if re.search(r'\>.*~/', command) or re.search(r'tee.*~/', command):
            return ('medium', 'Writing to home directory')
        
        # Default to medium risk
        return ('medium', 'Potentially modifies system state')
    
    def _is_safe_file_operation(self, command: str) -> bool:
        """Check if command is a safe file creation/modification"""
        # Match: touch, echo >, tee, cat >, etc.
        file_create_patterns = [
            r'touch\s+[\w/\-\.]+\.(' + '|'.join(ext[1:] for ext in self.SAFE_FILE_EXTENSIONS) + r')',
            r'echo\s+.*\>\s*[\w/\-\.]+\.(' + '|'.join(ext[1:] for ext in self.SAFE_FILE_EXTENSIONS) + r')',
        ]
        
        for pattern in file_create_patterns:
            if re.search(pattern, command):
                # Ensure it's in home directory or subdirectories
                if '~/' in command or '/home/' in command:
                    return True
        
        return False
    
    def confirm_if_needed(self, command: str, context: str = "") -> bool:
        """
        Main validation function - determines if command should execute
        
        Args:
            command: The command to validate
            context: Optional context about what the command is trying to do
            
        Returns:
            True if command should execute, False otherwise
        """
        risk, reason = self.classify(command)
        
        # Log the validation attempt
        logger.info(f"Safety check: {command[:50]}... | Risk: {risk} | Reason: {reason}")
        
        # SAFE commands: Auto-approve if enabled
        if risk == 'safe' and self.auto_approve_safe:
            console.print(f"[dim green]✓ Auto-approved: {command[:60]}...[/dim green]")
            self.command_history.append(command)
            return True
        
        # HIGH RISK: Always require explicit confirmation
        if risk == 'high':
            console.print(f"\n[bold red]⚠️  HIGH RISK COMMAND DETECTED[/bold red]")
            console.print(f"[yellow]Reason: {reason}[/yellow]")
            console.print(f"[white]Command: {command}[/white]")
            if context:
                console.print(f"[dim]Context: {context}[/dim]")
            
            # Require typing CONFIRM
            confirmation = console.input("\n[bold]Type 'CONFIRM' to execute (case-sensitive): [/bold]")
            
            if confirmation == "CONFIRM":
                logger.warning(f"HIGH RISK command approved by user: {command}")
                self.command_history.append(command)
                return True
            else:
                logger.info(f"HIGH RISK command rejected: {command}")
                console.print("[red]Command cancelled[/red]")
                return False
        
        # MEDIUM RISK: Simple y/n confirmation
        if risk == 'medium':
            console.print(f"\n[yellow]Command needs confirmation:[/yellow]")
            console.print(f"[white]{command}[/white]")
            if context:
                console.print(f"[dim]Context: {context}[/dim]")
            
            if Confirm.ask("[bold]Execute this command?[/bold]", default=False):
                self.command_history.append(command)
                return True
            else:
                console.print("[yellow]Command cancelled[/yellow]")
                return False
        
        # Fallback (shouldn't reach here)
        return False
    
    def get_command_history(self) -> List[str]:
        """Return list of executed commands"""
        return self.command_history.copy()
    
    def clear_history(self):
        """Clear command history"""
        self.command_history.clear()
