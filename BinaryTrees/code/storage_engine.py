"""
Storage Engine Layer - The Foundation

This module implements three types of storage engines:
1. BTreeStorage - Disk-optimized, fast reads (PostgreSQL style)
2. LSMStorage - Write-optimized, append-only (Cassandra style)  
3. HybridStorage - Best of both worlds (TiDB style)
"""

import json
from typing import Any, Optional, List, Tuple


class BTreeStorage:
    """
    B-Tree Storage Engine
    
    Characteristics:
    - Fast reads: O(log n) seeks
    - Slower writes: Read-modify-write on every insert
    - Used by: PostgreSQL, MySQL InnoDB, SQLite
    """
    
    def __init__(self):
        self.data = {}  # Simplified: page_id → data
        self.root_page_id = 0
        
    def put(self, key: bytes, value: bytes) -> None:
        """
        Insert or update key-value pair.
        
        In real B-Tree:
        1. Traverse tree to find leaf page
        2. Read page from disk (10ms)
        3. Modify page in memory
        4. Write page back to disk (10ms)
        Total: 20ms per write
        """
        # Simplified implementation
        self.data[key] = value
    
    def get(self, key: bytes) -> Optional[bytes]:
        """
        Lookup key in B-Tree.
        
        Real implementation:
        1. Binary search through tree levels
        2. Each level = 1 disk seek (10ms)
        3. For 1M keys with fanout=100: 3 seeks = 30ms
        """
        return self.data.get(key)
    
    def delete(self, key: bytes) -> None:
        """Delete key from B-Tree."""
        if key in self.data:
            del self.data[key]
    
    def scan_range(self, start_key: bytes, end_key: bytes) -> List[Tuple[bytes, bytes]]:
        """
        Range scan using B-Tree properties.
        
        In B+Tree:
        1. Find start_key using binary search (3 seeks)
        2. Follow leaf pointers (sequential read!)
        3. Stop at end_key
        
        This is why B+Trees are perfect for range queries.
        """
        results = []
        for key in sorted(self.data.keys()):
            if start_key <= key <= end_key:
                results.append((key, self.data[key]))
        return results
    
    def scan_prefix(self, prefix: bytes) -> List[Tuple[bytes, bytes]]:
        """Scan all keys with given prefix."""
        results = []
        for key, value in self.data.items():
            if key.startswith(prefix):
                results.append((key, value))
        return results


class LSMStorage:
    """
    LSM-Tree Storage Engine
    
    Characteristics:
    - Fast writes: O(1) append to memtable
    - Slower reads: Check memtable + multiple SSTables
    - Used by: Cassandra, RocksDB, LevelDB, HBase
    """
    
    def __init__(self, memtable_size: int = 1000):
        self.memtable = {}  # In-memory writes (SkipList in production)
        self.sstables = []  # List of immutable SSTables on disk
        self.memtable_size = memtable_size
        
    def put(self, key: bytes, value: bytes) -> None:
        """
        Write to LSM-Tree (blazing fast!).
        
        Steps:
        1. Write to memtable (in-memory, 0.1ms)
        2. When memtable full → flush to SSTable
        3. That's it! No disk reads needed.
        
        Write throughput: 10,000+ writes/sec
        vs B-Tree: 50 writes/sec
        """
        self.memtable[key] = value
        
        # Flush to SSTable when memtable full
        if len(self.memtable) >= self.memtable_size:
            self._flush_memtable()
    
    def get(self, key: bytes) -> Optional[bytes]:
        """
        Read from LSM-Tree (slower than B-Tree).
        
        Steps:
        1. Check memtable first (fast!)
        2. Check SSTable 1 (most recent)
        3. Check SSTable 2
        4. ... check all SSTables
        
        Worst case: Check all SSTables = many disk reads
        Optimization: Bloom filters (check "is key NOT in this SSTable?")
        """
        # Check memtable first
        if key in self.memtable:
            return self.memtable[key]
        
        # Check SSTables (newest first)
        for sstable in reversed(self.sstables):
            if key in sstable:
                return sstable[key]
        
        return None
    
    def delete(self, key: bytes) -> None:
        """
        Delete in LSM = write tombstone marker.
        Actual deletion happens during compaction.
        """
        self.memtable[key] = None  # Tombstone
    
    def _flush_memtable(self) -> None:
        """
        Flush memtable to immutable SSTable.
        
        In production:
        1. Sort memtable by key
        2. Write to disk as SSTable file
        3. Build index (key → offset in file)
        4. Clear memtable
        """
        # Create new SSTable from memtable
        sstable = dict(sorted(self.memtable.items()))
        self.sstables.append(sstable)
        self.memtable.clear()
    
    def compact(self) -> None:
        """
        Compaction: Merge SSTables, remove tombstones.
        
        This is literally LeetCode #23: Merge K Sorted Lists!
        
        Steps:
        1. Merge all SSTables (k-way merge)
        2. Remove duplicate keys (keep newest)
        3. Remove tombstones
        4. Write new merged SSTable
        """
        if len(self.sstables) < 2:
            return
        
        # Merge all SSTables
        merged = {}
        for sstable in self.sstables:
            for key, value in sstable.items():
                # Keep newest value (later SSTables override earlier ones)
                if value is not None:  # Skip tombstones
                    merged[key] = value
        
        # Replace all SSTables with one merged SSTable
        self.sstables = [merged]
    
    def scan_range(self, start_key: bytes, end_key: bytes) -> List[Tuple[bytes, bytes]]:
        """
        Range scan in LSM-Tree (slower than B-Tree).
        Must check all SSTables and merge results.
        """
        results = {}
        
        # Collect from all sources
        for key, value in self.memtable.items():
            if start_key <= key <= end_key and value is not None:
                results[key] = value
        
        for sstable in self.sstables:
            for key, value in sstable.items():
                if start_key <= key <= end_key and value is not None:
                    if key not in results:  # Newer values already in results
                        results[key] = value
        
        return sorted(results.items())


