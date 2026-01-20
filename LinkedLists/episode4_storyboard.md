# Episode 4: Time Travel – How Immutable Data Structures Power Modern Undo Systems
## Comprehensive Storyboard — Season 1, Episode 4

---

## 🎯 Presenter's Intent

**Core message**: "The real challenge isn't implementing undo. It's implementing undo across 50,000 concurrent users without corrupting state, losing history, or melting your servers. Immutable persistent data structures solve this—the same technique powering Redux, Git, and CRDTs."

**Audience**: Senior engineers who will ask:
- "Why not just deep copy on every change?" → Addressed in Act 2
- "What about memory overhead of keeping all versions?" → Acts 3-4
- "How does this work in collaborative editing?" → Act 5
- "When do immutable structures break down?" → Act 7
- "How does this relate to Redux/Git?" → Throughout

**Duration**: 35-40 minutes (can be split into two 18-20 min sessions)

---

## Narrative Arc

```
ACT 1: The Problem — Undo at Scale (4 min)
    ↓
ACT 2: LeetCode Foundation — Mutation vs Immutability (5 min)
    ↓
ACT 3: Engineering Layer 1 — Structural Sharing (6 min)
    ↓
ACT 4: Engineering Layer 2 — Persistent History DAG (5 min)
    ↓
ACT 5: Engineering Layer 3 — CRDTs for Collaboration (6 min)
    ↓
ACT 6: Engineering Layer 4 — Production Optimizations (5 min)
    ↓
ACT 7: When Immutability Breaks (4 min)
    ↓
EPILOGUE: Time Travel Debugging & What's Next (4 min)
```

---

## ACT 1: The Problem Statement (4 minutes)

### Slide 1: Opening Hook

> "You're building Google Docs. Every keystroke must be undoable. 50 users typing simultaneously. Redo must handle conflicts. History must survive crashes. And you can't melt your servers doing it."

**Visual**: Google Docs with 50 cursors typing, undo history tree branching

---

### Slide 2: The Scale Reality

**Animation**: Naive approach failing

```
Traditional approaches FAIL:

Deep copy on every change:
├── 100MB document
├── 1,000 edits/second
├── = 100GB/s memory churn
└── 💥 Server explodes

Storing deltas only:
├── Need to see state at edit #5000
├── Must replay 5000 deltas
├── = O(n) access time
└── 💥 User waits 10 seconds

Mutable structures:
├── Alice undoes at position 5
├── Bob undoes at position 5 (same time)
├── Race condition!
└── 💥 Document corrupted
```

**Say**: "None of these scale. We need something fundamentally different."

---

### Slide 3: What We Need

**Visual**: Requirements checklist

```
PRODUCTION UNDO REQUIREMENTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Instant undo/redo (O(1) or O(log n))
✓ Branching undo (undo then type = new branch)
✓ Concurrent safe (no race conditions)
✓ Memory efficient (not 100GB for 1000 edits)
✓ Crash recovery (history survives restarts)
✓ Collaborative (50 users, consistent state)
✓ Time travel (jump to ANY version instantly)
```

---

### Slide 4: The Solution Preview

**Animation**: Immutable tree with structural sharing

```
IMMUTABLE PERSISTENT DATA STRUCTURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Key insight: Values NEVER change.
Operations return NEW versions.
But... structural sharing means copying is O(log n), not O(n)!

100MB document + 1 character insert
├── Traditional: Copy 100MB → new 100MB
├── Structural sharing: Copy ~30 nodes → share rest
└── Actual copy: ~3KB!

Every version accessible. Every version immutable.
No race conditions possible.
```

---

## ACT 2: The LeetCode Foundation (5 minutes)

### Slide 5: LeetCode #1472 — Design Browser History

**Animation**: Problem statement

```python
class BrowserHistory:
    def __init__(self, homepage: str):
        """Start on homepage"""
        pass
    
    def visit(self, url: str) -> None:
        """Visit url. Clears forward history."""
        pass
    
    def back(self, steps: int) -> str:
        """Move back steps. Return current URL."""
        pass
    
    def forward(self, steps: int) -> str:
        """Move forward steps. Return current URL."""
        pass
```

**Say**: "LeetCode never asks about immutability directly. But hidden in this problem is a fundamental truth: mutation makes correctness hard."

