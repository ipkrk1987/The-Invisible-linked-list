# Episode 2.8: Building a Database - The Complete Architecture

**Season 2 Capstone: From Data Structures to Production Systems**

---

## Episode Overview

**Goal**: Show how the data structures we learned (BST, AVL, B-Tree, LSM-Tree) become the foundation of complete database systems. Explain the 5-layer architecture and how choosing different structures creates different database types (PostgreSQL vs Cassandra vs TiDB).

**Arc**: Foundation → Layers → Choices → Complete Systems → Build Your Own

---

## ACT 1: THE FOUNDATION 🏗️

### Slide 1: Title
**🏗️ Building a Database**
**The Complete Architecture**

*From LeetCode Data Structures to Production Database Systems*

Season 2 Capstone • Episode 2.8

---

### Slide 2: The Journey So Far

**What We've Built This Season**

Episode 2.1-2.3: **Binary Search → SSTables**
- Foundation: Sorted data on disk
- Core primitive: Fast lookups in sorted files

Episode 2.4: **BST → AVL Trees**  
- In-memory dynamic structures
- Self-balancing for consistent performance

Episode 2.5: **B-Trees**
- Disk-optimized structure (fat nodes)
- PostgreSQL/MySQL storage engine

Episode 2.6: **LSM-Trees**
- Write-optimized structure (append-only)
- Cassandra/RocksDB storage engine

Episode 2.7: **Hybrid Engines**
- Combining multiple engines
- TiDB, CockroachDB approach

**TODAY**: How these pieces fit together to build a complete database! 🎯

---

### Slide 3: The Big Question

**🤔 "I know how to implement a B-Tree... but how does that become PostgreSQL?"**

**The Gap:**
- ✅ We can code a B-Tree in 100 lines
- ✅ We understand O(log n) lookups
- ❌ **How does this become a production database that handles:**
  - Thousands of concurrent users
  - Crash recovery
  - ACID transactions
  - SQL queries
  - Terabytes of data

**Today's Answer**: A database is a **5-layer architecture** where your data structure choice at Layer 1 determines everything else!

---

## ACT 2: THE 5 LAYERS 🏛️

### Slide 4: Database Architecture - The Complete Stack

**The 5 Layers of Every Database**

```
┌─────────────────────────────────────────┐
│  LAYER 5: Query Processor               │  ← SQL → Physical Operations
├─────────────────────────────────────────┤
│  LAYER 4: Transaction Manager           │  ← ACID, Locks, Isolation
├─────────────────────────────────────────┤
│  LAYER 3: Write-Ahead Log (WAL)         │  ← Durability, Recovery
├─────────────────────────────────────────┤
│  LAYER 2: Buffer Pool / Cache Manager   │  ← Memory Management
├─────────────────────────────────────────┤
│  LAYER 1: Storage Engine                │  ← B-Tree OR LSM OR Hybrid
└─────────────────────────────────────────┘
           ↓
       Disk I/O
```

**Key Insight**: Layer 1 choice (B-Tree vs LSM) changes ALL the other layers!

---

### Slide 5: Layer 1 - Storage Engine (The Foundation)

**🔧 Layer 1: Storage Engine - "How do we physically organize data on disk?"**

**This is where you choose your data structure!**

**Option A: B-Tree Storage Engine**
```python
# DESIGN: Read-optimized with in-place updates
class BTreeStorageEngine:
    
    def get(key):
        # Navigate tree: log_M(N) disk seeks
        page = load_page(root_page_id)
        while not page.is_leaf:
            # Binary search within node to find child
            child_idx = find_child(key, page)
            page = load_page(page.children[child_idx])  # Disk seek
        return find_in_leaf(key, page)
    
    def put(key, value):
        # Read-Modify-Write pattern
        page = find_leaf_page(key)     # 💥 Random disk READ
        insert_into_page(page, key, value)
        write_page_to_disk(page)       # 💥 Random disk WRITE
        
        if page.is_full():
            split_page(page)           # May cascade up tree
```

*👉 Working implementation: [code/episode5/btree.py](../code/episode5/btree.py)*

**Characteristics:**
- ✅ Fast reads: O(log n) seeks
- ❌ Slow writes: Read-modify-write cycle
- **Used by**: PostgreSQL, MySQL InnoDB, SQLite

---

**Option B: LSM-Tree Storage Engine**
```python
# DESIGN: Write-optimized with append-only files
class LSMStorageEngine:
    memtable = {}           # In-memory buffer (sorted)
    sstables = []           # Immutable disk files
    
    def put(key, value):
        # WRITE PATH: No disk reads needed!
        append_to_wal(key, value)      # ⚡ Sequential append
        memtable[key] = value          # ⚡ Memory write only
        
        if memtable.is_full():
            flush_to_sstable()         # Background async
        return  # Immediate response!
    
    def get(key):
        # READ PATH: Check multiple levels (read amplification)
        if key in memtable:
            return memtable[key]       # Fast: in memory
        
        for sstable in sstables (newest → oldest):
            if bloom_filter.might_contain(key):  # Skip 99% of lookups
                if value = sstable.get(key):
                    return value       # Found!
        return NOT_FOUND
    
    # Background compaction merges SSTables
    def compact():
        merge_sorted_sstables()        # LeetCode #23 at scale!
        remove_duplicates()
        update_bloom_filters()
```

*👉 Working implementation: [code/episode6/lsm_tree.py](../code/episode6/lsm_tree.py)*

**Characteristics:**
- ✅ Fast writes: Append-only, no reads
- ❌ Slower reads: Check multiple files
- **Used by**: Cassandra, RocksDB, ScyllaDB, HBase

---

**Option C: Hybrid Storage Engine**
```python
# DESIGN: Adaptive tiering based on access patterns
class HybridStorageEngine:
    hot_tier = LSMStorage()      # Recent data, fast writes
    cold_tier = BTreeStorage()   # Older data, fast reads
    
    def put(key, value):
        # WRITE: Always to LSM tier (optimized for writes)
        hot_tier.put(key, value)   # ⚡ Fast append
        track_access_pattern(key)
    
    def get(key):
        # READ: Check hot tier first, then cold
        if value = hot_tier.get(key):
            return value           # Recent data
        
        value = cold_tier.get(key) # Older data
        
        if is_frequently_accessed(key):
            promote_to_hot(key)    # Adaptive!
        return value
    
    # Background migration strategy
    def rebalance():
        for each key in hot_tier:
            if age(key) > threshold AND not_recently_accessed(key):
                migrate_to_cold_tier(key)  # Move to B-Tree
        
        for each key in cold_tier:
            if access_frequency(key) > threshold:
                promote_to_hot_tier(key)   # Move to LSM
```

