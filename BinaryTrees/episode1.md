Episode 2.1: "Sorted Logs - When Binary Search Meets Persistence"

(0:00) Hook: Real Production Pain Point

[Opening shot: Monitoring dashboard showing database latency spikes]

Host: "Have you ever been paged at 3 AM because a database query that normally takes milliseconds suddenly takes seconds? You check the indexes, they're there. You check the query plan, it looks right. But something's fundamentally broken.

The answer lies in an algorithm you learned in your first CS class. Today, we're going from LeetCode #704 to the beating heart of every database: the write-ahead log. We'll build it, break it, and harden it into a production-grade system."

(2:00) LeetCode Core: Binary Search

[Screen split: Left side shows LeetCode problem #704, right side shows clean implementation]

Host: "Let's start with the basics. LeetCode #704: Binary Search. Given a sorted array of integers, find a target value in O(log n) time."

```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = left + (right - left) // 2  # Avoid overflow
        
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1
```

Host: "This seems trivial, but let me ask: what's the fundamental requirement here?"

[Text appears: "SORTED DATA"]

Host: "Exactly. Binary search only works on sorted data. This 'obvious' constraint becomes everything when we move to production systems. The real concept here isn't just O(log n) search - it's maintaining sorted order for efficient lookup. This is the DNA of database indexes."

(8:00) Toy Production System: Write-Ahead Log

[Screen shows a simple database diagram with a "WAL" component highlighted]

Host: "Let's map this to a real system. Every database needs durability - if a power failure happens, committed writes shouldn't disappear. The solution: Write-Ahead Logging. Before any data goes to the main database, it gets written to a log on disk."

Toy System Design:

· Append-only log file
· Each entry: timestamp|key|value|checksum
· In-memory index mapping keys to file positions

```python
class ToyWAL:
    def __init__(self, log_file="wal.log"):
        self.log_file = log_file
        self.index = {}  # key -> (file_position, timestamp)
        
    def append(self, key, value):
        """Append a key-value pair to the log"""
        entry = f"{time.time()}|{key}|{value}|{hash(value)}\n"
        
        with open(self.log_file, 'a') as f:
            pos = f.tell()
            f.write(entry)
            
        # Update in-memory index
        self.index[key] = (pos, time.time())
        return True
    
    def get(self, key):
        """Get value by key using binary search on sorted index"""
        if key not in self.index:
            return None
            
        pos, _ = self.index[key]
        
        with open(self.log_file, 'r') as f:
            f.seek(pos)
            line = f.readline()
            _, _, value, _ = line.strip().split('|')
            
        return value
    
    def binary_search_in_log(self, target_key):
        """Binary search directly in sorted log (inefficient but educational)"""
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            
        # Extract keys and keep line positions
        entries = []
        current_pos = 0
        for line in lines:
            timestamp, key, value, checksum = line.strip().split('|')
            entries.append((key, current_pos, line))
            current_pos += len(line)
        
        # Sort entries by key (simulating sorted log)
        entries.sort(key=lambda x: x[0])
        
        # Binary search
        left, right = 0, len(entries) - 1
        while left <= right:
            mid = left + (right - left) // 2
            mid_key, pos, line = entries[mid]
            
            if mid_key == target_key:
                return line.split('|')[2]  # Return value
            elif mid_key < target_key:
                left = mid + 1
            else:
                right = mid - 1
                
        return None
```

Host: "This works! We have a durable log with O(log n) lookups via our in-memory index. But we're cheating - the actual log isn't sorted, our index is. What if we lose the index? We need binary search on the log itself."

(12:00) Scale Breaks: Real-World Failure Modes

[Dashboard shows metrics going red as load increases]

Host: "Let's run this at production scale and watch it break."

Failure Mode 1: The 1TB Log Problem

```python
# Simulate 1TB of log data
entries = 10_000_000_000  # 10 billion entries
log_size = entries * 100  # ~100 bytes per entry = 1TB

# Problem: Our "binary_search_in_log" reads ALL lines into memory!
# Memory required: 1TB → System crashes
```

Host: "We can't read 1TB into memory. We need to binary search directly on disk."

Failure Mode 2: Concurrent Writes Corrupt Data

```python
# Two threads write simultaneously
Thread 1: wal.append("user:100", "Alice")
Thread 2: wal.append("user:101", "Bob")

# Result in log: "timestamp|user:100|Alice|checksumtimestamp|user:101|Bob|checksum"
# The entries are mangled! No newlines, can't parse.
```

Host: "Append-only doesn't mean thread-safe. We need proper synchronization."

Failure Mode 3: Disk Failures and Corruption

```python
# Power fails during write
entry = "1234567890|user:100|Alice|"
# Write incomplete, checksum missing
# On restart: "unexpected end of data" - entire log corrupted?
```

Host: "Single disk failure shouldn't corrupt the entire log."

Failure Mode 4: In-Memory Index Lost

```python
# Process crashes, memory gone
# Index = {}
# To rebuild: read 1TB log linearly → 30+ minutes downtime
```

Host: "30 minutes to restart is unacceptable."

Failure Mode 5: Tombstones and Deletions

```python
wal.append("user:100", "DELETE")  # How do we clean this up?
# Log grows forever with deleted data
```

(18:00) Production Hardening: SSTables

[Animated transition from broken ToyWAL to SSTable architecture]

Host: "Time to build our production version. Enter: Sorted String Tables (SSTables)."

Layer 1: Durability & Corruption Recovery

```python
class SSTableSegment:
    def __init__(self, filename):
        self.filename = filename
        self.sparse_index = {}  # Every 4096th key -> file position
        self.bloom_filter = None  # For fast "not found" checks
        
    def write_segment(self, sorted_entries):
        """Write sorted entries to disk with checksums"""
        with open(self.filename, 'wb') as f:
            for key, value in sorted_entries:
                # Add checksum for each entry
                entry_data = f"{key}|{value}".encode()
                checksum = crc32(entry_data)
                record = struct.pack(f"I{len(entry_data)}sI", 
                                   len(entry_data), entry_data, checksum)
                f.write(record)
                
            # Add footer with segment metadata
            footer = struct.pack("QQ", f.tell(), len(sorted_entries))
            f.write(footer)
            
    def binary_search_disk(self, target_key):
        """Binary search directly on disk without loading全部 into memory"""
        with open(self.filename, 'rb') as f:
            f.seek(-16, 2)  # Seek to footer
            footer = f.read(16)
            data_start, num_entries = struct.unpack("QQ", footer)
            
            left, right = 0, num_entries - 1
            while left <= right:
                mid = left + (right - left) // 2
                
                # Seek to mid entry using sparse index or approximation
                pos = self._estimate_position(mid, num_entries, data_start)
                f.seek(pos)
                
                # Read entry at this position
                key, value = self._read_entry_at(f)
                
                if key == target_key:
                    return value
                elif key < target_key:
                    left = mid + 1
                else:
                    right = mid - 1
                    
        return None
```

Layer 2: Compaction for Tombstone Cleanup

```python
class SSTableWithCompaction:
    def __init__(self):
        self.memtable = {}  # In-memory sorted dictionary
        self.segments = []  # On-disk SSTable segments
        self.size_limit = 64 * 1024 * 1024  # 64MB
        
    def _flush_memtable(self):
        """Convert memtable to sorted on-disk segment"""
        if not self.memtable:
            return
            
        sorted_entries = sorted(self.memtable.items())
        segment = SSTableSegment(f"segment_{len(self.segments)}.sst")
        segment.write_segment(sorted_entries)
        self.segments.append(segment)
        self.memtable.clear()
        
    def _compact_segments(self):
        """Merge segments, removing deleted keys"""
        if len(self.segments) < 3:
            return
            
        # Merge multiple segments into one
        merged_entries = []
        for segment in self.segments[-3:]:
            merged_entries.extend(segment.read_all_entries())
            
        # Remove tombstones and keep latest version
        latest = {}
        for key, value in sorted(merged_entries):
            if value != "DELETE":
                latest[key] = value
                
        # Write new compacted segment
        new_segment = SSTableSegment(f"compact_{time.time()}.sst")
        new_segment.write_segment(sorted(latest.items()))
        
        # Replace old segments
        self.segments = self.segments[:-3] + [new_segment]
```

Layer 3: Concurrent Access with Readers-Writer Lock

```python
import threading

class ConcurrentSSTable:
    def __init__(self):
        self.rwlock = threading.Lock()
        self.readers = 0
        self.reader_cond = threading.Condition(self.rwlock)
        self.writer_cond = threading.Condition(self.rwlock)
        self.writer = False
        
    def get_with_lock(self, key):
        with self.rwlock:
            while self.writer:
                self.reader_cond.wait()
            self.readers += 1
            
        try:
            return self._internal_get(key)
        finally:
            with self.rwlock:
                self.readers -= 1
                if self.readers == 0:
                    self.writer_cond.notify()
                    
    def append_with_lock(self, key, value):
        with self.rwlock:
            while self.writer or self.readers > 0:
                self.writer_cond.wait()
            self.writer = True
            
        try:
            return self._internal_append(key, value)
        finally:
            with self.rwlock:
                self.writer = False
                self.reader_cond.notify_all()
                self.writer_cond.notify()
```

Layer 4: Monitoring & Recovery

```python
class ProductionSSTable(SSTableWithCompaction, ConcurrentSSTable):
    def __init__(self):
        super().__init__()
        self.metrics = {
            'reads_per_sec': 0,
            'writes_per_sec': 0,
            'segment_count': 0,
            'compaction_running': False
        }
        
    def rebuild_from_segments(self):
        """Recover index from segments after crash"""
        # 1. List all segment files
        # 2. Read each segment's sparse index
        # 3. Merge into global sparse index
        # 4. Verify checksums for corruption detection
        # Recovery time: O(number of segments), not O(total data)
        
    def background_compaction(self):
        """Async compaction with backpressure"""
        while True:
            if self._needs_compaction():
                self.metrics['compaction_running'] = True
                self._compact_with_backpressure()
                self.metrics['compaction_running'] = False
            time.sleep(1)
```

ProductionX Guarantee Document:

```
System: SSTable Storage Engine v1.0

Guarantees:
- Durability: All acknowledged writes survive process crashes
- Consistency: Readers see all previously committed writes
- Performance: O(log n) reads, O(1) amortized writes
- Recovery: Crash recovery in < 30 seconds for 1TB data

SLAs:
- P99 read latency: < 10ms
- P99 write latency: < 50ms
- Availability: 99.99% (excluding scheduled compactions)

Failure Modes Handled:
- Process crashes: Recover from WAL
- Disk corruption: Detect via checksums, skip bad segments
- Memory pressure: Spill to disk automatically
- Hot keys: Handle with concurrent readers
```

(24:00) Next Constraint & Teaser

Host: "We now have a production-grade storage engine that gives us single-key lookup with O(log n) performance. But what if our product manager comes to us and says: 'I need to find all user posts from last week'?

Single-key lookups aren't enough. We need range queries. We need to ask: 'Give me all keys between A and B.'

This is where our next algorithm comes in. LeetCode #34: Find First and Last Position in Sorted Array. It teaches us lower_bound and upper_bound - the fundamental operations for range queries.

In Episode 2.2, we'll build a social media feed pagination system that handles infinite scroll with millions of concurrent users. We'll learn about cursor stability, hot partitions, and how to paginate through real-time updating data."

(25:00) Recap & Key Takeaways

Host: "Let's recap what we've learned today:

1. Binary Search → Sorted Storage: The algorithm's requirement for sorted data becomes the system's requirement for sorted on-disk formats.
2. Toy to Production Journey: We started with a simple append-only log, hit 5 major scale failures, and built a hardened SSTable engine.
3. Production Patterns Learned:
   · SSTables: Sorted on-disk segments with sparse indexes
   · Compaction: Merging segments to remove deletions
   · Concurrent access: Reader-writer locks for scalability
   · Corruption handling: Entry-level checksums
4. When to Use This: SSTables are perfect for write-heavy, read-recent workloads. They're the foundation of Cassandra, RocksDB, and Bigtable.

The Big Insight: Every database index is fundamentally a sorted data structure that enables binary search. The innovation isn't the search algorithm - it's maintaining that sorted order efficiently on persistent storage while handling every possible failure mode.

Next time: From single keys to ranges. From binary search to bound search. See you in Episode 2.2."

[End screen shows Episode 2.2 preview: "Bound Search - The Infinite Scroll Algorithm"]