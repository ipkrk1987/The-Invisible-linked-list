"""
Episode 5: B-Trees - Disk-Optimized Data Structures
100+ keys per node = fewer disk seeks!
"""

from typing import Optional, List, Tuple, Any


class BTreeNode:
    """
    B-Tree Node
    
    Properties:
    - Contains multiple keys (not just 1 like BST)
    - All leaves at same level
    - Minimizes disk I/O
    """
    
    def __init__(self, is_leaf: bool = True):
        self.keys: List[int] = []
        self.values: List[Any] = []
        self.children: List['BTreeNode'] = []
        self.is_leaf = is_leaf
    
    def is_full(self, order: int) -> bool:
        """Check if node needs to split."""
        return len(self.keys) >= order - 1


class BTree:
    """
    B-Tree: Optimized for disk storage
    
    Key properties:
    - Order M: Each node has M-1 to M keys
    - Balanced: All leaves at same depth
    - Fanout ~100: log₁₀₀(1M) = 3 seeks vs log₂(1M) = 20 seeks in BST
    
    Used by: PostgreSQL, MySQL InnoDB, SQLite
    """
    
    def __init__(self, order: int = 5):
        """
        Args:
            order: Maximum number of children per node
                   Typical values: 100-1000 (for 4KB pages)
        """
        self.root = BTreeNode()
        self.order = order
        self.size = 0
    
    def search(self, key: int) -> Optional[Any]:
        """
        Search for key: O(log n) with large fanout.
        
        For 1M keys with order=100:
        - Height = log₁₀₀(1,000,000) ≈ 3
        - Disk seeks = 3 (vs 20 in BST!)
        """
        return self._search_recursive(self.root, key)
    
    def _search_recursive(self, node: BTreeNode, key: int) -> Optional[Any]:
        """Search recursively through tree."""
        # Binary search within node
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1
        
        # Found key
        if i < len(node.keys) and key == node.keys[i]:
            return node.values[i]
        
        # Key not found, search children if not leaf
        if node.is_leaf:
            return None
        else:
            return self._search_recursive(node.children[i], key)
    
    def insert(self, key: int, value: Any) -> None:
        """
        Insert key-value pair.
        May cause splits to maintain B-Tree properties.
        """
        root = self.root
        
        # If root is full, split it
        if root.is_full(self.order):
            new_root = BTreeNode(is_leaf=False)
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root
        
        self._insert_non_full(self.root, key, value)
        self.size += 1
    
    def _insert_non_full(self, node: BTreeNode, key: int, value: Any) -> None:
        """Insert into node that is not full."""
        i = len(node.keys) - 1
        
        if node.is_leaf:
            # Insert in leaf node
            node.keys.append(None)
            node.values.append(None)
            
            while i >= 0 and key < node.keys[i]:
                node.keys[i + 1] = node.keys[i]
                node.values[i + 1] = node.values[i]
                i -= 1
            
            node.keys[i + 1] = key
            node.values[i + 1] = value
        else:
            # Find child to insert into
            while i >= 0 and key < node.keys[i]:
                i -= 1
            i += 1
            
            # Split child if full
            if node.children[i].is_full(self.order):
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            
            self._insert_non_full(node.children[i], key, value)
    
    def _split_child(self, parent: BTreeNode, index: int) -> None:
        """
        Split child node at index.
        
        This is the key operation that maintains balance:
        - Median key moves up to parent
        - Node splits into two half-full nodes
        """
        order = self.order
        child = parent.children[index]
        new_child = BTreeNode(is_leaf=child.is_leaf)
        
        # Split point
        mid = len(child.keys) // 2
        
        # Move median key up to parent
        parent.keys.insert(index, child.keys[mid])
        parent.values.insert(index, child.values[mid])
        parent.children.insert(index + 1, new_child)
        
        # Split keys/values
        new_child.keys = child.keys[mid + 1:]
        new_child.values = child.values[mid + 1:]
        child.keys = child.keys[:mid]
        child.values = child.values[:mid]
        
        # Split children if not leaf
        if not child.is_leaf:
            new_child.children = child.children[mid + 1:]
            child.children = child.children[:mid + 1]
    
    def range_scan(self, start_key: int, end_key: int) -> List[Tuple[int, Any]]:
        """
        Range query: Find all keys in [start_key, end_key].
        
        Without B+Tree optimization: Need to traverse entire tree
        With B+Tree: Leaves are linked, just walk the linked list!
        """
        results = []
        self._range_scan_recursive(self.root, start_key, end_key, results)
        return results
    
    def _range_scan_recursive(self, node: BTreeNode, start: int, end: int, results: List) -> None:
        """Collect keys in range."""
        i = 0
        
        while i < len(node.keys):
            if node.is_leaf:
                # Leaf node: Check if key in range
                if start <= node.keys[i] <= end:
                    results.append((node.keys[i], node.values[i]))
                elif node.keys[i] > end:
                    break
                i += 1
            else:
                # Internal node: Recurse on appropriate children
                if start <= node.keys[i]:
                    self._range_scan_recursive(node.children[i], start, end, results)
                i += 1
        
        # Visit rightmost child if not leaf
        if not node.is_leaf and i < len(node.children):
            self._range_scan_recursive(node.children[i], start, end, results)


class BPlusTreeNode:
    """
    B+Tree Node (linked leaves for fast range scans).
    """
    
    def __init__(self, is_leaf: bool = True):
        self.keys: List[int] = []
        self.is_leaf = is_leaf
        
        if is_leaf:
            self.values: List[Any] = []
            self.next: Optional['BPlusTreeNode'] = None  # Linked list!
        else:
            self.children: List['BPlusTreeNode'] = []


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("Episode 5: B-Trees - Disk-Optimized Storage")
    print("=" * 70)
    
    # Create B-Tree with order 5 (for demonstration)
    btree = BTree(order=5)
    
    print("\n📝 Inserting data into B-Tree...")
    for i in [10, 20, 5, 6, 12, 30, 7, 17, 3, 15]:
        btree.insert(i, f"value_{i}")
        print(f"   Inserted {i}")
    
    print(f"\n📊 B-Tree stats:")
    print(f"   Size: {btree.size} keys")
    print(f"   Order: {btree.order} (max {btree.order-1} keys per node)")
    
    print(f"\n🔍 Searching:")
    for key in [10, 12, 100]:
        value = btree.search(key)
        print(f"   Key {key}: {value if value else 'Not found'}")
    
    print(f"\n📈 Range scan [5, 15]:")
    results = btree.range_scan(5, 15)
    for key, value in results:
        print(f"   {key}: {value}")
    
    print("\n💡 Why B-Trees Beat BST for Databases:")
    print("   1. High fanout: log₁₀₀(1M) = 3 vs log₂(1M) = 20")
    print("   2. Disk I/O: 3 seeks vs 20 seeks")
    print("   3. Cache-friendly: 100+ keys per 4KB page")
    print("\n✅ Used by PostgreSQL, MySQL, SQLite!")