---

### Slide 6: The Mutable Solution

**Animation**: Mutation causing problems

```python
class BrowserHistoryMutable:
    """The naive solution - works for interviews, breaks in production"""
    
    def __init__(self, homepage: str):
        self.history = [homepage]
        self.current = 0
    
    def visit(self, url: str):
        # MUTATION: destroy forward history
        self.history = self.history[:self.current + 1]  # Slice creates new list!
        self.history.append(url)  # Mutate!
        self.current += 1
    
    def back(self, steps: int) -> str:
        self.current = max(0, self.current - steps)  # Mutate pointer!
        return self.history[self.current]
```

**Highlight the problems**:
1. `self.history[:self.current + 1]` — destroys forward history forever
2. Two threads calling `visit()` simultaneously → race condition
3. No branching: once you overwrite, old path is gone

---

### Slide 7: What Mutation Breaks

**Visual**: Race condition timeline

```
THREAD A                    THREAD B
────────                    ────────
read self.current = 5
                            read self.current = 5
slice history[:6]
                            slice history[:6]
append "page_A"
                            append "page_B"
self.current = 6
                            self.current = 6

RESULT: Only one page survives! Data loss!
```

**Say**: "In production with concurrent users, mutation is a ticking time bomb."

---

### Slide 8: The Immutable Mindset Shift

**Animation**: Values vs Variables

```
MUTABLE WORLD:              IMMUTABLE WORLD:
═══════════════             ════════════════

x = [1, 2, 3]              x = [1, 2, 3]
x.append(4)                y = x + [4]  # x unchanged!

x is now [1, 2, 3, 4]      x is still [1, 2, 3]
Old value lost forever!     y is [1, 2, 3, 4]
                           Both versions exist!

Undo = ???                  Undo = just use x!
```

**Key insight**: "If values never change, undo is trivial—just point to the old version."

---

## ACT 3: Engineering Layer 1 — Structural Sharing (6 minutes)

### Slide 9: The Memory Problem

**Animation**: Naive immutability failing

```python
# Naive immutable approach:
document = "..." # 100MB of text

# Each edit creates full copy
v1 = document                      # 100MB
v2 = v1 + "a"                      # 100MB
v3 = v2 + "b"                      # 100MB
v4 = v3 + "c"                      # 100MB

# After 1000 edits: 100GB of memory!
# This is WORSE than mutable!
```

**Say**: "Naive immutability is a memory disaster. We need something smarter."

---

### Slide 10: Structural Sharing — The Breakthrough

**Animation**: Tree with shared nodes

```
STRUCTURAL SHARING
━━━━━━━━━━━━━━━━━━

Store text as a TREE, not a flat array.

Insert "X" at position 5:

BEFORE:                    AFTER:
    Root                      Root'
   /    \                    /    \
  A      B                  A      B'
 /\     /\                 /\     /\
1  2   3  4               1  2   3' 4

Only nodes along the path change!
A, 1, 2, 4 are SHARED between versions.

100MB document = ~25 levels deep
Insert = copy 25 nodes ≈ 3KB
NOT 100MB!
```

---

### Slide 11: Immutable Text Implementation

**Animation**: Code walkthrough

```python
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass(frozen=True)  # frozen = immutable!
class TextNode:
    """Immutable text node - NEVER modified after creation."""
    pass

@dataclass(frozen=True)
class Leaf(TextNode):
    """Stores actual text."""
    text: str
    
    def length(self) -> int:
        return len(self.text)

@dataclass(frozen=True)
class Branch(TextNode):
    """Combines two subtrees."""
    left: TextNode
    right: TextNode
    _length: int
    
    def length(self) -> int:
        return self._length
```

**Key point**: `frozen=True` means Python enforces immutability. No accidents.

---

### Slide 12: Insert with Structural Sharing

**Animation**: Insert operation step by step

```python
class ImmutableText:
    def __init__(self, root: TextNode):
        self.root = root
    
    def insert(self, pos: int, text: str) -> 'ImmutableText':
        """Insert text, returning NEW ImmutableText."""
        
        # Split at position
        left, right = self._split(self.root, pos)
        
        # Create new leaf for inserted text
        new_leaf = Leaf(text)
        
        # Combine: left + new_leaf + right
        new_node = Branch(left, 
                         Branch(new_leaf, right, len(text) + right.length()),
                         left.length() + len(text) + right.length())
        
        return ImmutableText(new_node)
        # Original self.root UNCHANGED!
```

