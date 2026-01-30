# Episode 4: Binary Search Trees & AVL Trees

In-memory data structures for fast lookups.

## Files

- `bst_avl.py` - BST and AVL tree implementations

## Key Concepts

**Binary Search Tree (BST):**
- O(log n) average case
- O(n) worst case (degenerates to linked list)
- Used in: Memory indexes, small datasets

**AVL Tree (Self-Balancing BST):**
- O(log n) guaranteed (worst case)
- Maintains balance: |height(left) - height(right)| <= 1
- Uses rotations to rebalance
- Used in: In-memory caches, language runtimes

## Run

```bash
python bst_avl.py
```

## Problem Statement

**Why not use BST/AVL for databases?**
- In-memory only (no persistence)
- Poor disk I/O patterns (random access)
- Solution: B-Trees (Episode 5)
