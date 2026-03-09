"""
Voice Response Formatter - Makes responses speech-friendly
Converts technical outputs into natural language summaries
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class VoiceResponseFormatter:
    """
    Formats JARVIS responses for natural speech output
    
    Converts:
    - Terminal output → Natural language
    - File listings → Concise summaries
    - Long text → Key points
    - Error messages → User-friendly explanations
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize formatter
        
        Args:
            llm_client: LLM instance for summarization (e.g., interpreter)
        """
        self.llm = llm_client
        
    def format_for_voice(self, response: str, context: str = "") -> str:
        """
        Convert response to speech-friendly format
        
        Args:
            response: Raw response from JARVIS
            context: Original user command (for context)
            
        Returns:
            Natural language summary suitable for speech
        """
        
        # Quick checks for response type
        response_type = self._detect_response_type(response)
        
        logger.info(f"Response type detected: {response_type}")
        
        # Handle based on type
        if response_type == "file_listing":
            return self._summarize_file_listing(response, context)
        
        elif response_type == "terminal_output":
            return self._summarize_terminal_output(response, context)
        
        elif response_type == "search_results":
            return self._summarize_search_results(response, context)
        
        elif response_type == "error":
            return self._humanize_error(response)
        
        elif response_type == "long_text":
            return self._summarize_long_text(response, context)
        
        elif response_type == "short_text":
            # Already concise, just clean up
            return self._clean_for_speech(response)
        
        else:
            # Unknown type, use LLM to summarize
            return self._llm_summarize(response, context)
    
    def _detect_response_type(self, response: str) -> str:
        """Detect what type of response this is"""
        
        response_lower = response.lower()
        
        # File listing (ls output)
        if any(indicator in response for indicator in ['drwxr', 'total ', '-rw-r--r--', 'lrwxrwxrwx']):
            return "file_listing"
        
        # Terminal command output
        if response.startswith('/') or ('\n' in response and len(response.split('\n')) > 5):
            if any(cmd in response_lower for cmd in ['error', 'command not found', 'permission denied']):
                return "error"
            return "terminal_output"
        
        # Search results
        if 'search results for' in response_lower or 'http' in response_lower:
            return "search_results"
        
        # Error messages
        if any(err in response_lower for err in ['error', 'failed', 'could not', 'unable to']):
            return "error"
        
        # Long text (more than 300 chars or 5 lines)
        if len(response) > 300 or response.count('\n') > 5:
            return "long_text"
        
        # Short text
        return "short_text"
    
    def _summarize_file_listing(self, response: str, context: str) -> str:
        """
        Convert file listing to natural language
        
        Example:
        Input: "drwxr-xr-x 1 austin austin 1370 Mar..."
        Output: "Your documents folder contains 47 items, including..."
        """
        
        # Count items
        lines = response.strip().split('\n')
        
        # Remove header lines (total, ., ..)
        files = [line for line in lines if line and not line.startswith('total') 
                 and not line.split()[-1] in ['.', '..']]
        
        total_items = len(files)
        
        if total_items == 0:
            return "The folder is empty."
        
        # Extract file names and types
        directories = []
        regular_files = []
        
        for line in files:
            if line.startswith('d'):
                # Directory
                name = line.split()[-1]
                directories.append(name)
            elif line.startswith('-'):
                # Regular file
                name = line.split()[-1]
                regular_files.append(name)
        
        # Build natural response
        response_parts = []
        
        if total_items <= 5:
            # List all items
            all_items = directories + regular_files
            items_list = ", ".join(all_items[:-1]) + f" and {all_items[-1]}" if len(all_items) > 1 else all_items[0]
            response_parts.append(f"There are {total_items} items: {items_list}.")
        else:
            # Summarize
            response_parts.append(f"There are {total_items} items in total.")
            
            if directories:
                dir_count = len(directories)
                if dir_count <= 3:
                    dir_list = ", ".join(directories)
                    response_parts.append(f"{dir_count} folders: {dir_list}.")
                else:
                    dir_sample = ", ".join(directories[:3])
                    response_parts.append(f"{dir_count} folders including {dir_sample}.")
            
            if regular_files:
                file_count = len(regular_files)
                if file_count <= 3:
                    file_list = ", ".join(regular_files)
                    response_parts.append(f"{file_count} files: {file_list}.")
                else:
                    file_sample = ", ".join(regular_files[:3])
                    response_parts.append(f"{file_count} files including {file_sample}.")
        
        return " ".join(response_parts)
    
    def _summarize_terminal_output(self, response: str, context: str) -> str:
        """Summarize terminal command output"""
        
        # Use LLM to interpret terminal output if available
        if self.llm:
            prompt = f"""Summarize this terminal output in one natural sentence for voice:

