Episode 2.5 Final: "B-Trees - The Database Index Engine"

The Hook: The 150GB Cliff

Your database has been humming along with 100GB of customer data. Queries return in 10ms, users are happy. Then you cross 150GB.

Suddenly, 99th percentile latency jumps to 500ms. Your monitoring shows 100% disk utilization on random reads. The database is thrashing, reading from disk for every query.

You check: indexes exist, queries are tuned. The problem isn't SQL. It's physics: your data structure is fighting disk access patterns.

Random disk seeks are orders of magnitude slower than RAM:

· RAM: ~100ns
· NVMe SSD: ~20-50µs (200-500× slower)
· SATA SSD: ~100µs (1,000× slower)
· HDD: ~5-10ms (50,000-100,000× slower)

Your beautiful in-memory BST from Episode 2.4 becomes a performance disaster when it spills to disk. The solution has powered every relational database for 40+ years: B-Trees.

---

From BSTs to B-Trees: The Physics Problem

Recall Episode 2.4: In-Memory BST

```python
class BSTNode:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.left = None   # ≤ key
        self.right = None  # ≥ key
```

Problem: Each node is tiny (a few bytes) but requires a random memory access. If we store BST nodes on disk:

· 1M nodes = 1M random disk reads
· HDD: 10ms × 1,000,000 = 10,000 seconds (2.7 hours!)
· Even NVMe SSD: 50µs × 1,000,000 = 50 seconds

The insight: Disk doesn't care about your pretty pointer chains. It reads in blocks (typically 4KB). Reading 1 byte or 4KB costs the same.

B-Tree Solution: Think in Disk Blocks

```python
class BTreeNode:
    def __init__(self, is_leaf=True):
        self.keys = []          # Sorted keys in this node (many of them!)
        self.children = []      # Child nodes (if not leaf)
        self.is_leaf = is_leaf
```

Key difference: A B-Tree node holds B-1 to 2B-1 keys, where B is chosen so the entire node fits in one disk block.

Visual comparison:

```
BST (for 1M keys, height ~20):
           [500]
          /     \
     [250]       [750]    ... 20 levels
    /    \       /   \        ↓ 20 disk reads
 [125]  [375] [625] [875]

B-Tree with B=100 (for 1M keys, height ~3):
          [keys 1-1000]
        /      |        \
 [1-333]  [334-666]  [667-1000]
   (each node = 1 disk block)
          ↓ 3 disk reads
```

The math:

· BST height: log₂(1,000,000) ≈ 20
· B-Tree height: log₁₀₀(1,000,000) ≈ 3

From 20 random disk reads to 3. That's the B-Tree breakthrough.

---

Why B+Trees? The Database-Optimized Variant

Databases use B+Trees, a variant with crucial advantages:

1. Only Leaves Store Values

· Internal nodes: Store only keys (no values) → higher branching factor
· Leaf nodes: Store (key, value) pairs and are linked together

```
Visual Structure:
Internal Nodes: [10, 20, 30] → pointers to children
              /     |      \
Leaf Level: [5,9] → [12,15,19] → [21,25,29] → ...
           (linked for range scans)
```

2. Higher Branching Factor

Since internal nodes don't store values, more keys fit per page:

· B-Tree (with values): ~100 keys per 4KB page
· B+Tree (no values): ~200-500 keys per 4KB page

Result: Even shallower trees!

3. Efficient Range Scans

```python
# B+Tree leaf linkage enables sequential scans
def range_scan(start_key, end_key):
    # 1. Binary search to find start_key leaf
    leaf = find_leaf(start_key)  # O(log_B n)
    
    # 2. Sequential scan through linked leaves
    while leaf and leaf.keys[0] <= end_key:
        for key, value in leaf.items():
            if start_key <= key <= end_key:
                yield (key, value)
        leaf = leaf.next_leaf  # Follow pointer
```

Clustered vs Non-Clustered Indexes:

· Clustered: Leaf nodes contain actual table rows (e.g., InnoDB primary key)
· Non-clustered: Leaf nodes contain pointers to rows (e.g., secondary indexes)

This is why SELECT * with a clustered index range scan is faster—no extra pointer chasing.

---

B+Tree Implementation: Search & Insert

