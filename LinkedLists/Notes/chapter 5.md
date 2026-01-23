# Episode 5: The Cache That Forgets
## How LRU Cache Powers Your Browser, Database, and OS

**Season 1 — The Invisible Linked List**  
**Episode: S1E5**

---

## The Problem Every System Faces

LeetCode #146 - LRU Cache. It's one of the most popular interview questions. You've probably solved it. But here's what they don't tell you: this exact data structure runs **billions of times per second** in your browser, your database, your operating system, and every layer of the computing stack.

Every system faces the same constraint: **fast storage is limited, slow storage is abundant**. RAM is faster than disk. Disk is faster than network. L1 cache is faster than RAM. The solution? Keep recently-used data in the fast layer, evict the rest. This is the LRU pattern.

Today, we're building production-grade caches from LeetCode's foundation, then discovering why vanilla LRU breaks at scale.

---

## Part 1: The Theory of Caching

### Why Caches Exist: The Memory Hierarchy

Modern computers have a memory hierarchy, each level trading capacity for speed:

```
L1 Cache:    32-64 KB      ~1 ns access      (CPU register speed)
L2 Cache:    256-512 KB    ~3 ns access
L3 Cache:    8-32 MB       ~12 ns access
RAM:         8-64 GB       ~100 ns access    (100x slower than L1!)
SSD:         256GB-4TB     ~100 µs access    (1000x slower than RAM!)
HDD:         1-10 TB       ~5 ms access      (50x slower than SSD!)
Network:     ∞             ~50-500 ms        (100,000x slower than RAM!)
```

The gap between levels is **exponential**. A cache miss to disk costs 50,000x more than a hit in RAM. This is why caching matters.

### The Principle of Locality

Caches work because of **locality**—the observation that programs exhibit predictable access patterns:

**1. Temporal locality**: "If I accessed X recently, I'll likely access it again soon"
- Example: Loading the same profile picture 100 times while scrolling Instagram
- Exploited by: LRU, LFU (Least Frequently Used)

**2. Spatial locality**: "If I accessed X, I'll likely access nearby data soon"
- Example: Reading sequential array elements, loading adjacent image tiles
- Exploited by: Prefetching, cache line sizes (load 64 bytes even if you asked for 1)

**3. Semantic locality**: "Related items are accessed together"
- Example: User profile + user posts + user followers
- Exploited by: Application-level caches, graph databases

### Eviction Policies: Choosing What to Forget

When the cache is full, which item do you evict?

| Policy | Strategy | Best For | Worst For |
|--------|----------|----------|----------|
| **LRU** (Least Recently Used) | Evict oldest access | Temporal locality, general purpose | Sequential scans (thrashing) |
| **LFU** (Least Frequently Used) | Evict lowest access count | Hot items accessed repeatedly | Stale popular items |
| **FIFO** | Evict oldest insertion | Simple hardware caches | Ignores access patterns |
| **Random** | Evict random item | Low overhead, surprisingly good | No guarantees |
| **ARC** (Adaptive Replacement Cache) | Balance recency + frequency | Mixed workloads | Complex implementation |
| **2Q** | Two queues (recent + frequent) | Ghost entries for adaptation | Memory overhead |
| **CLOCK** | Circular buffer with "second chance" bit | OS page replacement | Not truly optimal |

**Why LRU wins**: Simple to implement, exploits temporal locality, performs well on average. Most production systems use LRU or LRU variants.

### The Cache Coherence Problem

In distributed systems, multiple caches can hold the same data. **Cache coherence** ensures consistency:

**Problem**: Server A caches `user:123 = {name: "Alice"}`. User changes name to "Alicia". Server B still serves stale "Alice".

**Solutions**:
1. **TTL (Time To Live)**: Entries expire after N seconds (eventual consistency)
2. **Cache invalidation**: Explicit invalidation messages (requires coordination)
3. **Write-through**: Writes update both cache and database (slow writes)
4. **Write-behind**: Writes update cache, async update database (risk of data loss)

**Famous quote**: "There are only two hard things in Computer Science: cache invalidation and naming things." —Phil Karlton

Now let's implement this.

---

## Part 2: The LeetCode Foundation

The classic O(1) solution combines two data structures:

