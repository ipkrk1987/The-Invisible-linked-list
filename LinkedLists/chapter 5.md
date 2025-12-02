Perfect! Let's split this into two tightly-focused episodes. Here's the logical split:

Episode 5: Single-machine LRU - From interview to production caches
Episode 6: Distributed & approximate LRU - Scaling to infrastructure

---

EPISODE 5: The Cache That Forgets - LRU from LeetCode to Production Caches

(0:00 - The Most Common Interview Question)

Narration: "LeetCode #146 - LRU Cache. You've probably solved it. But did you know this exact algorithm runs billions of times per second in your browser, your database, and your operating system?"

```python
# The O(1) solution every engineer should know:
class DListNode:
    def __init__(self, key=0, value=0):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None

class LRUCache:
    """Hash map + doubly linked list = O(1) operations."""
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}  # key -> node
        self.head = DListNode()  # Most recent
        self.tail = DListNode()  # Least recent
        self.head.next = self.tail
        self.tail.prev = self.head
    
    def _add_node(self, node):
        """Add after head (most recent)."""
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node
    
    def _remove_node(self, node):
        """Remove from linked list."""
        node.prev.next = node.next
        node.next.prev = node.prev
    
    def _move_to_head(self, node):
        """Mark as recently used."""
        self._remove_node(node)
        self._add_node(node)
    
    def _pop_tail(self):
        """Remove and return least recently used."""
        lru = self.tail.prev
        self._remove_node(lru)
        return lru
    
    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        
        node = self.cache[key]
        self._move_to_head(node)  # Critical: update recency
        return node.value
    
    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            node = self.cache[key]
            node.value = value
            self._move_to_head(node)
        else:
            if len(self.cache) >= self.capacity:
                # Evict LRU
                lru = self._pop_tail()
                del self.cache[lru.key]
            
            new_node = DListNode(key, value)
            self.cache[key] = new_node
            self._add_node(new_node)

# Visual: head <-> [MRU] <-> [A] <-> [B] <-> [LRU] <-> tail
# get(B): head <-> [B] <-> [MRU] <-> [A] <-> [tail]
# Capacity full? Remove tail.prev
```

