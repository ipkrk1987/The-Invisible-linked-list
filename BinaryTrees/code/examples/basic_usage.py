"""
Example: Basic database operations

Demonstrates simple CRUD operations using the database components.
"""

from storage_engine import BTreeStorage, LSMStorage, HybridStorage
from buffer_pool import BufferPool
from free_list import FreeList
from wal import WriteAheadLog, LogEntry, LogEntryType
import tempfile
import os


def basic_storage_example():
    """Demonstrate basic storage engine operations."""
    print("=" * 70)
    print("Example 1: Basic Storage Operations")
    print("=" * 70)
    
    # Create B-Tree storage engine
    storage = BTreeStorage()
    
    # Insert data
    print("\n📝 Inserting data...")
    storage.put(b"user:1", b'{"name": "Alice", "age": 30, "city": "NYC"}')
    storage.put(b"user:2", b'{"name": "Bob", "age": 25, "city": "SF"}')
    storage.put(b"user:3", b'{"name": "Charlie", "age": 35, "city": "NYC"}')
    
    # Read data
    print("\n📖 Reading data...")
    value = storage.get(b"user:2")
    print(f"user:2 = {value.decode()}")
    
    # Range scan
    print("\n🔍 Range scan (user:1 to user:3)...")
    for key, value in storage.scan_range(b"user:1", b"user:3"):
        print(f"  {key.decode()}: {value.decode()}")
    
    # Update
    print("\n✏️  Updating user:1...")
    storage.put(b"user:1", b'{"name": "Alice", "age": 31, "city": "LA"}')
    value = storage.get(b"user:1")
    print(f"user:1 = {value.decode()}")
    
    # Delete
    print("\n🗑️  Deleting user:2...")
    storage.delete(b"user:2")
    value = storage.get(b"user:2")
    print(f"user:2 = {value}")  # Should be None


def buffer_pool_example():
    """Demonstrate buffer pool caching."""
    print("\n\n" + "=" * 70)
    print("Example 2: Buffer Pool Caching")
    print("=" * 70)
    
    # Create buffer pool with small capacity
    buffer_pool = BufferPool(capacity_mb=1, page_size=4096)
    disk_storage = {}
    
    # Initialize disk
    print("\n📀 Setting up disk storage...")
    for i in range(100):
        disk_storage[i] = f"Page {i} data".encode().ljust(4096, b'\x00')
    
    # First read (cache miss)
    print("\n📖 First read of page 5 (should be cache MISS)...")
    data = buffer_pool.get_page(5, disk_storage)
    print(f"   Read: {data[:20].decode()}...")
    
    # Second read (cache hit)
    print("\n📖 Second read of page 5 (should be cache HIT)...")
    data = buffer_pool.get_page(5, disk_storage)
    print(f"   Read: {data[:20].decode()}...")
    
    # Stats
    buffer_pool.print_stats()


def wal_durability_example():
    """Demonstrate WAL for durability and crash recovery."""
    print("\n\n" + "=" * 70)
    print("Example 3: Write-Ahead Log (WAL) & Crash Recovery")
    print("=" * 70)
    
    wal_file = tempfile.mktemp(suffix='.wal')
    storage = {}
    
    try:
        # Setup WAL
        wal = WriteAheadLog(wal_file)
        
        # Transaction 1 (will be committed)
        print("\n✅ Transaction 1 (COMMIT):")
        wal.append(LogEntry(LogEntryType.BEGIN, txn_id=1))
        wal.append(LogEntry(LogEntryType.INSERT, txn_id=1, table="products",
                            key=b"product:1", value=b"Laptop"))
        wal.append(LogEntry(LogEntryType.INSERT, txn_id=1, table="products",
                            key=b"product:2", value=b"Phone"))
        wal.append(LogEntry(LogEntryType.COMMIT, txn_id=1))
        wal.flush()
        
        # Apply changes
        storage[b"product:1"] = b"Laptop"
        storage[b"product:2"] = b"Phone"
        
        print(f"   Applied: {storage}")
        
        # Transaction 2 (will NOT be committed - simulating crash)
        print("\n❌ Transaction 2 (NO COMMIT - crash before commit):")
        wal.append(LogEntry(LogEntryType.BEGIN, txn_id=2))
        wal.append(LogEntry(LogEntryType.INSERT, txn_id=2, table="products",
                            key=b"product:3", value=b"Tablet", old_value=None))
        wal.flush()
        
        print(f"   NOT applied to storage (crash happened!)")
        
        # Simulate crash and recovery
        print("\n💥 SIMULATING CRASH...")
        print(f"   Storage before recovery: {storage}")
        
        # Create new WAL instance (simulating restart after crash)
        wal2 = WriteAheadLog(wal_file)
        wal2.recover(storage)
        
        print(f"\n   Storage after recovery: {storage}")
        print(f"\n✅ Transaction 1's changes survived (product:1, product:2)")
        print(f"✅ Transaction 2 rolled back (product:3 does NOT exist)")
        
    finally:
        # Cleanup
        if os.path.exists(wal_file):
            os.remove(wal_file)