**Visual**: Show old tree and new tree side by side, highlighting shared nodes

---

### Slide 13: Memory Comparison

**Animation**: Side by side comparison

```
NAIVE COPY vs STRUCTURAL SHARING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

100MB document, 1000 edits:

NAIVE COPY:
├── Each edit: 100MB copy
├── Total: 100GB
└── Time: Minutes (GC overwhelmed)

STRUCTURAL SHARING:
├── Tree depth: ~25 levels
├── Each edit: ~25 nodes copied (~3KB)
├── Total: 3MB + 100MB base = 103MB
└── Time: Microseconds per edit

IMPROVEMENT: 1000× less memory!
```

**Say**: "This is why Redux, Git, and Figma use immutable structures. The math just works."

---

## ACT 4: Engineering Layer 2 — Persistent History DAG (5 minutes)

### Slide 14: From Versions to History DAG

**Animation**: Building the history graph

```
PERSISTENT HISTORY = DIRECTED ACYCLIC GRAPH (DAG)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every edit creates a new node in the history graph.
Parent pointers enable undo.
Multiple children enable BRANCHING.

       v1 "Hello"
         │
       v2 "Hello World"
         │
       v3 "Hello World!"
        / \
       /   \
v4 "Hello!"  v5 "Hello World!!!"
(branch A)   (branch B)

Both branches exist! User can explore either!
```

---

### Slide 15: History Node Structure

**Animation**: HistoryNode fields

```python
@dataclass
class HistoryNode:
    """Node in the history DAG."""
    
    version_id: str        # Unique identifier (content-addressable hash)
    text: ImmutableText    # The actual document state
    parent: Optional[str]  # Parent version (for undo)
    timestamp: float       # When this version was created
    operation: str         # "insert(5, 'X')" - what created this
    children: Set[str]     # Child versions (for branching redo)
    
    def __init__(self, text: ImmutableText, parent: Optional[str], operation: str):
        self.text = text
        self.parent = parent
        self.operation = operation
        self.timestamp = time.time()
        self.children = set()
        
        # Content-addressable ID (like Git!)
        content = f"{text.get_text()}:{parent}:{operation}"
        self.version_id = hashlib.sha256(content.encode()).hexdigest()[:16]
```

**Key insight**: "Content-addressable IDs mean identical states have identical IDs. This enables deduplication and integrity checking—just like Git."

---

### Slide 16: Branching Undo in Action

**Animation**: User creating branches

```python
history = PersistentHistory()
history.initialize("")

# User types "Hello"
history.insert(0, "Hello")      # v1
history.insert(5, " World")     # v2: "Hello World"

# User realizes mistake, undoes
history.undo()                  # Back to v1: "Hello"

# User types something different
history.insert(5, "!")          # v3: "Hello!" (NEW BRANCH!)

# Now the history looks like:
#     v0 ""
#      │
#     v1 "Hello"
#      ├────────┐
#     v2        v3
# "Hello World" "Hello!"
```

**Say**: "Both branches preserved. User can switch between them. No data loss."

---

### Slide 17: Redo with Multiple Branches

**Animation**: Redo selection UI

```python
def redo(self) -> Optional[str]:
    """Redo - but which branch?"""
    current = self.versions[self.current_version]
    
    if not current.children:
        return None  # Nothing to redo
    
    if len(current.children) == 1:
        # Only one option - take it
        self.current_version = list(current.children)[0]
    else:
        # Multiple branches! Options:
        # 1. Pick most recent (default)
        # 2. Show user a branch picker
        # 3. Remember their previous choice
        
        children = [self.versions[cid] for cid in current.children]
        next_version = max(children, key=lambda n: n.timestamp)
        self.current_version = next_version.version_id
    
    return self.current_version
```

**Visual**: Branch picker UI mockup showing both paths

---

## ACT 5: Engineering Layer 3 — CRDTs for Collaboration (6 minutes)

### Slide 18: The Collaboration Challenge

**Animation**: Two users editing simultaneously