```python
class BPlusTree:
    def __init__(self, order=100):  # ~4KB page with 100-200 keys
        self.order = order
        self.min_keys = order - 1
        self.max_keys = 2 * order - 1
        self.root = BTreeNode(is_leaf=True)
        
    def search(self, key):
        """Find key with minimal disk reads"""
        node = self.root
        
        # Traverse internal nodes
        while not node.is_leaf:
            # Binary search within this disk block
            idx = self._binary_search_in_block(node, key)
            # Read next block from disk
            node = self._read_disk_block(node.children[idx])
            
        # Now at leaf - binary search within block
        idx = self._binary_search_in_block(node, key)
        if idx < len(node.keys) and node.keys[idx] == key:
            return node.values[idx]
        return None
        
    def _binary_search_in_block(self, node, key):
        """Binary search within a B-Tree node"""
        left, right = 0, len(node.keys) - 1
        
        while left <= right:
            mid = left + (right - left) // 2
            if node.keys[mid] == key:
                return mid
            elif node.keys[mid] < key:
                left = mid + 1
            else:
                right = mid - 1
                
        return left  # Insertion position
        
    def insert(self, key, value):
        """Insert with possible splits"""
        # If root is full, split it
        if len(self.root.keys) >= self.max_keys:
            new_root = BTreeNode(is_leaf=False)
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root
            
        self._insert_nonfull(self.root, key, value)
        
    def _split_child(self, parent, child_index):
        """
        Split a full child, promoting middle key.
        Example with max_keys=5:
        Before: [5, 9, 12, 20, 30] (full)
        After:  Left: [5, 9]
                Right: [12, 20, 30]
                Promote: 12
        """
        child = parent.children[child_index]
        
        # Create new sibling
        sibling = BTreeNode(is_leaf=child.is_leaf)
        mid = len(child.keys) // 2
        
        if child.is_leaf:
            # B+Tree: split keys/values, duplicate first of right in parent
            sibling.keys = child.keys[mid:]
            sibling.values = child.values[mid:]
            child.keys = child.keys[:mid]
            child.values = child.values[:mid]
            
            # Link leaves for range scans
            sibling.next_leaf = child.next_leaf
            child.next_leaf = sibling
            
            # Promote first key of right sibling (B+Tree specific)
            promote_key = sibling.keys[0]
        else:
            # Internal node: middle key goes up
            promote_key = child.keys[mid]
            sibling.keys = child.keys[mid+1:]
            sibling.children = child.children[mid+1:]
            child.keys = child.keys[:mid]
            child.children = child.children[:mid+1]
            
        # Insert promote_key and sibling into parent
        parent.keys.insert(child_index, promote_key)
        parent.children.insert(child_index + 1, sibling)
```

Key Mapping:

```
Key → Binary search in internal nodes → Page number
Page number → Read disk block → Leaf node
Leaf node → Binary search → Value or row pointer
```

---

Buffer Pool: The Performance Multiplier

Reading from disk for every operation would still be slow. Solution: cache disk blocks in RAM.

```python
class BufferPool:
    def __init__(self, capacity=1000):  # Cache 1000 disk blocks (~4MB)
        self.cache = {}  # block_id → (data, pinned, dirty)
        self.capacity = capacity
        
    def get_block(self, block_id):
        if block_id in self.cache:
            # Cache hit: move to MRU
            return self.cache[block_id][0]
            
        # Cache miss: read from disk
        data = self._read_from_disk(block_id)
        
        # Make space if needed (evict unpinned, non-dirty pages)
        if len(self.cache) >= self.capacity:
            self._evict_one()
            
        # Cache it
        self.cache[block_id] = [data, False, False]  # (data, pinned, dirty)
        return data
        
    def pin_block(self, block_id):
        """Prevent eviction during multi-page operations"""
        if block_id in self.cache:
            self.cache[block_id][1] = True  # pinned
            
    def unpin_block(self, block_id):
        """Allow eviction after operation completes"""
        if block_id in self.cache:
            self.cache[block_id][1] = False
            
    def mark_dirty(self, block_id):
        """Block modified, needs write-back"""
        if block_id in self.cache:
            self.cache[block_id][2] = True  # dirty
            
    def _evict_one(self):
        """Evict least recently used unpinned page"""
        for block_id in self.cache:
            if not self.cache[block_id][1]:  # not pinned
                if self.cache[block_id][2]:  # dirty
                    self._write_to_disk(block_id, self.cache[block_id][0])
                del self.cache[block_id]
                return
```

