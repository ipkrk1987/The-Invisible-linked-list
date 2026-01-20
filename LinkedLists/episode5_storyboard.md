# Episode 5 Storyboard: The Cache That Forgets
## How LRU Cache Powers Your Browser, Database, and OS

**Series**: From LeetCode to Production  
**Season**: 1 - The Invisible Linked List  
**Episode**: S1E05  
**Duration**: 25 minutes  
**Release Target**: [TBD]

---

## Executive Summary

This episode transforms LeetCode #146 (LRU Cache) from an interview problem into production-grade browser caches, database buffers, and OS page replacement algorithms. We explore the theory of caching (locality, eviction policies, coherence), implement a full browser resource cache with size-aware eviction and HTTP semantics, then examine how real systems like Redis, MySQL InnoDB, and operating systems adapt the basic LRU pattern for their specific workloads.

---

## 🎯 Presenter's Intent

**Core message**: "LRU Cache isn't just an interview problem—it's the algorithm running in your browser right now, in your database's buffer pool, and in your operating system's page table. The LeetCode solution is 50 lines. Production systems add thread safety, memory accounting, and observability. Let's see what separates a whiteboard solution from Chrome's real cache."

**Audience**: Senior engineers who will ask:
- "Why not just use a hash map with timestamps?" → Addressed in Act 2
- "How does Redis handle LRU at scale?" → Act 5
- "When is LRU the wrong choice?" → Act 6
- "How big should my cache be?" → Throughout + FAQ
- "What about cache invalidation?" → Act 1 + Episode 6 teaser

**Duration**: 25 minutes (can be split into two 12-13 min sessions)

---

## Act Structure

### Act 1: The Caching Imperative (Slides 1-6) [5 min]
- **Hook**: The memory hierarchy problem (L1 cache to network: 100,000x difference)
- **Theory**: Principle of locality (temporal, spatial, semantic)
- **Framework**: Eviction policies comparison (LRU, LFU, FIFO, ARC, CLOCK)
- **Challenge**: Cache coherence problem

### Act 2: The LeetCode Foundation (Slides 7-11) [4 min]
- **Classic Solution**: Hash map + doubly-linked list for O(1) operations
- **Visual**: Head/tail sentinel nodes, move-to-front mechanics
- **Code Walkthrough**: Complete LRUCache implementation
- **What's Missing**: Thread safety, size accounting, monitoring

### Act 3: Production Browser Cache (Slides 12-18) [6 min]
- **Requirements**: Multi-tier (RAM/SSD/HTTP), resource prioritization
- **Architecture**: Size-aware eviction, type limits, HTTP cache semantics
- **Implementation**: BrowserResourceCache with metrics tracking
- **Memory Pressure**: Proactive eviction under system pressure

### Act 4: Scale Breaks (Slides 19-23) [4 min]
- **Break #1**: Thread safety (corrupted linked lists)
- **Break #2**: Memory accounting failures (OOM from large values)
- **Break #3**: No observability (blind cache debugging)
- **Solutions**: Locking strategies, byte tracking, comprehensive metrics

### Act 5: Real-World Variants (Slides 24-28) [4 min]
- **Redis**: Approximate LRU with sampling (90% benefit, 10% cost)
- **OS CLOCK**: Second-chance algorithm with hardware reference bits
- **MySQL InnoDB**: Segmented LRU (young/old lists for scan resistance)
- **Comparison**: When each variant wins

### Act 6: When LRU Breaks (Slides 29-31) [2 min]
- **Sequential Scans**: 0% hit rate problem
- **Looping Patterns**: Working set thrashing
- **Bulk Loads**: Cache pollution with cold data
- **Decision Matrix**: When NOT to use LRU

### Act 7: Season Transition (Slides 32-33) [1 min]
- **Teaser**: Single machine limits (256GB max, 100K QPS)
- **Preview**: Episode 6 - Distributed caching at 10,000 servers
- **Key Insight**: Same algorithm, exponentially harder engineering

---

## Detailed Slide Breakdown

### Slide 1: Title Card
**Visual**: Browser cache icon with LRU eviction arrows, memory hierarchy pyramid
**Text**: 
- "Episode 5: The Cache That Forgets"
- "How LRU Cache Powers Your Browser, Database, and OS"
- "From LeetCode #146 to Production Systems"
**Duration**: 15 seconds

---