```python
class DListNode:
    """Node in doubly-linked list for O(1) removal"""
    def __init__(self, key=0, value=0):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None

class LRUCache:
    """
    Hash map + doubly linked list = O(1) operations.
    
    The trick: Hash map gives O(1) lookup.
               Doubly-linked list gives O(1) move-to-front and eviction.
    """
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}  # key -> DListNode
        
        # Sentinel nodes simplify edge cases
        self.head = DListNode()  # Most recent (MRU)
        self.tail = DListNode()  # Least recent (LRU)
        self.head.next = self.tail
        self.tail.prev = self.head
    
    def _add_node(self, node: DListNode):
        """Add node right after head (most recent position)"""
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node
    
    def _remove_node(self, node: DListNode):
        """Remove node from its current position"""
        prev_node = node.prev
        next_node = node.next
        prev_node.next = next_node
        next_node.prev = prev_node
    
    def _move_to_head(self, node: DListNode):
        """Mark node as most recently used"""
        self._remove_node(node)
        self._add_node(node)
    
    def _pop_tail(self) -> DListNode:
        """Remove and return least recently used node"""
        lru = self.tail.prev
        self._remove_node(lru)
        return lru
    
    def get(self, key: int) -> int:
        """O(1) lookup with recency update"""
        if key not in self.cache:
            return -1
        
        node = self.cache[key]
        self._move_to_head(node)  # Critical: update access order
        return node.value
    
    def put(self, key: int, value: int) -> None:
        """O(1) insertion with automatic eviction"""
        if key in self.cache:
            # Update existing key
            node = self.cache[key]
            node.value = value
            self._move_to_head(node)
        else:
            # New key
            if len(self.cache) >= self.capacity:
                # Evict LRU item
                lru = self._pop_tail()
                del self.cache[lru.key]
            
            # Insert new node
            new_node = DListNode(key, value)
            self.cache[key] = new_node
            self._add_node(new_node)

# Visual representation:
# head <-> [MRU: key=5] <-> [key=3] <-> [key=7] <-> [LRU: key=1] <-> tail
#
# After get(7):
# head <-> [key=7] <-> [key=5] <-> [key=3] <-> [key=1] <-> tail
#
# If cache full and put(9):
# head <-> [key=9] <-> [key=7] <-> [key=5] <-> [key=3] <-> tail
#          (key=1 evicted)
```

**What this teaches:** The algorithm. Pointer manipulation. O(1) complexity. This is pure data structures—and it's absolutely correct for interviews.

But production systems need more.

---

## Part 3: Multi-Tier Caching Theory

### Why Browsers Need Different Caches

Browsers don't use a single cache—they use **tiered caches** with different policies for different resource types:

**Memory cache (RAM)**:
- Fastest access (~100ns)
- Small capacity (~50-200MB)
- Volatile (cleared on restart)
- Stores: Decoded images, parsed CSS/JS, hot API responses

**Disk cache (SSD)**:
- Slower access (~100µs), but 1000x larger
- Persistent across restarts
- Stores: Raw file bytes (images, scripts, fonts)

**HTTP cache (semantic)**:
- Respects `Cache-Control`, `ETag`, `Last-Modified` headers
- Can revalidate with server (`304 Not Modified`)
- Handles versioning and staleness

### Resource Prioritization

Not all cached items are equal. Chrome's cache uses **resource type quotas**:

```
Critical rendering path:
  1. HTML (highest priority)
  2. CSS (render-blocking)
  3. Fonts (render-blocking for text)
  4. Scripts (can be deferred)
  5. Images (lazy-loadable)

Cache allocation:
  - Scripts/CSS: 50% of cache (frequently reused across pages)
  - Images: 30% (largest bytes, but specific to pages)
  - Fonts: 10% (shared across site, rarely change)
  - API responses: 10% (short TTL, user-specific)
```

**Why this matters**: Without quotas, a single 50MB video could evict 500 critical scripts. Partitioned caches prevent this.

### Proactive Eviction Under Memory Pressure

Browsers must react to memory pressure **before** the OS kills them:

**Levels of pressure**:
1. **Normal**: Standard LRU eviction when cache full
2. **Warning** (80% memory used): Evict least-valuable items first (images before scripts)
3. **Critical** (95% memory): Aggressive eviction, disable caching
4. **Emergency**: Clear all caches immediately

Now let's build this.

---

## Part 4: Building a Production Browser Cache

Your browser caches everything: images, CSS, JavaScript, fonts, API responses. Let's build a realistic browser resource cache:

```python
import time
import hashlib
from typing import Optional, Dict
from dataclasses import dataclass
from enum import Enum

class ResourceType(Enum):
    IMAGE = "image"
    STYLESHEET = "stylesheet"
    SCRIPT = "script"
    FONT = "font"
    API_RESPONSE = "api"
    DOCUMENT = "document"

@dataclass
class CacheMetrics:
    """Track cache performance"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_bytes_stored: int = 0
    total_bytes_served: int = 0
    
    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def bandwidth_saved_ratio(self) -> float:
        """How much network bandwidth did caching save?"""
        total = self.total_bytes_served + self.misses  # Approximate
        return self.total_bytes_served / total if total > 0 else 0.0

class Resource:
    """Cached web resource with metadata"""
    def __init__(self, url: str, content: bytes, content_type: str, 
                 resource_type: ResourceType):
        self.url = url
        self.content = content
        self.content_type = content_type
        self.resource_type = resource_type
        self.size = len(content)
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0
        
        # HTTP cache headers (simplified)
        self.cache_control_max_age = 3600  # 1 hour default
        self.etag = hashlib.md5(content).hexdigest()[:16]
    
    def is_expired(self) -> bool:
        """Check if resource exceeded max-age"""
        age = time.time() - self.created_at
        return age > self.cache_control_max_age
    
    def touch(self):
        """Update access metadata"""
        self.last_accessed = time.time()
        self.access_count += 1

class BrowserResourceCache:
    """
    Production-grade browser cache with:
    1. Size-based eviction (not just count)
    2. Resource type awareness
    3. HTTP cache semantics
    4. Comprehensive metrics
    5. Thread-safe operations (simplified for demo)
    """
    
    def __init__(self, max_size_mb: int = 100):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size_bytes = 0
        
        # Core LRU mechanism
        self.lru = LRUCache(capacity=10000)  # Max 10k resources
        self.resources: Dict[str, Resource] = {}
        
        # Metrics
        self.metrics = CacheMetrics()
        
        # Resource type limits (prevent one type from dominating)
        self.type_limits = {
            ResourceType.IMAGE: int(max_size_mb * 0.5 * 1024 * 1024),  # 50% for images
            ResourceType.SCRIPT: int(max_size_mb * 0.2 * 1024 * 1024),  # 20% for scripts
            ResourceType.STYLESHEET: int(max_size_mb * 0.15 * 1024 * 1024),  # 15% for CSS
            ResourceType.FONT: int(max_size_mb * 0.1 * 1024 * 1024),  # 10% for fonts
            ResourceType.API_RESPONSE: int(max_size_mb * 0.05 * 1024 * 1024)  # 5% for API
        }
        self.type_current_sizes = {t: 0 for t in ResourceType}
    
    def get_resource(self, url: str) -> Optional[bytes]:
        """
        Get cached resource with validation.
        Returns None if not cached or expired.
        """
        if url not in self.resources:
            self.metrics.misses += 1
            return None
        
        resource = self.resources[url]
        
        # Check expiration (HTTP cache semantics)
        if resource.is_expired():
            # Expired - treat as miss and remove
            self._remove_resource(url)
            self.metrics.misses += 1
            return None
        
        # Cache hit - update access order
        self.lru.get(url)  # Internally moves to MRU position
        resource.touch()
        
        # Update metrics
        self.metrics.hits += 1
        self.metrics.total_bytes_served += resource.size
        
        return resource.content
    
    def put_resource(self, url: str, content: bytes, content_type: str,
                    resource_type: ResourceType, max_age: int = 3600) -> bool:
        """
        Cache a resource with size management.
        Returns False if resource is too large to cache.
        """
        resource = Resource(url, content, content_type, resource_type)
        resource.cache_control_max_age = max_age
        
        # Sanity check: don't cache resources larger than 10% of total cache
        if resource.size > self.max_size_bytes * 0.1:
            return False
        
        # Check type-specific limits
        type_limit = self.type_limits.get(resource_type, self.max_size_bytes)
        if self.type_current_sizes[resource_type] + resource.size > type_limit:
            # Evict same-type resources first
            self._evict_by_type(resource_type, resource.size)
        
        # Make space if needed
        while self.current_size_bytes + resource.size > self.max_size_bytes:
            self._evict_one()
        
        # Store resource
        self.resources[url] = resource
        self.lru.put(url, 1)  # Value doesn't matter for our use case
        self.current_size_bytes += resource.size
        self.type_current_sizes[resource_type] += resource.size
        
        return True
    
    def _evict_one(self) -> None:
        """Evict least recently used resource"""
        # In real implementation, would extract LRU key from LRU cache
        # For simplicity: find oldest by last_accessed
        oldest_url = None
        oldest_time = float('inf')
        
        for url, resource in self.resources.items():
            if resource.last_accessed < oldest_time:
                oldest_time = resource.last_accessed
                oldest_url = url
        
        if oldest_url:
            self._remove_resource(oldest_url)
            self.metrics.evictions += 1
    
    def _evict_by_type(self, resource_type: ResourceType, needed_space: int):
        """Evict resources of specific type to make space"""
        freed = 0
        to_remove = []
        
        # Find LRU resources of this type
        candidates = [
            (url, r) for url, r in self.resources.items()
            if r.resource_type == resource_type
        ]
        candidates.sort(key=lambda x: x[1].last_accessed)
        
        for url, resource in candidates:
            if freed >= needed_space:
                break
            to_remove.append(url)
            freed += resource.size
        
        for url in to_remove:
            self._remove_resource(url)
            self.metrics.evictions += 1
    
    def _remove_resource(self, url: str):
        """Remove resource and update accounting"""
        if url in self.resources:
            resource = self.resources[url]
            self.current_size_bytes -= resource.size
            self.type_current_sizes[resource.resource_type] -= resource.size
            del self.resources[url]
    
    def get_metrics(self) -> CacheMetrics:
        """Get current cache performance metrics"""
        return self.metrics
    
    def get_stats(self) -> dict:
        """Get detailed cache statistics"""
        return {
            "total_resources": len(self.resources),
            "size_bytes": self.current_size_bytes,
            "size_mb": self.current_size_bytes / (1024 * 1024),
            "hit_ratio": self.metrics.hit_ratio,
            "hits": self.metrics.hits,
            "misses": self.metrics.misses,
            "evictions": self.metrics.evictions,
            "resources_by_type": {
                t.value: sum(1 for r in self.resources.values() if r.resource_type == t)
                for t in ResourceType
            },
            "size_by_type_mb": {
                t.value: self.type_current_sizes[t] / (1024 * 1024)
                for t in ResourceType
            }
        }

# Usage example:
cache = BrowserResourceCache(max_size_mb=50)

# Cache an image
image_data = b"..." # Image bytes
cache.put_resource(
    "https://example.com/logo.png",
    image_data,
    "image/png",
    ResourceType.IMAGE,
    max_age=86400  # Cache for 24 hours
)

# Later retrieval
cached_image = cache.get_resource("https://example.com/logo.png")
if cached_image:
    print("Cache hit! Saved network request")
else:
    print("Cache miss - need to fetch from network")

# Monitor performance
stats = cache.get_stats()
print(f"Hit ratio: {stats['hit_ratio']:.2%}")
print(f"Cache size: {stats['size_mb']:.1f} MB")
```

