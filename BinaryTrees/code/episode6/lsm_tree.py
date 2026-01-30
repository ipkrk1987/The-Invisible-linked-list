"""
Episode 6: LSM-Trees - Write-Optimized Storage
Append-only = 100× faster writes!
"""

import heapq
from typing import List, Tuple, Optional, Any, Dict


class MemTable:
    """
    In-memory write buffer (SkipList in production).
    Sorted structure for fast inserts and scans.
    """
    
    def __init__(self, max_size: int = 1000):
        self.data: Dict[bytes, bytes] = {}
        self.max_size = max_size
    
    def put(self, key: bytes, value: bytes) -> None:
        """Insert key-value pair."""
        self.data[key] = value
    
    def get(self, key: bytes) -> Optional[bytes]:
        """Get value for key."""
        return self.data.get(key)
    
    def is_full(self) -> bool:
        """Check if memtable needs flushing."""
        return len(self.data) >= self.max_size
    
    def to_sstable(self) -> 'SSTable':
        """Flush to immutable SSTable."""
        sorted_items = sorted(self.data.items())
        return SSTable(sorted_items)


class SSTable:
    """
    Sorted String Table - Immutable on-disk file.
    Once written, never modified (append-only).
    """
    
    def __init__(self, data: List[Tuple[bytes, bytes]]):
        self.data = dict(data)  # In production: write to disk file
        self.keys = sorted(self.data.keys())  # For binary search
    
    def get(self, key: bytes) -> Optional[bytes]:
        """Get value (binary search)."""
        return self.data.get(key)
    
    def range_scan(self, start_key: bytes, end_key: bytes) -> List[Tuple[bytes, bytes]]:
        """Scan range of keys."""
        results = []
        for key in self.keys:
            if start_key <= key <= end_key:
                results.append((key, self.data[key]))
        return results


class BloomFilter:
    """
    Probabilistic data structure: "Key definitely NOT here!"
    
    False positive rate: ~1% with 10 bits per key
    Saves 99% of unnecessary SSTable lookups
    """
    
    def __init__(self, size: int = 1000):
        self.size = size
        self.bits = [False] * size
    
    def add(self, key: bytes) -> None:
        """Add key to filter."""
        for i in self._hash_functions(key):
            self.bits[i] = True
    
    def might_contain(self, key: bytes) -> bool:
        """Check if key MIGHT be in set."""
        return all(self.bits[i] for i in self._hash_functions(key))
    
    def _hash_functions(self, key: bytes) -> List[int]:
        """Multiple hash functions for Bloom filter."""
        # Simplified: In production use MurmurHash, etc.
        h1 = hash(key) % self.size
        h2 = hash(key[::-1]) % self.size
        h3 = (hash(key) * 31) % self.size
        return [h1, h2, h3]


