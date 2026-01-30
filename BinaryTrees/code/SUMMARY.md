# Code Repository Summary - LeetCode to Production Series

This document provides a comprehensive overview of the code implementations for each episode in the Binary Trees series.

## Quick Navigation

- [Episode 4: BST & AVL Trees](#episode-4-bst--avl-trees) - In-memory foundations
- [Episode 5: B-Trees](#episode-5-b-trees) - Disk-optimized storage
- [Episode 6: LSM-Trees](#episode-6-lsm-trees) - Write-optimized storage
- [Episode 7: Hybrid Storage](#episode-7-hybrid-storage) - Adaptive tiering
- [Episode 8: Complete Database](#episode-8-complete-database) - Full architecture
- [Testing & Validation](#testing--validation) - How to run and verify

---

## Episode 4: BST & AVL Trees

**Directory**: `episode4/`

**Files**:
- `bst_avl.py` (290 lines) - Binary Search Tree and AVL Tree implementations
- `README.md` - Documentation and usage guide

**What It Contains**:
- `BSTNode`, `BinarySearchTree` - Unbalanced binary search tree
- `AVLNode`, `AVLTree` - Self-balancing tree with rotations
- Operations: insert, search, delete, traversal
- Balance factor calculation
- Left/right rotations

**Key Insight**:
```
BST: O(n) worst case when inserting sorted data
AVL: O(log n) guaranteed through automatic balancing

Example with 15 nodes:
BST height: 7 (degenerates to linked list)
AVL height: 3 (stays balanced)
```

**Run It**:
```bash
cd episode4
python bst_avl.py
```

**Real-World Connection**: This shows WHY databases don't use simple BSTs. They need guaranteed O(log n), leading us to B-Trees.

---

## Episode 5: B-Trees

**Directory**: `episode5/`

**Files**:
- `btree.py` (330 lines) - B-Tree and B+Tree implementations
- `README.md` - Documentation with performance analysis

**What It Contains**:
- `BTreeNode`, `BTree` - Multi-key nodes with high fanout
- `BPlusTreeNode` - Linked leaves for range scans
- Operations: insert, search, split, range_scan
- Order customization (default 5, production uses 100-1000)

**Performance Math**:
```
1 million keys, fanout = 100:

BST: log₂(1M) = 20 disk seeks
B-Tree: log₁₀₀(1M) = 3 disk seeks

At 10ms per seek:
BST: 200ms
B-Tree: 30ms ⚡ 6.7× faster!
```

**Run It**:
```bash
cd episode5
python btree.py
```

**Used By**: PostgreSQL, MySQL InnoDB, SQLite

---

## Episode 6: LSM-Trees

**Directory**: `episode6/`

**Files**:
- `lsm_tree.py` (310 lines) - Complete LSM-Tree with compaction
- `README.md` - Documentation with compaction analysis

**What It Contains**:
- `MemTable` - In-memory write buffer (sorted dict)
- `SSTable` - Immutable sorted string tables
- `BloomFilter` - Probabilistic "definitely not here" checks
- `LSMTree` - Orchestrates writes, reads, flushes, compaction

**Write vs Read Tradeoff**:
```
Writes:
B-Tree: 50 writes/sec (random disk I/O)
LSM: 10,000+ writes/sec (sequential I/O) ⚡ 200× faster!

Reads:
B-Tree: 1 lookup (direct)
LSM: N lookups where N = # of SSTables (read amplification)
```

**Compaction = LeetCode #23**: Merge K Sorted Lists in production!

**Run It**:
```bash
cd episode6
python lsm_tree.py
```

**Used By**: Cassandra, RocksDB, LevelDB, HBase, ScyllaDB

---

## Episode 7: Hybrid Storage

**Directory**: `episode7/`

**Files**:
- `hybrid_storage.py` (290 lines) - Tiered storage with access tracking
- `README.md` - Documentation with tiering strategies

**What It Contains**:
- `AccessTracker` - Monitors access patterns (hot vs cold)
- `SimpleBTree` - Hot tier (read-optimized)
- `SimpleLSM` - Cold tier (space-efficient)
- `HybridStorage` - Automatic promotion/demotion between tiers

**Tiering Strategy**:
```
Hot data (20% of keys, 80% of accesses):
→ B-Tree tier (3ms reads)

Cold data (80% of keys, 20% of accesses):
→ LSM-Tree tier (space efficient)

Result: Fast reads + efficient storage!
```

**Run It**:
```bash
cd episode7
python hybrid_storage.py
```

**Used By**: TiDB (TiKV+TiFlash), CockroachDB (range-based), YugabyteDB (DocDB)

---

## Episode 8: Complete Database

**Directory**: `episode8/`

**Files**:
- `storage_engine.py` (280 lines) - B-Tree, LSM, Hybrid engines
- `free_list.py` (140 lines) - Page recycling and space management
- `buffer_pool.py` (190 lines) - LRU caching layer
- `wal.py` (230 lines) - Write-Ahead Log for durability
- `transaction_manager.py` (280 lines) - MVCC, locks, isolation
- `examples/basic_usage.py` - CRUD demonstrations
- `examples/transactions.py` - Transaction scenarios

**5-Layer Architecture**:
```
Layer 5: Query Processor (SQL → Operations)
         ↓
Layer 4: Transaction Manager (ACID guarantees)
         ↓
Layer 3: Write-Ahead Log (Durability)
         ↓
Layer 2: Buffer Pool (Memory caching)
         ↓
Layer 1: Storage Engine (Disk I/O)
```

**What Each Component Does**:

| Component | Purpose | Key Technique |
|-----------|---------|---------------|
| Storage Engine | Persist data | B-Tree, LSM, or Hybrid |
| Free List | Reclaim space | Page recycling, compaction |
| Buffer Pool | Cache hot pages | LRU eviction |
| WAL | Survive crashes | REDO/UNDO logging |
| Transactions | ACID guarantees | MVCC + 2PL |

**Run It**:
```bash
cd episode8
python examples/basic_usage.py
python examples/transactions.py
```

**Real-World Example**: PostgreSQL uses all 5 layers!

---

## Testing & Validation

### Individual Episodes

Each episode can be tested independently:

```bash
# Episode 4
cd episode4
python bst_avl.py
# Should show: BST height=7, AVL height=3

# Episode 5
cd episode5
python btree.py
# Should show: 10 inserts, 3 searches, range scan [5,15]

# Episode 6
cd episode6
python lsm_tree.py
# Should show: 3 SSTables → 1 after compaction

# Episode 7
cd episode7
python hybrid_storage.py
# Should show: 3 promotions to hot tier

# Episode 8
cd episode8
python examples/basic_usage.py
python examples/transactions.py
# Should show: CRUD operations and transaction scenarios
```

### Expected Outcomes

**Episode 4**:
- ✅ BST degenerates with sorted input
- ✅ AVL maintains balance through rotations

**Episode 5**:
- ✅ B-Tree handles multiple keys per node
- ✅ Range scans return sorted results

**Episode 6**:
- ✅ Memtable flushes to SSTables when full
- ✅ Compaction merges multiple SSTables into one
- ✅ Bloom filters reduce unnecessary lookups

**Episode 7**:
- ✅ Hot keys automatically promoted to B-Tree tier
- ✅ Cold keys stay in LSM-Tree tier
- ✅ Access tracking identifies hot vs cold data

**Episode 8**:
- ✅ All storage engines work (B-Tree, LSM, Hybrid)
- ✅ Buffer pool caches hot pages
- ✅ WAL enables crash recovery
- ✅ Transactions provide ACID guarantees

---

## Code Statistics

| Episode | Lines of Code | Key Classes | Complexity |
|---------|---------------|-------------|------------|
| Episode 4 | 290 | 4 (BST, AVL) | ⭐⭐ |
| Episode 5 | 330 | 3 (BTree, BPlusTree) | ⭐⭐⭐ |
| Episode 6 | 310 | 4 (MemTable, SSTable, Bloom, LSM) | ⭐⭐⭐⭐ |
| Episode 7 | 290 | 4 (Tracker, BTree, LSM, Hybrid) | ⭐⭐⭐⭐ |
| Episode 8 | 1,120 | 10+ (complete system) | ⭐⭐⭐⭐⭐ |
| **Total** | **2,340** | **25+** | - |

---

## Progression Summary

The series follows a clear learning progression:

```
Episode 4: "Trees are too simple for databases"
    ↓
Episode 5: "B-Trees minimize disk seeks"
    ↓
Episode 6: "LSM-Trees optimize writes"
    ↓
Episode 7: "Hybrid combines both approaches"
    ↓
Episode 8: "Complete database needs 5 layers"
```

Each episode answers a limitation of the previous one:

1. **BST Problem**: O(n) worst case → **AVL Solution**: Rotations
2. **AVL Problem**: 1 key per node = many disk seeks → **B-Tree Solution**: 100+ keys per node
3. **B-Tree Problem**: Slow random writes → **LSM Solution**: Append-only writes
4. **LSM Problem**: Slow reads → **Hybrid Solution**: Hot/cold tiering
5. **Hybrid Problem**: Missing ACID, durability, queries → **Full DB Solution**: 5-layer architecture

---

## Next Steps

1. **Run All Demos**: Execute each episode to see the concepts in action
2. **Read the Presentations**: Each episode has a corresponding HTML presentation
3. **Modify the Code**: Try changing parameters (B-Tree order, LSM memtable size, etc.)
4. **Benchmark**: Add timing code to compare performance
5. **Extend**: Add new features (e.g., compression, replication)

---

## References

- **Presentations**: Located in `../html/` directory
- **Episode 8 Markdown**: `../episode8.md` (2406 lines)
- **Book**: "Build Your Own Database From Scratch" - https://build-your-own.org/database/
- **Source Code**: PostgreSQL, RocksDB, TiDB on GitHub

---

**License**: MIT - For educational purposes

**Status**: ✅ All implementations working and tested