**Production Improvements:**

1. **Size-aware eviction** - Tracks bytes, not just item count
2. **Resource type limits** - Prevents images from crowding out scripts
3. **HTTP semantics** - Respects cache-control headers
4. **Comprehensive metrics** - Hit ratio, bandwidth saved, eviction rate
5. **Graceful degradation** - Rejects oversized resources instead of thrashing

---

## Part 3: The Scale Breaks - When LRU Meets Reality

### Scale Break #1: Thread Safety

```python
# Our LRU cache is not thread-safe!
# What happens with concurrent access?

import threading

cache = LRUCache(capacity=100)

def worker(thread_id):
    for i in range(1000):
        cache.put(f"key_{thread_id}_{i}", i)
        cache.get(f"key_{thread_id}_{i}")

# Create 10 threads
threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
for t in threads: t.start()
for t in threads: t.join()

# Result: Corrupted linked list! Segfaults! Lost data!
```

**The Problem:** Doubly-linked list manipulation is not atomic. Multiple threads can corrupt pointers.

**Production Solution:**

```python
import threading

class ThreadSafeLRUCache(LRUCache):
    """Thread-safe LRU with locking"""
    
    def __init__(self, capacity: int):
        super().__init__(capacity)
        self._lock = threading.Lock()
    
    def get(self, key: int) -> int:
        with self._lock:
            return super().get(key)
    
    def put(self, key: int, value: int) -> None:
        with self._lock:
            super().put(key, value)

# Alternative: Lock-free designs (more complex)
# - Per-segment locks (like Java's ConcurrentHashMap)
# - Read-Copy-Update (RCU) for read-heavy workloads
# - Lock-free linked lists (using compare-and-swap)
```

---

### Scale Break #2: Memory Accounting Failures

```python
# Capacity of 1000 items sounds reasonable...
cache = LRUCache(capacity=1000)

# Until each item is 1MB
for i in range(1000):
    cache.put(i, b"x" * 1024 * 1024)  # 1MB each

# Result: 1GB of memory! Process killed by OOM!
```

**The Problem:** Count-based limits ignore actual memory usage.

**Production Solution:** Track bytes, not items (like our BrowserResourceCache above).

---

### Scale Break #3: No Monitoring or Observability