*👉 Working implementation: [code/episode7/hybrid_storage.py](../code/episode7/hybrid_storage.py)*

**Characteristics:**
- ✅ Fast writes (LSM) + Fast reads (B-Tree)
- ⚠️ More complexity, background migration
- **Used by**: TiDB, CockroachDB, MyRocks (Facebook)

---

### Slide 5.5: Space Management - Free List (The Recycler)

**♻️ Free List: "Never waste disk space!"**

**The Problem:**
```python
# Delete 1 million rows from B-Tree
for i in range(1_000_000):
    btree.delete(key)

# Disk space: Still 10GB! 😱
# Pages are marked "deleted" but NOT reused
# Database grows forever even with deletions
```

**The Solution: Free List**
```python
# DESIGN: Track and reuse freed pages (like malloc/free)
class FreeList:
    free_pages = Stack()      # Reusable page IDs
    next_new_page = 0         # High water mark
    
    def allocate_page():
        # Need a page for new data
        if free_pages.is_empty():
            # No recycled pages available
            return next_new_page++     # Extend file
        else:
            # Reuse deleted page ♻️
            return free_pages.pop()    # Recycled!
    
    def free_page(page_id):
        # Mark page as deleted (don't erase)
        free_pages.push(page_id)       # Available for reuse
        # Actual data still on disk until overwritten
    
    def compact():
        # Optional: Defragmentation
        # 1. Identify live data in fragmented regions
        # 2. Copy to consecutive pages
        # 3. Update all pointers/indexes
        # 4. Free old pages
        #
        # Trade-off: CPU + I/O now vs disk space savings
```

**Design Decisions:**

| Approach | When to Use | Example |
|----------|-------------|----------|
| **Lazy recycling** | High write throughput | Cassandra: Tombstones until compaction |
| **Eager vacuum** | Space-constrained | PostgreSQL: VACUUM FULL |
| **Background compaction** | Balanced | RocksDB: Level-based compaction |

*👉 Working implementation: [code/episode8/free_list.py](../code/episode8/free_list.py)*

**Production Considerations:**

**1. Free List Metadata (where to store it?):**
```python
# Option A: Store in special page (page 0)
class FreeListPage:
    magic = b"FREEL"  # 5 bytes
    count = 0          # 4 bytes: number of free pages
    pages = []         # Array of page IDs

# Option B: Linked list of free pages
class FreePage:
    next_free_page_id = 0  # First 4 bytes of deleted page
    # Rest of page unused

# PostgreSQL uses visibility map + FSM (Free Space Map)
# SQLite uses freelist trunk pages + leaf pages
```

**2. Fragmentation Challenge:**
```
Database grows: 100GB → 200GB → 50GB (after deletes)

Without compaction:         With compaction:
[XXXX____XXX___XX____]     [XXXXXXXXXXX_____________]
40% disk space wasted       All data packed efficiently

PostgreSQL: VACUUM FULL (locks table, rewrites)
Cassandra: Automatic compaction (background, no locks)
```

**3. Crash Safety:**
```python
# WAL entry for page allocation
class AllocatePageLogEntry:
    page_id = 12345
    txn_id = 999
    # During recovery: Remove from free list

# WAL entry for page deletion  
class FreePageLogEntry:
    page_id = 12345
    txn_id = 999
    # During recovery: Add back to free list
```

**Real-World Impact:**
- **PostgreSQL**: Without VACUUM, deleted rows = "dead tuples" = bloat
  - War story: 100GB table with 90GB dead tuples → VACUUM reclaimed 85GB!
- **Cassandra**: Tombstones (deletion markers) until compaction
  - Recommendation: `gc_grace_seconds = 864000` (10 days)
- **SQLite**: `PRAGMA auto_vacuum = FULL;` (automatic space reclamation)

**Why This Matters:**
✅ Prevents database from growing forever  
✅ Reuses disk space efficiently  
✅ Critical for update-heavy workloads (e.g., user profiles, counters)  

---

### Slide 6: Layer 2 - Buffer Pool (Memory Management)

**🧠 Layer 2: Buffer Pool - "Keep hot data in RAM!"**

**Why needed**: Disk is 100,000× slower than RAM. Cache the most-used pages.

```python
# DESIGN: Cache hot pages in RAM (LRU eviction policy)
class BufferPool:
    cache = HashMap()         # page_id → page_data
    lru_list = DoublyLinkedList()  # LeetCode #146!
    dirty_pages = Set()       # Modified pages
    capacity = SIZE_IN_PAGES
    
    def get_page(page_id):
        if page_id in cache:
            # Cache HIT: 100× faster than disk
            lru_list.move_to_front(page_id)  # Mark as recently used
            return cache[page_id]            # ⚡ ~100 nanoseconds
        
        # Cache MISS: Must read from disk
        page = read_from_disk(page_id)       # 💥 ~10 milliseconds
        
        # Evict if cache full (LRU policy)
        if cache.is_full():
            victim = lru_list.get_least_recently_used()
            
            if victim in dirty_pages:
                write_to_disk(victim)        # Flush before eviction
                dirty_pages.remove(victim)
            
            cache.remove(victim)
        
        # Add to cache
        cache[page_id] = page
        lru_list.add_to_front(page_id)
        return page
    
    def mark_dirty(page_id):
        # Page modified in memory, needs write-back
        dirty_pages.add(page_id)
    
    def checkpoint():
        # Flush all dirty pages (for durability)
        for page_id in dirty_pages:
            write_to_disk(cache[page_id])
        dirty_pages.clear()
```

**Design Insights:**
- **LRU = LeetCode #146** (Implement LRU Cache) in production!
- **Dirty pages** = Write-back cache (delay writes for performance)
- **Cache hit ratio** = Critical metric (aim for >95%)

*👉 Working implementation: [code/episode8/buffer_pool.py](../code/episode8/buffer_pool.py)*

**Production Configuration:**
```sql
-- PostgreSQL
SET shared_buffers = '8GB';           -- 25% of RAM
SET effective_cache_size = '24GB';    -- Total cache estimate

-- MySQL InnoDB  
SET innodb_buffer_pool_size = 8589934592;  -- 8GB
SET innodb_buffer_pool_instances = 8;      -- Parallel
```

**Key Metrics:**
- Cache hit ratio: >95% is good, <90% means undersized buffer
- Dirty page ratio: High = many pending writes
- Eviction rate: High = cache thrashing

---

### Slide 7: Layer 3 - Write-Ahead Log (Durability)

**📝 Layer 3: WAL - "Never lose committed data, even if we crash!"**

**The Durability Promise:**
```
User: "INSERT INTO users VALUES (123, 'Alice')"
Database: "OK, committed!" ✓
*CRASH* 💥
Database restarts: Alice must still exist!
```