```
ALICE (New York)              BOB (London)
────────────────              ───────────
Document: "Hello"             Document: "Hello"

Insert "X" at pos 5           Insert "Y" at pos 5
(latency: 100ms)              (latency: 100ms)

Local result: "HelloX"        Local result: "HelloY"

─── Operations cross in transit ───

Alice receives Bob's op       Bob receives Alice's op
Apply "Y" at pos 5?           Apply "X" at pos 5?

Without coordination:
Alice: "HelloXY" or "HelloYX"?
Bob:   "HelloXY" or "HelloYX"?

MUST BE SAME! Or document diverges!
```

---

### Slide 19: Vector Clocks — Tracking Causality

**Animation**: Vector clock ticking

```python
@dataclass
class VectorClock:
    """Track causality across replicas."""
    clocks: Dict[str, int]  # replica_id → timestamp
    
    def increment(self, replica_id: str):
        self.clocks[replica_id] = self.clocks.get(replica_id, 0) + 1
    
    def happens_before(self, other: 'VectorClock') -> bool:
        """Does self causally precede other?"""
        # self < other if all self's clocks ≤ other's
        # and at least one is strictly <
        for replica_id, ts in self.clocks.items():
            if ts > other.clocks.get(replica_id, 0):
                return False
        return any(self.clocks.get(r, 0) < other.clocks.get(r, 0) 
                   for r in other.clocks)
    
    def concurrent_with(self, other: 'VectorClock') -> bool:
        """Are operations concurrent (conflict)?"""
        return not self.happens_before(other) and not other.happens_before(self)
```

**Visual**: Timeline showing concurrent operations

---

### Slide 20: Operational Transformation

**Animation**: Position transformation

```python
def transform_position(self, op: CRDTOperation) -> int:
    """Adjust position based on concurrent operations."""
    adjusted_pos = op.position
    
    for logged_op in self.operation_log:
        if logged_op.vector_clock.concurrent_with(op.vector_clock):
            # Concurrent operation! Must transform.
            
            if logged_op.op_type == 'insert' and logged_op.position <= op.position:
                # Their insert was before our position
                # Shift our position right
                adjusted_pos += len(logged_op.content)
            
            elif logged_op.op_type == 'delete' and logged_op.position < op.position:
                # Their delete was before our position
                # Shift our position left
                adjusted_pos -= min(op.position - logged_op.position, 
                                    len(logged_op.content))
    
    return max(0, adjusted_pos)
```

---

### Slide 21: CRDT Undo Across Replicas

**Animation**: Distributed undo with tombstones

```
CRDT UNDO = TOMBSTONING
━━━━━━━━━━━━━━━━━━━━━━━

Alice undoes Bob's edit:

1. Alice adds Bob's op_id to tombstones set
2. Alice broadcasts tombstone to all replicas
3. Each replica receives tombstone
4. Each replica rebuilds document, skipping tombstoned ops
5. All replicas converge to same state!

Tombstones are CRDT-safe:
├── Adding to set is commutative
├── Order doesn't matter
├── Duplicates are idempotent
└── Eventual consistency guaranteed!
```

```python
def undo_operation(self, op_id: str):
    """Undo a specific operation (works across replicas)."""
    # Add to tombstones (CRDT-safe operation)
    self.tombstones.add(op_id)
    
    # Rebuild document from scratch, skipping tombstoned ops
    self.history = PersistentHistory()
    self.history.initialize("")
    
    for op in self.operation_log:
        if op.op_id not in self.tombstones:
            # Apply non-tombstoned operations
            self._apply_operation(op)
```

---

### Slide 22: Convergence Guarantee

**Visual**: All replicas converging

```
CONVERGENCE IN ACTION
━━━━━━━━━━━━━━━━━━━━━

Initial: "Hello" (all replicas)

Alice: insert "X" at 5 (op_A)
Bob:   insert "Y" at 5 (op_B)
Carol: delete 0-2     (op_C)

After all operations delivered:

Replica A: applies op_A, receives op_B, op_C
Replica B: applies op_B, receives op_A, op_C  
Replica C: applies op_C, receives op_A, op_B

Transformation ensures ALL replicas reach: "lloXY"

Alice undoes op_A:
├── Tombstone {op_A} propagates
├── All replicas rebuild without op_A
└── All replicas converge to: "lloY"
```

