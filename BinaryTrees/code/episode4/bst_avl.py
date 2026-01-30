"""
Episode 4: Binary Search Trees and AVL Trees
In-memory data structures for fast lookups
"""

from typing import Optional, Any, List


class BSTNode:
    """Binary Search Tree Node."""
    
    def __init__(self, key: int, value: Any):
        self.key = key
        self.value = value
        self.left: Optional['BSTNode'] = None
        self.right: Optional['BSTNode'] = None


class BinarySearchTree:
    """
    Binary Search Tree
    
    Operations: O(log n) average, O(n) worst case
    Problem: Can become unbalanced
    """
    
    def __init__(self):
        self.root: Optional[BSTNode] = None
        self.size = 0
    
    def insert(self, key: int, value: Any) -> None:
        """Insert key-value pair."""
        if self.root is None:
            self.root = BSTNode(key, value)
            self.size += 1
        else:
            self._insert_recursive(self.root, key, value)
    
    def _insert_recursive(self, node: BSTNode, key: int, value: Any) -> BSTNode:
        """Helper: Insert recursively."""
        if key < node.key:
            if node.left is None:
                node.left = BSTNode(key, value)
                self.size += 1
            else:
                self._insert_recursive(node.left, key, value)
        elif key > node.key:
            if node.right is None:
                node.right = BSTNode(key, value)
                self.size += 1
            else:
                self._insert_recursive(node.right, key, value)
        else:
            # Update existing key
            node.value = value
        
        return node
    
    def search(self, key: int) -> Optional[Any]:
        """Search for key."""
        return self._search_recursive(self.root, key)
    
    def _search_recursive(self, node: Optional[BSTNode], key: int) -> Optional[Any]:
        """Helper: Search recursively."""
        if node is None:
            return None
        
        if key == node.key:
            return node.value
        elif key < node.key:
            return self._search_recursive(node.left, key)
        else:
            return self._search_recursive(node.right, key)
    
    def inorder_traversal(self) -> List[tuple]:
        """Return sorted list of (key, value) pairs."""
        result = []
        self._inorder_recursive(self.root, result)
        return result
    
    def _inorder_recursive(self, node: Optional[BSTNode], result: List) -> None:
        """Helper: Inorder traversal."""
        if node is not None:
            self._inorder_recursive(node.left, result)
            result.append((node.key, node.value))
            self._inorder_recursive(node.right, result)
    
    def height(self) -> int:
        """Calculate tree height."""
        return self._height_recursive(self.root)
    
    def _height_recursive(self, node: Optional[BSTNode]) -> int:
        """Helper: Calculate height recursively."""
        if node is None:
            return 0
        return 1 + max(self._height_recursive(node.left), 
                       self._height_recursive(node.right))


class AVLNode:
    """AVL Tree Node (with balance factor)."""
    
    def __init__(self, key: int, value: Any):
        self.key = key
        self.value = value
        self.left: Optional['AVLNode'] = None
        self.right: Optional['AVLNode'] = None
        self.height = 1  # New node has height 1


