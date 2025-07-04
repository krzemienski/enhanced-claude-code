"""Path handling and normalization utilities for Claude Code Builder."""
import os
import sys
from pathlib import Path
from typing import List, Optional, Union, Tuple, Iterator
import platform
import tempfile
import re

from ..exceptions.base import ValidationError, FileOperationError
from ..logging.logger import get_logger

logger = get_logger(__name__)


def normalize_path(path: Union[str, Path], resolve: bool = True) -> Path:
    """Normalize and optionally resolve a path.
    
    Args:
        path: Path to normalize
        resolve: Resolve to absolute path
        
    Returns:
        Normalized path
    """
    path = Path(path)
    
    # Expand user home directory
    path = path.expanduser()
    
    # Resolve to absolute path if requested
    if resolve:
        path = path.resolve()
    
    return path


def ensure_parent_dir(path: Union[str, Path]) -> Path:
    """Ensure parent directory exists.
    
    Args:
        path: File path
        
    Returns:
        Path object
        
    Raises:
        FileOperationError: If directory creation fails
    """
    path = normalize_path(path)
    parent = path.parent
    
    try:
        parent.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as e:
        raise FileOperationError(f"Failed to create parent directory: {e}")


def relative_to_cwd(path: Union[str, Path]) -> Path:
    """Get path relative to current working directory.
    
    Args:
        path: Path to convert
        
    Returns:
        Relative path or original if not relative to cwd
    """
    path = normalize_path(path)
    cwd = Path.cwd()
    
    try:
        return path.relative_to(cwd)
    except ValueError:
        # Path is not relative to cwd
        return path


def common_path(paths: List[Union[str, Path]]) -> Optional[Path]:
    """Find common path among multiple paths.
    
    Args:
        paths: List of paths
        
    Returns:
        Common path or None
    """
    if not paths:
        return None
    
    normalized = [normalize_path(p) for p in paths]
    
    try:
        return Path(os.path.commonpath([str(p) for p in normalized]))
    except ValueError:
        # No common path (e.g., different drives on Windows)
        return None


def is_subpath(path: Union[str, Path], parent: Union[str, Path]) -> bool:
    """Check if path is a subpath of parent.
    
    Args:
        path: Path to check
        parent: Parent path
        
    Returns:
        True if path is subpath of parent
    """
    path = normalize_path(path)
    parent = normalize_path(parent)
    
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def safe_join(base: Union[str, Path], *parts: str) -> Path:
    """Safely join path parts preventing directory traversal.
    
    Args:
        base: Base path
        parts: Path parts to join
        
    Returns:
        Joined path
        
    Raises:
        ValidationError: If path would escape base directory
    """
    base = normalize_path(base)
    
    # Join parts
    joined = base
    for part in parts:
        # Remove any parent directory references
        clean_part = part.replace('..', '').replace('~', '')
        joined = joined / clean_part
    
    # Normalize and check if still under base
    joined = normalize_path(joined)
    
    if not is_subpath(joined, base):
        raise ValidationError(f"Path escapes base directory: {joined}")
    
    return joined


def find_project_root(
    start_path: Union[str, Path] = ".",
    markers: Optional[List[str]] = None
) -> Optional[Path]:
    """Find project root by looking for marker files.
    
    Args:
        start_path: Starting path
        markers: Marker files to look for
        
    Returns:
        Project root path or None
    """
    markers = markers or [
        '.git', 'pyproject.toml', 'setup.py', 'setup.cfg',
        'requirements.txt', 'package.json', 'Cargo.toml'
    ]
    
    current = normalize_path(start_path)
    
    # If start_path is a file, start from its parent
    if current.is_file():
        current = current.parent
    
    # Walk up directory tree
    while current != current.parent:
        for marker in markers:
            if (current / marker).exists():
                logger.debug(f"Found project root at {current}")
                return current
        current = current.parent
    
    return None


def find_files(
    pattern: str,
    start_path: Union[str, Path] = ".",
    recursive: bool = True,
    ignore_patterns: Optional[List[str]] = None
) -> List[Path]:
    """Find files matching pattern.
    
    Args:
        pattern: File pattern (glob)
        start_path: Starting directory
        recursive: Search recursively
        ignore_patterns: Patterns to ignore
        
    Returns:
        List of matching file paths
    """
    ignore_patterns = ignore_patterns or [
        '*.pyc', '__pycache__', '.git', '.venv', 'venv',
        'node_modules', '.pytest_cache', '.mypy_cache'
    ]
    
    start = normalize_path(start_path)
    
    if not start.is_dir():
        return []
    
    # Get all matching files
    if recursive:
        matches = list(start.rglob(pattern))
    else:
        matches = list(start.glob(pattern))
    
    # Filter out ignored patterns
    filtered = []
    for match in matches:
        # Check if any part of the path matches ignore patterns
        parts = match.parts
        ignored = False
        
        for part in parts:
            for ignore_pattern in ignore_patterns:
                if Path(part).match(ignore_pattern):
                    ignored = True
                    break
            if ignored:
                break
        
        if not ignored:
            filtered.append(match)
    
    return sorted(filtered)