```python
# How do you debug poor cache performance?
# How do you know if cache is helping or hurting?

cache = LRUCache(capacity=1000)
# ... cache is used for hours ...

# Questions you can't answer:
# - What's the hit ratio?
# - Which keys are hot?
# - Is capacity too small or too large?
# - Are evictions happening frequently?
```

**Production Solution:** Comprehensive metrics and monitoring.

```python
class ObservableLRUCache(ThreadSafeLRUCache):
    """LRU cache with full observability"""
    
    def __init__(self, capacity: int):
        super().__init__(capacity)
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_get_time_ms": 0.0,
            "total_put_time_ms": 0.0,
        }
        self.hot_keys = {}  # key -> access_count
    
    def get(self, key: int) -> int:
        start = time.time()
        result = super().get(key)
        elapsed = (time.time() - start) * 1000
        
        with self._lock:
            self.metrics["total_get_time_ms"] += elapsed
            if result != -1:
                self.metrics["hits"] += 1
                self.hot_keys[key] = self.hot_keys.get(key, 0) + 1
            else:
                self.metrics["misses"] += 1
        
        return result
    
    def put(self, key: int, value: int) -> None:
        start = time.time()
        
        # Check if this will cause eviction
        will_evict = len(self.cache) >= self.capacity and key not in self.cache
        
        super().put(key, value)
        elapsed = (time.time() - start) * 1000
        
        with self._lock:
            self.metrics["total_put_time_ms"] += elapsed
            if will_evict:
                self.metrics["evictions"] += 1
    
    def get_performance_stats(self) -> dict:
        """Export metrics for monitoring dashboards"""
        total_ops = self.metrics["hits"] + self.metrics["misses"]
        hit_ratio = self.metrics["hits"] / total_ops if total_ops > 0 else 0
        
        avg_get_time = (self.metrics["total_get_time_ms"] / self.metrics["hits"] 
                       if self.metrics["hits"] > 0 else 0)
        
        # Find hottest keys
        top_keys = sorted(self.hot_keys.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "hit_ratio": hit_ratio,
            "total_hits": self.metrics["hits"],
            "total_misses": self.metrics["misses"],
            "total_evictions": self.metrics["evictions"],
            "avg_get_latency_ms": avg_get_time,
            "current_size": len(self.cache),
            "capacity": self.capacity,
            "utilization": len(self.cache) / self.capacity,
            "hottest_keys": top_keys
        }

# In production: Export to Prometheus, DataDog, CloudWatch, etc.
```

---

## Part 4: Real-World LRU Variants

### Variant 1: Redis - Approximate LRU with Sampling

```python
class RedisStyleApproximateLRU:
    """
    Redis doesn't use exact LRU - it's too expensive.
    Instead: sample N keys, evict the oldest from sample.
    
    Result: 90% of LRU benefit, 10% of cost.
    """
    
    def __init__(self, max_memory_bytes: int, sample_size: int = 5):
        self.max_memory = max_memory_bytes
        self.current_memory = 0
        self.data = {}  # key -> (value, lru_timestamp)
        self.sample_size = sample_size
        
        # Redis optimization: 24-bit LRU clock (saves memory)
        self.lru_clock = 0
    
    def get(self, key):
        if key not in self.data:
            return None
        
        value, _ = self.data[key]
        
        # Update LRU timestamp (but not always - another optimization!)
        # Redis uses probabilistic updates to reduce overhead
        import random
        if random.random() < 0.1:  # Update 10% of the time
            self.data[key] = (value, self._get_lru_clock())
        
        return value
    
    def set(self, key, value):
        value_size = self._estimate_size(value)
        
        # Evict using approximate LRU if needed
        while self.current_memory + value_size > self.max_memory:
            self._evict_approximate_lru()
        
        # Store with current timestamp
        self.data[key] = (value, self._get_lru_clock())
        self.current_memory += value_size
    
    def _evict_approximate_lru(self):
        """Redis's key insight: Don't check ALL keys, just sample N"""
        import random
        
        if len(self.data) == 0:
            return
        
        sample_size = min(self.sample_size, len(self.data))
        samples = random.sample(list(self.data.items()), sample_size)
        
        # Find oldest in sample (not globally oldest!)
        oldest_key, (oldest_value, oldest_lru) = min(
            samples, key=lambda x: x[1][1]
        )
        
        # Evict it
        del self.data[oldest_key]
        self.current_memory -= self._estimate_size(oldest_value)
    
    def _get_lru_clock(self) -> int:
        """24-bit clock wraps every ~194 days"""
        self.lru_clock = (self.lru_clock + 1) & 0xFFFFFF
        return self.lru_clock
    
    def _estimate_size(self, value) -> int:
        # Simplified - real Redis uses precise accounting
        import sys
        return sys.getsizeof(value)

# Why approximate?
# Exact LRU: O(n) to find global LRU on eviction
# Approximate: O(1) with sampling - good enough!
```