**How WAL Works:**
```python
# DESIGN: Log-structured durability (append-only)
class WriteAheadLog:
    log_file = AppendOnlyFile()
    lsn = 0  # Log Sequence Number (never resets)
    
    def append(txn_id, operation, key, value):
        # CRITICAL: Write to log BEFORE modifying data!
        entry = {
            'lsn': lsn++,
            'txn_id': txn_id,
            'operation': operation,  # INSERT/UPDATE/DELETE
            'key': key,
            'value': value
        }
        
        # Append to log file
        log_file.write(serialize(entry))
        log_file.flush()              # OS buffer → disk cache
        fsync(log_file)               # 💥 Force physical write!
        
        # Now safe to return to user
        return lsn
    
    def recover(storage_engine):
        # Called after crash: Replay uncommitted work
        print("🔄 Crash recovery: Replaying WAL...")
        
        for entry in read_log_file():
            if entry.operation == 'INSERT':
                storage_engine.put(entry.key, entry.value)
            elif entry.operation == 'DELETE':
                storage_engine.delete(entry.key)
            # Idempotent: Safe to replay multiple times
        
        print(f"✅ Recovered to LSN {lsn}")
```

**Design Decisions:**

| Technique | Trade-off | Used By |
|-----------|-----------|----------|
| **fsync() every write** | Slow writes, max durability | PostgreSQL (default) |
| **Group commit** | Batch commits, fast | MySQL InnoDB |
| **Async commit** | Risk losing <1s of data | PostgreSQL (async mode) |

*👉 Working implementation: [code/episode8/wal.py](../code/episode8/wal.py)*

**Write Path with WAL:**
```python
# DESIGN: Write-Ahead = Durability before acknowledgment
def execute_insert(key, value, txn_id):
    
    # PHASE 1: Ensure durability (write to log)
    lsn = wal.append(txn_id, 'INSERT', key, value)  # ⚡ Sequential
    # Log is now on disk! Safe from crash
    
    # PHASE 2: Acknowledge to user
    return "OK" to client  # Transaction committed!
    
    # PHASE 3: Apply to in-memory structures (async)
    storage_engine.put(key, value)    # Update B-Tree/LSM
    buffer_pool.mark_dirty(page_id)   # Track modification
    
    # PHASE 4: Eventually flush to disk (lazy)
    # Happens during checkpoint or cache eviction
    # If crash before flush: WAL replay restores it!
```

**Why This Works:**
1. WAL is **sequential** (fast ~10ms) vs random writes (slow ~100ms)
2. WAL is **small** (just the changes) vs full pages (4KB)
3. Crash recovery: Just replay WAL entries (idempotent operations)

**Key Properties:**
- **Sequential writes**: WAL is append-only (fast!)
- **Group commit**: Batch multiple transactions' log writes
- **Checkpoint**: Periodically flush storage engine + truncate old WAL

---

### Slide 8: Layer 4 - Transaction Manager (ACID)

**🔒 Layer 4: Transaction Manager - "Multiple users, isolated transactions, correct results!"**

**The ACID Guarantees:**
- **A**tomicity: All or nothing
- **C**onsistency: Valid state always
- **I**solation: Transactions don't interfere
- **D**urability: Committed = permanent (WAL handles this!)

```python
# DESIGN: Coordinating concurrent transactions (ACID guarantees)
class TransactionManager:
    active_transactions = {}
    lock_table = {}  # key → lock_owner
    
    def begin_transaction(isolation_level):
        txn_id = generate_unique_id()
        txn = Transaction({
            'id': txn_id,
            'isolation': isolation_level,
            'locks': set(),
            'undo_log': []  # For rollback
        })
        active_transactions[txn_id] = txn
        return txn_id
    
    def execute_read(txn_id, key):
        # 1. Acquire lock (shared lock for reads)
        acquire_lock(txn_id, key, type=SHARED)
        
        # 2. Read value
        value = storage_engine.get(key)
        
        # 3. Check visibility (MVCC)
        if is_visible_to(value, txn_id):
            return value
        else:
            # Read older version from version chain
            return find_visible_version(key, txn_id)
    
    def execute_write(txn_id, key, value):
        # 1. Acquire exclusive lock
        acquire_lock(txn_id, key, type=EXCLUSIVE)
        
        # 2. Save undo information (for rollback)
        old_value = storage_engine.get(key)
        txn.undo_log.append(('UPDATE', key, old_value))
        
        # 3. Write to WAL (durability)
        wal.append(txn_id, 'UPDATE', key, value)
        
        # 4. Apply change with versioning
        storage_engine.put(key, value, version=txn_id)
    
    def commit(txn_id):
        # 1. Write commit record to WAL
        wal.append(txn_id, 'COMMIT', null, null)
        wal.fsync()  # Ensure durable!
        
        # 2. Release all locks
        for key in txn.locks:
            release_lock(key)
        
        # 3. Cleanup
        delete active_transactions[txn_id]
    
    def rollback(txn_id):
        # 1. Undo all operations (reverse order)
        for (operation, key, old_value) in reverse(txn.undo_log):
            storage_engine.put(key, old_value)  # Restore old value
        
        # 2. Release locks
        for key in txn.locks:
            release_lock(key)
        
        # 3. Mark as aborted
        wal.append(txn_id, 'ABORT', null, null)
```

**Design Techniques:**

| Technique | Purpose | Trade-off |
|-----------|---------|----------|
| **2PL (Two-Phase Locking)** | Serializability | Can deadlock |
| **MVCC (Multi-Version)** | No read locks | More storage |
| **Deadlock Detection** | Find cycles in wait graph | CPU overhead |
| **Lock Timeout** | Abort & retry | May abort valid txns |

*👉 Working implementation: [code/episode8/transaction_manager.py](../code/episode8/transaction_manager.py)*

**Isolation Levels:**
```
READ UNCOMMITTED → Can see dirty writes (almost never used)
READ COMMITTED   → See only committed data (most common)
REPEATABLE READ  → Consistent snapshot within transaction
SERIALIZABLE     → As if transactions ran one-at-a-time (slowest)
```

**PostgreSQL Example:**
```sql
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;
  SELECT balance FROM accounts WHERE id = 123;  -- See snapshot
  UPDATE accounts SET balance = balance - 100 WHERE id = 123;
  UPDATE accounts SET balance = balance + 100 WHERE id = 456;
COMMIT;  -- Atomically applies both updates
```

---

### Slide 8.5: Tables & Relational Model (Building on KV Store)

**🗂️ From Key-Value Store to Relational Tables**

**The Journey:**
```
Episodes 2.4-2.7: Built storage engines
    ↓
Storage Engine API: put(key, value), get(key), scan()
    ↓
But users want: CREATE TABLE, SELECT * FROM users WHERE age > 25
    ↓
Need relational layer on top of KV store!
```

