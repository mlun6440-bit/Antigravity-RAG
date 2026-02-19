#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Query Cache
In-memory LRU cache for RAG query results to reduce API costs and latency.
"""

import hashlib
import time
import logging
from typing import Dict, Any, Optional
from collections import OrderedDict
import threading
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QueryCache:
    """Thread-safe LRU cache for query results."""

    def __init__(self, max_size: int = 128, ttl_seconds: int = 3600):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of entries (default: 128)
            ttl_seconds: Time to live in seconds (default: 1 hour)
        """
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        logger.info(f"QueryCache initialized (size={max_size}, ttl={ttl_seconds}s)")

    def _generate_key(self, query: str, mode: str, kwargs: Dict[str, Any]) -> str:
        """Generate a unique hash key for a query + params."""
        # Create a canonical representation of the input
        # Dictionary keys are sorted to ensure consistency
        key_data = {
            'q': query.strip().lower(),
            'm': mode,
            'k': json.dumps(kwargs, sort_keys=True, default=str)
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()

    def get(self, query: str, mode: str = 'default', **kwargs) -> Optional[Dict[str, Any]]:
        """
        Retrieve a result from the cache.
        
        Args:
            query: User text query
            mode: Query mode/type
            **kwargs: Additional parameters affecting the result
            
        Returns:
            Cached result dict or None
        """
        key = self._generate_key(query, mode, kwargs)
        
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            entry = self.cache[key]
            
            # Check expiration
            if time.time() > entry['expiry']:
                del self.cache[key]
                self.misses += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            logger.info(f"Cache HIT for query: {query[:30]}...")
            return entry['data']

    def put(self, query: str, data: Dict[str, Any], mode: str = 'default', **kwargs) -> None:
        """
        Add a result to the cache.
        
        Args:
            query: User text query
            data: Result dictionary to cache
            mode: Query mode/type
            **kwargs: Additional parameters used to generate the key
        """
        key = self._generate_key(query, mode, kwargs)
        
        with self.lock:
            # Evict oldest if full
            if len(self.cache) >= self.max_size and key not in self.cache:
                self.cache.popitem(last=False)
            
            self.cache[key] = {
                'data': data,
                'expiry': time.time() + self.ttl
            }
            self.cache.move_to_end(key)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': f"{hit_rate:.1f}%"
            }

    def clear(self) -> None:
        """Clear the entire cache."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            logger.info("Cache cleared")

if __name__ == "__main__":
    # Simple test
    cache = QueryCache(max_size=2, ttl_seconds=2)
    
    # Test put/get
    cache.put("test", {"result": "val"}, mode="test")
    res = cache.get("test", mode="test")
    print(f"Get result: {res}")  # Should be {'result': 'val'}
    
    # Test stats
    print(f"Stats: {cache.get_stats()}")
