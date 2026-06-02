# ============================================================================
# JIG ONE v1.1 - File Helper Utilities
# ============================================================================

import os
from typing import Optional


def find_word_in_file(search_word: str, filepath: str) -> bool:
    """
    Search for a word/phrase in a text file.
    
    Args:
        search_word: Word or phrase to find
        filepath: Path to the file
        
    Returns:
        True if found, False otherwise
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            return search_word in content
    except Exception:
        return False


def ensure_directory(path: str) -> bool:
    """
    Ensure a directory exists, create if needed.
    
    Args:
        path: Directory path
        
    Returns:
        True if directory exists/created successfully
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"[FILE] Error creating directory {path}: {e}")
        return False


def get_relative_path(full_path: str, base_path: str) -> str:
    """
    Get relative path from base path.
    
    Args:
        full_path: Full path
        base_path: Base path to make relative from
        
    Returns:
        Relative path or original if not possible
    """
    try:
        return os.path.relpath(full_path, base_path)
    except ValueError:
        return full_path


def safe_file_write(filepath: str, content: str) -> bool:
    """
    Safely write content to file with directory creation.
    
    Args:
        filepath: Path to write to
        content: Content to write
        
    Returns:
        True if successful
    """
    try:
        directory = os.path.dirname(filepath)
        if directory:
            ensure_directory(directory)
        
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[FILE] Error writing to {filepath}: {e}")
        return False


def safe_file_read(filepath: str) -> Optional[str]:
    """
    Safely read content from file.
    
    Args:
        filepath: Path to read from
        
    Returns:
        File content or None on error
    """
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"[FILE] Error reading {filepath}: {e}")
        return None


def list_files_with_extension(directory: str, extension: str) -> list:
    """
    List files in directory with specific extension.
    
    Args:
        directory: Directory to search
        extension: File extension (e.g., '.json', '.hex')
        
    Returns:
        List of filenames
    """
    files = []
    try:
        if os.path.exists(directory):
            for f in os.listdir(directory):
                if f.endswith(extension):
                    files.append(f)
    except Exception as e:
        print(f"[FILE] Error listing {directory}: {e}")
    
    return files