Command context: {context}

Output:
{response[:500]}

Summary (one sentence, conversational):"""
            
            summary = self._call_llm(prompt)
            if summary:
                return summary
        
        # Fallback: just clean it up
        return self._clean_for_speech(response[:200])
    
    def _summarize_search_results(self, response: str, context: str) -> str:
        """Summarize search results"""
        
        lines = response.split('\n')
        
        # Count results
        results = [line for line in lines if line.strip() and line[0].isdigit()]
        result_count = len(results)
        
        if result_count == 0:
            return "I found no results for your search."
        
        # Extract first few titles
        titles = []
        for line in results[:3]:
            # Extract title (after number and dot)
            if '. ' in line:
                title = line.split('. ', 1)[1].strip()
                # Remove URL if present
                if 'http' in title:
                    title = title.split('http')[0].strip()
                titles.append(title)
        
        if result_count <= 3:
            title_list = ", ".join(titles)
            return f"I found {result_count} results: {title_list}. Check the screen for links."
        else:
            title_sample = ", ".join(titles[:2])
            return f"I found {result_count} results. Top results include {title_sample}. Full list is on screen."
    
    def _humanize_error(self, response: str) -> str:
        """Make error messages user-friendly"""
        
        error_lower = response.lower()
        
        # Common error patterns
        if "not found" in error_lower:
            return "I couldn't find that. Please check the name and try again."
        
        if "permission denied" in error_lower:
            return "Access denied. You might need elevated permissions for that."
        
        if "connection" in error_lower or "network" in error_lower:
            return "I'm having trouble connecting. Check your network connection."
        
        if "timeout" in error_lower:
            return "That request timed out. It might be too slow or unavailable."
        
        # Generic error
        return "Something went wrong. Check the screen for details."
    
    def _summarize_long_text(self, response: str, context: str) -> str:
        """Summarize long responses"""
        
        # Count content
        word_count = len(response.split())
        line_count = response.count('\n') + 1
        
        if word_count > 100 and self.llm:
            # Use LLM to summarize
            prompt = f"""Summarize this response in 2-3 sentences for voice output:

User asked: {context}

Response:
{response[:1000]}

Voice summary (2-3 sentences):"""
            
            summary = self._call_llm(prompt)
            
            if summary:
                return summary + " Full details are displayed on screen."
            else:
                return "I've prepared a detailed response. Please check the screen."
        
        # Not that long, just clean it
        return self._clean_for_speech(response)
    
    def _clean_for_speech(self, text: str) -> str:
        """Remove formatting that doesn't work in speech"""
        
        # Remove markdown
        cleaned = text.replace('**', '').replace('*', '')
        cleaned = cleaned.replace('`', '').replace('#', '')
        
        # Remove special characters
        cleaned = cleaned.replace('✓', 'Success:')
        cleaned = cleaned.replace('✗', 'Error:')
        cleaned = cleaned.replace('→', 'to')
        cleaned = cleaned.replace('•', '')
        
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    def _llm_summarize(self, response: str, context: str) -> str:
        """Use LLM to summarize unknown response types"""
        
        if not self.llm:
            return self._clean_for_speech(response[:200])
        
        prompt = f"""Convert this response to natural speech (2-3 sentences max):

User asked: {context}

Response:
{response[:800]}

Natural speech version:"""
        
        summary = self._call_llm(prompt)
        return summary or self._clean_for_speech(response[:200])
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM for summarization"""
        
        try:
            # Use the LLM client to generate summary
            response = self.llm.chat(
                prompt,
                display=False,
                stream=False
            )
            
            # Extract text from response
            if isinstance(response, str):
                return response.strip()
            elif isinstance(response, list):
                # Extract text from message chunks
                text = ""
                for chunk in response:
                    if isinstance(chunk, dict) and "content" in chunk:
                        text += str(chunk["content"])
                return text.strip()
            else:
                return str(response).strip()
        
        except Exception as e:
            logger.error(f"LLM summarization failed: {str(e)}")
            return ""