### Slide 2: The Memory Hierarchy Problem
**Visual**: Animated pyramid showing access latencies
```
L1 Cache:    32-64 KB      ~1 ns access
L2 Cache:    256-512 KB    ~3 ns access
L3 Cache:    8-32 MB       ~12 ns access
RAM:         8-64 GB       ~100 ns access    (100x slower!)
SSD:         256GB-4TB     ~100 µs access    (1000x slower!)
HDD:         1-10 TB       ~5 ms access      (50x slower!)
Network:     ∞             ~50-500 ms        (100,000x slower!)
```
**Narration**: "The gap between levels is exponential. A cache miss to disk costs 50,000 times more than a hit in RAM. This is why caching matters."
**Animation**: Numbers highlight with increasing intensity showing the exponential gaps
**Duration**: 45 seconds

---

### Slide 3: The Principle of Locality
**Visual**: Three panels showing access patterns
**Content**:
1. **Temporal Locality**: "If I accessed X recently, I'll access it again soon"
   - Example: Same profile picture loaded 100 times scrolling Instagram
2. **Spatial Locality**: "If I accessed X, I'll access nearby data soon"
   - Example: Array sequential access, adjacent image tiles
3. **Semantic Locality**: "Related items accessed together"
   - Example: User profile + posts + followers
**Animation**: Icons representing each type with access pattern arrows
**Duration**: 50 seconds

---

### Slide 4: Eviction Policy Comparison
**Visual**: Animated comparison table with decision tree
| Policy | Strategy | Best For | Worst For |
|--------|----------|----------|----------|
| **LRU** | Evict oldest access | Temporal locality | Sequential scans |
| **LFU** | Evict lowest count | Hot items | Stale popular items |
| **FIFO** | Evict oldest insert | Simple hardware | Ignores access |
| **ARC** | Recency + frequency | Mixed workloads | Complex |
| **CLOCK** | Second chance bit | OS pages | Not optimal |
**Narration**: "LRU wins because it's simple, exploits temporal locality, and performs well on average. Most production systems use LRU or LRU variants."
**Duration**: 60 seconds

---

### Slide 5: The Cache Coherence Problem
**Visual**: Two servers with stale/fresh data conflict
**Scenario**:
- Server A caches `user:123 = {name: "Alice"}`
- User updates name to "Alicia"
- Server B still serves stale "Alice"
**Solutions Grid**:
1. TTL (Time To Live) - eventual consistency
2. Cache invalidation - explicit messages
3. Write-through - slow writes
4. Write-behind - risk of data loss
**Quote**: "There are only two hard things in Computer Science: cache invalidation and naming things." —Phil Karlton
**Duration**: 55 seconds

---

### Slide 6: Theory Summary
**Visual**: Mind map of caching concepts
**Key Takeaways**:
- Memory hierarchy creates 100,000x latency gaps
- Locality principles make caching effective
- LRU is the default choice for most workloads
- Coherence is the hardest problem
**Transition**: "Now let's implement it."
**Duration**: 30 seconds

---

### Slide 7: The Classic O(1) LRU Solution
**Visual**: Architecture diagram showing hash map + doubly-linked list
```
Hash Map: key → DListNode
          ↓
Doubly Linked List: head ↔ [MRU] ↔ [key2] ↔ [key3] ↔ [LRU] ↔ tail
```
**Narration**: "The trick: hash map gives O(1) lookup, doubly-linked list gives O(1) move-to-front and eviction."
**Animation**: Show get/put operations with pointer movements
**Duration**: 45 seconds

---

### Slide 8: DListNode and Sentinel Pattern
**Visual**: Code with node structure highlighting
```python
class DListNode:
    """Node in doubly-linked list for O(1) removal"""
    def __init__(self, key=0, value=0):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None
```
**Key Insight**: Sentinel nodes (dummy head/tail) eliminate edge cases
**Animation**: Show empty list with just head↔tail, then adding first node
**Duration**: 40 seconds

---

### Slide 9: Core LRU Operations
**Visual**: Animated code walkthrough
```python
def _add_node(self, node):
    """Add node right after head (most recent position)"""
    node.prev = self.head
    node.next = self.head.next
    self.head.next.prev = node
    self.head.next = node

def _remove_node(self, node):
    """Remove node from its current position"""
    prev_node = node.prev
    next_node = node.next
    prev_node.next = next_node
    next_node.prev = prev_node
```
**Animation**: Step-by-step pointer manipulation with visual highlighting
**Duration**: 50 seconds