**Step 1: Schema Definition**
```python
# DESIGN: Define table structure (CREATE TABLE)
class TableSchema:
    table_name = "users"
    columns = [
        Column("id", type=INTEGER, constraints=[PRIMARY_KEY, NOT_NULL]),
        Column("name", type=TEXT, constraints=[NOT_NULL]),
        Column("email", type=TEXT, constraints=[UNIQUE, NOT_NULL]),
        Column("age", type=INTEGER),
    ]
    
    def validate_row(row):
        # Check types match
        # Check constraints (NOT NULL, UNIQUE, etc.)
        # Throw error if invalid
```

**Step 2: Row Encoding (How to store rows as bytes)**
```python
# DESIGN: Serialize structured data to raw bytes
class RowCodec:
    
    def encode_row(schema, row):
        # Row: {"id": 123, "name": "Alice", "age": 30}
        # → Bytes: [header][col1][col2][col3]
        
        buffer = ByteArray()
        
        # Header: column count + null bitmap
        buffer.write(num_columns)
        buffer.write(null_bitmap)  # 1 bit per column
        
        # Column values (in schema order)
        for each column in schema:
            value = row[column.name]
            
            if value is NULL:
                # Skip (null bitmap already set)
                continue
            
            if column.type == INTEGER:
                buffer.write_int64(value)      # Fixed 8 bytes
            elif column.type == TEXT:
                buffer.write_int32(len(value)) # Length prefix
                buffer.write_bytes(value)      # Variable length
            # ... other types
        
        return buffer.to_bytes()
    
    def decode_row(schema, bytes):
        # Reverse: bytes → row dictionary
        # Read header, check null bitmap, deserialize values
```

**Encoding Strategies:**

| Format | Pro | Con | Used By |
|--------|-----|-----|----------|
| **Binary (row-wise)** | Fast, compact | Not human-readable | PostgreSQL |
| **JSON** | Flexible, readable | Larger, slower | MongoDB |
| **Columnar** | Analytics-optimized | Slower updates | Parquet, TiFlash |

**Step 3: Table Storage (Mapping table rows to KV pairs)**
```python
# DESIGN: Relational table on top of key-value storage
class Table:
    
    def insert(row):
        # validate_row(row)
        
        # Key design: table_name:primary_key_value
        pk = row[primary_key_column]
        key = f"users:{pk}"  # e.g., "users:123"
        
        # Encode row to bytes
        value = encode_row(schema, row)
        
        # Store in KV engine
        storage_engine.put(key, value)
    
    def get(primary_key):
        # Point lookup by primary key
        key = f"users:{primary_key}"
        value = storage_engine.get(key)
        return decode_row(schema, value)
    
    def scan(filter_fn):
        # Full table scan (slow without index!)
        results = []
        
        for key, value in storage_engine.scan_prefix("users:"):
            row = decode_row(schema, value)
            
            if filter_fn(row):  # WHERE clause
                results.append(row)
        
        return results  # Potentially 1M rows!
    
    def update(primary_key, changes):
        # Read-modify-write
        row = get(primary_key)
        row.update(changes)  # Apply changes
        insert(row)  # Overwrite (atomically if in transaction)
```

**Key Design Insight:**
- ✅ Primary key → Storage key (fast lookups: O(log n))
- ❌ Filter without index = Full scan (slow: O(n))
- 👉 Solution: **Secondary indexes!** (Next slide)

**What's Still Missing?**
❌ Secondary indexes (for `WHERE age > 25` queries)  
❌ Joins (combining multiple tables)  
❌ Aggregations (COUNT, SUM, AVG)  
👉 That's what Query Processor solves! (Next slide)

---

### Slide 9: Layer 5 - Query Processor (SQL to Operations)

**🔍 Layer 5: Query Processor - "Turn SQL into storage engine operations!"**

**The Query Pipeline:**
```
SQL String: "SELECT name, age FROM users WHERE age > 25"
    ↓
[1. LEXER] → Tokens: [SELECT] [name] [,] [age] [FROM] [users] [WHERE] [age] [>] [25]
    ↓  
[2. PARSER] → AST: SelectStatement {
                      columns: ['name', 'age'],
                      table: 'users',
                      where: BinaryOp(column='age', op='>', value=25)
                   }
    ↓
[3. VALIDATE] → Check: Table exists? Columns exist? Types match?
    ↓
[4. LOGICAL PLAN] → Project(name, age)
                        ↓
                      Filter(age > 25)
                        ↓
                      Scan(users)
    ↓
[5. OPTIMIZE] → Index available on age? Replace Scan with IndexScan!
    ↓
[6. PHYSICAL PLAN] → Project(name, age)
                        ↓
                      IndexScan(users, age_idx, age > 25)  ← Using index!
    ↓
[7. EXECUTE] → Call storage engine APIs, return results
```

**Step 1-2: Lexer & Parser (SQL → Structured Representation)**
```python
# DESIGN GOAL: Convert text to structured data

class Lexer:
    # Break SQL into tokens
    def tokenize(sql_string):
        # "SELECT * FROM users WHERE age > 25"
        # → [Token(SELECT), Token(STAR), Token(FROM), Token(IDENTIFIER, "users"), ...]
        
        tokens = []
        for word in sql_string.split():
            if word in KEYWORDS:
                tokens.append(Token(type=KEYWORD, value=word))
            elif word.isdigit():
                tokens.append(Token(type=NUMBER, value=int(word)))
            else:
                tokens.append(Token(type=IDENTIFIER, value=word))
        return tokens

class Parser:
    # Build Abstract Syntax Tree (AST)
    def parse(tokens):
        # Tokens → Tree structure
        
        ast = SelectStatement()
        ast.columns = parse_column_list(tokens)  # ['name', 'age']
        ast.table = parse_table_name(tokens)     # 'users'
        ast.where = parse_where_clause(tokens)   # BinaryOp('age', '>', 25)
        return ast
```

**Why AST?** Structured data is easier to validate and transform than raw strings.

