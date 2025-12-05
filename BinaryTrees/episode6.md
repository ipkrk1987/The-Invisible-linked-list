Episode 2.6 Final: "LSM-Trees - The Write-Optimized Engine"

The Hook: The Clickstream That Broke PostgreSQL

You're building a clickstream analytics system. Every user click generates an event. You need to ingest 1 million events per second, then run analytics on the data.

You start with PostgreSQL. It handles 10K writes/second, then 50K, then at 100K writes/second, the database locks up. Disk I/O is at 100%, CPU is idle, and you're losing millions of events.

The problem isn't PostgreSQL. It's the fundamental physics of B-Trees: every write requires random disk seeks, and even NVMe SSDs max out at ~1 million random IOPs.

This is when engineers at Google, Facebook, and Amazon faced the same problem and invented a different approach. Instead of updating data in place (random I/O), they append to logs (sequential I/O) and merge in the background.

This is LSM-Trees (Log-Structured Merge Trees), the technology behind RocksDB, Cassandra, and ScyllaDB that powers billions of writes per day.

---

LeetCode Core: Merging Sorted Lists

The fundamental operation in LSM-Trees is merging sorted lists. This is exactly LeetCode #23: Merge k Sorted Lists.

```python
def merge_k_sorted(lists):
    """Merge k sorted lists into one sorted list"""
    import heapq
    
    # Min-heap with (value, list_index, element_index)
    heap = []
    for i, lst in enumerate(lists):
        if lst:
            heapq.heappush(heap, (lst[0], i, 0))
    
    result = []
    while heap:
        val, list_idx, elem_idx = heapq.heappop(heap)
        result.append(val)
        
        # Push next element from the same list
        if elem_idx + 1 < len(lists[list_idx]):
            next_elem = lists[list_idx][elem_idx + 1]
            heapq.heappush(heap, (next_elem, list_idx, elem_idx + 1))
    
    return result
```

The connection to LSM-Trees:

· Each "sorted list" is a disk file (SSTable) from Episode 2.1
· The "merge" operation happens during compaction
· Result: One sorted file, ready for efficient binary search

But LSM-Trees add a twist: we merge on disk with files that can be gigabytes in size, using multiway merge instead of in-memory heaps.

---

The Core Insight: Trading Read Cost for Write Speed

B-Tree (Episode 2.5):

```
Write: O(log_B n) random disk seeks
Read:  O(log_B n) random disk seeks
Best for: Read-heavy, update-heavy workloads
```

LSM-Tree:

```
Write: Amortized O(1) sequential append to log
       (plus background compaction cost)
Read:  O(k) seeks across multiple files (k = number of levels)
Best for: Write-heavy, append-only workloads
```

The tradeoff: We accept slower reads (checking multiple files) for lightning-fast writes (sequential append).

---

Toy System: Building a Minimal LSM Engine

Let's build the simplest possible LSM storage engine:

```python
class SimpleLSM:
    """
    Minimal LSM Tree with:
    1. In-memory memtable (hash map - in production: skip list or AVL tree)
    2. On-disk SSTables (sorted files)
    3. Background compaction
    """
    
    def __init__(self, memtable_size_limit=64 * 1024 * 1024):  # 64MB
        self.memtable = {}  # Hash map (in production: sorted structure for efficient flush)
        self.immutable_memtables = []  # Waiting to be flushed
        self.sstables = []  # List of SSTable files (sorted by creation time)
        self.memtable_size_limit = memtable_size_limit
        self.wal = WriteAheadLog("lsm_wal.log")  # From Episode 2.1
        
    def put(self, key, value):
        # 1. Write to WAL first (durability)
        self.wal.append("PUT", key, value)
        
        # 2. Update in-memory memtable
        self.memtable[key] = value
        
        # 3. Check if memtable is full
        if self._estimate_size() >= self.memtable_size_limit:
            self._flush_memtable()
            
    def get(self, key):
        # 1. Check current memtable (local read-your-writes guarantee)
        if key in self.memtable:
            val = self.memtable[key]
            if val == "DELETE":  # Tombstone
                return None
            return val
            
        # 2. Check immutable memtables (newest first)
        for memtable in reversed(self.immutable_memtables):
            if key in memtable:
                val = memtable[key]
                if val == "DELETE":
                    return None
                return value
                
        # 3. Check SSTables (newest first)
        for sstable in reversed(self.sstables):
            val = sstable.get(key)
            if val is not None:
                if val == "DELETE":
                    return None
                return val
                
        return None  # Not found
        
    def delete(self, key):
        # Special tombstone marker
        self.put(key, "DELETE")
        
    def _flush_memtable(self):
        """Convert memtable to SSTable on disk"""
        if not self.memtable:
            return
            
        # 1. Make memtable immutable
        immutable = self.memtable
        self.immutable_memtables.append(immutable)
        self.memtable = {}
        
        # 2. Write to SSTable in background
        self._background_flush(immutable)
        
    def _background_flush(self, memtable):
        """Async: sort keys and write to SSTable"""
        # Sort by key (in production: memtable is already sorted)
        sorted_items = sorted(memtable.items())
        
        # Create SSTable (from Episode 2.1)
        sstable = SSTable(f"sstable_{len(self.sstables)}.sst")
        sstable.write(sorted_items)
        
        # Add to SSTable list
        self.sstables.append(sstable)
        
        # Remove from immutable list
        self.immutable_memtables.remove(memtable)
        
        # Truncate WAL (data now safely on disk)
        self.wal.truncate()
```

