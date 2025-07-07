"""File operations and path utilities for Claude Code Builder."""
import os
import shutil
import tempfile
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Iterator
from dataclasses import dataclass
from datetime import datetime
import json
import yaml
import toml

from ..models.base import TimestampedModel
from ..exceptions.base import (
    ClaudeCodeBuilderError,
    FileOperationError,
    ValidationError
)
from ..logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FileInfo(TimestampedModel):
    """Information about a file."""
    path: Path = Path()
    size: int = 0
    mime_type: str = ""
    encoding: str = ""
    checksum: str = ""
    is_binary: bool = False
    permissions: int = 0
    
    @property
    def exists(self) -> bool:
        """Check if file exists."""
        return self.path.exists()
    
    @property
    def is_readable(self) -> bool:
        """Check if file is readable."""
        return os.access(self.path, os.R_OK)
    
    @property
    def is_writable(self) -> bool:
        """Check if file is writable."""
        return os.access(self.path, os.W_OK)


class FileHandler:
    """Handles file operations with safety and validation."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize file handler.
        
        Args:
            base_path: Base path for operations
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self._temp_files: List[Path] = []
        
    def read_file(self, path: Union[str, Path], encoding: str = 'utf-8') -> str:
        """Read text file content.
        
        Args:
            path: File path
            encoding: File encoding
            
        Returns:
            File content
            
        Raises:
            FileOperationError: If read fails
        """
        try:
            file_path = self._resolve_path(path)
            logger.debug(f"Reading file: {file_path}")
            
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
                
        except Exception as e:
            raise FileOperationError(f"Failed to read file {path}: {e}")
    
    def write_file(
        self,
        path: Union[str, Path],
        content: str,
        encoding: str = 'utf-8',
        create_dirs: bool = True,
        backup: bool = False
    ) -> Path:
        """Write content to file.
        
        Args:
            path: File path
            content: Content to write
            encoding: File encoding
            create_dirs: Create parent directories if needed
            backup: Create backup of existing file
            
        Returns:
            Path to written file
            
        Raises:
            FileOperationError: If write fails
        """
        try:
            file_path = self._resolve_path(path)
            logger.debug(f"Writing file: {file_path}")
            
            # Create directories if needed
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Backup existing file if requested
            if backup and file_path.exists():
                self._create_backup(file_path)
            
            # Write content
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            return file_path
            
        except Exception as e:
            raise FileOperationError(f"Failed to write file {path}: {e}")
    
    def copy_file(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
        overwrite: bool = False
    ) -> Path:
        """Copy file to destination.
        
        Args:
            source: Source file path
            destination: Destination path
            overwrite: Overwrite existing file
            
        Returns:
            Path to copied file
            
        Raises:
            FileOperationError: If copy fails
        """
        try:
            src_path = self._resolve_path(source)
            dst_path = self._resolve_path(destination)
            
            if not src_path.exists():
                raise FileOperationError(f"Source file not found: {source}")
            
            if dst_path.exists() and not overwrite:
                raise FileOperationError(f"Destination exists: {destination}")
            
            logger.debug(f"Copying {src_path} to {dst_path}")
            
            # Ensure destination directory exists
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(src_path, dst_path)
            
            return dst_path
            
        except Exception as e:
            raise FileOperationError(f"Failed to copy file: {e}")
    
    def move_file(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
        overwrite: bool = False
    ) -> Path:
        """Move file to destination.
        
        Args:
            source: Source file path
            destination: Destination path
            overwrite: Overwrite existing file
            
        Returns:
            Path to moved file
            
        Raises:
            FileOperationError: If move fails
        """
        try:
            src_path = self._resolve_path(source)
            dst_path = self._resolve_path(destination)
            
            if not src_path.exists():
                raise FileOperationError(f"Source file not found: {source}")
            
            if dst_path.exists() and not overwrite:
                raise FileOperationError(f"Destination exists: {destination}")
            
            logger.debug(f"Moving {src_path} to {dst_path}")
            
            # Ensure destination directory exists
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(str(src_path), str(dst_path))
            
            return dst_path
            
        except Exception as e:
            raise FileOperationError(f"Failed to move file: {e}")
    
    def delete_file(self, path: Union[str, Path], safe: bool = True) -> None:
        """Delete file.
        
        Args:
            path: File path
            safe: Move to trash instead of permanent delete
            
        Raises:
            FileOperationError: If delete fails
        """
        try:
            file_path = self._resolve_path(path)
            
            if not file_path.exists():
                logger.warning(f"File not found: {path}")
                return
            
            logger.debug(f"Deleting file: {file_path}")
            
            if safe:
                # Move to trash directory
                trash_dir = self.base_path / '.trash'
                trash_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                trash_path = trash_dir / f"{timestamp}_{file_path.name}"
                shutil.move(str(file_path), str(trash_path))
            else:
                # Permanent delete
                file_path.unlink()
                
        except Exception as e:
            raise FileOperationError(f"Failed to delete file {path}: {e}")
    
    def get_file_info(self, path: Union[str, Path]) -> FileInfo:
        """Get detailed file information.
        
        Args:
            path: File path
            
        Returns:
            File information
            
        Raises:
            FileOperationError: If operation fails
        """
        try:
            file_path = self._resolve_path(path)
            
            if not file_path.exists():
                raise FileOperationError(f"File not found: {path}")
            
            stat = file_path.stat()
            
            # Determine MIME type
            mime_type, encoding = mimetypes.guess_type(str(file_path))
            
            # Calculate checksum
            checksum = self._calculate_checksum(file_path)
            
            # Check if binary
            is_binary = self._is_binary_file(file_path)
            
            return FileInfo(
                path=file_path,
                size=stat.st_size,
                mime_type=mime_type or 'application/octet-stream',
                encoding=encoding or 'utf-8',
                checksum=checksum,
                is_binary=is_binary,
                permissions=stat.st_mode
            )
            
        except Exception as e:
            raise FileOperationError(f"Failed to get file info: {e}")
    
    def list_files(
        self,
        path: Union[str, Path] = ".",
        pattern: str = "*",
        recursive: bool = False,
        include_hidden: bool = False
    ) -> List[Path]:
        """List files in directory.
        
        Args:
            path: Directory path
            pattern: File pattern (glob)
            recursive: Search recursively
            include_hidden: Include hidden files
            
        Returns:
            List of file paths
            
        Raises:
            FileOperationError: If operation fails
        """
        try:
            dir_path = self._resolve_path(path)
            
            if not dir_path.is_dir():
                raise FileOperationError(f"Not a directory: {path}")
            
            if recursive:
                files = list(dir_path.rglob(pattern))
            else:
                files = list(dir_path.glob(pattern))
            
            # Filter hidden files if needed
            if not include_hidden:
                files = [f for f in files if not f.name.startswith('.')]
            
            return sorted(files)
            
        except Exception as e:
            raise FileOperationError(f"Failed to list files: {e}")
    
    def create_temp_file(
        self,
        suffix: str = "",
        prefix: str = "tmp_",
        content: Optional[str] = None
    ) -> Path:
        """Create temporary file.
        
        Args:
            suffix: File suffix
            prefix: File prefix
            content: Optional content to write
            
        Returns:
            Path to temporary file
        """
        try:
            # Create temp file
            fd, temp_path = tempfile.mkstemp(
                suffix=suffix,
                prefix=prefix,
                dir=self.base_path
            )
            
            temp_file = Path(temp_path)
            self._temp_files.append(temp_file)
            
            # Write content if provided
            if content:
                with os.fdopen(fd, 'w') as f:
                    f.write(content)
            else:
                os.close(fd)
            
            logger.debug(f"Created temp file: {temp_file}")
            return temp_file
            
        except Exception as e:
            raise FileOperationError(f"Failed to create temp file: {e}")
    
    def cleanup_temp_files(self) -> None:
        """Clean up temporary files."""
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_file}: {e}")
        
        self._temp_files.clear()
    
    def read_json(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Read JSON file.
        
        Args:
            path: File path
            
        Returns:
            Parsed JSON data
        """
        content = self.read_file(path)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in {path}: {e}")
    
    def write_json(
        self,
        path: Union[str, Path],
        data: Dict[str, Any],
        indent: int = 2
    ) -> Path:
        """Write JSON file.
        
        Args:
            path: File path
            data: Data to write
            indent: JSON indentation
            
        Returns:
            Path to written file
        """
        content = json.dumps(data, indent=indent, default=str)
        return self.write_file(path, content)
    
    def read_yaml(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Read YAML file.
        
        Args:
            path: File path
            
        Returns:
            Parsed YAML data
        """
        content = self.read_file(path)
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML in {path}: {e}")
    
    def write_yaml(
        self,
        path: Union[str, Path],
        data: Dict[str, Any]
    ) -> Path:
        """Write YAML file.
        
        Args:
            path: File path
            data: Data to write
            
        Returns:
            Path to written file
        """
        content = yaml.dump(data, default_flow_style=False)
        return self.write_file(path, content)
    
    def read_toml(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Read TOML file.
        
        Args:
            path: File path
            
        Returns:
            Parsed TOML data
        """
        content = self.read_file(path)
        try:
            return toml.loads(content)
        except toml.TomlDecodeError as e:
            raise ValidationError(f"Invalid TOML in {path}: {e}")
    
    def write_toml(
        self,
        path: Union[str, Path],
        data: Dict[str, Any]
    ) -> Path:
        """Write TOML file.
        
        Args:
            path: File path
            data: Data to write
            
        Returns:
            Path to written file
        """
        content = toml.dumps(data)
        return self.write_file(path, content)
    
    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """Resolve path relative to base path.
        
        Args:
            path: Path to resolve
            
        Returns:
            Resolved path
        """
        path = Path(path)
        if not path.is_absolute():
            path = self.base_path / path
        return path.resolve()
    
    def _create_backup(self, path: Path) -> Path:
        """Create backup of file.
        
        Args:
            path: File to backup
            
        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = path.with_suffix(f'.{timestamp}.bak')
        shutil.copy2(path, backup_path)
        logger.debug(f"Created backup: {backup_path}")
        return backup_path
    
    def _calculate_checksum(self, path: Path, algorithm: str = 'sha256') -> str:
        """Calculate file checksum.
        
        Args:
            path: File path
            algorithm: Hash algorithm
            
        Returns:
            Hex digest of checksum
        """
        hash_func = hashlib.new(algorithm)
        
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    def _is_binary_file(self, path: Path, sample_size: int = 8192) -> bool:
        """Check if file is binary.
        
        Args:
            path: File path
            sample_size: Bytes to sample
            
        Returns:
            True if binary file
        """
        try:
            with open(path, 'rb') as f:
                sample = f.read(sample_size)
            
            # Check for null bytes
            if b'\x00' in sample:
                return True
            
            # Check text characters ratio
            text_chars = bytes(range(32, 127)) + b'\n\r\t\b'
            non_text = sum(1 for byte in sample if byte not in text_chars)
            
            return non_text / len(sample) > 0.3
            
        except Exception:
            return True
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp files."""
        self.cleanup_temp_files()