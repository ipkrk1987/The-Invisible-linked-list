"""
Free List - Space Management and Page Recycling

Prevents database from growing forever by reusing deleted pages.
"""

from typing import List, Set, Optional


class FreeList:
    """
    Tracks deleted/unused pages for recycling.
    
    When storage engine needs a page:
    1. Check free list first
    2. If empty, allocate new page
    
    When page is deleted:
    1. Add to free list
    2. Don't physically delete (can reuse later)
    """
    
    def __init__(self):
        self.free_pages: List[int] = []  # Stack of available page IDs
        self.next_page_id: int = 0        # If free list empty, allocate new
        
    def allocate_page(self) -> int:
        """
        Get a page for writing new data.
        
        Returns:
            Page ID to use
        """
        if self.free_pages:
            # Recycle deleted page ♻️
            page_id = self.free_pages.pop()
            print(f"♻️  Recycling page {page_id}")
            return page_id
        else:
            # Allocate brand new page
            page_id = self.next_page_id
            self.next_page_id += 1
            print(f"🆕 Allocating new page {page_id}")
            return page_id
    
    def free_page(self, page_id: int) -> None:
        """
        Mark page as available for reuse.
        
        Don't physically delete! Just mark as recyclable.
        """
        if page_id not in self.free_pages:
            self.free_pages.append(page_id)
            print(f"🗑️  Freed page {page_id} (available for reuse)")
    
    def get_fragmentation(self) -> float:
        """
        Calculate fragmentation: % of allocated pages that are free.
        
        High fragmentation (>50%) = time to compact!
        """
        if self.next_page_id == 0:
            return 0.0
        
        return len(self.free_pages) / self.next_page_id
    
    def compact(self, data_pages: dict) -> dict:
        """
        Compact database: Move data to eliminate fragmentation.
        
        This is what PostgreSQL VACUUM FULL does.
        
        Args:
            data_pages: Current page_id → data mapping
            
        Returns:
            New compacted page_id → data mapping
        """
        print("\n🔄 Starting compaction...")
        
        # Copy live data to new pages (sequential)
        new_pages = {}
        new_page_id = 0
        mapping = {}  # old_page_id → new_page_id
        
        for old_page_id in sorted(data_pages.keys()):
            data = data_pages[old_page_id]
            if data is not None:  # Skip deleted data
                new_pages[new_page_id] = data
                mapping[old_page_id] = new_page_id
                new_page_id += 1
        
        # Reset free list
        self.free_pages.clear()
        self.next_page_id = new_page_id
        
        fragmentation_before = self.get_fragmentation()
        fragmentation_after = 0.0
        
        print(f"✅ Compaction complete!")
        print(f"   Pages before: {len(data_pages)}")
        print(f"   Pages after: {len(new_pages)}")
        print(f"   Space reclaimed: {len(data_pages) - len(new_pages)} pages")
        
        return new_pages


class FreeListPage:
    """
    Alternative: Store free list as linked pages.
    
    PostgreSQL uses this approach:
    - Page 0 = FSM (Free Space Map) metadata
    - Each deleted page stores next_free_page_id in first bytes
    """
    
    def __init__(self, page_id: int, next_free_page_id: Optional[int] = None):
        self.page_id = page_id
        self.next_free_page_id = next_free_page_id  # Linked list
    
    def serialize(self) -> bytes:
        """Serialize to first 8 bytes of page."""
        import struct
        return struct.pack('II', self.page_id, self.next_free_page_id or 0)
    
    @staticmethod
    def deserialize(data: bytes) -> 'FreeListPage':
        """Deserialize from first 8 bytes."""
        import struct
        page_id, next_id = struct.unpack('II', data[:8])
        return FreeListPage(page_id, next_id if next_id != 0 else None)


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Free List Demo")
    print("=" * 60)
    
    free_list = FreeList()
    data_pages = {}
    
    # Allocate 10 pages
    print("\n📝 Allocating 10 pages...")
    for i in range(10):
        page_id = free_list.allocate_page()
        data_pages[page_id] = f"Data block {i}"
    
    print(f"\nTotal pages allocated: {free_list.next_page_id}")
    print(f"Pages in free list: {len(free_list.free_pages)}")
    print(f"Fragmentation: {free_list.get_fragmentation():.1%}")
    
    # Delete some pages
    print("\n🗑️  Deleting pages 2, 5, 7...")
    for page_id in [2, 5, 7]:
        free_list.free_page(page_id)
        data_pages[page_id] = None
    
    print(f"Pages in free list: {len(free_list.free_pages)}")
    print(f"Fragmentation: {free_list.get_fragmentation():.1%}")
    
    # Allocate more pages (should reuse freed pages)
    print("\n📝 Allocating 5 more pages...")
    for i in range(10, 15):
        page_id = free_list.allocate_page()
        data_pages[page_id] = f"Data block {i}"
    
    print(f"\nTotal pages allocated: {free_list.next_page_id}")
    print(f"Pages in free list: {len(free_list.free_pages)}")
    print(f"Fragmentation: {free_list.get_fragmentation():.1%}")
    
    # Compact database
    print("\n" + "=" * 60)
    print("Compaction")
    print("=" * 60)
    
    # Delete more pages to increase fragmentation
    for page_id in [0, 1, 3, 4, 6, 8, 9]:
        free_list.free_page(page_id)
        data_pages[page_id] = None
    
    print(f"\nBefore compaction:")
    print(f"  Total pages: {free_list.next_page_id}")
    print(f"  Free pages: {len(free_list.free_pages)}")
    print(f"  Fragmentation: {free_list.get_fragmentation():.1%}")
    
    # Compact
    new_data_pages = free_list.compact(data_pages)
    
    print(f"\nAfter compaction:")
    print(f"  Total pages: {free_list.next_page_id}")
    print(f"  Free pages: {len(free_list.free_pages)}")
    print(f"  Fragmentation: {free_list.get_fragmentation():.1%}")
    
    print(f"\nRemaining data:")
    for page_id, data in sorted(new_data_pages.items()):
        print(f"  Page {page_id}: {data}")