class AVLTree:
    """
    AVL Tree - Self-Balancing BST
    
    Guarantees: O(log n) for all operations (worst case)
    Maintains balance: |height(left) - height(right)| <= 1
    """
    
    def __init__(self):
        self.root: Optional[AVLNode] = None
        self.size = 0
    
    def insert(self, key: int, value: Any) -> None:
        """Insert and rebalance."""
        self.root = self._insert_recursive(self.root, key, value)
    
    def _insert_recursive(self, node: Optional[AVLNode], key: int, value: Any) -> AVLNode:
        """Insert recursively and rebalance."""
        # Standard BST insertion
        if node is None:
            self.size += 1
            return AVLNode(key, value)
        
        if key < node.key:
            node.left = self._insert_recursive(node.left, key, value)
        elif key > node.key:
            node.right = self._insert_recursive(node.right, key, value)
        else:
            node.value = value  # Update
            return node
        
        # Update height
        node.height = 1 + max(self._get_height(node.left), 
                              self._get_height(node.right))
        
        # Get balance factor
        balance = self._get_balance(node)
        
        # Rebalance if needed
        # Left-Left case
        if balance > 1 and key < node.left.key:
            return self._rotate_right(node)
        
        # Right-Right case
        if balance < -1 and key > node.right.key:
            return self._rotate_left(node)
        
        # Left-Right case
        if balance > 1 and key > node.left.key:
            node.left = self._rotate_left(node.left)
            return self._rotate_right(node)
        
        # Right-Left case
        if balance < -1 and key < node.right.key:
            node.right = self._rotate_right(node.right)
            return self._rotate_left(node)
        
        return node
    
    def _rotate_left(self, z: AVLNode) -> AVLNode:
        """Left rotation."""
        y = z.right
        T2 = y.left
        
        # Perform rotation
        y.left = z
        z.right = T2
        
        # Update heights
        z.height = 1 + max(self._get_height(z.left), self._get_height(z.right))
        y.height = 1 + max(self._get_height(y.left), self._get_height(y.right))
        
        return y
    
    def _rotate_right(self, z: AVLNode) -> AVLNode:
        """Right rotation."""
        y = z.left
        T3 = y.right
        
        # Perform rotation
        y.right = z
        z.left = T3
        
        # Update heights
        z.height = 1 + max(self._get_height(z.left), self._get_height(z.right))
        y.height = 1 + max(self._get_height(y.left), self._get_height(y.right))
        
        return y
    
    def _get_height(self, node: Optional[AVLNode]) -> int:
        """Get node height."""
        if node is None:
            return 0
        return node.height
    
    def _get_balance(self, node: Optional[AVLNode]) -> int:
        """Get balance factor."""
        if node is None:
            return 0
        return self._get_height(node.left) - self._get_height(node.right)
    
    def search(self, key: int) -> Optional[Any]:
        """Search for key."""
        return self._search_recursive(self.root, key)
    
    def _search_recursive(self, node: Optional[AVLNode], key: int) -> Optional[Any]:
        """Search recursively."""
        if node is None:
            return None
        
        if key == node.key:
            return node.value
        elif key < node.key:
            return self._search_recursive(node.left, key)
        else:
            return self._search_recursive(node.right, key)
    
    def inorder_traversal(self) -> List[tuple]:
        """Return sorted list."""
        result = []
        self._inorder_recursive(self.root, result)
        return result
    
    def _inorder_recursive(self, node: Optional[AVLNode], result: List) -> None:
        """Inorder traversal."""
        if node:
            self._inorder_recursive(node.left, result)
            result.append((node.key, node.value))
            self._inorder_recursive(node.right, result)


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("Episode 4: Binary Search Trees")
    print("=" * 70)
    
    # BST Example
    print("\n📝 Binary Search Tree (unbalanced):")
    bst = BinarySearchTree()
    
    # Insert in order (worst case - becomes linked list!)
    for i in [1, 2, 3, 4, 5, 6, 7]:
        bst.insert(i, f"value_{i}")
    
    print(f"   Height: {bst.height()} (unbalanced!)")
    print(f"   Search 5: {bst.search(5)}")
    
    # AVL Example
    print("\n🌳 AVL Tree (self-balancing):")
    avl = AVLTree()
    
    # Same insertion order
    for i in [1, 2, 3, 4, 5, 6, 7]:
        avl.insert(i, f"value_{i}")
    
    print(f"   Height: {avl._get_height(avl.root)} (balanced!)")
    print(f"   Search 5: {avl.search(5)}")
    
    print("\n💡 Key Difference:")
    print(f"   BST: Height = {bst.height()} (O(n) worst case)")
    print(f"   AVL: Height = {avl._get_height(avl.root)} (O(log n) guaranteed)")
    
    print("\n✅ AVL trees maintain balance through rotations!")
    print("   - Left rotation: Fix right-heavy unbalance")
    print("   - Right rotation: Fix left-heavy unbalance")
    print("   - Guarantees O(log n) for all operations")
