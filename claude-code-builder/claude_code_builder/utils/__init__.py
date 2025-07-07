"""Utilities package for Claude Code Builder."""

# Import all utility modules
from .constants import *
from .file_handler import FileHandler, FileInfo
from .json_utils import (
    JSONEncoder, StreamingJSONParser, parse_json, dumps_json,
    validate_json_schema, merge_json, diff_json, flatten_json,
    unflatten_json, extract_json_from_text, json_to_yaml, json_to_toml
)
from .string_utils import (
    clean_string, truncate_string, wrap_text, snake_case, camel_case,
    kebab_case, title_case, extract_numbers, extract_urls, extract_emails,
    highlight_text, remove_accents, get_string_metrics, levenshtein_distance,
    similarity_ratio, hash_string, encode_base64, decode_base64,
    url_encode, url_decode, pluralize, format_bytes, StringMetrics
)
from .path_utils import (
    normalize_path, ensure_parent_dir, relative_to_cwd, common_path,
    is_subpath, safe_join, find_project_root, find_files, get_temp_dir,
    get_home_dir, get_config_dir, get_cache_dir, split_path,
    change_extension, sanitize_filename, walk_files, make_executable
)
from .template_engine import TemplateEngine, TemplateContext
from .config_loader import ConfigLoader, ConfigSchema
from .error_handler import (
    ErrorHandler, ErrorContext, handle_error, register_handler,
    retry_on_error, ignore_errors, error_context, format_exception
)
from .cache_manager import (
    CacheManager, CacheEntry, get_cache, clear_all_caches, cache_stats
)

__all__ = [
    # Constants
    'VERSION', 'DEFAULT_MAX_TOKENS', 'DEFAULT_MODEL', 'PHASES',
    
    # File handler
    'FileHandler', 'FileInfo',
    
    # JSON utils
    'JSONEncoder', 'StreamingJSONParser', 'parse_json', 'dumps_json',
    'validate_json_schema', 'merge_json', 'diff_json', 'flatten_json',
    'unflatten_json', 'extract_json_from_text', 'json_to_yaml', 'json_to_toml',
    
    # String utils
    'clean_string', 'truncate_string', 'wrap_text', 'snake_case', 'camel_case',
    'kebab_case', 'title_case', 'extract_numbers', 'extract_urls', 'extract_emails',
    'highlight_text', 'remove_accents', 'get_string_metrics', 'levenshtein_distance',
    'similarity_ratio', 'hash_string', 'encode_base64', 'decode_base64',
    'url_encode', 'url_decode', 'pluralize', 'format_bytes', 'StringMetrics',
    
    # Path utils
    'normalize_path', 'ensure_parent_dir', 'relative_to_cwd', 'common_path',
    'is_subpath', 'safe_join', 'find_project_root', 'find_files', 'get_temp_dir',
    'get_home_dir', 'get_config_dir', 'get_cache_dir', 'split_path',
    'change_extension', 'sanitize_filename', 'walk_files', 'make_executable',
    
    # Template engine
    'TemplateEngine', 'TemplateContext',
    
    # Config loader
    'ConfigLoader', 'ConfigSchema',
    
    # Error handler
    'ErrorHandler', 'ErrorContext', 'handle_error', 'register_handler',
    'retry_on_error', 'ignore_errors', 'error_context', 'format_exception',
    
    # Cache manager
    'CacheManager', 'CacheEntry', 'get_cache', 'clear_all_caches', 'cache_stats'
]