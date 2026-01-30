"""
Buffer Pool - Memory Management Layer

Caches hot pages in RAM to avoid disk I/O.
Disk is 100,000× slower than RAM!
"""

import time
from typing import Optional, Any, Dict, Set
from collections import OrderedDict


class BufferPool:
    """
    Buffer Pool with LRU eviction policy.
    
    Sits between Storage Engine and Disk:
    - Storage engine calls: buffer_pool.get_page(page_id)
    - Buffer pool decides: RAM cache hit OR disk read
    
    Used by: PostgreSQL (shared_buffers), MySQL (innodb_buffer_pool_size)
    """
    
    def __init__(self, capacity_mb: int = 1024, page_size: int = 4096):
        """
        Args:
            capacity_mb: Buffer pool size in megabytes
            page_size: Page size in bytes (typically 4KB or 8KB)
        """
        self.capacity = capacity_mb * 1024 * 1024 // page_size  # Pages
        self.page_size = page_size
        
        # LRU cache: OrderedDict maintains insertion/access order
        self.cache: OrderedDict[int, bytes] = OrderedDict()
        self.dirty_pages: Set[int] = set()  # Modified but not written
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.disk_reads = 0
        self.disk_writes = 0
    
    def get_page(self, page_id: int, disk_storage: Dict[int, bytes]) -> bytes:
        """
        Get page from buffer pool or disk.
        
        Args:
            page_id: Page to fetch
            disk_storage: Simulated disk storage
            
        Returns:
            Page data
        """
        # Check cache first
        if page_id in self.cache:
            self.hits += 1
            # Move to end (most recently used)
            self.cache.move_to_end(page_id)
            return self.cache[page_id]  # ⚡ Cache hit: 100ns
        
        # Cache miss: Load from disk
        self.misses += 1
        self.disk_reads += 1
        page_data = self._disk_read(page_id, disk_storage)  # 💥 Disk read: 10ms
        
        # Evict LRU page if cache full
        if len(self.cache) >= self.capacity:
            self._evict_lru_page(disk_storage)
        
        # Add new page to cache
        self.cache[page_id] = page_data
        return page_data
    
    def put_page(self, page_id: int, page_data: bytes) -> None:
        """
        Update page in buffer pool (mark as dirty).
        
        Write-back strategy: Don't write to disk immediately.
        Batch writes for better performance.
        """
        self.cache[page_id] = page_data
        self.cache.move_to_end(page_id)
        self.dirty_pages.add(page_id)
    
    def flush_dirty_pages(self, disk_storage: Dict[int, bytes]) -> None:
        """
        Write all dirty pages to disk.
        
        Called during:
        - Checkpoint
        - Graceful shutdown
        - When dirty page ratio too high
        """
        print(f"\n💾 Flushing {len(self.dirty_pages)} dirty pages to disk...")
        
        for page_id in list(self.dirty_pages):
            if page_id in self.cache:
                self._disk_write(page_id, self.cache[page_id], disk_storage)
                self.dirty_pages.remove(page_id)
        
        print(f"✅ Flush complete!")
    
    def _evict_lru_page(self, disk_storage: Dict[int, bytes]) -> None:
        """
        Evict least recently used page.
        
        If page is dirty, write it back to disk first.
        """
        # Get LRU page (first item in OrderedDict)
        victim_id, victim_data = self.cache.popitem(last=False)
        self.evictions += 1
        
        # Write back if dirty
        if victim_id in self.dirty_pages:
            self._disk_write(victim_id, victim_data, disk_storage)
            self.dirty_pages.remove(victim_id)
    
    def _disk_read(self, page_id: int, disk_storage: Dict[int, bytes]) -> bytes:
        """Simulate disk read (10ms latency)."""
        # In production: fseek() + fread()
        time.sleep(0.00001)  # 10 microseconds (scaled down)
        return disk_storage.get(page_id, b'\x00' * self.page_size)
    
    def _disk_write(self, page_id: int, data: bytes, disk_storage: Dict[int, bytes]) -> None:
        """Simulate disk write (10ms latency)."""
        # In production: fseek() + fwrite() + fsync()
        time.sleep(0.00001)  # 10 microseconds (scaled down)
        disk_storage[page_id] = data
        self.disk_writes += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer pool statistics."""
        total_accesses = self.hits + self.misses
        hit_rate = (self.hits / total_accesses * 100) if total_accesses > 0 else 0
        
        return {
            'capacity_pages': self.capacity,
            'used_pages': len(self.cache),
            'dirty_pages': len(self.dirty_pages),
            'hit_rate': f"{hit_rate:.1f}%",
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'disk_reads': self.disk_reads,
            'disk_writes': self.disk_writes,
        }
    
    def print_stats(self) -> None:
        """Print buffer pool statistics."""
        stats = self.get_stats()
        print("\n" + "=" * 60)
        print("Buffer Pool Statistics")
        print("=" * 60)
        for key, value in stats.items():
            print(f"{key:20}: {value}")


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Buffer Pool Demo")
    print("=" * 60)
    
    # Create buffer pool (small capacity to demonstrate eviction)
    buffer_pool = BufferPool(capacity_mb=1, page_size=4096)  # 256 pages
    disk_storage = {}
    
    # Simulate disk with 1000 pages
    print(f"\n📀 Initializing disk with 1000 pages...")
    for i in range(1000):
        disk_storage[i] = f"Page {i} data".encode().ljust(4096, b'\x00')
    
    # Access pages (first access = cache miss)
    print(f"\n📖 Reading pages 0-99 (should cause cache misses)...")
    for i in range(100):
        data = buffer_pool.get_page(i, disk_storage)
    
    buffer_pool.print_stats()
    
    # Access same pages again (should be cache hits!)
    print(f"\n📖 Reading pages 0-99 again (should be cache hits!)...")
    for i in range(100):
        data = buffer_pool.get_page(i, disk_storage)
    
    buffer_pool.print_stats()
    
    # Modify some pages (mark dirty)
    print(f"\n✏️  Modifying pages 10-19...")
    for i in range(10, 20):
        new_data = f"Modified page {i}".encode().ljust(4096, b'\x00')
        buffer_pool.put_page(i, new_data)
    
    buffer_pool.print_stats()
    
    # Flush dirty pages
    buffer_pool.flush_dirty_pages(disk_storage)
    
    buffer_pool.print_stats()
    
    # Access many pages to cause evictions
    print(f"\n📖 Reading pages 0-500 (will cause evictions)...")
    for i in range(500):
        data = buffer_pool.get_page(i, disk_storage)
    
    buffer_pool.print_stats()
    
    print(f"\n💡 Key Insights:")
    print(f"   - Cache hit rate: {buffer_pool.hits / (buffer_pool.hits + buffer_pool.misses) * 100:.1f}%")
    print(f"   - Disk reads avoided: {buffer_pool.hits} (would be 10ms each!)")
    print(f"   - Evictions: {buffer_pool.evictions} (LRU pages removed)")
    print(f"\n🎯 Production config examples:")
    print(f"   PostgreSQL: shared_buffers = 8GB (25% of RAM)")
    print(f"   MySQL: innodb_buffer_pool_size = 64GB (70-80% of RAM)")
