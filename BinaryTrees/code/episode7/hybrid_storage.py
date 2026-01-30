"""
Episode 7: Hybrid Storage - Best of Both Worlds
Hot data in B-Tree, cold data in LSM-Tree
"""

from typing import Optional, Any, Dict, List
from collections import defaultdict
import time


class AccessTracker:
    """
    Track access patterns to classify data as hot/cold.
    
    Strategy:
    - Hot: Frequently accessed → B-Tree (fast reads)
    - Cold: Rarely accessed → LSM-Tree (space efficient)
    """
    
    def __init__(self, hot_threshold: int = 5):
        self.access_counts: Dict[bytes, int] = defaultdict(int)
        self.last_access: Dict[bytes, float] = {}
        self.hot_threshold = hot_threshold
    
    def record_access(self, key: bytes) -> None:
        """Record key access."""
        self.access_counts[key] += 1
        self.last_access[key] = time.time()
    
    def is_hot(self, key: bytes) -> bool:
        """Check if key is hot (frequently accessed)."""
        return self.access_counts[key] >= self.hot_threshold
    
    def get_cold_keys(self, age_threshold: float = 60.0) -> List[bytes]:
        """Find keys that haven't been accessed recently."""
        current_time = time.time()
        cold_keys = []
        
        for key, last_time in self.last_access.items():
            if current_time - last_time > age_threshold:
                cold_keys.append(key)
        
        return cold_keys


class SimpleBTree:
    """Simplified B-Tree for hot data (read-optimized)."""
    
    def __init__(self):
        self.data: Dict[bytes, bytes] = {}
        self.read_count = 0
        self.write_count = 0
    
    def get(self, key: bytes) -> Optional[bytes]:
        """Fast reads: O(log n) with disk cache."""
        self.read_count += 1
        return self.data.get(key)
    
    def put(self, key: bytes, value: bytes) -> None:
        """Slower writes: In-place updates."""
        self.write_count += 1
        self.data[key] = value
    
    def delete(self, key: bytes) -> bool:
        """Delete key."""
        if key in self.data:
            del self.data[key]
            return True
        return False
    
    def size(self) -> int:
        """Number of keys."""
        return len(self.data)


class SimpleLSM:
    """Simplified LSM-Tree for cold data (write-optimized)."""
    
    def __init__(self):
        self.data: Dict[bytes, bytes] = {}
        self.read_count = 0
        self.write_count = 0
    
    def get(self, key: bytes) -> Optional[bytes]:
        """Slower reads: Check multiple SSTables."""
        self.read_count += 1
        return self.data.get(key)
    
    def put(self, key: bytes, value: bytes) -> None:
        """Fast writes: Append-only."""
        self.write_count += 1
        self.data[key] = value
    
    def delete(self, key: bytes) -> bool:
        """Delete via tombstone."""
        if key in self.data:
            self.data[key] = b'__TOMBSTONE__'
            return True
        return False
    
    def size(self) -> int:
        """Number of keys."""
        return len([k for k, v in self.data.items() if v != b'__TOMBSTONE__'])