---

### Slide 10: Get and Put Operations
**Visual**: Split screen - code on left, visual on right
**Get Operation**:
```python
def get(self, key: int) -> int:
    if key not in self.cache:
        return -1
    node = self.cache[key]
    self._move_to_head(node)  # Critical: update access order
    return node.value
```
**Animation**: Show key lookup, node movement to head
**Duration**: 45 seconds

---

### Slide 11: Put with Eviction
**Visual**: Animated eviction scenario
```python
def put(self, key: int, value: int) -> None:
    if key in self.cache:
        node = self.cache[key]
        node.value = value
        self._move_to_head(node)
    else:
        if len(self.cache) >= self.capacity:
            lru = self._pop_tail()  # Evict LRU
            del self.cache[lru.key]
        new_node = DListNode(key, value)
        self.cache[key] = new_node
        self._add_node(new_node)
```
**Animation**: Show capacity check, tail eviction, new node insertion
**Takeaway**: "This is pure data structures - absolutely correct for interviews. But production needs more."
**Duration**: 55 seconds

---

### Slide 12: Browser Cache Requirements
**Visual**: Tiered architecture diagram
**Multi-Tier Caching**:
1. **Memory cache** (~100ns) - 50-200MB, decoded images, parsed JS
2. **Disk cache** (~100µs) - 10GB+, raw files, persistent
3. **HTTP cache** - Headers, ETags, validation
**Resource Prioritization**:
- Scripts/CSS: 50% (frequently reused)
- Images: 30% (largest bytes)
- Fonts: 10% (rarely change)
- API responses: 10% (short TTL)
**Duration**: 50 seconds

---

### Slide 13: BrowserResourceCache Class
**Visual**: Code structure diagram
```python
class BrowserResourceCache:
    def __init__(self, max_size_mb: int = 100):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size_bytes = 0
        
        self.lru = LRUCache(capacity=10000)
        self.resources: Dict[str, Resource] = {}
        self.metrics = CacheMetrics()
        
        # Resource type limits
        self.type_limits = {
            ResourceType.IMAGE: int(max_size_mb * 0.5 * 1024 * 1024),
            ResourceType.SCRIPT: int(max_size_mb * 0.2 * 1024 * 1024),
            # ...
        }
```
**Narration**: "Size-based eviction, not just count. Type limits prevent images from crowding out scripts."
**Duration**: 50 seconds

---

### Slide 14: Resource Class with HTTP Semantics
**Visual**: Resource metadata structure
```python
class Resource:
    def __init__(self, url, content, content_type, resource_type):
        self.url = url
        self.content = content
        self.size = len(content)
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0
        
        # HTTP cache headers
        self.cache_control_max_age = 3600
        self.etag = hashlib.md5(content).hexdigest()[:16]
    
    def is_expired(self) -> bool:
        age = time.time() - self.created_at
        return age > self.cache_control_max_age
```
**Animation**: Highlight expiration check flow
**Duration**: 45 seconds

---

### Slide 15: Get Resource with Validation
**Visual**: Flow diagram of get operation
```python
def get_resource(self, url: str) -> Optional[bytes]:
    if url not in self.resources:
        self.metrics.misses += 1
        return None
    
    resource = self.resources[url]
    
    if resource.is_expired():
        self._remove_resource(url)
        self.metrics.misses += 1
        return None
    
    # Cache hit
    self.lru.get(url)
    resource.touch()
    self.metrics.hits += 1
    self.metrics.total_bytes_served += resource.size
    
    return resource.content
```
**Animation**: Decision tree showing hit/miss/expired paths
**Duration**: 50 seconds

---

### Slide 16: Put Resource with Type Limits
**Visual**: Capacity management visualization
```python
def put_resource(self, url, content, content_type, resource_type, max_age=3600):
    resource = Resource(url, content, content_type, resource_type)
    
    # Sanity check: don't cache > 10% of total
    if resource.size > self.max_size_bytes * 0.1:
        return False
    
    # Check type-specific limits
    type_limit = self.type_limits.get(resource_type, self.max_size_bytes)
    if self.type_current_sizes[resource_type] + resource.size > type_limit:
        self._evict_by_type(resource_type, resource.size)
    
    # Make space if needed
    while self.current_size_bytes + resource.size > self.max_size_bytes:
        self._evict_one()
    
    # Store
    self.resources[url] = resource
    # ...
```
**Animation**: Show type bucket filling, eviction triggered
**Duration**: 55 seconds

