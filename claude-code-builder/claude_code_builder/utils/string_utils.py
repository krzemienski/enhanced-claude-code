"""String manipulation helpers for Claude Code Builder."""
import re
import textwrap
import unicodedata
from typing import List, Optional, Tuple, Dict, Any, Pattern
from dataclasses import dataclass
import hashlib
import base64
from urllib.parse import quote, unquote

from ..logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StringMetrics:
    """Metrics for string analysis."""
    length: int = 0
    words: int = 0
    lines: int = 0
    characters: int = 0
    whitespace: int = 0
    alphanumeric: int = 0
    special: int = 0
    uppercase: int = 0
    lowercase: int = 0
    digits: int = 0


def clean_string(
    text: str,
    normalize_whitespace: bool = True,
    strip: bool = True,
    remove_empty_lines: bool = True
) -> str:
    """Clean and normalize string.
    
    Args:
        text: Input text
        normalize_whitespace: Normalize whitespace characters
        strip: Strip leading/trailing whitespace
        remove_empty_lines: Remove empty lines
        
    Returns:
        Cleaned string
    """
    if not text:
        return ""
    
    # Normalize whitespace
    if normalize_whitespace:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Remove empty lines
    if remove_empty_lines:
        lines = [line for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
    
    # Strip whitespace
    if strip:
        text = text.strip()
    
    return text


def truncate_string(
    text: str,
    max_length: int,
    suffix: str = "...",
    whole_words: bool = True
) -> str:
    """Truncate string to maximum length.
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to append
        whole_words: Truncate at word boundaries
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    truncated_length = max_length - len(suffix)
    
    if truncated_length <= 0:
        return suffix[:max_length]
    
    if whole_words:
        # Find last word boundary
        truncated = text[:truncated_length]
        last_space = truncated.rfind(' ')
        
        if last_space > 0:
            truncated = truncated[:last_space]
    else:
        truncated = text[:truncated_length]
    
    return truncated + suffix


def wrap_text(
    text: str,
    width: int = 80,
    initial_indent: str = "",
    subsequent_indent: str = "",
    break_long_words: bool = False
) -> str:
    """Wrap text to specified width.
    
    Args:
        text: Input text
        width: Line width
        initial_indent: First line indent
        subsequent_indent: Other lines indent
        break_long_words: Break long words
        
    Returns:
        Wrapped text
    """
    return textwrap.fill(
        text,
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_long_words=break_long_words
    )


def snake_case(text: str) -> str:
    """Convert string to snake_case.
    
    Args:
        text: Input text
        
    Returns:
        snake_case string
    """
    # Replace non-alphanumeric with spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Insert spaces before capitals
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    
    # Convert to lowercase and replace spaces with underscores
    return re.sub(r'\s+', '_', text.strip().lower())


def camel_case(text: str, upper_first: bool = False) -> str:
    """Convert string to camelCase or PascalCase.
    
    Args:
        text: Input text
        upper_first: Use PascalCase
        
    Returns:
        camelCase/PascalCase string
    """
    # Split by non-alphanumeric
    words = re.findall(r'\w+', text)
    
    if not words:
        return ""
    
    # Capitalize words
    if upper_first:
        return ''.join(word.capitalize() for word in words)
    else:
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:])


def kebab_case(text: str) -> str:
    """Convert string to kebab-case.
    
    Args:
        text: Input text
        
    Returns:
        kebab-case string
    """
    # Replace non-alphanumeric with spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Insert spaces before capitals
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    
    # Convert to lowercase and replace spaces with hyphens
    return re.sub(r'\s+', '-', text.strip().lower())


def title_case(text: str, exceptions: Optional[List[str]] = None) -> str:
    """Convert string to Title Case.
    
    Args:
        text: Input text
        exceptions: Words to keep lowercase
        
    Returns:
        Title case string
    """
    exceptions = exceptions or ['a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']
    
    words = text.split()
    result = []
    
    for i, word in enumerate(words):
        # Always capitalize first and last word
        if i == 0 or i == len(words) - 1:
            result.append(word.capitalize())
        elif word.lower() in exceptions:
            result.append(word.lower())
        else:
            result.append(word.capitalize())
    
    return ' '.join(result)


def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from text.
    
    Args:
        text: Input text
        
    Returns:
        List of numbers
    """
    # Pattern for integers and floats
    pattern = r'-?\d+\.?\d*'
    matches = re.findall(pattern, text)
    
    numbers = []
    for match in matches:
        try:
            if '.' in match:
                numbers.append(float(match))
            else:
                numbers.append(float(match))
        except ValueError:
            continue
    
    return numbers


def extract_urls(text: str) -> List[str]:
    """Extract URLs from text.
    
    Args:
        text: Input text
        
    Returns:
        List of URLs
    """
    # URL pattern
    pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
    return re.findall(pattern, text)


def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text.
    
    Args:
        text: Input text
        
    Returns:
        List of email addresses
    """
    # Email pattern
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(pattern, text)


def highlight_text(
    text: str,
    search_terms: List[str],
    prefix: str = "**",
    suffix: str = "**",
    case_sensitive: bool = False
) -> str:
    """Highlight search terms in text.
    
    Args:
        text: Input text
        search_terms: Terms to highlight
        prefix: Highlight prefix
        suffix: Highlight suffix
        case_sensitive: Case sensitive search
        
    Returns:
        Text with highlighted terms
    """
    for term in search_terms:
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.escape(term)
        replacement = f"{prefix}{term}{suffix}"
        text = re.sub(pattern, replacement, text, flags=flags)
    
    return text


def remove_accents(text: str) -> str:
    """Remove accents from characters.
    
    Args:
        text: Input text
        
    Returns:
        Text without accents
    """
    # Normalize to NFD (decomposed form)
    nfd = unicodedata.normalize('NFD', text)
    
    # Filter out combining characters (accents)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')


def get_string_metrics(text: str) -> StringMetrics:
    """Calculate string metrics.
    
    Args:
        text: Input text
        
    Returns:
        String metrics
    """
    metrics = StringMetrics()
    
    if not text:
        return metrics
    
    metrics.length = len(text)
    metrics.lines = text.count('\n') + 1
    metrics.words = len(text.split())
    
    for char in text:
        if char.isspace():
            metrics.whitespace += 1
        elif char.isalnum():
            metrics.alphanumeric += 1
            if char.isupper():
                metrics.uppercase += 1
            elif char.islower():
                metrics.lowercase += 1
            elif char.isdigit():
                metrics.digits += 1
        else:
            metrics.special += 1
    
    metrics.characters = metrics.alphanumeric + metrics.special
    
    return metrics


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between strings.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Edit distance
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            
            current_row.append(min(insertions, deletions, substitutions))
        
        previous_row = current_row
    
    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """Calculate similarity ratio between strings.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Similarity ratio (0.0 to 1.0)
    """
    if not s1 and not s2:
        return 1.0
    
    if not s1 or not s2:
        return 0.0
    
    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    
    return 1.0 - (distance / max_len)


def hash_string(text: str, algorithm: str = 'sha256') -> str:
    """Generate hash of string.
    
    Args:
        text: Input text
        algorithm: Hash algorithm
        
    Returns:
        Hex digest
    """
    hash_func = hashlib.new(algorithm)
    hash_func.update(text.encode('utf-8'))
    return hash_func.hexdigest()


def encode_base64(text: str) -> str:
    """Encode string to base64.
    
    Args:
        text: Input text
        
    Returns:
        Base64 encoded string
    """
    return base64.b64encode(text.encode('utf-8')).decode('ascii')


def decode_base64(encoded: str) -> str:
    """Decode base64 string.
    
    Args:
        encoded: Base64 encoded string
        
    Returns:
        Decoded string
    """
    return base64.b64decode(encoded.encode('ascii')).decode('utf-8')


def url_encode(text: str, safe: str = '') -> str:
    """URL encode string.
    
    Args:
        text: Input text
        safe: Characters to not encode
        
    Returns:
        URL encoded string
    """
    return quote(text, safe=safe)


def url_decode(encoded: str) -> str:
    """URL decode string.
    
    Args:
        encoded: URL encoded string
        
    Returns:
        Decoded string
    """
    return unquote(encoded)


def pluralize(word: str, count: int) -> str:
    """Simple pluralization of word based on count.
    
    Args:
        word: Word to pluralize
        count: Item count
        
    Returns:
        Pluralized word
    """
    if count == 1:
        return word
    
    # Simple rules for common cases
    if word.endswith(('s', 'ss', 'sh', 'ch', 'x', 'z')):
        return word + 'es'
    elif word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
        return word[:-1] + 'ies'
    elif word.endswith('f'):
        return word[:-1] + 'ves'
    elif word.endswith('fe'):
        return word[:-2] + 'ves'
    else:
        return word + 's'


def format_bytes(num_bytes: int, precision: int = 2) -> str:
    """Format bytes as human readable string.
    
    Args:
        num_bytes: Number of bytes
        precision: Decimal precision
        
    Returns:
        Formatted string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.{precision}f} {unit}"
        num_bytes /= 1024.0
    
    return f"{num_bytes:.{precision}f} EB"