How it works:

1. Writes go to memory first (fast)
2. When memory fills, flush to disk as sorted file (SSTable)
3. Reads check memory, then disk files newest to oldest
4. Deletes are special markers (tombstones)

---

The Problem: Read Amplification

Our simple LSM works, but has a critical flaw:

```python
def get_slow(key):
    # Check memtable: 1 lookup
    # Check 5 immutable memtables: 5 lookups  
    # Check 100 SSTables: 100 binary searches!
    # Total: 106 operations for 1 read
```

If we have 100 SSTables, each read does 100 binary searches! This is read amplification.

Visualizing the problem:

```
SSTable 1: [a-d]
SSTable 2: [e-h]  
SSTable 3: [i-l]
...
SSTable 100: [wa-zd]

To find key "carrot":
1. Binary search in SSTable 1
2. Binary search in SSTable 2
3. ... 
100. Binary search in SSTable 100
```

The solution: Bloom Filters and Compaction.

---

Scale Breaks: Real LSM Challenges

Failure Mode 1: Write Amplification

```python
# Each key gets rewritten multiple times during compaction
key = "user:1000"
write_count = 0

# Write to memtable
write_count += 1

# Flush to L0 SSTable  
write_count += 1

# Compact L0 → L1 (rewrites key)
write_count += 1

# Compact L1 → L2 (rewrites key again)
write_count += 1

# Total: 4 physical writes for 1 logical write!
# For 1M writes/sec: 4M disk writes/sec (SSD wear-out)
```

Failure Mode 2: Compaction Storms

```python
def background_compaction():
    while True:
        if needs_compaction():
            # Start merging 10GB files
            merge_large_sstables()  # Takes 30 minutes
            # During this time: high disk I/O, high CPU
            # Writes slow down, reads slow down
```

Problem: Background compaction consumes resources, affecting foreground operations.

Failure Mode 3: Space Amplification

```python
# Data exists in multiple SSTables simultaneously
sstable1 = {"key1": "value1", "key2": "value2"}
sstable2 = {"key1": "value1_updated", "key3": "value3"}

# Total unique keys: 3
# Total stored data: 4 key-value pairs
# Space amplification: 4/3 = 1.33x
```

Result: Need 1.33x more disk space than actual data.

Failure Mode 4: The Tombstone Problem

```python
# Delete leaves marker
put("key1", "DELETE")

# Tombstone exists forever unless compaction removes it
# Result: Database grows indefinitely even with deletes
```

Failure Mode 5: Hot Key Overwrites

```python
# Update same key 1000 times/second
for i in range(1000):
    put("hot_key", f"value_{i}")
    
# Each write creates new version
# Compaction must merge all versions
# These overwrites dramatically increase write amplification because 
# every compaction has to re-process all historical versions of the hot key
```

---

Production Hardening: Building RocksDB's Engine

Layer 1: Leveled Compaction Strategy

Instead of all SSTables at one level, organize them into levels:

```python
class LeveledLSM(SimpleLSM):
    def __init__(self):
        super().__init__()
        self.levels = [
            [],  # Level 0: SSTables from memtable flushes (unsorted ranges)
            [],  # Level 1: Sorted, non-overlapping SSTables (10MB each)
            [],  # Level 2: Sorted, non-overlapping (100MB each)
            [],  # Level 3: Sorted, non-overlapping (1GB each)
            []   # Level 4: Sorted, non-overlapping (10GB each)
        ]
        
    def _should_compact(self, level):
        """Check if level exceeds size limit"""
        # (RocksDB typically uses a size ratio, not power-of-ten growth; simplified here)
        size_limits = [0, 10*1024*1024, 100*1024*1024, 1024*1024*1024, 10*1024*1024*1024]
        current_size = sum(sst.size() for sst in self.levels[level])
        return current_size > size_limits[level]
        
    def _compact_level(self, level):
        """Compact level into next level"""
        if level >= len(self.levels) - 1:
            return  # Last level
            
        # 1. Select subset of SSTables to compact (real engines select subset, not all)
        # (Simplified for teaching - real leveled compaction selects a small subset)
        to_compact = self._select_compaction_subset(level)
        next_level_tables = self.levels[level + 1]
        
        # 2. Multiway merge all SSTables
        # In production: entries have timestamps/sequence numbers for deduplication
        all_entries = []
        for sst in to_compact + next_level_tables:
            # Production LSMs attach a sequence number to each key
            entries = [(k, v, sst.sequence) for k, v in sst.read_all()]
            all_entries.extend(entries)
            
        # 3. Sort and deduplicate (keep newest based on timestamp)
        sorted_entries = sorted(all_entries, key=lambda x: (x[0], -x[2]))  # key asc, timestamp desc
        merged = self._merge_with_duplicates(sorted_entries)
        
        # 4. Write new SSTables to next level
        new_sstables = self._split_into_sstables(merged, level + 1)
        self.levels[level + 1] = new_sstables
        self.levels[level] = []  # Clear this level
        
    def _merge_with_duplicates(self, entries):
        """Merge sorted entries, keeping only the newest for each key"""
        result = []
        current_key = None
        
        for key, value, timestamp in entries:
            if key != current_key:
                # First occurrence of this key (newest due to sorting)
                result.append((key, value))
                current_key = key
                
        return result
```

Why leveled compaction works:

· Level 0: New SSTables (may have overlapping ranges)
· Level 1+: SSTables have non-overlapping key ranges
· Read only checks one SSTable per level after L0
· From ~100 binary searches to ~5

Layer 2: Bloom Filters for "Not Found" Acceleration

```python
class BloomFilter:
    """Probabilistic data structure for set membership"""
    def __init__(self, n_bits, n_hashes):
        self.n_bits = n_bits
        self.n_hashes = n_hashes
        self.bits = [0] * n_bits
        
    def add(self, key):
        for i in range(self.n_hashes):
            # Hash function
            hash_val = (hash(key) + i * 0x9e3779b9) & 0xffffffff
            bit_pos = hash_val % self.n_bits
            self.bits[bit_pos] = 1
            
    def might_contain(self, key):
        for i in range(self.n_hashes):
            hash_val = (hash(key) + i * 0x9e3779b9) & 0xffffffff
            bit_pos = hash_val % self.n_bits
            if self.bits[bit_pos] == 0:
                return False  # Definitely not in set
        return True  # Probably in set (false positive possible)

class SSTableWithBloomFilter(SSTable):
    def __init__(self, filename):
        super().__init__(filename)
        # Bloom filter is built during SSTable creation and stored with index
        self.bloom = BloomFilter(n_bits=10*len(self.keys), n_hashes=7)
        for key in self.keys:
            self.bloom.add(key)
            
    def get(self, key):
        # Fast rejection: if bloom says no, skip binary search
        if not self.bloom.might_contain(key):
            return None
        return super().get(key)
```

Performance impact: Eliminates 95% of unnecessary SSTable lookups.

Layer 3: Tiered vs Leveled Compaction

Different workloads need different strategies:

```python
class CompactionStrategy:
    def compact(self, sstables):
        pass

class TieredCompaction(CompactionStrategy):
    """For write-heavy workloads (like Cassandra)"""
    def compact(self, sstables):
        # Merge all SSTables at same level
        # Write new larger SSTable to next level
        # More write amplification, faster writes
        
class LeveledCompaction(CompactionStrategy):
    """For read-heavy workloads (like RocksDB default)"""
    def compact(self, sstables):
        # Merge SSTables with overlapping ranges
        # Write many small SSTables to next level  
        # Less write amplification, faster reads
        
class TimeWindowCompaction(CompactionStrategy):
    """For time-series data (like Cassandra TWCS)"""
    def compact(self, sstables):
        # Group SSTables by time window
        # Only compact within same time window
        # Efficient for TTL (time-to-live) expiry
```

Layer 4: Rate-Limited Compaction