class LSMTree:
    """
    Log-Structured Merge Tree
    
    Write path: O(1)
    1. Write to memtable (in-memory)
    2. When full, flush to SSTable (sequential write!)
    
    Read path: O(k) where k = number of SSTables
    1. Check memtable
    2. Check SSTable 1 (most recent)
    3. Check SSTable 2
    ...
    N. Background compaction merges SSTables
    
    Used by: Cassandra, RocksDB, LevelDB, HBase
    """
    
    def __init__(self, memtable_size: int = 100):
        self.memtable = MemTable(max_size=memtable_size)
        self.sstables: List[SSTable] = []
        self.bloom_filters: List[BloomFilter] = []
        
        self.write_count = 0
        self.read_count = 0
    
    def put(self, key: bytes, value: bytes) -> None:
        """
        Write to LSM-Tree (blazing fast!).
        
        B-Tree: 20ms per write (disk read + write)
        LSM-Tree: 0.1ms per write (memory write)
        
        100-200× faster writes!
        """
        # Write to memtable (in-memory, instant!)
        self.memtable.put(key, value)
        self.write_count += 1
        
        # Flush if full
        if self.memtable.is_full():
            self._flush_memtable()
    
    def get(self, key: bytes) -> Optional[bytes]:
        """
        Read from LSM-Tree (slower than B-Tree).
        
        Must check:
        1. Memtable (fast)
        2. All SSTables (potentially slow)
        
        Optimization: Bloom filters skip SSTables that don't contain key
        """
        self.read_count += 1
        
        # Check memtable first
        value = self.memtable.get(key)
        if value is not None:
            return value
        
        # Check SSTables (newest first)
        for sstable, bloom in zip(reversed(self.sstables), reversed(self.bloom_filters)):
            # Bloom filter: Skip if key definitely not here
            if not bloom.might_contain(key):
                continue
            
            value = sstable.get(key)
            if value is not None:
                return value
        
        return None
    
    def delete(self, key: bytes) -> None:
        """
        Delete = write tombstone marker.
        Actual deletion during compaction.
        """
        self.memtable.put(key, b'__TOMBSTONE__')
    
    def _flush_memtable(self) -> None:
        """
        Flush memtable to immutable SSTable.
        
        Steps:
        1. Convert memtable → SSTable
        2. Write to disk (sequential write - fast!)
        3. Build Bloom filter
        4. Clear memtable
        """
        print(f"📝 Flushing memtable ({len(self.memtable.data)} entries) to SSTable...")
        
        # Create SSTable
        sstable = self.memtable.to_sstable()
        self.sstables.append(sstable)
        
        # Build Bloom filter
        bloom = BloomFilter(size=len(sstable.data) * 10)
        for key in sstable.keys:
            bloom.add(key)
        self.bloom_filters.append(bloom)
        
        # Clear memtable
        self.memtable = MemTable(max_size=self.memtable.max_size)
        
        print(f"✅ SSTable created. Total SSTables: {len(self.sstables)}")
    
    def compact(self) -> None:
        """
        Compaction: Merge SSTables (LeetCode #23 in production!).
        
        This is literally "Merge K Sorted Lists"
        
        Steps:
        1. Take all SSTables
        2. Merge using k-way merge (min heap)
        3. Remove duplicates (keep newest)
        4. Remove tombstones
        5. Write merged SSTable
        """
        if len(self.sstables) < 2:
            return
        
        print(f"\n🔄 Compacting {len(self.sstables)} SSTables...")
        
        # K-way merge using heap
        merged_data = {}
        
        # Collect all entries (newest wins)
        for sstable in reversed(self.sstables):
            for key, value in sstable.data.items():
                if key not in merged_data and value != b'__TOMBSTONE__':
                    merged_data[key] = value
        
        # Create one merged SSTable
        items = sorted(merged_data.items())
        compacted_sstable = SSTable(items)
        
        # Build new Bloom filter
        bloom = BloomFilter(size=len(items) * 10)
        for key, _ in items:
            bloom.add(key)
        
        # Replace all SSTables with one
        self.sstables = [compacted_sstable]
        self.bloom_filters = [bloom]
        
        print(f"✅ Compaction complete! Merged into 1 SSTable ({len(items)} keys)")


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("Episode 6: LSM-Trees - Write-Optimized Storage")
    print("=" * 70)
    
    lsm = LSMTree(memtable_size=5)
    
    print("\n📝 Writing 15 keys (will trigger flushes)...")
    for i in range(15):
        key = f"key:{i:03d}".encode()
        value = f"value_{i}".encode()
        lsm.put(key, value)
    
    print(f"\n📊 LSM-Tree state:")
    print(f"   Writes: {lsm.write_count}")
    print(f"   SSTables: {len(lsm.sstables)}")
    print(f"   Memtable size: {len(lsm.memtable.data)}")
    
    print(f"\n🔍 Reading keys:")
    for i in [0, 7, 14]:
        key = f"key:{i:03d}".encode()
        value = lsm.get(key)
        print(f"   {key.decode()}: {value.decode() if value else 'Not found'}")
    
    print(f"\n   Total reads: {lsm.read_count}")
    
    print(f"\n🔄 Running compaction...")
    lsm.compact()
    
    print(f"\n📊 After compaction:")
    print(f"   SSTables: {len(lsm.sstables)}")
    
    print("\n💡 LSM-Tree Advantages:")
    print("   ✅ Write throughput: 10,000+ writes/sec (vs 50 for B-Tree)")
    print("   ✅ Sequential I/O: Append-only writes")
    print("   ✅ Space efficient: Compaction removes duplicates")
    print("\n⚠️  LSM-Tree Trade-offs:")
    print("   ❌ Read amplification: Check multiple SSTables")
    print("   ❌ Write amplification: Compaction rewrites data")
    
    print("\n✅ Used by Cassandra, RocksDB, LevelDB!")
