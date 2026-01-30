# Database Implementation Code - Episode 8

This directory contains all the working code examples from Episode 8: "Building a Database - The Complete Architecture"

## Structure

```
code/
├── README.md                    # This file
├── storage_engine.py           # Layer 1: B-Tree, LSM, Hybrid storage engines
├── free_list.py                # Space management and page recycling
├── buffer_pool.py              # Layer 2: Memory management with LRU cache
├── wal.py                      # Layer 3: Write-Ahead Log for durability
├── transaction_manager.py      # Layer 4: MVCC, locks, isolation
├── table.py                    # Tables, schemas, row encoding
├── indexes.py                  # Secondary indexes, composite indexes
├── query_processor.py          # Layer 5: SQL parser, optimizer, executor
├── minidb.py                   # Complete working database (~500 lines)
└── examples/
    ├── basic_usage.py          # Simple CRUD operations
    ├── transactions.py         # Transaction examples
    ├── indexing.py             # Index creation and queries
    └── performance_tests.py    # Benchmarks and comparisons
```

## Quick Start

```python
from minidb import MiniDB

# Create database
db = MiniDB()

# Create table
db.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER
    )
""")

# Insert data
db.execute("INSERT INTO users VALUES (1, 'Alice', 30)")
db.execute("INSERT INTO users VALUES (2, 'Bob', 25)")

# Query
results = db.execute("SELECT * FROM users WHERE age > 25")
print(results)  # [{'id': 1, 'name': 'Alice', 'age': 30}]
```

## Components

### Layer 1: Storage Engine
- **BTreeStorage**: Disk-optimized, fast reads (PostgreSQL style)
- **LSMStorage**: Write-optimized, append-only (Cassandra style)
- **HybridStorage**: Best of both worlds (TiDB style)

### Layer 2: Buffer Pool
- LRU caching for hot pages
- Dirty page tracking
- Eviction policies

### Layer 3: Write-Ahead Log (WAL)
- Durability guarantees
- Crash recovery
- Checkpoint mechanism

### Layer 4: Transaction Manager
- MVCC (Multi-Version Concurrency Control)
- Lock management (shared/exclusive)
- Isolation levels

### Layer 5: Query Processor
- SQL lexer and parser
- Query optimization
- Execution engine

## Running Tests

```bash
# From the code directory
python -m pytest tests/

# Or run individual examples
python examples/basic_usage.py
python examples/transactions.py
python examples/performance_tests.py
```

## Learning Path

1. Start with `storage_engine.py` - understand the foundation
2. Read `buffer_pool.py` - see how caching works
3. Study `wal.py` - learn about durability
4. Explore `transaction_manager.py` - understand ACID
5. Dive into `query_processor.py` - see SQL → operations
6. Run `examples/` - practical usage patterns
7. Finally, `minidb.py` - see how it all integrates

## Key Concepts Demonstrated

- **Data Structures**: B-Trees, LSM-Trees, Hash tables
- **Algorithms**: Binary search, LRU eviction, MVCC versioning
- **Systems**: Crash recovery, concurrency control, query optimization
- **Trade-offs**: Read vs write performance, consistency vs availability

## Production Considerations

This is educational code. For production, you'd need:
- ✅ Comprehensive error handling
- ✅ Extensive testing (unit, integration, stress)
- ✅ Monitoring and metrics
- ✅ Backup and restore
- ✅ Replication for high availability
- ✅ Performance profiling and optimization
- ✅ Security (authentication, authorization, encryption)

## References

- Episode 8 presentation markdown
- "Build Your Own Database From Scratch" by James Smith
- "Database Internals" by Alex Petrov
- PostgreSQL, Cassandra, TiDB source code

## License

MIT License - Educational purposes