def lsm_compaction_example():
    """Demonstrate LSM-Tree with compaction."""
    print("\n\n" + "=" * 70)
    print("Example 4: LSM-Tree with Compaction")
    print("=" * 70)
    
    # Create LSM storage with small memtable
    lsm = LSMStorage(memtable_size=3)
    
    # Insert data (will trigger flushes)
    print("\n📝 Inserting 10 records...")
    for i in range(10):
        lsm.put(f"log:{i}".encode(), f"event_{i}".encode())
        print(f"   Inserted log:{i}, SSTables: {len(lsm.sstables)}")
    
    print(f"\n📊 State before compaction:")
    print(f"   Memtable entries: {len(lsm.memtable)}")
    print(f"   Number of SSTables: {len(lsm.sstables)}")
    
    # Read data (must check all SSTables)
    print(f"\n📖 Reading log:5...")
    value = lsm.get(b"log:5")
    print(f"   Value: {value.decode()}")
    
    # Compact
    print(f"\n🔄 Running compaction (merge all SSTables)...")
    lsm.compact()
    
    print(f"\n📊 State after compaction:")
    print(f"   Memtable entries: {len(lsm.memtable)}")
    print(f"   Number of SSTables: {len(lsm.sstables)}")
    
    # Verify data still readable
    print(f"\n✅ Verifying data after compaction...")
    for i in range(10):
        value = lsm.get(f"log:{i}".encode())
        assert value == f"event_{i}".encode(), f"Data loss detected for log:{i}!"
    print(f"   All data intact!")


def hybrid_storage_example():
    """Demonstrate hybrid storage with hot/cold tiers."""
    print("\n\n" + "=" * 70)
    print("Example 5: Hybrid Storage (Hot/Cold Tiering)")
    print("=" * 70)
    
    hybrid = HybridStorage()
    
    # Write data (goes to LSM - fast writes)
    print("\n📝 Writing data (goes to LSM)...")
    hybrid.put(b"user:1", b"Alice")
    hybrid.put(b"user:2", b"Bob")
    hybrid.put(b"user:3", b"Charlie")
    
    # Read user:1 multiple times (becomes hot)
    print(f"\n📖 Reading user:1 many times (will become HOT)...")
    for i in range(12):
        value = hybrid.get(b"user:1")
    
    print(f"   Value: {value.decode()}")
    print(f"   Is user:1 in B-Tree (hot tier)? {b'user:1' in hybrid.btree.data}")
    print(f"   Is user:2 in B-Tree (hot tier)? {b'user:2' in hybrid.btree.data}")
    
    # Read user:2 (still cold)
    print(f"\n📖 Reading user:2 (still in LSM - cold tier)...")
    value = hybrid.get(b"user:2")
    print(f"   Value: {value.decode()}")
    
    print(f"\n💡 Insight:")
    print(f"   Hot data (user:1) → B-Tree (fast point lookups)")
    print(f"   Cold data (user:2, user:3) → LSM (space efficient)")


if __name__ == "__main__":
    # Run all examples
    basic_storage_example()
    buffer_pool_example()
    wal_durability_example()
    lsm_compaction_example()
    hybrid_storage_example()
    
    print("\n\n" + "=" * 70)
    print("✅ All examples completed successfully!")
    print("=" * 70)
    print("\n📚 What you've learned:")
    print("   1. Storage engines (B-Tree, LSM, Hybrid)")
    print("   2. Buffer pool caching (avoid disk I/O)")
    print("   3. WAL for durability (crash recovery)")
    print("   4. LSM compaction (space reclamation)")
    print("   5. Hybrid storage (hot/cold tiering)")
    print("\n🎯 Next steps:")
    print("   - Run: python examples/transactions.py")
    print("   - Run: python minidb.py")
