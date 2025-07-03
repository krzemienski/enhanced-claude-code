"""Memory query engine for intelligent memory retrieval and analysis."""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from collections import defaultdict

from .store import PersistentMemoryStore, MemoryQuery, MemoryEntry, MemoryType, MemoryPriority

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of memory queries."""
    SIMPLE = "simple"
    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    PATTERN = "pattern"
    AGGREGATION = "aggregation"
    RELATIONSHIP = "relationship"


class SortBy(Enum):
    """Sort options for query results."""
    TIMESTAMP_DESC = "timestamp_desc"
    TIMESTAMP_ASC = "timestamp_asc"
    RELEVANCE_DESC = "relevance_desc"
    PRIORITY_DESC = "priority_desc"
    ACCESS_COUNT_DESC = "access_count_desc"


@dataclass
class QueryFilter:
    """Advanced query filter specification."""
    memory_types: List[MemoryType] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    exclude_tags: List[str] = field(default_factory=list)
    priority_min: Optional[MemoryPriority] = None
    priority_max: Optional[MemoryPriority] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    key_patterns: List[str] = field(default_factory=list)
    content_patterns: List[str] = field(default_factory=list)
    metadata_filters: Dict[str, Any] = field(default_factory=dict)
    min_relevance: float = 0.0
    include_expired: bool = False


@dataclass
class QueryResult:
    """Query execution result with metadata."""
    entries: List[MemoryEntry]
    total_matches: int
    execution_time_ms: float
    query_metadata: Dict[str, Any]
    relevance_scores: Dict[str, float] = field(default_factory=dict)
    aggregations: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticMatch:
    """Semantic similarity match result."""
    entry: MemoryEntry
    similarity_score: float
    matching_terms: List[str]
    context_snippet: str


class MemoryQueryEngine:
    """Advanced query engine for memory retrieval and analysis."""
    
    def __init__(self, memory_store: PersistentMemoryStore):
        """Initialize the query engine."""
        self.memory_store = memory_store
        
        # Query caching
        self._query_cache: Dict[str, QueryResult] = {}
        self._cache_max_size = 1000
        self._cache_ttl_seconds = 300  # 5 minutes
        
        # Query statistics
        self.stats = {
            "queries_executed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_execution_time_ms": 0.0,
            "most_common_filters": defaultdict(int)
        }
        
        # Semantic analysis patterns
        self._semantic_patterns = self._build_semantic_patterns()
        
        logger.info("Memory Query Engine initialized")
    
    def query(
        self,
        query_filter: QueryFilter,
        sort_by: SortBy = SortBy.TIMESTAMP_DESC,
        limit: int = 100,
        offset: int = 0,
        include_aggregations: bool = False
    ) -> QueryResult:
        """Execute a complex memory query."""
        start_time = datetime.now()
        
        # Check cache first
        cache_key = self._generate_cache_key(query_filter, sort_by, limit, offset)
        if cache_key in self._query_cache:
            cached_result = self._query_cache[cache_key]
            if self._is_cache_valid(cached_result):
                self.stats["cache_hits"] += 1
                self.stats["queries_executed"] += 1
                return cached_result
            else:
                del self._query_cache[cache_key]
        
        # Execute query
        base_query = self._build_base_query(query_filter)
        entries = self.memory_store.query(base_query)
        
        # Apply advanced filtering
        filtered_entries = self._apply_advanced_filters(entries, query_filter)
        
        # Calculate relevance scores
        relevance_scores = self._calculate_relevance_scores(filtered_entries, query_filter)
        
        # Sort results
        sorted_entries = self._sort_entries(filtered_entries, sort_by, relevance_scores)
        
        # Apply pagination
        total_matches = len(sorted_entries)
        paginated_entries = sorted_entries[offset:offset + limit]
        
        # Generate aggregations if requested
        aggregations = {}
        if include_aggregations:
            aggregations = self._generate_aggregations(filtered_entries)
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Create result
        result = QueryResult(
            entries=paginated_entries,
            total_matches=total_matches,
            execution_time_ms=execution_time,
            query_metadata={
                "filter": query_filter,
                "sort_by": sort_by.value,
                "limit": limit,
                "offset": offset,
                "timestamp": datetime.now().isoformat()
            },
            relevance_scores={entry.id: relevance_scores.get(entry.id, 0.0) for entry in paginated_entries},
            aggregations=aggregations
        )
        
        # Cache result
        self._cache_result(cache_key, result)
        
        # Update statistics
        self._update_stats(execution_time, query_filter)
        
        logger.debug(f"Query executed in {execution_time:.2f}ms, {total_matches} matches")
        
        return result
    
    def semantic_search(
        self,
        search_text: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 20,
        min_similarity: float = 0.3
    ) -> List[SemanticMatch]:
        """Perform semantic search across memory content."""
        # Normalize search text
        search_terms = self._extract_search_terms(search_text)
        
        # Build filter
        query_filter = QueryFilter(
            memory_types=memory_types or list(MemoryType),
            content_patterns=[f"*{term}*" for term in search_terms]
        )
        
        # Get candidate entries
        result = self.query(query_filter, limit=limit * 2)  # Get more candidates for better filtering
        
        # Calculate semantic similarity
        semantic_matches = []
        for entry in result.entries:
            similarity_score = self._calculate_semantic_similarity(search_terms, entry)
            
            if similarity_score >= min_similarity:
                matching_terms = self._find_matching_terms(search_terms, entry)
                context_snippet = self._extract_context_snippet(search_text, entry)
                
                semantic_matches.append(SemanticMatch(
                    entry=entry,
                    similarity_score=similarity_score,
                    matching_terms=matching_terms,
                    context_snippet=context_snippet
                ))
        
        # Sort by similarity score
        semantic_matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return semantic_matches[:limit]
    
    def find_patterns(
        self,
        pattern_type: str,
        memory_types: Optional[List[MemoryType]] = None,
        time_window_hours: Optional[int] = None
    ) -> Dict[str, List[MemoryEntry]]:
        """Find patterns in memory entries."""
        # Build time filter
        query_filter = QueryFilter(memory_types=memory_types or list(MemoryType))
        
        if time_window_hours:
            query_filter.since = datetime.now() - timedelta(hours=time_window_hours)
        
        # Get entries
        result = self.query(query_filter, limit=10000)  # Large limit for pattern analysis
        
        # Analyze patterns
        patterns = self._analyze_patterns(result.entries, pattern_type)
        
        return patterns
    
    def get_related_entries(
        self,
        entry_id: str,
        relation_types: List[str],
        max_depth: int = 2,
        limit: int = 50
    ) -> Dict[str, List[MemoryEntry]]:
        """Find entries related to a specific entry."""
        # Get the source entry
        source_entry = self.memory_store.retrieve(entry_id)
        if not source_entry:
            return {}
        
        related_entries = {}
        visited = {entry_id}
        
        # Find relations at each depth level
        current_level = [source_entry]
        
        for depth in range(max_depth):
            next_level = []
            
            for entry in current_level:
                # Find direct relations
                for relation_type in relation_types:
                    relations = self._find_direct_relations(entry, relation_type)
                    
                    if relation_type not in related_entries:
                        related_entries[relation_type] = []
                    
                    for related_entry in relations:
                        if related_entry.id not in visited and len(related_entries[relation_type]) < limit:
                            related_entries[relation_type].append(related_entry)
                            next_level.append(related_entry)
                            visited.add(related_entry.id)
            
            current_level = next_level
            if not current_level:
                break
        
        return related_entries
    
    def aggregate_by_time(
        self,
        query_filter: QueryFilter,
        time_bucket: str = "hour",  # hour, day, week, month
        metric: str = "count"  # count, size, avg_priority
    ) -> Dict[str, Any]:
        """Aggregate memory entries by time buckets."""
        result = self.query(query_filter, limit=10000)
        
        # Group by time buckets
        time_buckets = defaultdict(list)
        
        for entry in result.entries:
            bucket_key = self._get_time_bucket_key(entry.timestamp, time_bucket)
            time_buckets[bucket_key].append(entry)
        
        # Calculate metrics
        aggregation = {}
        for bucket_key, entries in time_buckets.items():
            if metric == "count":
                aggregation[bucket_key] = len(entries)
            elif metric == "size":
                aggregation[bucket_key] = sum(entry.size_bytes for entry in entries)
            elif metric == "avg_priority":
                priorities = [entry.priority.value for entry in entries]
                aggregation[bucket_key] = sum(priorities) / len(priorities) if priorities else 0
        
        return aggregation
    
    def get_query_suggestions(
        self,
        partial_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get query suggestions based on partial input."""
        suggestions = []
        
        # Tag suggestions
        if partial_query.startswith("#"):
            tag_prefix = partial_query[1:]
            common_tags = self._get_common_tags(tag_prefix)
            suggestions.extend([
                {
                    "type": "tag",
                    "suggestion": f"#{tag}",
                    "description": f"Filter by tag: {tag}"
                }
                for tag in common_tags
            ])
        
        # Memory type suggestions
        if partial_query.startswith("type:"):
            type_prefix = partial_query[5:]
            matching_types = [
                mt.value for mt in MemoryType
                if mt.value.startswith(type_prefix.lower())
            ]
            suggestions.extend([
                {
                    "type": "memory_type",
                    "suggestion": f"type:{mt}",
                    "description": f"Filter by memory type: {mt}"
                }
                for mt in matching_types
            ])
        
        # Date range suggestions
        if any(word in partial_query.lower() for word in ["last", "recent", "since"]):
            suggestions.extend([
                {
                    "type": "time_range",
                    "suggestion": "last:24h",
                    "description": "Entries from last 24 hours"
                },
                {
                    "type": "time_range",
                    "suggestion": "last:7d",
                    "description": "Entries from last 7 days"
                },
                {
                    "type": "time_range",
                    "suggestion": "last:30d",
                    "description": "Entries from last 30 days"
                }
            ])
        
        # Content-based suggestions
        if len(partial_query) > 2 and not any(c in partial_query for c in [":", "#"]):
            similar_queries = self._get_similar_historical_queries(partial_query)
            suggestions.extend([
                {
                    "type": "similar_query",
                    "suggestion": query,
                    "description": f"Similar to previous search"
                }
                for query in similar_queries
            ])
        
        return suggestions[:10]  # Limit to top 10 suggestions
    
    def explain_query(self, query_filter: QueryFilter) -> Dict[str, Any]:
        """Explain how a query will be executed."""
        explanation = {
            "query_type": self._determine_query_type(query_filter),
            "estimated_matches": self._estimate_result_count(query_filter),
            "execution_plan": self._generate_execution_plan(query_filter),
            "optimization_suggestions": self._suggest_optimizations(query_filter),
            "index_usage": self._analyze_index_usage(query_filter)
        }
        
        return explanation
    
    def _build_base_query(self, query_filter: QueryFilter) -> MemoryQuery:
        """Build base MemoryQuery from QueryFilter."""
        return MemoryQuery(
            memory_type=query_filter.memory_types[0] if len(query_filter.memory_types) == 1 else None,
            tags=query_filter.tags,
            priority_min=query_filter.priority_min,
            since=query_filter.since,
            until=query_filter.until,
            include_expired=query_filter.include_expired,
            limit=10000  # Large limit for post-processing
        )
    
    def _apply_advanced_filters(
        self,
        entries: List[MemoryEntry],
        query_filter: QueryFilter
    ) -> List[MemoryEntry]:
        """Apply advanced filtering beyond basic MemoryQuery."""
        filtered = entries
        
        # Filter by memory types (if multiple specified)
        if len(query_filter.memory_types) > 1:
            filtered = [e for e in filtered if e.memory_type in query_filter.memory_types]
        
        # Filter by excluded tags
        if query_filter.exclude_tags:
            filtered = [
                e for e in filtered
                if not any(tag in e.tags for tag in query_filter.exclude_tags)
            ]
        
        # Filter by priority range
        if query_filter.priority_max:
            filtered = [e for e in filtered if e.priority.value <= query_filter.priority_max.value]
        
        # Filter by key patterns
        if query_filter.key_patterns:
            filtered = [
                e for e in filtered
                if any(self._matches_pattern(e.key, pattern) for pattern in query_filter.key_patterns)
            ]
        
        # Filter by content patterns
        if query_filter.content_patterns:
            filtered = [
                e for e in filtered
                if any(self._content_matches_pattern(e, pattern) for pattern in query_filter.content_patterns)
            ]
        
        # Filter by metadata
        if query_filter.metadata_filters:
            filtered = [
                e for e in filtered
                if self._metadata_matches_filters(e.metadata, query_filter.metadata_filters)
            ]
        
        return filtered
    
    def _calculate_relevance_scores(
        self,
        entries: List[MemoryEntry],
        query_filter: QueryFilter
    ) -> Dict[str, float]:
        """Calculate relevance scores for entries."""
        scores = {}
        
        for entry in entries:
            score = 0.0
            
            # Base score from priority
            score += entry.priority.value * 0.1
            
            # Recency score
            age_hours = (datetime.now() - entry.timestamp).total_seconds() / 3600
            if age_hours < 24:
                score += 0.3 * (1 - age_hours / 24)
            
            # Access frequency score
            if entry.access_count > 0:
                score += min(0.2, entry.access_count * 0.02)
            
            # Tag match score
            if query_filter.tags:
                matching_tags = set(entry.tags) & set(query_filter.tags)
                score += (len(matching_tags) / len(query_filter.tags)) * 0.3
            
            # Content pattern match score
            if query_filter.content_patterns:
                for pattern in query_filter.content_patterns:
                    if self._content_matches_pattern(entry, pattern):
                        score += 0.1
            
            scores[entry.id] = min(score, 1.0)  # Cap at 1.0
        
        return scores
    
    def _sort_entries(
        self,
        entries: List[MemoryEntry],
        sort_by: SortBy,
        relevance_scores: Dict[str, float]
    ) -> List[MemoryEntry]:
        """Sort entries according to sort criteria."""
        if sort_by == SortBy.TIMESTAMP_DESC:
            return sorted(entries, key=lambda e: e.timestamp, reverse=True)
        elif sort_by == SortBy.TIMESTAMP_ASC:
            return sorted(entries, key=lambda e: e.timestamp)
        elif sort_by == SortBy.RELEVANCE_DESC:
            return sorted(entries, key=lambda e: relevance_scores.get(e.id, 0.0), reverse=True)
        elif sort_by == SortBy.PRIORITY_DESC:
            return sorted(entries, key=lambda e: e.priority.value, reverse=True)
        elif sort_by == SortBy.ACCESS_COUNT_DESC:
            return sorted(entries, key=lambda e: e.access_count, reverse=True)
        else:
            return entries
    
    def _generate_aggregations(self, entries: List[MemoryEntry]) -> Dict[str, Any]:
        """Generate aggregation statistics."""
        aggregations = {
            "total_count": len(entries),
            "by_type": defaultdict(int),
            "by_priority": defaultdict(int),
            "by_hour": defaultdict(int),
            "total_size_bytes": 0,
            "avg_access_count": 0.0,
            "most_common_tags": defaultdict(int)
        }
        
        for entry in entries:
            aggregations["by_type"][entry.memory_type.value] += 1
            aggregations["by_priority"][entry.priority.value] += 1
            aggregations["by_hour"][entry.timestamp.hour] += 1
            aggregations["total_size_bytes"] += entry.size_bytes
            
            for tag in entry.tags:
                aggregations["most_common_tags"][tag] += 1
        
        if entries:
            aggregations["avg_access_count"] = sum(e.access_count for e in entries) / len(entries)
        
        # Convert defaultdicts to regular dicts
        aggregations["by_type"] = dict(aggregations["by_type"])
        aggregations["by_priority"] = dict(aggregations["by_priority"])
        aggregations["by_hour"] = dict(aggregations["by_hour"])
        aggregations["most_common_tags"] = dict(aggregations["most_common_tags"])
        
        return aggregations
    
    def _extract_search_terms(self, search_text: str) -> List[str]:
        """Extract and normalize search terms."""
        # Remove special characters and split
        terms = re.findall(r'\b\w+\b', search_text.lower())
        
        # Filter out common stop words
        stop_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "a", "an"}
        terms = [term for term in terms if term not in stop_words and len(term) > 2]
        
        return terms
    
    def _calculate_semantic_similarity(
        self,
        search_terms: List[str],
        entry: MemoryEntry
    ) -> float:
        """Calculate semantic similarity between search terms and entry."""
        # Convert entry content to searchable text
        entry_text = self._extract_entry_text(entry).lower()
        entry_words = set(re.findall(r'\b\w+\b', entry_text))
        
        # Direct word matches
        matching_words = set(search_terms) & entry_words
        direct_score = len(matching_words) / len(search_terms) if search_terms else 0.0
        
        # Semantic pattern matches
        semantic_score = 0.0
        for term in search_terms:
            for pattern_group in self._semantic_patterns.values():
                if term in pattern_group and any(synonym in entry_words for synonym in pattern_group):
                    semantic_score += 0.1
        
        # Context score (terms appearing near each other)
        context_score = self._calculate_context_score(search_terms, entry_text)
        
        # Combine scores
        total_score = (direct_score * 0.6) + (semantic_score * 0.2) + (context_score * 0.2)
        
        return min(total_score, 1.0)
    
    def _extract_entry_text(self, entry: MemoryEntry) -> str:
        """Extract searchable text from entry."""
        text_parts = [entry.key]
        
        # Add tags
        text_parts.extend(entry.tags)
        
        # Add content if it's text-like
        if isinstance(entry.data, str):
            text_parts.append(entry.data)
        elif isinstance(entry.data, dict):
            # Extract string values from dict
            for value in entry.data.values():
                if isinstance(value, str):
                    text_parts.append(value)
        
        return " ".join(text_parts)
    
    def _build_semantic_patterns(self) -> Dict[str, Set[str]]:
        """Build semantic pattern groups."""
        return {
            "error_terms": {"error", "exception", "fail", "failure", "bug", "issue", "problem"},
            "success_terms": {"success", "complete", "done", "finish", "achieve", "accomplish"},
            "config_terms": {"config", "configuration", "setting", "option", "parameter", "preference"},
            "performance_terms": {"performance", "speed", "fast", "slow", "optimize", "efficiency"},
            "security_terms": {"security", "auth", "authentication", "permission", "access", "secure"}
        }
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches a glob-like pattern."""
        # Convert glob pattern to regex
        regex_pattern = pattern.replace("*", ".*").replace("?", ".")
        return bool(re.match(f"^{regex_pattern}$", text, re.IGNORECASE))
    
    def _content_matches_pattern(self, entry: MemoryEntry, pattern: str) -> bool:
        """Check if entry content matches pattern."""
        entry_text = self._extract_entry_text(entry)
        return self._matches_pattern(entry_text, pattern)
    
    def _metadata_matches_filters(
        self,
        metadata: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> bool:
        """Check if metadata matches all filter criteria."""
        for key, expected_value in filters.items():
            if key not in metadata:
                return False
            
            actual_value = metadata[key]
            
            # Handle different comparison types
            if isinstance(expected_value, dict) and "operator" in expected_value:
                operator = expected_value["operator"]
                value = expected_value["value"]
                
                if operator == "eq" and actual_value != value:
                    return False
                elif operator == "gt" and actual_value <= value:
                    return False
                elif operator == "lt" and actual_value >= value:
                    return False
                elif operator == "contains" and str(value).lower() not in str(actual_value).lower():
                    return False
            else:
                # Direct equality check
                if actual_value != expected_value:
                    return False
        
        return True
    
    def _generate_cache_key(
        self,
        query_filter: QueryFilter,
        sort_by: SortBy,
        limit: int,
        offset: int
    ) -> str:
        """Generate cache key for query."""
        import hashlib
        
        key_parts = [
            str(query_filter),
            sort_by.value,
            str(limit),
            str(offset)
        ]
        
        content = "|".join(key_parts)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _is_cache_valid(self, cached_result: QueryResult) -> bool:
        """Check if cached result is still valid."""
        cache_time = datetime.fromisoformat(cached_result.query_metadata["timestamp"])
        age_seconds = (datetime.now() - cache_time).total_seconds()
        return age_seconds < self._cache_ttl_seconds
    
    def _cache_result(self, cache_key: str, result: QueryResult) -> None:
        """Cache query result."""
        if len(self._query_cache) >= self._cache_max_size:
            # Remove oldest entry
            oldest_key = min(
                self._query_cache.keys(),
                key=lambda k: self._query_cache[k].query_metadata["timestamp"]
            )
            del self._query_cache[oldest_key]
        
        self._query_cache[cache_key] = result
    
    def _update_stats(self, execution_time: float, query_filter: QueryFilter) -> None:
        """Update query statistics."""
        self.stats["queries_executed"] += 1
        self.stats["cache_misses"] += 1
        
        # Update average execution time
        total_time = self.stats["avg_execution_time_ms"] * (self.stats["queries_executed"] - 1)
        self.stats["avg_execution_time_ms"] = (total_time + execution_time) / self.stats["queries_executed"]
        
        # Track common filters
        for memory_type in query_filter.memory_types:
            self.stats["most_common_filters"][f"type:{memory_type.value}"] += 1
        
        for tag in query_filter.tags:
            self.stats["most_common_filters"][f"tag:{tag}"] += 1