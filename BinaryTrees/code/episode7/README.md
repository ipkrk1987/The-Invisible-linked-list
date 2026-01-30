# Episode 7: Hybrid Storage - Best of Both Worlds

Intelligent tiering: hot data in B-Tree, cold data in LSM-Tree.

## Files

- `hybrid_storage.py` - Hybrid storage engine with automatic tiering

## Key Concepts

**Tiered Architecture:**
- **Hot tier**: B-Tree for frequently accessed data (fast reads)
- **Cold tier**: LSM-Tree for infrequently accessed data (space efficient)
- **Access tracking**: Automatic promotion/demotion between tiers

**Tier Selection Strategy:**
```python
def routing_logic(key):
    if access_count[key] >= threshold:
        return HOT_TIER  # B-Tree
    else:
        return COLD_TIER  # LSM-Tree
```

## Performance

**Mixed workload:**
```
Hot data (20% of keys, 80% of reads):
→ Served by B-Tree (3ms reads)

Cold data (80% of keys, 20% of reads):
→ Served by LSM-Tree (space efficient)

Result: Fast + space efficient!
```

## Run

```bash
python hybrid_storage.py
```

## Features

1. **Automatic Promotion** - Cold → Hot when access count exceeds threshold
2. **Background Demotion** - Hot → Cold when data becomes stale
3. **Access Tracking** - Monitor access patterns for intelligent routing
4. **Rebalancing** - Background task to optimize tier distribution

## Used By

### TiDB
- TiKV (LSM-based) for OLTP
- TiFlash (columnar) for OLAP
- Automatic routing based on query type

### CockroachDB
- Pebble engine (RocksDB fork)
- Range-based splitting
- Leaseholder caching for hot ranges

### YugabyteDB
- DocDB (RocksDB-based)
- Tablet leaders for hot data
- Followers for read replicas