---

## ACT 6: Engineering Layer 4 — Production Optimizations (5 minutes)

### Slide 23: The Memory Problem Returns

**Animation**: History growing unbounded

```
PROBLEM: Infinite History
━━━━━━━━━━━━━━━━━━━━━━━━

User edits document for 8 hours:
├── 10 edits per minute
├── 4,800 versions
├── Each version: 3KB (structural sharing)
├── Total: 14.4MB just for history pointers
├── Plus document content shared across versions
└── Still manageable!

But Google Docs at scale:
├── 1 billion documents
├── Average 5,000 versions each
├── = 5 trillion history nodes
└── 💥 Petabytes of storage!

We need: GENERATIONAL GARBAGE COLLECTION
```

---

### Slide 24: Generational History Storage

**Animation**: Hot/cold generations

```python
@dataclass
class HistoryGeneration:
    """Compressed generation of history."""
    generation_id: int
    snapshot_version: str     # Base version (full snapshot)
    snapshot_data: bytes      # Compressed full text
    deltas: List[Tuple[str, bytes]]  # (version_id, compressed delta)
    size_bytes: int
    created_at: float

class ProductionHistorySystem:
    def __init__(self, max_memory_mb: int = 100):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # HOT: Recent versions (uncompressed, fast access)
        self.hot_versions: Dict[str, HistoryNode] = {}
        
        # COLD: Old versions (compressed, slow access)
        self.generations: List[HistoryGeneration] = []
        
        # LRU tracking
        self.access_log: deque = deque(maxlen=1000)
```

---

### Slide 25: Delta Compression

**Animation**: Snapshot + deltas

```
DELTA COMPRESSION STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━

Every 100 versions:
├── Store FULL SNAPSHOT (compressed)
├── Store DELTAS for next 99 versions
└── Deltas are tiny compared to snapshots!

Version 0:   [SNAPSHOT] "Hello World..." (10KB compressed)
Version 1:   [DELTA] insert(5, "X")      (50 bytes)
Version 2:   [DELTA] delete(3, 5)        (30 bytes)
...
Version 99:  [DELTA] insert(100, "Y")    (50 bytes)
Version 100: [SNAPSHOT] "..."            (10KB compressed)

Storage: 10KB + 99×50B + 10KB = 25KB
Naive:   100 × 10KB = 1MB

COMPRESSION: 40×!
```

---

### Slide 26: Garbage Collection

**Animation**: GC removing cold generations

```python
def garbage_collect(self):
    """Remove cold generations exceeding memory budget."""
    total_size = sum(g.size_bytes for g in self.generations)
    
    if total_size <= self.max_memory_bytes:
        return  # Under budget
    
    # Identify cold generations (not recently accessed)
    cold = [g for g in self.generations 
            if g.snapshot_version not in self.hot_versions]
    
    # Sort by age (oldest first)
    cold.sort(key=lambda g: g.created_at)
    
    # Evict until under budget
    while total_size > self.max_memory_bytes and cold:
        oldest = cold.pop(0)
        self.generations.remove(oldest)
        total_size -= oldest.size_bytes
        
        # Log for debugging
        logging.info(f"GC: Evicted generation {oldest.generation_id}, "
                    f"freed {oldest.size_bytes} bytes")
```

**Key insight**: "Keep hot versions (recent edits) fast. Let cold versions (old history) be compressed or evicted."

---

## ACT 7: When Immutability Breaks (4 minutes)

### Slide 27: The Performance Trade-offs

**Animation**: Comparison matrix

```
WHEN IMMUTABILITY IS WRONG
━━━━━━━━━━━━━━━━━━━━━━━━━━

| Scenario                    | Why It Fails                    | Use Instead                |
|-----------------------------|---------------------------------|----------------------------|
| High-frequency mutations    | O(log n) copies 1M/sec = GC     | Mutable + COW when needed  |
|                             | pressure overwhelms              |                            |
| Memory-constrained          | Structural sharing still uses   | Mutable + checkpoints      |
|                             | more memory than in-place       |                            |
| Cache-hostile workloads     | Tree traversal = pointer chase  | Flat arrays, arena alloc   |
|                             | = CPU cache misses              |                            |
| Write-heavy, read-light     | Optimized for many readers      | Mutable + fine locks       |
| Real-time systems           | GC pauses break latency SLAs    | Pre-allocated pools        |
```