---

### Slide 17: Memory Pressure Handling
**Visual**: Pressure levels diagram
**Pressure Levels**:
1. **Normal**: Standard LRU eviction
2. **Warning (80%)**: Evict low-value items first (images before scripts)
3. **Critical (95%)**: Aggressive eviction, disable caching
4. **Emergency**: Clear all caches immediately
**Narration**: "Browsers must react to memory pressure before the OS kills them."
**Duration**: 40 seconds

---

### Slide 18: Production Improvements Summary
**Visual**: Before/After comparison
| LeetCode | Production |
|----------|------------|
| Count-based capacity | Size-aware eviction (bytes) |
| Single type | Resource type limits |
| No headers | HTTP cache semantics |
| No metrics | Comprehensive observability |
| Silent failure | Graceful degradation |
**Duration**: 35 seconds

---

### Slide 19: Scale Break #1 - Thread Safety
**Visual**: Race condition diagram
```python
# Our LRU is not thread-safe!
cache = LRUCache(capacity=100)

def worker(thread_id):
    for i in range(1000):
        cache.put(f"key_{thread_id}_{i}", i)
        cache.get(f"key_{thread_id}_{i}")

# 10 threads = Corrupted linked list! Segfaults!
```
**Problem**: Doubly-linked list manipulation is not atomic
**Solution**: `ThreadSafeLRUCache` with locks
**Duration**: 45 seconds

---

### Slide 20: Scale Break #2 - Memory Accounting
**Visual**: OOM scenario animation
```python
cache = LRUCache(capacity=1000)  # Sounds reasonable...

for i in range(1000):
    cache.put(i, b"x" * 1024 * 1024)  # 1MB each!

# Result: 1GB memory! OOM!
```
**Problem**: Count-based limits ignore actual memory usage
**Solution**: Track bytes, not items
**Duration**: 40 seconds

---

### Slide 21: Scale Break #3 - No Observability
**Visual**: Dashboard with missing data
**Questions You Can't Answer**:
- What's the hit ratio?
- Which keys are hot?
- Is capacity too small or large?
- Are evictions happening frequently?
**Solution**: `ObservableLRUCache` with comprehensive metrics
**Duration**: 40 seconds

---

### Slide 22: ObservableLRUCache Implementation
**Visual**: Metrics collection code
```python
class ObservableLRUCache(ThreadSafeLRUCache):
    def __init__(self, capacity: int):
        super().__init__(capacity)
        self.metrics = {
            "hits": 0, "misses": 0, "evictions": 0,
            "total_get_time_ms": 0.0, "total_put_time_ms": 0.0
        }
        self.hot_keys = {}
    
    def get_performance_stats(self) -> dict:
        return {
            "hit_ratio": self.metrics["hits"] / total_ops,
            "avg_get_latency_ms": avg_get_time,
            "hottest_keys": top_keys,
            # ...
        }
```
**Narration**: "In production, export to Prometheus, DataDog, CloudWatch."
**Duration**: 50 seconds

---

### Slide 23: Production Alerts
**Visual**: Alert notification mockups
```python
def _check_alerts(self, stats):
    if hit_ratio < 0.5:
        print("⚠️ Low hit ratio - increase cache size")
    
    if recent_evictions > 100:
        print("⚠️ High eviction rate - cache thrashing")
    
    if utilization < 0.3:
        print("⚠️ Low utilization - reduce capacity")
    
    if avg_latency > 1.0:
        print("⚠️ High latency - lock contention")
```
**Duration**: 40 seconds

---

### Slide 24: Redis - Approximate LRU
**Visual**: Sampling diagram
```python
class RedisStyleApproximateLRU:
    def _evict_approximate_lru(self):
        # Don't check ALL keys, just sample N
        sample_size = min(5, len(self.data))
        samples = random.sample(list(self.data.items()), sample_size)
        
        # Find oldest in sample (not globally!)
        oldest_key = min(samples, key=lambda x: x[1][1])[0]
        del self.data[oldest_key]
```
**Key Insight**: "90% of LRU benefit, 10% of cost. Good enough!"
**Duration**: 50 seconds

---

