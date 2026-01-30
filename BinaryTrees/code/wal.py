"""
Write-Ahead Log (WAL) - Durability Layer

Ensures all committed writes survive crashes.
The secret: Log changes BEFORE modifying data pages.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from enum import Enum


class LogEntryType(Enum):
    """Types of WAL entries."""
    BEGIN = "BEGIN"
    COMMIT = "COMMIT"
    ABORT = "ABORT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CHECKPOINT = "CHECKPOINT"


class LogEntry:
    """Single WAL log entry."""
    
    def __init__(self, entry_type: LogEntryType, txn_id: int, 
                 table: Optional[str] = None, key: Optional[bytes] = None, 
                 value: Optional[bytes] = None, old_value: Optional[bytes] = None):
        self.entry_type = entry_type
        self.txn_id = txn_id
        self.table = table
        self.key = key
        self.value = value
        self.old_value = old_value  # For undo
        self.lsn = None  # Log Sequence Number (assigned when written)
        self.timestamp = time.time()
    
    def serialize(self) -> bytes:
        """Convert to bytes for writing to disk."""
        data = {
            'type': self.entry_type.value,
            'txn_id': self.txn_id,
            'table': self.table,
            'key': self.key.hex() if self.key else None,
            'value': self.value.hex() if self.value else None,
            'old_value': self.old_value.hex() if self.old_value else None,
            'lsn': self.lsn,
            'timestamp': self.timestamp,
        }
        return json.dumps(data).encode() + b'\n'
    
    @staticmethod
    def deserialize(data: bytes) -> 'LogEntry':
        """Parse from bytes."""
        obj = json.loads(data.decode())
        entry = LogEntry(
            entry_type=LogEntryType(obj['type']),
            txn_id=obj['txn_id'],
            table=obj.get('table'),
            key=bytes.fromhex(obj['key']) if obj.get('key') else None,
            value=bytes.fromhex(obj['value']) if obj.get('value') else None,
            old_value=bytes.fromhex(obj['old_value']) if obj.get('old_value') else None,
        )
        entry.lsn = obj['lsn']
        entry.timestamp = obj['timestamp']
        return entry


class WriteAheadLog:
    """
    Write-Ahead Log implementation.
    
    Key principle: Write log BEFORE modifying data.
    If crash happens: Replay log to recover.
    
    Sequential writes: WAL is append-only (fast!)
    """
    
    def __init__(self, wal_file: str = "database.wal"):
        self.wal_file = wal_file
        self.next_lsn = 0  # Log Sequence Number counter
        self.log_buffer: List[LogEntry] = []  # Buffer before fsync
        self.buffer_size = 100  # Flush after 100 entries
        
        # Recovery state
        self.last_checkpoint_lsn = 0
        
        # Create WAL file if doesn't exist
        if not os.path.exists(wal_file):
            open(wal_file, 'w').close()
        else:
            self._load_state()
    
    def append(self, entry: LogEntry) -> int:
        """
        Append log entry to WAL.
        
        Returns:
            LSN (Log Sequence Number) of written entry
        """
        entry.lsn = self.next_lsn
        self.next_lsn += 1
        
        self.log_buffer.append(entry)
        
        # Flush if buffer full
        if len(self.log_buffer) >= self.buffer_size:
            self.flush()
        
        return entry.lsn
    
    def flush(self) -> None:
        """
        Flush log buffer to disk with fsync().
        
        fsync() guarantees: Data written to physical disk (not just OS cache).
        This is THE operation that provides durability!
        """
        if not self.log_buffer:
            return
        
        with open(self.wal_file, 'ab') as f:
            for entry in self.log_buffer:
                f.write(entry.serialize())
            f.flush()
            os.fsync(f.fileno())  # 💥 Force write to disk!
        
        self.log_buffer.clear()
    
    def checkpoint(self) -> None:
        """
        Checkpoint: Mark point where all prior changes are on disk.
        
        After checkpoint:
        - All dirty pages flushed to data files
        - Can truncate WAL (no need for old entries)
        
        PostgreSQL: Checkpoint every checkpoint_timeout (default 5 minutes)
        """
        # Flush any pending log entries
        self.flush()
        
        # Record checkpoint in log
        checkpoint_entry = LogEntry(
            entry_type=LogEntryType.CHECKPOINT,
            txn_id=0,
        )
        self.append(checkpoint_entry)
        self.flush()
        
        self.last_checkpoint_lsn = checkpoint_entry.lsn
        
        print(f"✅ Checkpoint at LSN {self.last_checkpoint_lsn}")
    
    def recover(self, storage: Dict[bytes, bytes]) -> Dict[int, List[LogEntry]]:
        """
        Crash recovery: Replay WAL to restore consistent state.
        
        Steps:
        1. Read WAL from last checkpoint
        2. Redo all committed transactions
        3. Undo all uncommitted transactions
        
        Returns:
            Dictionary of txn_id → list of log entries
        """
        print("\n" + "=" * 60)
        print("💥 CRASH RECOVERY: Replaying WAL...")
        print("=" * 60)
        
        transactions: Dict[int, List[LogEntry]] = {}
        committed_txns = set()
        
        # Read all log entries from last checkpoint
        with open(self.wal_file, 'rb') as f:
            for line in f:
                if not line.strip():
                    continue
                
                entry = LogEntry.deserialize(line)
                
                # Only replay from last checkpoint
                if entry.lsn < self.last_checkpoint_lsn:
                    continue
                
                # Track transaction entries
                if entry.txn_id not in transactions:
                    transactions[entry.txn_id] = []
                transactions[entry.txn_id].append(entry)
                
                # Mark committed transactions
                if entry.entry_type == LogEntryType.COMMIT:
                    committed_txns.add(entry.txn_id)
        
        # Phase 1: REDO all committed transactions
        print(f"\n🔄 REDO Phase:")
        for txn_id in committed_txns:
            print(f"  Redoing txn {txn_id}...")
            for entry in transactions[txn_id]:
                if entry.entry_type == LogEntryType.INSERT:
                    storage[entry.key] = entry.value
                    print(f"    INSERT {entry.key.hex()[:8]}...")
                elif entry.entry_type == LogEntryType.UPDATE:
                    storage[entry.key] = entry.value
                    print(f"    UPDATE {entry.key.hex()[:8]}...")
                elif entry.entry_type == LogEntryType.DELETE:
                    if entry.key in storage:
                        del storage[entry.key]
                    print(f"    DELETE {entry.key.hex()[:8]}...")
        
        # Phase 2: UNDO all uncommitted transactions
        print(f"\n↩️  UNDO Phase:")
        for txn_id, entries in transactions.items():
            if txn_id not in committed_txns and txn_id != 0:
                print(f"  Undoing uncommitted txn {txn_id}...")
                for entry in reversed(entries):
                    if entry.entry_type in [LogEntryType.INSERT, LogEntryType.UPDATE, LogEntryType.DELETE]:
                        if entry.old_value is not None:
                            storage[entry.key] = entry.old_value
                            print(f"    UNDO {entry.entry_type.value} {entry.key.hex()[:8]}...")
                        elif entry.entry_type == LogEntryType.INSERT:
                            if entry.key in storage:
                                del storage[entry.key]
        
        print(f"\n✅ Recovery complete!")
        print(f"   Committed transactions: {len(committed_txns)}")
        print(f"   Rolled back transactions: {len([t for t in transactions if t not in committed_txns])}")
        
        return transactions
    
    def truncate(self) -> None:
        """
        Truncate WAL after checkpoint.
        
        Keep only entries after last checkpoint.
        Prevents WAL from growing forever.
        """
        entries_to_keep = []
        
        with open(self.wal_file, 'rb') as f:
            for line in f:
                if not line.strip():
                    continue
                entry = LogEntry.deserialize(line)
                if entry.lsn >= self.last_checkpoint_lsn:
                    entries_to_keep.append(line)
        
        # Rewrite WAL file
        with open(self.wal_file, 'wb') as f:
            for line in entries_to_keep:
                f.write(line)
        
        print(f"📝 WAL truncated: Kept {len(entries_to_keep)} entries after checkpoint")
    
    def _load_state(self) -> None:
        """Load state from existing WAL file."""
        max_lsn = -1
        last_checkpoint = 0
        
        if os.path.exists(self.wal_file):
            with open(self.wal_file, 'rb') as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = LogEntry.deserialize(line)
                    max_lsn = max(max_lsn, entry.lsn)
                    if entry.entry_type == LogEntryType.CHECKPOINT:
                        last_checkpoint = entry.lsn
        
        self.next_lsn = max_lsn + 1
        self.last_checkpoint_lsn = last_checkpoint


# Example usage
if __name__ == "__main__":
    import tempfile
    
    print("=" * 60)
    print("Write-Ahead Log Demo")
    print("=" * 60)
    
    # Create temporary WAL file
    wal_file = tempfile.mktemp(suffix='.wal')
    wal = WriteAheadLog(wal_file)
    storage = {}
    
    # Transaction 1: Committed
    print("\n📝 Transaction 1 (COMMIT):")
    wal.append(LogEntry(LogEntryType.BEGIN, txn_id=1))
    wal.append(LogEntry(LogEntryType.INSERT, txn_id=1, table="users", 
                        key=b"user:1", value=b"Alice"))
    wal.append(LogEntry(LogEntryType.INSERT, txn_id=1, table="users",
                        key=b"user:2", value=b"Bob"))
    wal.append(LogEntry(LogEntryType.COMMIT, txn_id=1))
    wal.flush()
    
    # Apply to storage
    storage[b"user:1"] = b"Alice"
    storage[b"user:2"] = b"Bob"
    
    # Transaction 2: NOT committed (crash before commit!)
    print("\n📝 Transaction 2 (NO COMMIT - will be rolled back):")
    wal.append(LogEntry(LogEntryType.BEGIN, txn_id=2))
    wal.append(LogEntry(LogEntryType.INSERT, txn_id=2, table="users",
                        key=b"user:3", value=b"Charlie", old_value=None))
    wal.flush()
    
    # DO NOT apply to storage (simulating crash)
    
    print(f"\n💥 SIMULATING CRASH...")
    print(f"   Storage before recovery: {storage}")
    
    # Recovery
    wal2 = WriteAheadLog(wal_file)
    wal2.recover(storage)
    
    print(f"\n   Storage after recovery: {storage}")
    print(f"\n✅ Transaction 1 committed: user:1 and user:2 exist")
    print(f"✅ Transaction 2 rolled back: user:3 does NOT exist")
    
    # Cleanup
    os.remove(wal_file)