---

### Slide 28: The GC Pressure Problem

**Animation**: GC pauses

```python
# High-frequency edits with immutable structures:

for i in range(1_000_000):
    document = document.insert(i, "x")
    # Each iteration creates ~25 new nodes
    # Old nodes become garbage
    # GC must run every ~1000 iterations

# GC impact:
# ├── 1M iterations × 25 nodes = 25M allocations
# ├── GC pause every ~1000 iterations
# ├── Each pause: 10-100ms
# └── Total GC time: 10-100 seconds!

# For real-time games or trading systems:
# This is UNACCEPTABLE
```

**Say**: "Immutability trades CPU cycles for correctness. Sometimes that trade isn't worth it."

---

### Slide 29: When Immutability WINS

**Visual**: Perfect use cases

```
IMMUTABILITY WINS WHEN:
━━━━━━━━━━━━━━━━━━━━━━━

✅ Collaborative editing (Google Docs, Figma)
   → Many readers, branching history, conflict resolution

✅ Version control (Git, Mercurial)
   → Need every version forever, content-addressable

✅ State management (Redux, Recoil)
   → Time-travel debugging, predictable state

✅ Distributed consensus (CRDTs, Raft)
   → Eventual consistency, conflict-free merging

✅ Functional programming (Clojure, Haskell)
   → Referential transparency, easier reasoning

✅ Database snapshots (MVCC in PostgreSQL)
   → Consistent reads without locks
```

---

## EPILOGUE: Time Travel Debugging & What's Next (4 minutes)

### Slide 30: The Ultimate Application — Time Travel Debugging

**Animation**: Debugger stepping through history

```python
class TimeTravelDebugger:
    """Record execution as immutable history."""
    
    def __init__(self):
        self.frames: List[ExecutionFrame] = []  # Immutable history!
    
    def replay_to_frame(self, index: int) -> ExecutionFrame:
        """Jump to ANY point in execution history."""
        return self.frames[index]  # O(1) access to any state!
    
    def get_call_tree(self) -> Dict:
        """Visualize entire execution as tree."""
        # Because frames are immutable, this is safe!
        pass

# Usage:
debugger = TimeTravelDebugger()
debugger.start_recording()

result = fibonacci(10)  # Record entire execution

debugger.stop_recording()

# NOW: Jump to frame 50, inspect state
frame = debugger.replay_to_frame(50)
print(f"At frame 50: n={frame.local_vars['n']}")
```

**Say**: "This is how Redux DevTools works. Record every state as immutable snapshot. Jump to any point instantly."

---

### Slide 31: Production Use Cases

**Visual**: Real-world systems using immutability

```
WHO USES IMMUTABLE STRUCTURES IN PRODUCTION?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Redux (Facebook):
├── Every action creates new state
├── Time-travel debugging
└── 5M+ apps

Git (Every developer):
├── Commits are immutable
├── Content-addressable storage
└── 100M+ developers

Figma (Design tool):
├── CRDT-based collaboration
├── Branching undo across users
└── 4M+ users

Datomic (Database):
├── Immutable facts over time
├── Time-travel queries
└── Used by Nubank (50M customers)

Clojure (Language):
├── Immutable by default
├── Persistent data structures
└── Powers many fintech systems
```

---

### Slide 32: Key Takeaways

**Visual**: Summary checklist

```
EPISODE 4 TAKEAWAYS
━━━━━━━━━━━━━━━━━━━

1. Mutation makes correctness hard
   → Race conditions, lost history, debugging nightmares

2. Immutability enables time travel
   → Every version preserved, instant access to any state

3. Structural sharing makes it efficient
   → O(log n) copies, not O(n)

4. DAGs enable branching history
   → Undo, redo, branch, merge — all preserved

5. CRDTs enable distributed undo
   → Eventual consistency, conflict-free collaboration

6. Know when NOT to use it
   → High-frequency mutations, real-time systems, cache-critical
```

---

### Slide 33: What's Next — Episode 5

**Visual**: LRU Cache teaser