---

### Variant 2: Operating System - Clock Algorithm (Second Chance)

```python
class OSPageCache:
    """
    OS can't track exact LRU for every memory access - too expensive.
    Solution: Clock algorithm using hardware reference bits.
    """
    
    def __init__(self, num_frames: int = 1024):
        self.frames = [None] * num_frames
        self.reference_bits = [False] * num_frames  # Set by hardware
        self.clock_hand = 0
        
        self.page_table = {}  # page_id -> frame_index
        self.page_faults = 0
        self.page_hits = 0
    
    def access_page(self, page_id: int):
        """Simulate page access"""
        if page_id in self.page_table:
            # Page hit
            frame_idx = self.page_table[page_id]
            self.reference_bits[frame_idx] = True  # Hardware sets this
            self.page_hits += 1
            return f"Hit: Page {page_id} in frame {frame_idx}"
        
        # Page fault - need to load page
        self.page_faults += 1
        frame_idx = self._find_victim_frame()
        
        # Evict old page if frame was occupied
        if self.frames[frame_idx] is not None:
            old_page = self.frames[frame_idx]
            del self.page_table[old_page]
        
        # Load new page
        self.frames[frame_idx] = page_id
        self.page_table[page_id] = frame_idx
        self.reference_bits[frame_idx] = True
        
        return f"Fault: Loaded page {page_id} to frame {frame_idx}"
    
    def _find_victim_frame(self) -> int:
        """Clock algorithm: find unreferenced page"""
        while True:
            if not self.reference_bits[self.clock_hand]:
                # Found victim - hasn't been referenced recently
                victim = self.clock_hand
                self.clock_hand = (self.clock_hand + 1) % len(self.frames)
                return victim
            else:
                # Give second chance - clear bit and keep looking
                self.reference_bits[self.clock_hand] = False
                self.clock_hand = (self.clock_hand + 1) % len(self.frames)

# Why Clock instead of LRU?
# - Hardware only provides reference bit (cheap)
# - Full LRU would require timestamp on EVERY memory access (impossible)
# - Clock gets 80-90% of LRU performance with hardware support
```

---

### Variant 3: MySQL InnoDB - Segmented LRU

```python
class SegmentedLRU:
    """
    InnoDB's trick: Split cache into "young" (5/8) and "old" (3/8) segments.
    
    Why? Prevents full table scans from evicting hot data.
    """
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        
        # 5/8 young (recently added), 3/8 old (frequently accessed)
        self.young_size = int(capacity * 5 / 8)
        self.old_size = capacity - self.young_size
        
        self.young_list = LRUCache(self.young_size)
        self.old_list = LRUCache(self.old_size)
        
        # Track access patterns
        self.young_access_threshold = 100  # ms - "recent" means < 100ms
        self.access_times = {}  # key -> first_access_time
    
    def get(self, key: int) -> int:
        # Try old list first (hot data)
        value = self.old_list.get(key)
        if value != -1:
            return value
        
        # Check young list
        value = self.young_list.get(key)
        if value != -1:
            # Check if accessed multiple times quickly (hot)
            if key in self.access_times:
                time_since_first = (time.time() - self.access_times[key]) * 1000
                if time_since_first < self.young_access_threshold:
                    # Promote to old list (it's hot!)
                    self.old_list.put(key, value)
                    # Keep in young too for now (InnoDB removes after promotion)
            else:
                self.access_times[key] = time.time()
            
            return value
        
        return -1
    
    def put(self, key: int, value: int):
        # All new pages start in young list
        self.young_list.put(key, value)
        self.access_times[key] = time.time()

# Result: Sequential scans fill young list but don't evict hot data from old list!
```

---

## Part 5: Monitoring and Observability in Production

### Real-World Metrics That Matter