class HybridStorage:
    """
    Hybrid Storage Engine: Tiered storage based on access patterns.
    
    Architecture:
    - Hot tier: B-Tree (read-optimized)
    - Cold tier: LSM-Tree (write-optimized, space-efficient)
    - Background: Migrate data between tiers
    
    Benefits:
    - Fast reads on hot data (B-Tree)
    - Fast writes on new data (LSM)
    - Space efficiency (LSM compaction)
    - Handles mixed workloads
    
    Used by: TiDB, CockroachDB, YugabyteDB
    """
    
    def __init__(self, hot_threshold: int = 3):
        self.hot_tier = SimpleBTree()
        self.cold_tier = SimpleLSM()
        self.tracker = AccessTracker(hot_threshold=hot_threshold)
        
        self.total_reads = 0
        self.total_writes = 0
        self.tier_promotions = 0
        self.tier_demotions = 0
    
    def put(self, key: bytes, value: bytes) -> None:
        """
        Write to hybrid storage.
        
        Strategy:
        1. New writes → LSM (fast append)
        2. Track access pattern
        3. Promote to B-Tree if becomes hot
        """
        self.total_writes += 1
        
        # Check if already in hot tier
        if self.hot_tier.get(key) is not None:
            self.hot_tier.put(key, value)
        else:
            # Write to cold tier (LSM - fast!)
            self.cold_tier.put(key, value)
    
    def get(self, key: bytes) -> Optional[bytes]:
        """
        Read from hybrid storage.
        
        Strategy:
        1. Check hot tier first (B-Tree - fast read)
        2. Check cold tier if not found
        3. Promote to hot tier if accessed frequently
        """
        self.total_reads += 1
        self.tracker.record_access(key)
        
        # Check hot tier first
        value = self.hot_tier.get(key)
        if value is not None:
            return value
        
        # Check cold tier
        value = self.cold_tier.get(key)
        if value is not None:
            # Promote to hot tier if accessed enough
            if self.tracker.is_hot(key):
                self._promote_to_hot(key, value)
        
        return value
    
    def delete(self, key: bytes) -> bool:
        """Delete from both tiers."""
        deleted_hot = self.hot_tier.delete(key)
        deleted_cold = self.cold_tier.delete(key)
        return deleted_hot or deleted_cold
    
    def _promote_to_hot(self, key: bytes, value: bytes) -> None:
        """
        Promote key from cold → hot tier.
        
        Happens when:
        - Access count exceeds threshold
        - Read latency matters
        """
        self.tier_promotions += 1
        
        # Move to hot tier
        self.hot_tier.put(key, value)
        self.cold_tier.delete(key)
        
        print(f"♨️  Promoted {key.decode()} to hot tier")
    
    def _demote_to_cold(self, key: bytes) -> None:
        """
        Demote key from hot → cold tier.
        
        Happens when:
        - Not accessed recently
        - Hot tier getting full
        """
        value = self.hot_tier.get(key)
        if value is None:
            return
        
        self.tier_demotions += 1
        
        # Move to cold tier
        self.cold_tier.put(key, value)
        self.hot_tier.delete(key)
        
        print(f"❄️  Demoted {key.decode()} to cold tier")
    
    def rebalance_tiers(self, age_threshold: float = 60.0) -> None:
        """
        Background task: Rebalance data between tiers.
        
        Move cold data from B-Tree → LSM to free up space.
        """
        cold_keys = self.tracker.get_cold_keys(age_threshold)
        
        for key in cold_keys:
            if self.hot_tier.get(key) is not None:
                self._demote_to_cold(key)
    
    def stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            'total_reads': self.total_reads,
            'total_writes': self.total_writes,
            'hot_tier_size': self.hot_tier.size(),
            'cold_tier_size': self.cold_tier.size(),
            'hot_tier_reads': self.hot_tier.read_count,
            'cold_tier_reads': self.cold_tier.read_count,
            'tier_promotions': self.tier_promotions,
            'tier_demotions': self.tier_demotions,
        }


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("Episode 7: Hybrid Storage - Best of Both Worlds")
    print("=" * 70)
    
    hybrid = HybridStorage(hot_threshold=3)
    
    print("\n📝 Writing 10 keys to storage...")
    for i in range(10):
        key = f"key:{i}".encode()
        value = f"value_{i}".encode()
        hybrid.put(key, value)
    
    print("\n🔥 Creating hot keys (accessing keys 0, 1, 2 multiple times)...")
    for _ in range(4):
        for i in [0, 1, 2]:
            key = f"key:{i}".encode()
            value = hybrid.get(key)
            print(f"   Read {key.decode()}: {value.decode()}")
    
    print("\n❄️  Reading cold keys (keys 5-9)...")
    for i in range(5, 10):
        key = f"key:{i}".encode()
        value = hybrid.get(key)
        print(f"   Read {key.decode()}: {value.decode()}")
    
    print("\n📊 Storage statistics:")
    stats = hybrid.stats()
    for metric, value in stats.items():
        print(f"   {metric}: {value}")
    
    hot_ratio = (stats['hot_tier_reads'] / stats['total_reads'] * 100) if stats['total_reads'] > 0 else 0
    print(f"\n   🎯 Hot tier hit rate: {hot_ratio:.1f}%")
    
    print("\n💡 Hybrid Storage Benefits:")
    print("   ✅ Fast reads on hot data (B-Tree)")
    print("   ✅ Fast writes on new/cold data (LSM)")
    print("   ✅ Automatic tiering based on access patterns")
    print("   ✅ Space efficient (LSM compaction)")
    
    print("\n🌟 Real-World Examples:")
    print("   • TiDB: Hybrid storage for HTAP workloads")
    print("   • CockroachDB: Pebble engine (LSM) + Range splits")
    print("   • YugabyteDB: DocDB (RocksDB + custom layer)")