### Slide 25: OS CLOCK Algorithm
**Visual**: Circular buffer with clock hand
```python
class OSPageCache:
    def _find_victim_frame(self) -> int:
        """Clock algorithm: find unreferenced page"""
        while True:
            if not self.reference_bits[self.clock_hand]:
                # Found victim - hasn't been referenced
                victim = self.clock_hand
                self.clock_hand = (self.clock_hand + 1) % len(self.frames)
                return victim
            else:
                # Give second chance
                self.reference_bits[self.clock_hand] = False
                self.clock_hand = (self.clock_hand + 1) % len(self.frames)
```
**Why**: "Hardware only provides reference bit (cheap). Full LRU would need timestamp on EVERY memory access."
**Duration**: 55 seconds

---

### Slide 26: MySQL InnoDB - Segmented LRU
**Visual**: Young/Old list diagram
```python
class SegmentedLRU:
    def __init__(self, capacity):
        # 5/8 young (recently added), 3/8 old (frequently accessed)
        self.young_list = LRUCache(int(capacity * 5 / 8))
        self.old_list = LRUCache(capacity - self.young_size)
```
**Key Insight**: "Prevents full table scans from evicting hot data."
**Animation**: Show sequential scan filling young list while old list preserved
**Duration**: 50 seconds

---

### Slide 27: LRU Variant Comparison
**Visual**: Decision matrix
| Scenario | Standard LRU | Approximate | CLOCK | Segmented |
|----------|-------------|-------------|-------|-----------|
| Random access | ✅ | ✅ | ✅ | ✅ |
| Memory overhead | High | Low | Low | Medium |
| CPU overhead | Medium | Low | Low | Medium |
| Sequential scan | ❌ | ❌ | ⚠️ | ✅ |
**Duration**: 40 seconds

---

### Slide 28: Real System Adoption
**Visual**: Company logos with their LRU variant
- **Redis**: Approximate LRU with sampling
- **Linux**: CLOCK with second chance
- **MySQL**: Segmented LRU
- **PostgreSQL**: CLOCK sweep
- **Chrome**: Segmented by resource type
**Duration**: 35 seconds

---

### Slide 29: When LRU Breaks - Sequential Scan
**Visual**: Animation of 0% hit rate
```python
# Full table scan on 1M rows with 10K row cache
cache = LRUCache(capacity=10000)

for i in range(1000000):
    cache.put(f"row_{i}", f"data_{i}")
    # After first 10K rows: cache has ONLY last 10K
    # First rows evicted even though needed again!

# Result: 0% hit ratio! Cache is useless!
```
**Why**: LRU evicts oldest, but in scans, oldest is next needed
**Duration**: 45 seconds

---

### Slide 30: When LRU Breaks - Looping Pattern
**Visual**: Carousel animation showing thrashing
```python
# Access: A, B, C, D, A, B, C, D, ...
# Cache size: 3

sequence = ['A', 'B', 'C', 'D']
for item in sequence:
    cache.get(item)  # Always misses!

# With N cache and N+1 loop: 0% hit ratio
```
**Why**: Working set exceeds cache, LRU always evicts next-needed item
**Duration**: 40 seconds

---

### Slide 31: LRU Decision Matrix
**Visual**: When to use / not use table
| Access Pattern | LRU Performance | Better Alternative |
|----------------|-----------------|-------------------|
| Random access | ✅ Excellent | - |
| Sequential scan | ❌ 0% hit rate | MRU or no cache |
| Looping (> cache) | ❌ Thrashing | LFU or larger cache |
| Bulk imports | ❌ Pollution | Segmented LRU |
| Write-heavy | ⚠️ High overhead | FIFO or Clock |
**Duration**: 45 seconds

---

### Slide 32: Single Machine Limits
**Visual**: Server capacity diagram
```python
class SingleServerReality:
    max_ram = 256 * (1024**3)  # 256GB ($50k server)
    max_qps = 100_000           # ~100K requests/second
    max_bandwidth = 10 Gbps     # Network limit
    
    # Real-world scale needed:
    # Twitter: 300M users
    # Netflix: 2B hours/month
    # Facebook: 4PB photos
    
    # One server is 1000x too small!
```
**Duration**: 40 seconds

---

### Slide 33: Episode 6 Preview
**Visual**: Distributed cache cluster diagram
**Questions Episode 6 Answers**:
1. How to shard cache across 100 servers? (Consistent hashing)
2. How to prevent thundering herd? (Request coalescing)
3. How to invalidate across 10,000 servers? (Pub/sub)
4. Multi-datacenter consistency? (Vector clocks)
**Tagline**: "The algorithm stays the same. The engineering explodes."
**Duration**: 45 seconds