> "You now understand how immutability enables correctness. But what happens when your immutable history grows to 100GB? How do you decide what to keep and what to evict?"

```
EPISODE 5: LRU Caches at Scale
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Challenge: 100,000 requests/sec with <1ms p99 latency

You'll build:
├── O(1) get/put/evict (doubly linked list + hashmap)
├── Resource type quotas (images vs scripts vs fonts)
├── Proactive eviction under memory pressure
├── Zero heap allocations in hot path
└── No lock contention between reader threads

The data structure: Doubly linked list meets hashmap.
The engineering: Cache-oblivious algorithms and lock-free design.
```

---

## 🎨 Animation Requirements

### Animation 1: Naive Copy vs Structural Sharing
- Split screen
- Left: full document copy (slow, red)
- Right: tree with few nodes changing (fast, green)
- Memory counter comparison

### Animation 2: History DAG Building
- Start with root node
- Each edit adds a node
- Branches form when undo + new edit
- Show parent/child pointers

### Animation 3: Concurrent Editing Timeline
- Two users (Alice, Bob) on timeline
- Operations crossing in transit
- Show conflict detection
- Show transformation result
- Convergence to same state

### Animation 4: Vector Clock Ticking
- Two clocks side by side
- Each operation increments
- Show happens-before relationships
- Show concurrent (conflict) case

### Animation 5: CRDT Tombstoning
- Operation applied to all replicas
- Undo adds tombstone
- Tombstone propagates
- All replicas rebuild without tombstoned op
- Convergence visualization

### Animation 6: Generational GC
- Hot tier (recent, uncompressed)
- Cold tier (old, compressed)
- GC moving versions from hot to cold
- Eviction when over budget

### Animation 7: Time Travel Debugger
- Code execution with frames recording
- Slider to jump to any frame
- State inspection at selected frame
- Call tree visualization

---

## 📊 Senior Engineer FAQ

**Q: "How is this different from event sourcing?"**
A: Event sourcing stores events (deltas), immutable structures store snapshots. Both are immutable, but snapshots give O(1) state access while events require O(n) replay. Hybrid approach: event sourcing with periodic snapshots.

**Q: "What's the overhead of content-addressable IDs?"**
A: SHA-256 is fast (~500MB/s on modern CPUs). For a 100KB document, hashing takes ~0.2ms. Amortized over many reads, it's negligible. The benefit: deduplication and integrity checking.

**Q: "How do CRDTs handle delete-delete conflicts?"**
A: Deleting already-deleted text is a no-op. The tombstone set is idempotent. Both deletes add the same op_id to tombstones, result is identical.

**Q: "Can you do partial document collaboration?"**
A: Yes! CRDTs can be scoped to subtrees. Notion does this—each block is a separate CRDT, reducing conflict scope.

**Q: "How do you GC in a collaborative system?"**
A: Requires consensus. All replicas must agree on which versions can be GC'd. Typically: keep all versions from last N days, require acknowledgment before purging.

**Q: "What about the rope data structure?"**
A: Ropes are a specific implementation of immutable text. Our tree-based approach is similar. Production systems like VS Code use ropes (actually "piece tables") for efficient text editing.

---

## 🎯 Key Moments to Nail

| Time | Moment | Why It Matters |
|------|--------|----------------|
| 0:30 | "50 users, 50,000 undos, no corruption" | Scale hook |
| 3:00 | Race condition diagram | Why mutation fails |
| 8:00 | "Copy 25 nodes, not 100MB" | Structural sharing breakthrough |
| 15:00 | Branching undo demo | "Both paths preserved!" |
| 22:00 | CRDT convergence visual | Distributed magic |
| 30:00 | "Know when NOT to use it" | Engineering judgment |
| 35:00 | Redux DevTools connection | Real-world relevance |

---

## 🔧 Technical Accuracy Checklist

- [x] Structural sharing achieves O(log n) copy instead of O(n)
- [x] Content-addressable IDs enable deduplication (like Git)
- [x] Vector clocks track causality for conflict detection
- [x] Operational transformation adjusts positions for concurrent edits
- [x] Tombstones are CRDT-safe (commutative, idempotent)
- [x] Generational GC separates hot (fast) from cold (compressed)
- [x] GC pressure is real concern for high-frequency mutations

