# Episode 6: LSM-Trees - Write-Optimized Storage

Append-only architecture for extreme write performance.

## Files

- `lsm_tree.py` - LSM-Tree with memtable, SSTables, Bloom filters, compaction

## Key Concepts

**LSM-Tree Components:**
1. **MemTable** - In-memory write buffer (SkipList)
2. **SSTable** - Immutable sorted files on disk
3. **Bloom Filter** - Probabilistic "not here!" check
4. **Compaction** - Merge SSTables (LeetCode #23!)

**Write Path: O(1)**
```
Write → MemTable (RAM, 0.1ms)
When full → Flush to SSTable (sequential disk write)
```

**Read Path: O(k) where k = SSTables**
```
Check MemTable
Check SSTable 1 (with Bloom filter)
Check SSTable 2 (with Bloom filter)
...
```

## Performance

```
Writes:
B-Tree: 50 writes/sec (random I/O)
LSM: 10,000+ writes/sec (sequential I/O)

100-200× faster writes!

Trade-off:
- Reads slower (check multiple SSTables)
- Background compaction needed
```

## Run

```bash
python lsm_tree.py
```

## Compaction = LeetCode #23

Merge K Sorted Lists in production!

```python
def compact_sstables(sstables):
    # K-way merge using min heap
    # Keep newest value for duplicates
    # Remove tombstones
    return merged_sstable
```

## Used By

- Cassandra (write-heavy workloads)
- RocksDB (embedded, Facebook)
- LevelDB (Google)
- HBase (Hadoop ecosystem)
- ScyllaDB