---

## Animation Requirements

### Animation 1: Memory Hierarchy Pyramid (Slide 2)
**Type**: Progressive reveal with zoom
**Elements**:
- Pyramid layers appear bottom-up
- Access times highlight with color intensity
- 100,000x gap visualized with scale comparison
**Interaction**: Auto-play with pause points

### Animation 2: LRU List Operations (Slides 9-11)
**Type**: Step-through with pointer highlighting
**States**:
1. Initial list: head ↔ A ↔ B ↔ C ↔ tail
2. Get(B): B moves to head position
3. Put(D) when full: C evicted, D added at head
**Interaction**: Click to advance steps

### Animation 3: Cache Type Buckets (Slide 16)
**Type**: Filling containers
**Elements**:
- 5 buckets for resource types
- Fill levels animate as resources added
- Eviction triggers when bucket overflows
**Interaction**: Drag resources to see bucket behavior

### Animation 4: CLOCK Algorithm (Slide 25)
**Type**: Circular sweep animation
**Elements**:
- Clock face with pages as positions
- Reference bits shown as on/off lights
- Clock hand sweeps, clearing bits
**Interaction**: Add pages to see algorithm behavior

---

## Interactive Code Demos

### Demo 1: Basic LRU Operations
```python
# Interactive demo showing get/put with visualization
cache = LRUCache(capacity=3)
cache.put(1, 'A')  # [1]
cache.put(2, 'B')  # [2, 1]
cache.put(3, 'C')  # [3, 2, 1]
cache.get(1)       # [1, 3, 2]  - 1 moved to front
cache.put(4, 'D')  # [4, 1, 3]  - 2 evicted!
```

### Demo 2: Browser Cache Simulation
```python
# Show size-based eviction and type limits
cache = BrowserResourceCache(max_size_mb=10)
cache.put_resource("logo.png", image_bytes, "image/png", ResourceType.IMAGE)
cache.put_resource("app.js", script_bytes, "text/javascript", ResourceType.SCRIPT)
print(cache.get_stats())  # Show type distribution
```

### Demo 3: LRU vs Sequential Scan
```python
# Demonstrate 0% hit rate problem
cache = LRUCache(capacity=100)
hits, misses = 0, 0
for i in range(1000):
    for j in range(200):  # Access 200 items cyclically
        if cache.get(j) != -1:
            hits += 1
        else:
            misses += 1
            cache.put(j, j)
print(f"Hit rate: {hits/(hits+misses):.1%}")  # 0%!
```

---

## Senior Engineer FAQ

### Q1: Why not use LFU (Least Frequently Used)?
**A**: LFU has the "stale popular item" problem. An item accessed 1 million times last week but never again still has the highest frequency. LRU naturally ages out stale items. Hybrid approaches like ARC balance both.

### Q2: How do real browsers handle cache eviction?
**A**: Chrome uses a combination of:
- Segmented storage by resource type
- Soft limits (evict gracefully) vs hard limits (reject)
- Memory pressure callbacks from OS
- LRU within each segment

### Q3: What's the actual overhead of LRU vs simpler policies?
**A**: 
- LRU: ~50ns per operation (hash lookup + pointer update)
- FIFO: ~20ns (just dequeue/enqueue)
- Random: ~10ns (no tracking needed)
For most systems, LRU's better hit rate outweighs the overhead.

### Q4: How does Redis's approximate LRU actually work?
**A**: Redis stores a 24-bit timestamp with each key (saves memory vs full timestamp). On eviction, it samples N random keys (default 5) and evicts the oldest among them. Studies show this achieves ~95% of perfect LRU's performance.

### Q5: When should I use write-through vs write-behind caching?
**A**:
- **Write-through**: When data consistency is critical (financial systems). Slower writes but guaranteed consistency.
- **Write-behind**: When write latency matters more than immediate consistency (social media posts). Faster but risk of data loss on crash.

---

## Technical Accuracy Checklist

- [ ] LRU time complexity: O(1) get and put with hash map + linked list
- [ ] Memory hierarchy numbers from current server hardware specs
- [ ] Redis sampling uses configurable sample size (maxmemory-samples)
- [ ] CLOCK algorithm matches Linux kernel implementation
- [ ] InnoDB's young/old ratio is actually 5/8 and 3/8
- [ ] Chrome's resource type priorities match DevTools Network panel