**Step 3-7: Optimization & Execution**
```python
# DESIGN: Transform AST → Physical Plan → Results
class QueryProcessor:
    
    def execute_query(sql):
        # Full pipeline
        tokens = Lexer(sql).tokenize()
        ast = Parser(tokens).parse()
        validate(ast)  # Tables/columns exist?
        logical_plan = to_logical_plan(ast)
        physical_plan = optimize(logical_plan)
        results = execute(physical_plan)
        return results
    
    def to_logical_plan(ast):
        # Abstract operations (database-agnostic)
        plan = ScanOp(ast.table)              # Scan 'users'
        
        if ast.where:
            plan = FilterOp(plan, ast.where)  # Filter age > 25
        
        if ast.columns != ['*']:
            plan = ProjectOp(plan, ast.columns)  # Select name, age
        
        if ast.order_by:
            plan = SortOp(plan, ast.order_by)  # Order by name
        
        return plan
    
    def optimize(logical_plan):
        # Key optimization: Index selection
        if has_filter_on_indexed_column(logical_plan):
            # Replace full scan with index scan!
            logical_plan = replace_with_index_scan(logical_plan)
        
        # Other optimizations:
        # - Predicate pushdown (move filters closer to scan)
        # - Column pruning (don't fetch unused columns)
        # - Join reordering (choose best join order)
        
        return logical_plan
    
    def execute(physical_plan):
        # Execute operators bottom-up
        if isinstance(physical_plan, IndexScanOp):
            # Use index for efficient lookup
            return index.range_scan(start, end)
        
        elif isinstance(physical_plan, FilterOp):
            rows = execute(physical_plan.child)
            return [row for row in rows if matches_filter(row)]
        
        elif isinstance(physical_plan, JoinOp):
            return execute_join(physical_plan)
```

**Join Algorithms (Design Choices):**

| Algorithm | Complexity | When to Use |
|-----------|------------|-------------|
| **Nested Loop** | O(n × m) | Small tables (<1000 rows) |
| **Hash Join** | O(n + m) | Equality joins, enough RAM |
| **Merge Join** | O(n log n) | Both tables sorted/indexed |
| **Index Nested Loop** | O(n × log m) | Index on join key exists |

*👉 Complete query processor design: Lines 800-1400 in episode8.md*<br>
*👉 Working implementations: [code/episode8/](../code/episode8/)*

---

### Slide 9.5: Secondary Indexes & Index Selection

**📇 Secondary Indexes: "Fast queries on non-primary-key columns!"**

**The Problem:**
```python
# Query: Find all users with age > 25
SELECT * FROM users WHERE age > 25;

# Without index: Full table scan (1 million rows)
for user in users.scan():
    if user['age'] > 25:
        yield user
# Time: 10 seconds 😱 (1M disk reads)

# With index on age: Range scan (10,000 matching rows)
for user_id in age_index.range(25, infinity):
    yield users.get(user_id)
# Time: 0.1 seconds ⚡ (10K index lookups)
```

**Secondary Index Implementation:**
```python
# DESIGN: Map non-primary-key → primary keys
class SecondaryIndex:
    # Example: Index on 'age' column
    # Maps: age_value → [user_ids with that age]
    
    def build_index(table, column_name):
        # Scan entire table (one-time cost)
        for row in table.scan_all():
            column_value = row[column_name]
            primary_key = row[primary_key_column]
            
            # Store: index_name:column_value:primary_key
            index_key = f"idx_{column_name}:{column_value}:{primary_key}"
            storage.put(index_key, empty)  # Just the key matters
    
    def lookup(value):
        # Find all rows where column = value
        # 1. Scan index for matching keys
        matching_pks = []
        for key in storage.scan_prefix(f"idx_age:{value}:"):
            pk = extract_pk_from(key)
            matching_pks.append(pk)
        
        # 2. Fetch actual rows
        return [table.get(pk) for pk in matching_pks]
    
    def range_scan(start, end):
        # WHERE age BETWEEN 25 AND 35
        # B-Tree property: Range queries are efficient!
        matching_pks = []
        
        for key in storage.scan_range(
            f"idx_age:{start}:",
            f"idx_age:{end}:~"
        ):
            pk = extract_pk_from(key)
            matching_pks.append(pk)
        
        return [table.get(pk) for pk in matching_pks]
```

**Composite Indexes (Multi-Column):**
```python
# DESIGN: Index on (city, age) tuple
class CompositeIndex:
    # Enables: WHERE city = 'NYC' AND age > 25
    # Does NOT help: WHERE age > 25 (wrong column order!)
    
    def build_index(table, columns):
        # columns = ['city', 'age']
        for row in table.scan_all():
            # Concatenate indexed values
            composite_key = f"{row['city']}:{row['age']}"
            index_key = f"idx_city_age:{composite_key}:{row['id']}"
            storage.put(index_key, empty)
    
    # Query: WHERE city = 'NYC' AND age BETWEEN 25 AND 35
    # ✅ Uses index! Scans: idx_city_age:NYC:25: to idx_city_age:NYC:35:
    
    # Query: WHERE age = 25
    # ❌ Cannot use index (city prefix missing)
```

