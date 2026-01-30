# Episode 5: B-Trees - Disk-Optimized Storage

Optimized for disk I/O with high fanout.

## Files

- `btree.py` - B-Tree and B+Tree implementations

## Key Concepts

**B-Tree Properties:**
- Order M: Each node has up to M children
- High fanout: 100+ keys per node (vs 1 in BST)
- Balanced: All leaves at same depth
- Minimizes disk seeks: log₁₀₀(1M) = 3 vs log₂(1M) = 20

**B+Tree Enhancements:**
- All data in leaves
- Leaves linked for fast range scans
- Internal nodes = routing only

## Performance

```
1 million keys, 4KB pages, 100 keys/page:

BST:   20 disk seeks (log₂ 1M)
B-Tree: 3 disk seeks (log₁₀₀ 1M)

1 seek = 10ms → 200ms vs 30ms ⚡
```

## Run

```bash
python btree.py
```

## Used By

- PostgreSQL (heap files + B-Tree indexes)
- MySQL InnoDB (clustered B+Tree)
- SQLite (B+Tree for tables and indexes)