```python
class ProductionLRUCache:
    """
    Cache with comprehensive monitoring for production debugging.
    """
    
    def __init__(self, capacity: int, name: str = "cache"):
        self.cache = ObservableLRUCache(capacity)
        self.name = name
        
        # Time-series metrics (last 60 seconds, 1-second buckets)
        self.metrics_history = {
            "hit_ratio": [0.0] * 60,
            "eviction_rate": [0] * 60,
            "avg_latency_ms": [0.0] * 60
        }
        self.current_bucket = 0
        self.last_metrics = {"hits": 0, "misses": 0, "evictions": 0}
    
    def get(self, key: int) -> int:
        return self.cache.get(key)
    
    def put(self, key: int, value: int):
        self.cache.put(key, value)
    
    def collect_metrics(self):
        """Called every second by monitoring system"""
        current = self.cache.get_performance_stats()
        
        # Calculate deltas
        new_hits = current["total_hits"] - self.last_metrics["hits"]
        new_misses = current["total_misses"] - self.last_metrics["misses"]
        new_evictions = current["total_evictions"] - self.last_metrics["evictions"]
        
        # Update time series
        bucket = self.current_bucket % 60
        
        total = new_hits + new_misses
        self.metrics_history["hit_ratio"][bucket] = (
            new_hits / total if total > 0 else 0
        )
        self.metrics_history["eviction_rate"][bucket] = new_evictions
        self.metrics_history["avg_latency_ms"][bucket] = current["avg_get_latency_ms"]
        
        self.last_metrics = {
            "hits": current["total_hits"],
            "misses": current["total_misses"],
            "evictions": current["total_evictions"]
        }
        self.current_bucket += 1
        
        # Check for alerts
        self._check_alerts(current)
    
    def _check_alerts(self, stats: dict):
        """Alert on problematic patterns"""
        hit_ratio = stats["hit_ratio"]
        utilization = stats["utilization"]
        
        # Alert: Low hit ratio
        if hit_ratio < 0.5:
            print(f"⚠️  {self.name}: Low hit ratio {hit_ratio:.1%}")
            print(f"   Suggestion: Increase cache size or check access patterns")
        
        # Alert: High eviction rate
        recent_evictions = sum(self.metrics_history["eviction_rate"][-10:])
        if recent_evictions > 100:
            print(f"⚠️  {self.name}: High eviction rate ({recent_evictions}/10s)")
            print(f"   Suggestion: Cache thrashing - increase capacity")
        
        # Alert: Low utilization
        if utilization < 0.3:
            print(f"⚠️  {self.name}: Low utilization {utilization:.1%}")
            print(f"   Suggestion: Cache oversized - reduce capacity to save memory")
        
        # Alert: High latency
        avg_latency = stats["avg_get_latency_ms"]
        if avg_latency > 1.0:
            print(f"⚠️  {self.name}: High latency {avg_latency:.2f}ms")
            print(f"   Suggestion: Lock contention or GC pressure")
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        stats = self.cache.get_performance_stats()
        
        return f"""
# HELP cache_hit_ratio Cache hit ratio (0-1)
# TYPE cache_hit_ratio gauge
cache_hit_ratio{{name="{self.name}"}} {stats["hit_ratio"]:.4f}

# HELP cache_size_current Current number of cached items
# TYPE cache_size_current gauge
cache_size_current{{name="{self.name}"}} {stats["current_size"]}

# HELP cache_evictions_total Total number of evictions
# TYPE cache_evictions_total counter
cache_evictions_total{{name="{self.name}"}} {stats["total_evictions"]}

# HELP cache_latency_seconds Average get latency
# TYPE cache_latency_seconds gauge
cache_latency_seconds{{name="{self.name}"}} {stats["avg_get_latency_ms"] / 1000:.6f}
"""

# Usage in production:
cache = ProductionLRUCache(capacity=10000, name="user_sessions")

# Monitoring loop (run in separate thread)
import threading
def monitoring_loop():
    while True:
        time.sleep(1)
        cache.collect_metrics()
        
        # Every 15 seconds, export to monitoring system
        if cache.current_bucket % 15 == 0:
            metrics = cache.export_prometheus_metrics()
            # POST to Prometheus pushgateway or scrape endpoint
            # send_to_monitoring_system(metrics)

monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
monitor_thread.start()
```

---

## When Linear LRU Breaks: The Limits of Recency

LRU assumes **recent access predicts future access**. But this fails in several real-world patterns:

### **Problem 1: Sequential Scanning (The Database Killer)**

```python
# Example: Full table scan on 1M row table with 10K row cache
cache = LRUCache(capacity=10000)

for i in range(1000000):  # Sequential scan
    cache.put(f"row_{i}", f"data_{i}")
    # After first 10K rows, cache contains ONLY the last 10K rows
    # First rows were evicted even though we might need them again

# Result: 0% hit ratio! Cache is useless!
```

**Why it breaks:** LRU evicts the *oldest* item, but in scans, the oldest item is the next one you'll need.

**Better alternative:** **MRU eviction** or **no caching** for sequential scans.

---

### **Problem 2: Looping Access Patterns**