*👉 Full design patterns: [episode8.md#slide-9.5](episode8.md)*

**Index Selection (Query Optimizer):**
```python
# DESIGN: Choose best index for a query
class IndexSelector:
    
    def select_best_index(query, available_indexes):
        # Query: WHERE city = 'NYC' AND age > 25 AND name = 'Alice'
        # Indexes: [city_idx, age_idx, city_age_idx, name_idx]
        
        best_index = None
        best_cost = INFINITY
        
        for index in available_indexes:
            # Estimate cost of using this index
            selectivity = estimate_selectivity(index, query)
            cost = selectivity * total_rows
            
            if cost < best_cost:
                best_cost = cost
                best_index = index
        
        return best_index
    
    def estimate_selectivity(index, query):
        # Selectivity = Fraction of rows matching condition
        # Lower = better (fewer rows to scan)
        
        # Example:
        # city = 'NYC': 5% of rows (50K / 1M)
        # age > 25: 60% of rows (600K / 1M)
        # name = 'Alice': 0.01% of rows (100 / 1M)
        
        # Best choice: name_idx (most selective)
        
        distinct_values = stats.get_distinct_count(index.column)
        return 1.0 / distinct_values  # Simplified
```

**Design Trade-offs:**

| Aspect | Pro | Con |
|--------|-----|-----|
| **More indexes** | Faster queries | Slower writes, more disk |
| **Composite indexes** | Optimize multi-column filters | Order matters |
| **Covering indexes** | Avoid table lookup | Much larger indexes |

**Production Examples:**

**PostgreSQL:**
```sql
-- Create index
CREATE INDEX users_age_idx ON users(age);

-- Composite index
CREATE INDEX users_city_age_idx ON users(city, age);

-- Check index usage
EXPLAIN ANALYZE SELECT * FROM users WHERE age > 25;
-- Output: Index Scan using users_age_idx (cost=0.43..8234.56)

-- Force full table scan (compare)
SET enable_indexscan = off;
EXPLAIN ANALYZE SELECT * FROM users WHERE age > 25;
-- Output: Seq Scan on users (cost=0.00..15234.56) -- 2× slower!
```

**Index Maintenance Cost:**
```python
# INSERT with 3 indexes = 4 writes total
# 1. Write row to table (primary key)
# 2. Update index on age
# 3. Update index on city
# 4. Update index on name

# Trade-off:
# ✅ Fast reads (0.1ms with index vs 10s without)
# ⚠️ Slower writes (4× write amplification)
# ⚠️ More disk space (each index = 20-50% of table size)

# Rule of thumb:
# - OLTP: 2-5 indexes per table (balance read/write)
# - OLAP: 10+ indexes (read-heavy, append-only writes)
```

**Key Insights:**
✅ **Secondary indexes = fast queries on any column**  
✅ **Composite indexes = optimize multi-column filters**  
✅ **Index selection = query optimizer finds best index**  
✅ **Trade-off**: Faster reads ↔ Slower writes + More disk space  

**When to add indexes:**
- Query runs frequently (hot path)
- WHERE clause filters on column
- Column has high cardinality (many distinct values)
- Read/write ratio > 10:1

**When NOT to add indexes:**
- Low cardinality columns (e.g., boolean, gender)
- Write-heavy workloads (index maintenance overhead)
- Small tables (full scan already fast)

---

## ACT 3: COMPLETE DATABASE ARCHITECTURES 🏛️

### Slide 10: PostgreSQL Architecture (B-Tree Based)

**🐘 PostgreSQL: The B-Tree Database**

```
┌─────────────────────────────────────────────────────┐
│              SQL Query Parser                       │
├─────────────────────────────────────────────────────┤
│      Query Planner & Optimizer (cost-based)         │
├─────────────────────────────────────────────────────┤
│   Transaction Manager (MVCC, 2PL locking)           │
├─────────────────────────────────────────────────────┤
│        Write-Ahead Log (WAL / pg_wal/)              │
├─────────────────────────────────────────────────────┤
│     Buffer Pool (shared_buffers, page cache)        │
├─────────────────────────────────────────────────────┤
│        B-Tree Storage Engine (heap + indexes)       │  ← Layer 1 choice!
│  • Primary data: Heap files (unordered pages)       │
│  • Indexes: B-Tree (default), GiST, GIN, BRIN      │
└─────────────────────────────────────────────────────┘
```

**Key Design Choices:**
- **Storage**: B-Tree indexes + heap files
- **Transactions**: Multi-Version Concurrency Control (MVCC)
  - Each row has `xmin` (creating txn) and `xmax` (deleting txn)
  - No read locks needed!
- **WAL**: All changes logged before applying
- **Buffer Pool**: LRU page cache (configurable size)

**Production Config:**
```sql
-- For read-heavy OLTP workload
shared_buffers = 8GB                  -- Cache hot pages
effective_cache_size = 24GB           -- Total OS + PG cache
work_mem = 64MB                       -- Per-query sort/hash
maintenance_work_mem = 1GB            -- For VACUUM, CREATE INDEX
wal_buffers = 16MB                    -- WAL write buffer
checkpoint_timeout = 15min            -- Flush frequency
max_wal_size = 4GB                    -- WAL size before checkpoint
```

**Performance Characteristics:**
- ✅ Excellent for: OLTP, complex queries, joins, read-heavy workloads
- ✅ ACID compliance, strong consistency
- ❌ Slower for: High write throughput, time-series inserts
- ❌ Write amplification: Read-modify-write on pages

**When to Use:**
- Transactional applications (e-commerce, banking)
- Complex analytical queries
- Need strong ACID guarantees
- Read:Write ratio > 3:1

---

### Slide 11: Cassandra Architecture (LSM-Tree Based)

**💎 Cassandra: The LSM-Tree Database**

```
┌─────────────────────────────────────────────────────┐
│              CQL Query Parser                       │
├─────────────────────────────────────────────────────┤
│      Coordinator Node (no single planner)           │
├─────────────────────────────────────────────────────┤
│   Lightweight Transactions (Paxos, optional)        │
├─────────────────────────────────────────────────────┤
│        Commit Log (append-only WAL)                 │
├─────────────────────────────────────────────────────┤
│     Row Cache + Key Cache (optional)                │
├─────────────────────────────────────────────────────┤
│        LSM-Tree Storage Engine                      │  ← Layer 1 choice!
│  • Memtables (in-memory sorted)                     │
│  • SSTables (immutable disk files)                  │
│  • Compaction (size-tiered or leveled)             │
│  • Bloom filters (for fast lookups)                │
└─────────────────────────────────────────────────────┘
```

**Key Design Choices:**
- **Storage**: LSM-Tree (memtable → SSTables)
- **Transactions**: Eventual consistency (tunable)
  - No multi-key transactions by default
  - Lightweight transactions via Paxos (slow)
- **WAL**: Commit log (append-only, fast)
- **Distributed**: Partition key determines node (consistent hashing)

**Production Config:**
```yaml
# cassandra.yaml - For write-heavy workload
memtable_allocation_type: heap_buffers
memtable_flush_writers: 4             # Parallel flushes
concurrent_writes: 128                # High write concurrency
compaction_throughput_mb_per_sec: 64  # Background compaction
bloom_filter_fp_chance: 0.01          # 1% false positive

# Key cache (for partition key lookups)
key_cache_size_in_mb: 2048

# Row cache (for hot rows, optional)
row_cache_size_in_mb: 1024
```

**Performance Characteristics:**
- ✅ Excellent for: High write throughput, time-series, logs, IoT
- ✅ Linear scalability, no single point of failure
- ✅ Tunable consistency (eventual → strong)
- ❌ Slower for: Complex joins, range scans across partitions
- ❌ Read amplification: Must check multiple SSTables

**When to Use:**
- Write-heavy workloads (>50% writes)
- Need horizontal scalability
- Can tolerate eventual consistency
- Time-series data, event logging
- Geographic distribution (multi-DC replication)

---

### Slide 12: TiDB Architecture (Hybrid Engines)

**🎯 TiDB: The Hybrid Database**

```
┌─────────────────────────────────────────────────────┐
│         MySQL-Compatible SQL Layer                  │
├─────────────────────────────────────────────────────┤
│    Query Optimizer (cost-based, statistics)         │
├─────────────────────────────────────────────────────┤
│   Transaction Manager (Percolator, MVCC)            │
├─────────────────────────────────────────────────────┤
│              Placement Driver (PD)                  │
│         (Metadata, scheduling, TSO)                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────┐  ┌────────────────────┐  │
│  │    TiKV (Row Store) │  │ TiFlash (Columnar) │  │  ← Dual engines!
│  │                     │  │                    │  │
│  │  • LSM-Tree (RocksDB)  │  DeltaTree + LSM  │  │
│  │  • Raft replication│  │  • Columnar format │  │
│  │  • For OLTP        │  │  • For OLAP        │  │
│  └─────────────────────┘  └────────────────────┘  │
│           ↕                        ↕               │
│      Raft Learner - Auto Sync (async replication)  │
└─────────────────────────────────────────────────────┘
```

**Key Design Choices:**
- **Storage**: DUAL ENGINES!
  - **TiKV**: LSM-Tree (RocksDB) for transactional writes
  - **TiFlash**: Columnar + LSM for analytical reads
  - Data automatically replicated between engines
- **Transactions**: Distributed MVCC (via Percolator)
- **Distributed**: Raft consensus per region (group of keys)

**Query Routing:**
```python
class TiDBQueryRouter:
    def route_query(self, sql):
        query_type = self.analyze(sql)
        
        if query_type == 'POINT_LOOKUP':
            # SELECT * FROM orders WHERE id = 123
            return self.tikv.get(key)  # LSM-Tree
        
        elif query_type == 'OLTP_TRANSACTION':
            # UPDATE accounts SET balance = balance - 100 WHERE id = 123
            return self.tikv.execute_transaction()
        
        elif query_type == 'OLAP_AGGREGATION':
            # SELECT country, SUM(amount), AVG(age)
            # FROM users GROUP BY country
            return self.tiflash.scan_columnar()  # Column store
        
        elif query_type == 'MIXED_WORKLOAD':
            # JOIN recent OLTP data with historical analytics
            recent = self.tikv.scan(recent_range)
            historical = self.tiflash.scan(old_range)
            return self.merge(recent, historical)
```

**Performance Characteristics:**
- ✅ Best of both worlds: Fast writes (TiKV) + Fast analytics (TiFlash)
- ✅ ACID transactions across distributed nodes
- ✅ MySQL compatibility (drop-in replacement)
- ⚠️ More complexity: Two storage engines to manage
- ⚠️ Replication lag: TiFlash may be slightly behind TiKV

**When to Use:**
- Hybrid workload (OLTP + OLAP on same data)
- Need horizontal scalability + ACID
- Want to avoid separate OLTP and data warehouse
- Real-time analytics on transactional data

---

## ACT 4: BUILDING YOUR OWN 🛠️

### Slide 13: Decision Tree - Which Database to Build?

**🌳 The Database Builder's Decision Tree**

```
START: What's your primary workload?
│
├─ Read-Heavy (>70% reads)
│   │
│   ├─ Need ACID transactions?
│   │   │
│   │   ├─ YES → **Build B-Tree Database**
│   │   │        (PostgreSQL-style)
│   │   │        • B+Tree storage engine
│   │   │        • MVCC for concurrency
│   │   │        • Strong consistency
│   │   │
│   │   └─ NO → **Build Eventual Consistent B-Tree**
│   │            (MongoDB-style)
│   │            • B-Tree for indexes
│   │            • Document-oriented
│   │            • Replication for reads
│   │
│   └─ Need horizontal scaling?
│       └─ YES → **Build Distributed B-Tree**
│                (CockroachDB-style)
│                • B-Tree per region
│                • Raft consensus
│                • Distributed transactions
│
├─ Write-Heavy (>50% writes)
│   │
│   ├─ Need strong consistency?
│   │   │
│   │   ├─ YES → **Build LSM with Consensus**
│   │   │        (CockroachDB with RocksDB)
│   │   │        • LSM storage engine
│   │   │        • Raft replication
│   │   │        • ACID across nodes
│   │   │
│   │   └─ NO → **Build Eventual Consistent LSM**
│   │            (Cassandra-style)
│   │            • LSM-Tree storage
│   │            • Tunable consistency
│   │            • High availability
│   │
│   └─ Extreme write throughput (millions/sec)?
│       └─ **Build Time-Series DB**
│                (InfluxDB-style)
│                • LSM optimized for time-series
│                • Downsampling & retention policies
│                • Column-oriented compression
│
└─ Mixed Workload (both reads & writes)
    │
    ├─ Can separate OLTP and OLAP?
    │   │
    │   ├─ YES → **Build Separate Systems**
    │   │        OLTP: PostgreSQL (B-Tree)
    │   │        OLAP: Data Warehouse (Columnar)
    │   │        + ETL pipeline between them
    │   │
    │   └─ NO → **Build Hybrid Engine**
    │            (TiDB-style)
    │            • LSM for writes (OLTP)
    │            • Columnar for analytics (OLAP)
    │            • Auto replication between engines
    │
    └─ Need real-time analytics?
        └─ **Build HTAP Database**
                (TiDB, CockroachDB, AlloyDB)
                • Single system for both workloads
                • Intelligent query routing
                • In-memory acceleration
```

---

### Slide 14: Implementation Checklist

**✅ Building Your Database - Layer by Layer**

**Phase 1: Core Storage Engine (Weeks 1-4)**
```
□ Choose data structure: B-Tree OR LSM-Tree OR Hybrid
□ Implement page management (4KB pages)
□ Serialize/deserialize pages to disk
□ Handle splits (B-Tree) or flushes (LSM)
□ Unit tests: Insert, lookup, delete, scan
```

**Phase 2: Memory Management (Week 5-6)**
```
□ Implement LRU buffer pool
□ Track dirty pages
□ Implement eviction policy
□ Add page pinning (for active pages)
□ Metrics: Cache hit rate, eviction rate
```

**Phase 3: Durability (Week 7-8)**
```
□ Write-Ahead Log (append-only)
□ fsync() for durability
□ Crash recovery (replay WAL)
□ Checkpoint mechanism (flush + truncate WAL)
□ Test: Kill process mid-operation, verify recovery
```

**Phase 4: Transactions (Week 9-12)**
```
□ Transaction manager (begin, commit, rollback)
□ Lock manager (shared/exclusive locks)
□ Deadlock detection
□ MVCC (multi-version concurrency control)
□ Isolation levels (at least READ COMMITTED)
□ Test: Concurrent transactions, rollback scenarios
```

**Phase 5: Query Layer (Week 13-16)**
```
□ SQL parser (or simple key-value API)
□ Query planner (sequence of operations)
□ Index selection logic
□ Join algorithms (nested loop, hash join)
□ Query optimizer (cost-based)
```

**Phase 6: Production Hardening (Ongoing)**
```
□ Monitoring & metrics (Prometheus/Grafana)
□ Performance profiling
□ Backup & restore
□ Replication (leader-follower)
□ Distributed consensus (Raft/Paxos)
□ Load testing (thousands of concurrent clients)
```

---

### Slide 15: Conceptual Database Architecture - Putting It Together

**🔧 From Concepts to Working System**

**The Architecture (Design Overview):**
```python
# DESIGN: Integrate all 5 layers

class MiniDatabase:
    # Layer 1: Choose storage engine
    storage = BTreeStorage()  # or LSMStorage() or HybridStorage()
    
    # Layer 2: Add memory caching
    buffer_pool = BufferPool(storage, capacity=100_pages)
    
    # Layer 3: Add durability
    wal = WriteAheadLog("database.wal")
    
    # Layer 4: Add transactions
    txn_manager = TransactionManager(storage, wal, buffer_pool)
    
    # Layer 5: Add query processing
    query_processor = QueryProcessor(storage, txn_manager)
    
    def execute_sql(sql_query):
        return query_processor.execute(sql_query)
```

**Transaction Flow (Design Sequence):**
```
User: BEGIN TRANSACTION
   ↓
User: INSERT INTO users VALUES (1, 'Alice', 30)
   ↓
1. Write to WAL (durability)           ← Layer 3
2. Acquire locks (isolation)           ← Layer 4
3. Update in buffer pool (performance) ← Layer 2
4. Put in storage engine (persistence) ← Layer 1
   ↓
User: COMMIT
   ↓
1. Commit record to WAL
2. Release locks
3. Flush dirty pages (async)
   ↓
User: "OK" (Transaction durable!)
```

**👉 Working implementation: [code/episode8/](../code/episode8/)** (1,120 lines)

**Key Takeaways:**
1. Each layer has a **clear responsibility**
2. Layers **compose** (buffer pool wraps storage, txn manager wraps both)
3. Same design pattern across **all databases** (PostgreSQL, MySQL, Cassandra)
4. Choice at Layer 1 (B-Tree vs LSM) **influences** all other layers

---

## ACT 5: MASTERY 🎯

### Slide 16: The Three Database Philosophies

**🎓 Every Database Makes These Tradeoffs**

**Philosophy 1: Consistency-First (B-Tree Databases)**
```
ACID > Everything
Strong consistency > Eventual consistency
Single-node simplicity > Distributed complexity

Examples: PostgreSQL, MySQL, SQLite

Mantra: "Correctness first, scale later"
```

**Philosophy 2: Availability-First (LSM Databases)**
```
Write throughput > Read latency
Eventual consistency acceptable
Always-on > Single point of failure

Examples: Cassandra, Riak, DynamoDB

Mantra: "Never go down, eventually correct"
```

**Philosophy 3: Hybrid (Modern Distributed)**
```
ACID + Scale = Hard but possible
Multiple engines for different workloads
Intelligent routing between hot/cold storage

Examples: TiDB, CockroachDB, YugabyteDB, AlloyDB

Mantra: "Best of both worlds, complexity managed"
```

---

### Slide 17: Key Takeaways

**🎯 The 5 Big Ideas**

**1. Data Structure Choice Determines Everything**
- B-Tree → Read-optimized, ACID-friendly
- LSM-Tree → Write-optimized, eventual consistency
- Hybrid → Complexity but flexibility

**2. Layers Build on Each Other**
- Storage Engine (data structure)
- Buffer Pool (caching)
- WAL (durability)
- Transactions (correctness)
- Query Processor (usability)

**3. No Perfect Database**
- PostgreSQL: Great OLTP, weak at massive writes
- Cassandra: Great writes, weak at complex queries
- TiDB: Great hybrid, complex to operate

**4. Production = Primitives + Engineering**
- The algorithms are well-known (B-Tree, LSM)
- The hard part: Making it fast, reliable, distributed

**5. You Can Build This!**
- Start with storage engine (~1 month)
- Add layers incrementally (~6 months)
- Production-ready = years of hardening

---

### Slide 18: Next Steps - Deeper Dives

**📚 Where to Go Deeper**

**🎯 Hands-On Building (START HERE!):**
- **[Build Your Own Database From Scratch](https://build-your-own.org/database/)** by James Smith
  - Step-by-step: B+Tree → Durability → Transactions → SQL
  - Part I free online (7 chapters on KV store)
  - Part II covers relational DB, concurrency, SQL parser
  - Written in Go, ~14 chapters total
- Alternative: [LSM-Tree Database in 45 Steps](https://trialofcode.org/) (test-driven approach)
- Practice: [CodeCrafters.io](https://codecrafters.io/) - Build Redis, SQLite, etc.

**Storage Engines:**
- Read: "Database Internals" by Alex Petrov
- Implement: Build your own B-Tree, then LSM-Tree
- Study: PostgreSQL heap files, RocksDB compaction strategies

**Transactions:**
- Paper: "A Critique of ANSI SQL Isolation Levels"
- Implement: MVCC, 2-phase locking
- Study: PostgreSQL's MVCC implementation

**Distributed Systems:**
- Paper: "Raft Consensus Algorithm"
- Implement: Leader election, log replication
- Study: CockroachDB's distributed transactions

**Query Optimization:**
- Read: "Database Systems: The Complete Book" (Garcia-Molina)
- Implement: Cost-based optimizer
- Study: PostgreSQL's planner (pg_plan.c)

**Production Operations:**
- Course: "Advanced Database Systems" (CMU 15-721)
- Practice: Run PostgreSQL/Cassandra, tune configs
- Study: Real outage post-mortems

---

### Slide 19: The Complete Picture

**🏛️ From LeetCode to Production Database**

```
Episode 2.1: Binary Search
    ↓
Episode 2.2-2.3: SSTables
    ↓
Episode 2.4: BST/AVL (In-Memory)
    ↓
         ┌──────────────────────┐
         │                      │
Episode 2.5:              Episode 2.6:
B-Tree                    LSM-Tree
(PostgreSQL)              (Cassandra)
         │                      │
         └──────────┬───────────┘
                    ↓
              Episode 2.7:
              Hybrid Engines
              (TiDB)
                    ↓
              Episode 2.8: 👈 YOU ARE HERE
              Complete Architecture
              
                    ↓
         Season 3: Distributed Systems?
         (Raft, Paxos, Distributed Transactions)
```

**You now understand:**
- ✅ How databases store data (Layer 1)
- ✅ How they manage memory (Layer 2)
- ✅ How they guarantee durability (Layer 3)
- ✅ How they handle transactions (Layer 4)
- ✅ How they process queries (Layer 5)

**Most importantly:**
✅ How to BUILD your own database from first principles! 🚀

---

### Slide 20: Final Thought

**💡 The Secret of Database Engineering**

*"A production database is not magic.*

*It's a data structure you learned in school...*

*+ A cache layer*

*+ A log for durability*

*+ Locks for correctness*

*+ Years of bug fixes and optimizations."*

**You have the fundamentals. The rest is engineering.** 🎯

---

**THE END** 🎬

Season 2 Complete: Binary Trees → Production Database Systems

**Coming Next: Season 3 - Distributed Systems?**

---