```python
class RateLimitedCompaction:
    def __init__(self, iops_limit=1000, mbps_limit=100):
        self.iops_limit = iops_limit  # I/O operations per second
        self.mbps_limit = mbps_limit  # Megabytes per second
        self.last_check = time.time()
        self.iops_count = 0
        self.bytes_written = 0
        
    def can_proceed(self, operation_size=0):  # Conceptual code - compaction cost estimation omitted
        now = time.time()
        elapsed = now - self.last_check
        
        # Reset counters every second
        if elapsed >= 1.0:
            self.iops_count = 0
            self.bytes_written = 0
            self.last_check = now
            
        # Check limits
        if self.iops_count >= self.iops_limit:
            return False
        if self.bytes_written + operation_size > self.mbps_limit * 1024 * 1024:
            return False
            
        self.iops_count += 1
        self.bytes_written += operation_size
        return True
```

Why rate limiting: Prevents compaction storms from starving foreground operations.

Layer 5: Compression & Encoding

```python
class CompressedSSTable(SSTable):
    def write(self, entries):
        # 1. Key prefix compression
        compressed = self._prefix_compress(entries)
        
        # 2. Value compression (Snappy, Zstd, LZ4)
        compressed = self._value_compress(compressed)
        
        # 3. Write with checksum
        super().write(compressed)
        
    def _prefix_compress(self, entries):
        """Store only key differences"""
        result = []
        last_key = ""
        for key, value in entries:
            # Find common prefix with last key
            common_len = 0
            for i in range(min(len(key), len(last_key))):
                if key[i] == last_key[i]:
                    common_len += 1
                else:
                    break
                    
            # Store: (common_length, suffix, value)
            result.append((common_len, key[common_len:], value))
            last_key = key
        return result
```

Space savings: Typically 2-10x reduction in disk usage.

---

ProductionX: The Complete LSM Engine

```python
class ProductionLSMEngine:
    """
    Production-grade LSM engine with:
    1. Memtable with skip list for concurrent access
    2. Multi-level SSTable organization
    3. Bloom filters for fast negative lookups
    4. Configurable compaction strategies
    5. Rate limiting and prioritization
    6. Compression and checksums
    7. Metrics and monitoring
    """
    
    def __init__(self, data_dir, options):
        self.data_dir = data_dir
        self.options = options
        
        # Core components
        self.memtable = SkipListMemtable()
        self.immutable_memtables = []
        self.levels = [[] for _ in range(options.num_levels)]
        
        # Optimization layers
        self.bloom_filters = {}  # SSTable → BloomFilter
        self.block_cache = ShardedLRUCache(options.block_cache_size)  # Sharded for concurrency
        self.index_cache = ShardedLRUCache(options.index_cache_size)
        
        # Compaction management
        self.compaction_strategy = self._create_strategy(options.strategy)
        self.compaction_limiter = RateLimitedCompaction(
            iops_limit=options.compaction_iops_limit,
            mbps_limit=options.compaction_throughput_limit
        )
        
        # Background workers
        self.flush_thread = threading.Thread(target=self._flush_worker)
        self.compaction_thread = threading.Thread(target=self._compaction_worker)
        self.stats_thread = threading.Thread(target=self._stats_worker)
        
        # Recovery
        self._recover()
        
    def put(self, key, value, write_options=None):
        # 1. Write to WAL (sync based on write_options)
        wal_sync = write_options.sync if write_options else True
        self.wal.append(key, value, sync=wal_sync)
        
        # 2. Insert into memtable
        self.memtable.insert(key, value)
        
        # 3. Check if memtable needs flush
        if self.memtable.size() >= self.options.memtable_size:
            self._schedule_flush()
            
        # 4. Update metrics
        self.metrics.record_write()
        
    def get(self, key, read_options=None):
        # 1. Check block cache
        cache_key = f"block:{hash(key) % 1000}"
        if cache_key in self.block_cache:
            return self.block_cache[cache_key]
            
        # 2. Check memtable (read-your-writes guarantee for single node)
        value = self.memtable.get(key)
        if value is not None:
            if value == "DELETE":
                return None
            return value
            
        # Note: Read-your-writes consistency can break across replicas or 
        # when WAL sync is relaxed, even though a single node's memtable 
        # guarantees local read-your-writes
            
        # 3. Check immutable memtables (newest first)
        for memtable in reversed(self.immutable_memtables):
            value = memtable.get(key)
            if value is not None:
                if value == "DELETE":
                    return None
                return value
                
        # 4. Check SSTables with bloom filter acceleration
        for level in range(len(self.levels)):
            for sst in reversed(self.levels[level]):
                # Fast rejection via bloom filter
                if sst.bloom and not sst.bloom.might_contain(key):
                    continue
                    
                # Check index (cached)
                if sst.filename in self.index_cache:
                    index = self.index_cache[sst.filename]
                else:
                    index = sst.read_index()
                    self.index_cache[sst.filename] = index
                    
                # Binary search in index
                block_idx = index.find_block(key)
                if block_idx is not None:
                    # Read block (maybe cached)
                    block = sst.read_block(block_idx)
                    value = block.get(key)
                    if value is not None:
                        if value == "DELETE":
                            return None
                        # Cache for next time
                        self.block_cache[cache_key] = value
                        return value
                        
        return None
        
    def _compaction_worker(self):
        """Background compaction thread"""
        while not self.stopped:
            # Find level that needs compaction
            for level in range(len(self.levels) - 1):
                if self._needs_compaction(level):
                    # Rate limiting check (conceptual - operation size omitted)
                    if self.compaction_limiter.can_proceed():
                        self._compact_level(level)
                        break
            time.sleep(0.1)  # Small delay between checks
            
    def _needs_compaction(self, level):
        """Decide if level needs compaction"""
        if level == 0:
            # L0: compact if too many files
            return len(self.levels[0]) >= self.options.l0_compaction_trigger
        else:
            # L1+: compact if exceeds size limit
            level_size = sum(sst.size() for sst in self.levels[level])
            level_limit = self.options.level_size_base * (10 ** level)
            return level_size > level_limit
            
    def _compact_level(self, level):
        """Execute compaction with rate limiting"""
        # Select files to compact (subset, not all)
        files_to_compact = self._select_compaction_files(level)
        
        # Multiway merge with deduplication
        merged = self._merge_files(files_to_compact)
        
        # Split into new files for next level
        new_files = self._split_into_files(merged, level + 1)
        
        # Atomically replace old files with new
        self._atomic_compaction_replace(level, files_to_compact, new_files)
        
        # Update metrics
        self.metrics.record_compaction(len(files_to_compact), len(new_files))
```