class HybridStorage:
    """
    Hybrid Storage Engine
    
    Combines B-Tree (fast reads) + LSM (fast writes)
    Used by: TiDB, CockroachDB, MyRocks
    
    Strategy:
    - Recent writes → LSM (fast ingestion)
    - Hot data → B-Tree (fast point lookups)
    - Cold data → LSM (space efficient)
    """
    
    def __init__(self):
        self.lsm = LSMStorage()     # For writes
        self.btree = BTreeStorage()  # For reads
        self.access_count = {}       # Track hot keys
        self.hot_threshold = 10      # Promote after 10 reads
        
    def put(self, key: bytes, value: bytes) -> None:
        """
        Always write to LSM (fast).
        Background job migrates hot data to B-Tree.
        """
        self.lsm.put(key, value)
    
    def get(self, key: bytes) -> Optional[bytes]:
        """
        Check B-Tree first (hot data), then LSM (recent writes).
        Track access patterns for promotion.
        """
        # Track access count
        self.access_count[key] = self.access_count.get(key, 0) + 1
        
        # Promote to B-Tree if hot
        if self.access_count[key] == self.hot_threshold:
            value = self.lsm.get(key)
            if value:
                self.btree.put(key, value)
        
        # Try B-Tree first (hot data)
        value = self.btree.get(key)
        if value is not None:
            return value
        
        # Fall back to LSM (recent writes)
        return self.lsm.get(key)
    
    def delete(self, key: bytes) -> None:
        """Delete from both engines."""
        self.btree.delete(key)
        self.lsm.delete(key)
    
    def compact(self) -> None:
        """Run LSM compaction in background."""
        self.lsm.compact()
    
    def scan_range(self, start_key: bytes, end_key: bytes) -> List[Tuple[bytes, bytes]]:
        """Merge results from both engines."""
        btree_results = self.btree.scan_range(start_key, end_key)
        lsm_results = self.lsm.scan_range(start_key, end_key)
        
        # Merge and deduplicate (LSM takes precedence)
        merged = {k: v for k, v in btree_results}
        merged.update({k: v for k, v in lsm_results})
        
        return sorted(merged.items())


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("B-Tree Storage Engine")
    print("=" * 60)
    
    btree = BTreeStorage()
    btree.put(b"user:1", b'{"name": "Alice", "age": 30}')
    btree.put(b"user:2", b'{"name": "Bob", "age": 25}')
    btree.put(b"user:3", b'{"name": "Charlie", "age": 35}')
    
    print(f"Get user:2: {btree.get(b'user:2')}")
    print(f"Range scan user:1 to user:3:")
    for key, value in btree.scan_range(b"user:1", b"user:3"):
        print(f"  {key.decode()}: {value.decode()}")
    
    print("\n" + "=" * 60)
    print("LSM Storage Engine")
    print("=" * 60)
    
    lsm = LSMStorage(memtable_size=2)
    lsm.put(b"log:1", b"event_2024_01_01")
    lsm.put(b"log:2", b"event_2024_01_02")
    lsm.put(b"log:3", b"event_2024_01_03")  # Triggers flush
    lsm.put(b"log:4", b"event_2024_01_04")
    
    print(f"Get log:2: {lsm.get(b'log:2')}")
    print(f"Number of SSTables: {len(lsm.sstables)}")
    
    lsm.compact()
    print(f"After compaction, SSTables: {len(lsm.sstables)}")
    
    print("\n" + "=" * 60)
    print("Hybrid Storage Engine")
    print("=" * 60)
    
    hybrid = HybridStorage()
    
    # Write data (goes to LSM)
    hybrid.put(b"product:1", b"Laptop")
    hybrid.put(b"product:2", b"Phone")
    
    # Read product:1 many times (becomes hot → moves to B-Tree)
    for i in range(12):
        value = hybrid.get(b"product:1")
    
    print(f"Product:1: {value}")
    print(f"Product:1 is now in B-Tree: {b'product:1' in hybrid.btree.data}")