---

## 📁 Deliverables

1. **episode4_revealjs.html** — Full Reveal.js presentation
2. **episode4_animations.html** — Standalone interactive animations  
3. **episode4_storyboard.md** — This file (presenter notes)
4. **LinkedLists/Chapter 4.md** — Source content

---

## 🎬 Suggested Session Split

**Option A: Single 40-minute session**
- Full presentation, technical deep dive

**Option B: Two 20-minute sessions**
- **Session 1** (Acts 1-4): "Immutability Fundamentals" — Structural sharing to persistent history
- **Session 2** (Acts 5-7): "Distributed Undo & Production" — CRDTs, GC, when not to use

---

## 🏆 Challenge for the Audience

> "Design an undo system for a collaborative spreadsheet where users can undo their own changes without affecting others' work. How would you track which operations belong to which user while maintaining a consistent view for everyone?"

**Hint**: Each user has their own "view" of the history DAG. Undoing traverses only your operations while keeping others' changes. Use operation metadata (user_id) combined with vector clocks to determine which operations to skip during rebuild.

---

## Interactive Code Demos

### Demo 1: Structural Sharing Visualization
```python
# Show memory savings with structural sharing
text1 = ImmutableText.from_string("Hello World")
text2 = text1.insert(5, "Beautiful ")

print(f"text1: {text1.get_text()}")  # "Hello World"
print(f"text2: {text2.get_text()}")  # "Hello Beautiful World"
print(f"Shared nodes: {text1.count_shared_nodes(text2)}")
```

### Demo 2: Branching Undo
```python
# Show branching history
history = PersistentHistory()
history.initialize("")

history.insert(0, "Hello")      # v1
history.insert(5, " World")     # v2
history.undo()                   # back to v1
history.insert(5, "!")          # v3 (new branch!)

print(history.get_branches())    # Shows both v2 and v3
```

### Demo 3: CRDT Convergence
```python
# Show two replicas converging
alice = CRDTDocument("alice")
bob = CRDTDocument("bob")

alice.insert(0, "Hello")
bob.insert(0, "World")

# Exchange operations
alice.receive(bob.get_operations())
bob.receive(alice.get_operations())

assert alice.get_text() == bob.get_text()  # Converged!
```

---

## Episode Metadata

**Prerequisites**: 
- Episode 3 (doubly linked lists, browser history)
- Basic tree data structures

**Key Terms Introduced**:
- Immutability
- Structural sharing
- Persistent data structures
- History DAG
- Vector clocks
- CRDTs (Conflict-free Replicated Data Types)
- Operational transformation
- Tombstoning

**Connections to Other Episodes**:
- Episode 1-2: Linear history → branching history (DAG)
- Episode 3: Browser history → undo history (more complex)
- Episode 5: LRU cache for history eviction
- Episode 6: Distributed systems → CRDTs at scale
- Episode 7: Ring buffers for operation logs

**Real-World Systems Referenced**:
- Redux, Recoil (state management)
- Git, Mercurial (version control)
- Figma, Google Docs (collaborative editing)
- Datomic (immutable database)
- Clojure (functional language)

---

## Production Code Repository Structure

```
episode4-immutable-undo/
├── basic/
│   ├── mutable_history.py          # Mutable solution (problems)
│   ├── immutable_text.py           # ImmutableText with structural sharing
│   └── test_basic.py
├── history/
│   ├── history_node.py             # HistoryNode (DAG node)
│   ├── persistent_history.py       # PersistentHistory (branching undo)
│   └── test_history.py
├── crdt/
│   ├── vector_clock.py             # VectorClock implementation
│   ├── crdt_document.py            # CRDTDocument with OT
│   ├── tombstone.py                # Tombstone-based undo
│   └── test_crdt.py
├── production/
│   ├── generational_gc.py          # ProductionHistorySystem
│   ├── delta_compression.py        # Snapshot + delta storage
│   └── test_production.py
└── benchmarks/
    ├── structural_sharing.py       # Memory savings measurement
    ├── gc_pressure.py              # GC impact analysis
    └── convergence_time.py         # CRDT convergence benchmarks
```

---

*"The real challenge isn't implementing undo. It's implementing undo that works when 50 users are all undoing at once. Immutability makes that possible."*