```python
# Access pattern: A, B, C, D, A, B, C, D, ...
# Cache size: 3

cache = LRUCache(capacity=3)

sequence = ['A', 'B', 'C', 'D']
for _ in range(10):
    for item in sequence:
        result = cache.get(item)  # Always misses!
        if result == -1:
            cache.put(item, item)

# With cache size N and loop size N+1: 0% hit ratio
```

**Why it breaks:** Working set (4 items) exceeds cache size (3 items), and LRU always evicts the next-needed item.

**Better alternative:** **LFU** (Least Frequently Used) or increase cache size.

---

### **Problem 3: One-Time Bulk Loads**

```python
# Import 100K user records into system
for i in range(100000):
    user = load_user_from_csv(i)
    cache.put(user.id, user)  # Cache them

# Result: Cache filled with users accessed ONCE
# Evicted hot users (frequently accessed ones) to make room
```

**Why it breaks:** Bulk operations pollute cache with cold data.

**Better alternatives:**
- **Segmented LRU** (like InnoDB) - bulk loads stay in "young" segment
- **LFU** - tracks frequency, not just recency
- **ARC (Adaptive Replacement Cache)** - balances recency and frequency

---

### **Problem 4: Write-Heavy Workloads**

```python
# Write-heavy cache (e.g., session store)
cache = LRUCache(capacity=10000)

# 90% writes, 10% reads
for i in range(100000):
    if random.random() < 0.9:
        cache.put(f"session_{i}", {"data": "..."})
    else:
        cache.get(f"session_{random.randint(0, i)}")

# Problem: Eviction overhead is high
# LRU moves EVERY write to head of list
# O(1) per operation, but constant factor is high
```

**Why it breaks:** LRU has overhead on both reads AND writes (moving nodes).

**Better alternatives:**
- **FIFO** - simpler, no move-to-head on reads
- **Clock** - cheaper to update (just set bit)
- **Random eviction** - surprisingly competitive for some workloads

---

### **When NOT to Use LRU**

| Access Pattern | LRU Performance | Better Alternative |
|----------------|-----------------|-------------------|
| Random access | ✅ Excellent | - |
| Sequential scan | ❌ 0% hit rate | MRU eviction or no cache |
| Looping (working set > cache) | ❌ Thrashing | LFU or larger cache |
| Bulk imports | ❌ Cache pollution | Segmented LRU or admission policy |
| Write-heavy | ⚠️ High overhead | FIFO or Clock |
| Mixed recency + frequency | ⚠️ Suboptimal | ARC or LIRS |

---

## What Comes Next: When One Machine Isn't Enough

Everything we've built runs on a single machine. But real systems span **thousands of servers**:

```python
# Imagine this scenario:
# - 10,000 web servers
# - Each has local LRU cache
# - User makes request to server A, then server B

# Server A's cache:
cache_a.put("user_123_profile", profile_data)

# Server B has NO idea:
cache_b.get("user_123_profile")  # Cache miss! Fetch from DB again

# Problems:
# 1. Cache inconsistency across servers
# 2. Wasted memory (same data cached 10,000 times)
# 3. Cache invalidation nightmare (update on server A, stale on servers B-J)
# 4. "Thundering herd" on cache miss (10,000 servers hit DB simultaneously)
```

**The distributed caching challenge:**

```
Your infrastructure:
- 10,000 web servers (each with 10GB local cache)
- 100 cache servers (Redis cluster with 1TB total cache)
- 50 database servers (PostgreSQL with 500GB RAM)

Questions Episode 6 answers:
1. How do you shard cache across 100 servers? (Consistent hashing)
2. How do you prevent thundering herd? (Probabilistic early expiration)
3. How do you invalidate cache across 10,000 servers? (Pub/sub, CRDT)
4. How do you balance hot keys? (Replica reads, local cache)
5. What about multi-datacenter consistency? (Eventual consistency, vector clocks)
```

**In Episode 6: "Caching at Scale,"** we'll discover:

1. **Consistent hashing** - LeetCode pattern applied to distributed systems
2. **Multi-tier caching** - L1 (local) + L2 (Redis) + L3 (Database)
3. **Thundering herd mitigation** - Request coalescing and probabilistic early refresh
4. **Cache invalidation** - The hardest problem in computer science
5. **Observability at scale** - Monitoring 10,000 caches as one system

The algorithm stays the same. The engineering explodes.

---

**Next Episode: From Single-Machine LRU to Distributed Caching at 10,000 Servers**

The complete code for this implementation is available at [GitHub Repository Link]. Caching is never just about the algorithm—it's about understanding your workload.