Production Guarantees:

· ✅ Write throughput: Millions of writes/second with sequential I/O
· ✅ Space efficiency: Compression + deduplication reduces storage
· ✅ Read performance: Bloom filters + caching + leveled structure
· ✅ Predictable latency: Rate-limited compaction prevents storms
· ✅ Durability: WAL + fsync options
· ✅ Maintainability: Configurable strategies for different workloads

---

The Next Constraint: Mixed Read-Write Workloads

Our LSM engine now handles write-heavy workloads beautifully. But what about mixed workloads with:

· 50% reads, 50% writes
· Hot keys that are both read and written frequently
· Real-time analytics with fresh data queries

LSM weakness for mixed workloads:

1. Read-your-writes consistency: New writes in memtable, reads might go to older SSTables
2. Hot key updates: Same key updated frequently causes write amplification
3. Range query performance: Need to merge results from multiple SSTables

The hybrid solution: Combine B-Tree and LSM approaches:

· B-Tree cache for hot data (fast reads, updates in place)
· LSM background for cold data (efficient writes, compression)
· Intelligent tiering based on access patterns

In Episode 2.7, we'll build a hybrid storage engine that automatically places data in the right structure based on access patterns. We'll learn how modern databases like Google's Bigtable and Azure CosmosDB use hybrid approaches to get the best of both worlds.

The complete evolution:

· 2.5: B-Trees (read-optimized, traditional databases)
· 2.6: LSM-Trees (write-optimized, modern NoSQL) ← We are here
· 2.7: Hybrid engines (best of both, production-grade databases)

---

Key Takeaways

1. LSM-Trees optimize for writes by replacing random I/O with sequential appends (amortized O(1) writes).
2. The tradeoff is read amplification - checking multiple SSTables requires bloom filters and smart compaction.
3. Compaction strategy is critical - leveled (RocksDB) vs tiered (Cassandra) vs time-windowed.
4. Real systems need layers - bloom filters, block caching, rate limiting, compression.
5. Choose based on workload:
   · B-Trees: Mixed read-write, point lookups, transactions
   · LSM-Trees: Write-heavy, append-only, time-series data
   · Hybrid: Best of both, but most complex

The production insight: When you see "millions of writes per second" in a database's marketing, it's almost certainly using LSM-Trees. Understanding this tradeoff helps you choose the right database for your workload and predict its behavior at scale.

---

Next episode: We combine B-Trees and LSM-Trees into a hybrid engine that automatically adapts to workload patterns, building the kind of storage system used by Google Bigtable and Azure CosmosDB.