The magic: With a 4GB buffer pool (1M blocks), a 100GB database has hot data cached. Most queries hit RAM, not disk.

---

Write-Ahead Logging: Crash Safety

Critical rule: WAL must reach disk before the actual page write.

```python
def btree_insert_safe(key, value):
    # 1. Write to WAL first (sequential, fast)
    wal_entry = f"INSERT|{key}|{value}|{txn_id}"
    wal_file.write(wal_entry)
    wal_file.flush()  # Force to disk
    
    # 2. Update buffer pool (lazy write to disk)
    page = buffer_pool.get_page(page_id)
    update_page(page, key, value)
    buffer_pool.mark_dirty(page_id)
    
    # 3. Pages flush later during checkpoint
    # WAL is source of truth until then
```

Why this matters: If crash happens before page flush, we replay WAL. If crash happens during page write, we have WAL to restore.

---

Production Engine: The Complete Picture

A production B+Tree sits in a complete storage engine:

```
Query → Parser → Planner → Executor
                    ↓
            Storage Engine
                    ↓
        Buffer Pool (RAM cache)
           ↓ pin/unpin blocks
        B+Tree Traversal
           ↓ page numbers
        Disk Manager
           ↓ block reads
        Physical Storage
                    ↓
    WAL (crash safety) + MVCC (concurrency) + Vacuum (maintenance)
```

Tuning parameters:

· Page fill factor: How full to keep pages (e.g., PostgreSQL defaults to 90%)
· Buffer pool size: Typically 70-80% of available RAM
· Checkpoint interval: How often to flush dirty pages

---

When B-Trees Struggle: The Write Amplification Problem

Our B+Tree now handles reads beautifully. But consider write-heavy workloads:

· Clickstream analytics: 1M writes/second
· IoT sensors: 10M events/minute
· Real-time metrics: 100K samples/second

The B-Tree write bottleneck:

```python
def btree_write(key, value):
    # 1. Read leaf page (random I/O)
    # 2. Update page in memory
    # 3. Write page back (random I/O)
    # 4. Possibly split pages (more random I/Os)
    # Result: 2-4 random disk IOPs per write
```

Write amplification: Each logical write causes multiple physical writes. At 1M writes/second:

· NVMe SSD: 50µs × 3 × 1M = 150 seconds of disk time per second
· Reality: Even the fastest SSD can only do ~1M IOPs

The fundamental tradeoff: B-Trees optimize for reads (O(log_B n) seeks) at the cost of write amplification.

---

Next Episode: The Write-Optimized Revolution

What if we flipped the tradeoff? What if we optimized for writes instead of reads?

LSM-Trees (Log-Structured Merge Trees) do exactly that:

1. Append-only writes to a log (sequential, fast)
2. Background merging of sorted files (Episode 2.1's SSTables)
3. Bloom filters for fast "not found" checks

The tradeoff: Much faster writes, slightly slower reads.

In Episode 2.6, we'll build an LSM storage engine that can handle millions of writes per second. We'll combine:

· Episode 2.1's sorted logs (SSTables)
· Episode 2.4's trees (for in-memory sorting)
· Background compaction (merge of sorted files)

This is how Cassandra, RocksDB, and ScyllaDB achieve their incredible write throughput.

---

Key Takeaways

1. B-Trees optimize for disk blocks, not individual keys. Wide nodes = shallow trees = few disk seeks.
2. B+Trees improve upon B-Trees with higher branching (no values in internal nodes) and linked leaves for range scans.
3. Buffer pools are essential - they turn random disk I/O into (mostly) RAM access.
4. WAL provides crash safety - log before modify, replay on recovery.
5. The fundamental tradeoff: B-Trees optimize reads, LSM-Trees optimize writes. Choose based on workload.

The production insight: When your database says CREATE INDEX, it's building a B+Tree. When your queries are fast on large datasets, it's because of this 40-year-old data structure that perfectly matches disk hardware characteristics. Understanding this lets you predict performance, tune databases, and choose the right storage engine for your workload.

---

Next episode: We flip the optimization tradeoff and build a write-optimized storage engine with LSM-Trees, learning how modern databases handle millions of writes per second.