def get_temp_dir(prefix: str = "claude_code_builder_") -> Path:
    """Get a temporary directory.
    
    Args:
        prefix: Directory prefix
        
    Returns:
        Path to temporary directory
    """
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
    logger.debug(f"Created temp directory: {temp_dir}")
    return temp_dir


def get_home_dir() -> Path:
    """Get user home directory.
    
    Returns:
        Home directory path
    """
    return Path.home()


def get_config_dir(app_name: str = "claude_code_builder") -> Path:
    """Get application config directory.
    
    Args:
        app_name: Application name
        
    Returns:
        Config directory path
    """
    system = platform.system()
    
    if system == "Windows":
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    elif system == "Darwin":  # macOS
        base = Path.home() / 'Library' / 'Application Support'
    else:  # Linux and others
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    
    config_dir = base / app_name
    config_dir.mkdir(parents=True, exist_ok=True)
    
    return config_dir


def get_cache_dir(app_name: str = "claude_code_builder") -> Path:
    """Get application cache directory.
    
    Args:
        app_name: Application name
        
    Returns:
        Cache directory path
    """
    system = platform.system()
    
    if system == "Windows":
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    elif system == "Darwin":  # macOS
        base = Path.home() / 'Library' / 'Caches'
    else:  # Linux and others
        base = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
    
    cache_dir = base / app_name
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    return cache_dir


def split_path(path: Union[str, Path]) -> Tuple[Path, str, str]:
    """Split path into directory, name, and extension.
    
    Args:
        path: Path to split
        
    Returns:
        Tuple of (directory, name, extension)
    """
    path = normalize_path(path)
    
    directory = path.parent
    name = path.stem
    extension = path.suffix
    
    return directory, name, extension


def change_extension(path: Union[str, Path], new_ext: str) -> Path:
    """Change file extension.
    
    Args:
        path: File path
        new_ext: New extension (with or without dot)
        
    Returns:
        Path with new extension
    """
    path = normalize_path(path)
    
    # Ensure extension starts with dot
    if new_ext and not new_ext.startswith('.'):
        new_ext = '.' + new_ext
    
    return path.with_suffix(new_ext)


def sanitize_filename(
    filename: str,
    replacement: str = "_",
    max_length: Optional[int] = 255
) -> str:
    """Sanitize filename for filesystem.
    
    Args:
        filename: Original filename
        replacement: Replacement for invalid characters
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename
    """
    # Invalid characters for various filesystems
    invalid_chars = r'<>:"/\|?*'
    
    # Additional Windows reserved names
    windows_reserved = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    
    # Replace invalid characters
    for char in invalid_chars:
        filename = filename.replace(char, replacement)
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Handle Windows reserved names
    name_upper = filename.upper()
    for reserved in windows_reserved:
        if name_upper == reserved or name_upper.startswith(reserved + '.'):
            filename = replacement + filename
            break
    
    # Truncate if needed
    if max_length and len(filename) > max_length:
        # Preserve extension if possible
        parts = filename.rsplit('.', 1)
        if len(parts) == 2 and len(parts[1]) < 10:
            name, ext = parts
            max_name_length = max_length - len(ext) - 1
            filename = name[:max_name_length] + '.' + ext
        else:
            filename = filename[:max_length]
    
    # Ensure filename is not empty
    if not filename or filename == replacement:
        filename = "unnamed"
    
    return filename


def walk_files(
    root: Union[str, Path],
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None
) -> Iterator[Path]:
    """Walk directory tree yielding file paths.
    
    Args:
        root: Root directory
        include_patterns: Patterns to include
        exclude_patterns: Patterns to exclude
        
    Yields:
        File paths
    """
    root = normalize_path(root)
    
    exclude_patterns = exclude_patterns or [
        '*.pyc', '__pycache__', '.git', '.venv', 'venv',
        'node_modules', '.pytest_cache', '.mypy_cache'
    ]
    
    for dirpath, dirnames, filenames in os.walk(root):
        dir_path = Path(dirpath)
        
        # Filter directories
        dirnames[:] = [
            d for d in dirnames
            if not any(Path(d).match(pattern) for pattern in exclude_patterns)
        ]
        
        # Yield files
        for filename in filenames:
            file_path = dir_path / filename
            
            # Check exclude patterns
            if any(file_path.match(pattern) for pattern in exclude_patterns):
                continue
            
            # Check include patterns
            if include_patterns:
                if not any(file_path.match(pattern) for pattern in include_patterns):
                    continue
            
            yield file_path


def make_executable(path: Union[str, Path]) -> None:
    """Make file executable.
    
    Args:
        path: File path
        
    Raises:
        FileOperationError: If operation fails
    """
    path = normalize_path(path)
    
    try:
        current_mode = path.stat().st_mode
        # Add execute permission for user, group, and others
        new_mode = current_mode | 0o111
        path.chmod(new_mode)
        logger.debug(f"Made {path} executable")
    except Exception as e:
        raise FileOperationError(f"Failed to make {path} executable: {e}")