---

## Production Code Repository Structure

```
episode5-lru-cache/
├── basic/
│   ├── lru_cache.py           # LeetCode solution
│   └── test_lru.py
├── production/
│   ├── browser_cache.py       # BrowserResourceCache
│   ├── thread_safe_cache.py   # ThreadSafeLRUCache
│   ├── observable_cache.py    # With metrics
│   └── test_production.py
├── variants/
│   ├── approximate_lru.py     # Redis-style
│   ├── clock_algorithm.py     # OS-style
│   ├── segmented_lru.py       # InnoDB-style
│   └── test_variants.py
└── benchmarks/
    ├── access_patterns.py     # Random, sequential, looping
    └── performance_comparison.py
```

---

## Presenter Notes

### Key Transitions
- **Theory → Implementation**: "Now let's build it" (Slide 6→7)
- **LeetCode → Production**: "Absolutely correct for interviews, but production needs more" (Slide 11→12)
- **Production → Scale Breaks**: "What happens when this meets reality?" (Slide 18→19)
- **Variants → Limitations**: "Even with these improvements, LRU has limits" (Slide 28→29)

### Emphasis Points
1. **The 100,000x gap** - Make this visceral, it's the entire motivation
2. **Sentinel nodes** - Emphasize how they eliminate edge cases
3. **Size vs count** - This is THE production gotcha
4. **Sampling approximation** - "Good enough" is an engineering principle

### Common Audience Questions to Anticipate
- "How big should my cache be?" → "Measure hit rate, start at 10% of working set"
- "Should I use Redis or in-process cache?" → "Depends on sharing needs and data size"
- "How do I know if my cache is working?" → "Metrics: hit ratio > 90% is good"

---

## 📁 Deliverables

1. **episode5_revealjs.html** — Full Reveal.js presentation
2. **episode5_animations.html** — Standalone interactive animations
3. **episode5_storyboard.md** — This file (presenter notes)
4. **LinkedLists/chapter 5.md** — Source content

---

## 🎬 Suggested Session Split

**Option A: Single 25-minute session**
- Full presentation, standard pace

**Option B: Two 12-13 minute sessions**
- **Session 1** (Acts 1-3): "LRU Fundamentals" — Theory to browser cache
- **Session 2** (Acts 4-7): "Production & Variants" — Scale breaks, Redis, OS, limitations

---

## 🏆 Challenge for the Audience

> "Design a cache that handles the sequential scan problem. How would you detect when LRU is performing poorly and automatically switch to a different eviction policy?"

**Hint**: Track hit rate in a sliding window. If it drops below a threshold, switch to MRU (Most Recently Used) for scan-resistant behavior. This is what PostgreSQL's clock-sweep does!

---

## 🎯 Key Moments to Nail

| Time | Moment | Why It Matters |
|------|--------|----------------|
| 0:30 | "100,000x latency gap" | The entire motivation |
| 3:00 | Eviction policy comparison | Sets up why LRU wins |
| 7:00 | Hash map + linked list trick | The algorithm insight |
| 10:00 | Sentinel nodes simplify code | Elegant engineering |
| 13:00 | "Size not count" revelation | THE production gotcha |
| 17:00 | Thread safety demo | Concurrency is hard |
| 20:00 | Redis approximate LRU | "Good enough" wins |
| 23:00 | Sequential scan 0% hit rate | Know the limits |
| 25:00 | Episode 6 teaser | Build anticipation |

---

## Episode Metadata

**Prerequisites**: 
- Episode 3 (doubly-linked lists)
- Basic hash table understanding

**Key Terms Introduced**:
- Temporal/spatial/semantic locality
- Cache coherence
- LRU, LFU, FIFO, ARC, CLOCK
- Approximate LRU
- Segmented LRU

**Connections to Other Episodes**:
- Episode 3: Doubly-linked list mechanics (LRU uses same pointer manipulation)
- Episode 4: Immutable structures for cache snapshots (cache versioning)
- Episode 6: Distributed caching (sequel - scaling LRU across servers)
- Episode 7: Ring buffers use similar eviction concepts

**Real-World Systems Referenced**:
- Redis, Memcached
- Chrome browser cache
- MySQL InnoDB buffer pool
- Linux page cache