(4:00 - Your Browser's Secret: Caching Web Resources)

Narration: "Every time you revisit a website, your browser uses LRU. Images, CSS, JavaScript - cached to avoid re-downloading. Let's build a simplified browser cache:"

```python
class BrowserResourceCache:
    """LRU cache for web resources."""
    
    def __init__(self, max_size_mb=100):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size = 0
        
        # Core LRU for O(1) operations
        self.lru = LRUCache(capacity=10000)  # Tracks keys only
        self.resources = {}  # key -> Resource
        
        # Simple statistics
        self.hits = 0
        self.misses = 0
    
    class Resource:
        def __init__(self, url, content, content_type):
            self.url = url
            self.content = content
            self.content_type = content_type
            self.size = len(content)
            self.last_accessed = time.time()
    
    def get_resource(self, url: str):
        """Get cached resource or None."""
        if url in self.resources:
            resource = self.resources[url]
            # Update LRU position
            self.lru.get(url)  # get() moves to head internally
            resource.last_accessed = time.time()
            self.hits += 1
            return resource.content
        
        self.misses += 1
        return None
    
    def put_resource(self, url: str, content: bytes, content_type: str):
        """Cache a new resource."""
        resource = self.Resource(url, content, content_type)
        
        # Check if we need to make space
        while self.current_size + resource.size > self.max_size_bytes:
            self._evict_one()
        
        # Store
        self.resources[url] = resource
        self.lru.put(url, 1)  # Value doesn't matter
        self.current_size += resource.size
    
    def _evict_one(self):
        """Evict least recently used resource."""
        # Our LRU cache's tail has the LRU key
        # We need to extract it (simplified for demo)
        
        # In real browsers: more complex with multiple cache types
        # For demo: find oldest by access time
        oldest_url = None
        oldest_time = float('inf')
        
        for url, resource in self.resources.items():
            if resource.last_accessed < oldest_time:
                oldest_time = resource.last_accessed
                oldest_url = url
        
        if oldest_url:
            # Remove from cache
            resource = self.resources[oldest_url]
            self.current_size -= resource.size
            del self.resources[oldest_url]
            # Note: Would also remove from LRU cache

# Real browser optimizations:
# 1. Multiple cache types (memory vs disk)
# 2. Cache partitioning (by domain, by resource type)
# 3. HTTP cache headers control eviction
```

(8:00 - The Database Layer: Redis Eviction Policies)

Narration: "Redis, the in-memory database, offers 8 eviction policies. The default? Approximate LRU. Why approximate? Because exact LRU is too expensive at scale."

```python
class RedisStyleLRU:
    """Redis-style LRU with sampling for efficiency."""
    
    def __init__(self, max_memory_bytes):
        self.max_memory = max_memory_bytes
        self.current_memory = 0
        self.data = {}  # key -> (value, lru_timestamp)
        
        # Redis optimization: 24-bit LRU clock (saves memory)
        self.lru_clock = 0
    
    def get(self, key):
        if key not in self.data:
            return None
        
        value, _ = self.data[key]
        
        # Update LRU timestamp (but not always - another optimization!)
        if self._should_update_lru():
            self.data[key] = (value, self._get_lru_clock())
        
        return value
    
    def set(self, key, value):
        """Set key, evicting if needed using approximate LRU."""
        value_size = self._estimate_size(value)
        
        # Check memory limit
        if self.current_memory + value_size > self.max_memory:
            self._evict_using_approximate_lru()
        
        # Store with current LRU timestamp
        self.data[key] = (value, self._get_lru_clock())
        self.current_memory += value_size
    
    def _evict_using_approximate_lru(self):
        """Redis's trick: sample N keys, evict the oldest."""
        sample_size = 5  # Configurable: maxmemory-samples
        
        if len(self.data) < sample_size:
            sample_size = len(self.data)
        
        if sample_size == 0:
            return
        
        # Sample random keys (not all keys!)
        import random
        samples = random.sample(list(self.data.items()), sample_size)
        
        # Find the one with smallest LRU timestamp
        oldest_key, (oldest_value, oldest_lru) = min(
            samples, key=lambda x: x[1][1]
        )
        
        # Evict it
        del self.data[oldest_key]
        self.current_memory -= self._estimate_size(oldest_value)
    
    def _get_lru_clock(self):
        """24-bit LRU clock (wraps every 194 days)."""
        self.lru_clock = (self.lru_clock + 1) & 0xFFFFFF  # 24 bits
        return self.lru_clock
    
    def _should_update_lru(self):
        """Don't update on every access - save CPU."""
        # Redis uses probabilistic updates
        # Update probability decreases as cache grows
        import random
        update_prob = 1.0 / max(1, len(self.data) // 10)
        return random.random() < update_prob

# Redis eviction policies:
# 1. noeviction: Don't evict, return errors
# 2. allkeys-lru: Evict any key by approximate LRU (default)
# 3. volatile-lru: Only evict keys with TTL set
# 4. allkeys-random: Random eviction
# 5. volatile-random: Random from keys with TTL
# 6. volatile-ttl: Evict by shortest TTL remaining
```

(12:00 - The Operating System: Page Cache & Memory Management)

Narration: "Your OS faces the same problem: limited RAM, infinite memory demands. The solution? Virtual memory with page replacement. LRU is optimal but impossible to implement exactly."

```python
class MemoryManager:
    """OS page cache with Clock algorithm (LRU approximation)."""
    
    def __init__(self, total_frames=1024):
        self.total_frames = total_frames
        self.page_table = {}  # virtual page -> (frame, reference_bit)
        self.frames = [None] * total_frames  # What's in each frame
        self.reference_bits = [0] * total_frames  # Recently accessed?
        self.clock_hand = 0  # Clock algorithm pointer
        
        self.page_faults = 0
        self.hits = 0
    
    def access_page(self, page_number: int) -> str:
        """Access a page, handling page faults."""
        if page_number in self.page_table:
            # Page hit - set reference bit
            frame, _ = self.page_table[page_number]
            self.reference_bits[frame] = 1
            self.hits += 1
            return f"Page {page_number} in frame {frame}"
        
        # Page fault - need to load page
        self.page_faults += 1
        
        if None in self.frames:
            # Free frame available
            frame = self.frames.index(None)
        else:
            # Need to evict - use Clock algorithm
            frame = self._find_victim_frame()
            
            # Evict current occupant
            old_page = self.frames[frame]
            if old_page is not None:
                del self.page_table[old_page]
        
        # Load new page
        self.frames[frame] = page_number
        self.page_table[page_number] = (frame, 1)
        self.reference_bits[frame] = 1
        
        return f"Page fault: loaded {page_number} to frame {frame}"
    
    def _find_victim_frame(self):
        """Clock algorithm: find page with reference_bit = 0."""
        while True:
            if self.reference_bits[self.clock_hand] == 0:
                # Found victim
                victim = self.clock_hand
                self.clock_hand = (self.clock_hand + 1) % self.total_frames
                return victim
            else:
                # Give second chance - clear bit and move on
                self.reference_bits[self.clock_hand] = 0
                self.clock_hand = (self.clock_hand + 1) % self.total_frames

# Why not exact LRU for OS?
# 1. Would need to track access time for EVERY memory access
# 2. Hardware support limited (reference bits are cheap)
# 3. Clock algorithm gets 90% of benefit with 10% of cost
```

(16:00 - Modern Variations: Adaptive and Segmented LRU)

Narration: "Production systems don't use vanilla LRU. They adapt. Let's look at two advanced patterns:"

```python
class SegmentedLRUCache:
    """LRU with hot/cold segments (like InnoDB Buffer Pool)."""
    
    def __init__(self, capacity):
        self.capacity = capacity
        
        # MySQL InnoDB trick: 5/8 of cache is "new" (cold) pages
        # 3/8 is "old" (hot) pages
        self.new_segment_size = int(capacity * 5/8)
        self.old_segment_size = capacity - self.new_segment_size
        
        self.new_segment = LRUCache(self.new_segment_size)  # Recently added
        self.old_segment = LRUCache(self.old_segment_size)  # Frequently accessed
        
        # Pages must visit new segment before graduating to old
        self.midpoint_insertion = True
    
    def get(self, key):
        # Try old segment first (hot data)
        value = self.old_segment.get(key)
        if value != -1:
            return value
        
        # Try new segment
        value = self.new_segment.get(key)
        if value != -1:
            # Promote to old segment if accessed again
            # (InnoDB: page accessed in new segment gets moved to old)
            self.old_segment.put(key, value)
            return value
        
        return -1
    
    def put(self, key, value):
        # All new pages go to new segment initially
        self.new_segment.put(key, value)
        
        # If new segment is full, evict from its LRU
        # Evicted pages don't go to old segment (they weren't re-accessed)

class AdaptiveLRUCache:
    """LRU that tunes itself based on access patterns."""
    
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = LRUCache(capacity)
        
        # Track access frequency
        self.access_counts = {}  # key -> count
        
        # Adaptive parameters
        self.promotion_threshold = 3  # Accesses to be "hot"
        self.hot_keys = set()
        
        # Statistics for self-tuning
        self.hit_ratio_history = []
    
    def get(self, key):
        value = self.cache.get(key)
        
        if value != -1:
            # Track frequency
            count = self.access_counts.get(key, 0) + 1
            self.access_counts[key] = count
            
            # Promote to hot set if frequently accessed
            if count >= self.promotion_threshold:
                self.hot_keys.add(key)
        
        return value
    
    def auto_tune(self):
        """Adjust parameters based on recent performance."""
        if len(self.hit_ratio_history) < 10:
            return
        
        recent_hit_ratio = sum(self.hit_ratio_history[-10:]) / 10
        
        if recent_hit_ratio < 0.7:
            # Poor performance - be more aggressive
            self.promotion_threshold = 2
        else:
            # Good performance - be more conservative
            self.promotion_threshold = 4

# Real-world examples:
# 1. MySQL InnoDB: 5/8 new, 3/8 old segments
# 2. Linux Page Cache: active/inactive lists
# 3. Varnish: LRU with grace mode for stale content
```

(20:00 - The Big Picture: LRU at Every Layer)

[Visual: Stack diagram]

Narration: "Let's connect the dots. LRU appears at every layer of computing:"

```
APPLICATION LAYER
  Browser cache (images, CSS, JS)
  CDN edge caches
  
DATA STORE LAYER  
  Redis/Memcached eviction
  Database query cache
  
OPERATING SYSTEM LAYER
  Page cache (file contents)
  Buffer cache (disk blocks)
  TLB (translation lookaside buffer)
  
HARDWARE LAYER
  CPU caches (L1, L2, L3)
  GPU texture cache
  
Common pattern: Limited fast storage, 
                need to evict something,
                recent access predicts future access.
```

(22:00 - Tradeoffs and When Not to Use LRU)

Narration: "LRU isn't always right. Let's see when it fails:"

```python
# Problem 1: Sequential scanning
# If you read a huge file once, LRU fills cache with data you'll never reuse
def sequential_scan_problem(cache):
    """Reading a 1GB file fills cache with useless data."""
    for i in range(1000000):  # 1 million pages
        cache.put(f"page_{i}", "data")
        # After this, cache contains only the END of the file
        # Beginning was evicted even though we might re-read it

# Problem 2: Looping access patterns
# Access pattern: A, B, C, A, B, C... with cache size 2
# LRU always evicts the next item to be accessed!
def looping_access_problem(cache):
    """LRU fails on cyclic access patterns."""
    items = ['A', 'B', 'C']
    for i in range(100):
        item = items[i % 3]
        cache.get(item)  # Always a miss with size 2 cache!

# Better alternatives:
# 1. LFU (Least Frequently Used): Count accesses
# 2. ARC (Adaptive Replacement Cache): Balance recency and frequency
# 3. LIRS (Low Inter-reference Recency Set): For scanning workloads
# 4. Random eviction: Surprisingly good for some databases
```

(24:00 - Recap & Next Episode Teaser)

Narration: "Today we saw LRU from interview to infrastructure. We learned:"

Key Insights:

1. Hash map + doubly linked list = O(1) LRU
2. Browsers use LRU for resource caching
3. Redis approximates LRU with sampling (performance tradeoff)
4. OS uses Clock algorithm (LRU approximation for pages)
5. Production systems adapt (segmented, adaptive LRU)
6. LRU is everywhere but has failure cases

Narration: "But what happens when your cache spans hundreds of servers? When you need consistency across data centers? When memory, SSD, and network caches work together?"

[Visual: Distributed cache cluster, multi-tier architecture]

Narration: "That's distributed caching at scale - where LRU meets consistent hashing, replication, and multi-tier architectures. That's Episode 6."

---

EPISODE 5 COMPLETE 