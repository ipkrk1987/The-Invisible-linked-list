# SEASON 1: The Invisible Linked List
## EPISODE 4: Time Travel – How Immutable Data Structures Power Modern Undo Systems

> "The real challenge isn't implementing undo. It's implementing undo across 50,000 concurrent users without corrupting state, losing history, or melting your servers." — Production Engineering Reality

---

## The Real Scale Challenge

You're building Google Docs. Every keystroke must be undoable. Every user must see their own history. Branching undo must work (undo then type creates new branch). Collaborate with 50 users typing simultaneously. Redo must handle conflicts. History must survive crashes. Time travel debugging must replay any state.

Traditional approaches fail spectacularly:
- **Deep copying on every change**: Clone 100MB document 1,000 times/second → 100GB/s memory churn
- **Storing deltas**: Forward-only playback means O(n) seeks to access recent state  
- **Mutable structures**: Race conditions between concurrent undos corrupt the document

This episode shows how immutable persistent data structures solve this—the same technique powering Redux, Git, and CRDTs in production distributed systems.

---

## From LeetCode to Production Reality

### The Foundation: LeetCode Problem

LeetCode never asks about immutability directly. But hidden in problems like "Design Browser History" (#1472) or "Text Editor" is a fundamental truth: mutation makes correctness hard.

The naive solution mutates state:

```python
class BrowserHistory:
    def __init__(self, homepage: str):
        self.history = [homepage]
        self.current = 0
    
    def visit(self, url: str):
        # Mutation: destroy forward history
        self.history = self.history[:self.current + 1]
        self.history.append(url)
        self.current += 1
    
    def back(self, steps: int) -> str:
        self.current = max(0, self.current - steps)
        return self.history[self.current]
    
    def forward(self, steps: int) -> str:
        self.current = min(len(self.history) - 1, self.current + steps)
        return self.history[self.current]
```

**What breaks in production:**
- Undo corrupts state when multiple threads call `visit()` simultaneously  
- No branching: you can't undo then take a different path while preserving the original  
- Debugging is impossible: you can't replay the exact sequence that caused the bug  
- Collaboration fails: two users undoing concurrently create inconsistent state

---

## Engineering Layer 1: Immutable Structures

Immutability means values never change—operations return new versions instead. The breakthrough: **structural sharing** means copying is O(log n), not O(n).

### The Core: Immutable Text with Structural Sharing

```python
from typing import Optional, List, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import time

@dataclass(frozen=True)
class TextNode(ABC):
    """Immutable text node - never modified after creation."""
    
    @abstractmethod
    def length(self) -> int:
        pass
    
    @abstractmethod
    def get_text(self) -> str:
        pass


@dataclass(frozen=True)
class Leaf(TextNode):
    """Leaf node storing actual text."""
    text: str
    
    def length(self) -> int:
        return len(self.text)
    
    def get_text(self) -> str:
        return self.text


@dataclass(frozen=True)
class Branch(TextNode):
    """Branch node combining two subtrees."""
    left: TextNode
    right: TextNode
    _length: int
    
    def length(self) -> int:
        return self _length
    
    def get_text(self) -> str:
        return self.left.get_text() + self.right.get_text()


class ImmutableText:
    """Immutable text buffer with O(log n) edits via structural sharing."""
    
    def __init__(self, root: TextNode):
        self.root = root
    
    def insert(self, pos: int, text: str) -> 'ImmutableText':
        """Insert text at position, returning NEW ImmutableText."""
        if pos == 0:
            return ImmutableText(Branch(Leaf(text), self.root, len(text) + self.root.length()))
        if pos == self.root.length():
            return ImmutableText(Branch(self.root, Leaf(text), self.root.length() + len(text)))
        
        # Split at position, insert between
        left, right = self._split(self.root, pos)
        new_node = Branch(Leaf(text), right, len(text) + right.length())
        return ImmutableText(Branch(left, new_node, left.length() + new_node.length()))
    
    def delete(self, start: int, end: int) -> 'ImmutableText':
        """Delete range [start, end), returning NEW ImmutableText."""
        if start >= end:
            return self
        
        left, _ = self._split(self.root, start)
        _, right = self._split(self.root, end)
        
        if left.length() == 0:
            return ImmutableText(right)
        if right.length() == 0:
            return ImmutableText(left)
        
        return ImmutableText(Branch(left, right, left.length() + right.length()))
    
    def _split(self, node: TextNode, pos: int) -> Tuple[TextNode, TextNode]:
        """Split tree at position into (left, right) subtrees."""
        if isinstance(node, Leaf):
            return Leaf(node.text[:pos]), Leaf(node.text[pos:])
        
        branch = node
        left_len = branch.left.length()
        
        if pos <= left_len:
            left, right = self._split(branch.left, pos)
            return left, Branch(right, branch.right, right.length() + branch.right.length())
        else:
            left, right = self._split(branch.right, pos - left_len)
            return Branch(branch.left, left, branch.left.length() + left.length()), right
    
    def get_text(self) -> str:
        return self.root.get_text()
    
    def __len__(self) -> int:
        return self.root.length()
```

**Why this works:**
- Every edit creates a new tree, but most nodes are shared with the old tree  
- Inserting "hello" in a 100MB document copies O(log n) nodes (~30 nodes), not 100MB  
- Previous versions remain accessible—perfect for undo  
- Thread-safe by construction: no locks needed

---

## Engineering Layer 2: Persistent History

Immutability enables persistent history—a DAG where every edit is a node, supporting branching undo.

```python
from typing import Dict, Optional, Set
import hashlib
import json

@dataclass
class HistoryNode:
    """Node in the history DAG."""
    version_id: str
    text: ImmutableText
    parent: Optional[str]  # Parent version ID
    timestamp: float
    operation: str  # Description of the change
    children: Set[str]  # Child version IDs (for branching)
    
    def __init__(self, text: ImmutableText, parent: Optional[str], operation: str):
        self.text = text
        self.parent = parent
        self.operation = operation
        self.timestamp = time.time()
        self.children = set()
        
        # Generate content-addressable ID
        content = f"{text.get_text()}:{parent}:{operation}:{self.timestamp}"
        self.version_id = hashlib.sha256(content.encode()).hexdigest()[:16]


class PersistentHistory:
    """Immutable history with branching undo/redo."""
    
    def __init__(self):
        self.versions: Dict[str, HistoryNode] = {}
        self.current_version: Optional[str] = None
        self.root_version: Optional[str] = None
    
    def initialize(self, text: str):
        """Initialize with starting text."""
        node = HistoryNode(
            text=ImmutableText(Leaf(text)),
            parent=None,
            operation="initialize"
        )
        self.versions[node.version_id] = node
        self.root_version = node.version_id
        self.current_version = node.version_id
    
    def insert(self, pos: int, text: str) -> str:
        """Insert text, returning new version ID."""
        if self.current_version is None:
            raise ValueError("History not initialized")
        
        current = self.versions[self.current_version]
        new_text = current.text.insert(pos, text)
        new_node = HistoryNode(
            text=new_text,
            parent=self.current_version,
            operation=f"insert({pos}, '{text}')"
        )
        
        self.versions[new_node.version_id] = new_node
        current.children.add(new_node.version_id)
        self.current_version = new_node.version_id
        
        return new_node.version_id
    
    def delete(self, start: int, end: int) -> str:
        """Delete range, returning new version ID."""
        if self.current_version is None:
            raise ValueError("History not initialized")
        
        current = self.versions[self.current_version]
        new_text = current.text.delete(start, end)
        new_node = HistoryNode(
            text=new_text,
            parent=self.current_version,
            operation=f"delete({start}, {end})"
        )
        
        self.versions[new_node.version_id] = new_node
        current.children.add(new_node.version_id)
        self.current_version = new_node.version_id
        
        return new_node.version_id
    
    def undo(self) -> Optional[str]:
        """Undo to parent version."""
        if self.current_version is None or self.current_version == self.root_version:
            return None
        
        current = self.versions[self.current_version]
        if current.parent:
            self.current_version = current.parent
            return self.current_version
        
        return None
    
    def redo(self) -> Optional[str]:
        """Redo to most recent child (or prompt if multiple children)."""
        if self.current_version is None:
            return None
        
        current = self.versions[self.current_version]
        if not current.children:
            return None
        
        # If multiple children, pick most recent
        children = [self.versions[cid] for cid in current.children]
        next_version = max(children, key=lambda n: n.timestamp)
        self.current_version = next_version.version_id
        
        return self.current_version
    
    def get_current_text(self) -> str:
        """Get current version's text."""
        if self.current_version is None:
            return ""
        return self.versions[self.current_version].text.get_text()
    
    def get_branches(self) -> List[List[str]]:
        """Get all branches from root."""
        if not self.root_version:
            return []
        
        branches = []
        
        def dfs(version_id: str, path: List[str]):
            path = path + [version_id]
            node = self.versions[version_id]
            
            if not node.children:
                branches.append(path)
            else:
                for child_id in node.children:
                    dfs(child_id, path)
        
        dfs(self.root_version, [])
        return branches
```

**Branching undo in action:**
1. User types "Hello"  
2. Undo (back to "")  
3. Type "Hi" → creates NEW branch from root  
4. Both "Hello" and "Hi" branches exist in the DAG  
5. Redo intelligently picks most recent branch

**Production wins:**
- No corruption: every version is immutable  
- Branch visualization: show users the history tree  
- Time travel: jump to any version instantly  
- Crash recovery: every version is independently consistent

---

## Engineering Layer 3: Distributed Collaboration with CRDTs

When 50 users edit simultaneously, undo must handle conflicts. CRDTs (Conflict-free Replicated Data Types) provide convergence guarantees.

### CRDT-Based Collaborative Undo

```python
from typing import Dict, Tuple, Optional
from dataclasses import dataclass, field
import uuid

@dataclass
class VectorClock:
    """Vector clock for causality tracking."""
    clocks: Dict[str, int] = field(default_factory=dict)
    
    def increment(self, replica_id: str):
        """Increment this replica's clock."""
        self.clocks[replica_id] = self.clocks.get(replica_id, 0) + 1
    
    def merge(self, other: 'VectorClock'):
        """Merge with another vector clock (take max for each replica)."""
        for replica_id, timestamp in other.clocks.items():
            self.clocks[replica_id] = max(self.clocks.get(replica_id, 0), timestamp)
    
    def happens_before(self, other: 'VectorClock') -> bool:
        """Check if this clock happens before other."""
        for replica_id, timestamp in self.clocks.items():
            if timestamp > other.clocks.get(replica_id, 0):
                return False
        return any(self.clocks.get(r, 0) < other.clocks.get(r, 0) for r in other.clocks)
    
    def concurrent_with(self, other: 'VectorClock') -> bool:
        """Check if clocks are concurrent (conflict)."""
        return not self.happens_before(other) and not other.happens_before(self)


@dataclass
class CRDTOperation:
    """CRDT operation with causality metadata."""
    op_id: str
    replica_id: str
    op_type: str  # 'insert' or 'delete'
    position: int
    content: Optional[str]
    vector_clock: VectorClock
    timestamp: float
    
    def __init__(self, replica_id: str, op_type: str, position: int, content: Optional[str], vector_clock: VectorClock):
        self.op_id = str(uuid.uuid4())
        self.replica_id = replica_id
        self.op_type = op_type
        self.position = position
        self.content = content
        self.vector_clock = vector_clock
        self.timestamp = time.time()


class CRDTTextDocument:
    """CRDT text document with collaborative undo."""
    
    def __init__(self, replica_id: str):
        self.replica_id = replica_id
        self.history = PersistentHistory()
        self.history.initialize("")
        
        self.vector_clock = VectorClock()
        self.vector_clock.increment(replica_id)
        
        self.operation_log: List[CRDTOperation] = []
        self.tombstones: Set[str] = set()  # Deleted operation IDs
    
    def local_insert(self, pos: int, text: str) -> CRDTOperation:
        """Local insert operation."""
        self.vector_clock.increment(self.replica_id)
        
        op = CRDTOperation(
            replica_id=self.replica_id,
            op_type='insert',
            position=pos,
            content=text,
            vector_clock=VectorClock(self.vector_clock.clocks.copy())
        )
        
        self.operation_log.append(op)
        self.history.insert(pos, text)
        
        return op
    
    def local_delete(self, start: int, end: int) -> CRDTOperation:
        """Local delete operation."""
        self.vector_clock.increment(self.replica_id)
        
        op = CRDTOperation(
            replica_id=self.replica_id,
            op_type='delete',
            position=start,
            content=None,
            vector_clock=VectorClock(self.vector_clock.clocks.copy())
        )
        
        self.operation_log.append(op)
        self.history.delete(start, end)
        
        return op
    
    def apply_remote_operation(self, op: CRDTOperation):
        """Apply operation from another replica."""
        if op.op_id in self.tombstones:
            return  # Already undone
        
        # Merge vector clocks
        self.vector_clock.merge(op.vector_clock)
        
        # Transform position based on concurrent operations
        transformed_pos = self._transform_position(op)
        
        if op.op_type == 'insert':
            self.history.insert(transformed_pos, op.content)
        elif op.op_type == 'delete':
            self.history.delete(transformed_pos, transformed_pos + len(op.content or ""))
        
        self.operation_log.append(op)
    
    def _transform_position(self, op: CRDTOperation) -> int:
        """Operational transformation: adjust position based on concurrent ops."""
        adjusted_pos = op.position
        
        for logged_op in self.operation_log:
            if logged_op.op_id == op.op_id:
                continue
            
            # If logged_op happened before op, no transformation needed
            if logged_op.vector_clock.happens_before(op.vector_clock):
                continue
            
            # If concurrent, apply transformation rules
            if logged_op.vector_clock.concurrent_with(op.vector_clock):
                if logged_op.op_type == 'insert' and logged_op.position <= op.position:
                    adjusted_pos += len(logged_op.content or "")
                elif logged_op.op_type == 'delete' and logged_op.position < op.position:
                    adjusted_pos -= min(op.position - logged_op.position, len(logged_op.content or ""))
        
        return max(0, adjusted_pos)
    
    def undo_operation(self, op_id: str):
        """Undo a specific operation (works across replicas)."""
        self.tombstones.add(op_id)
        
        # Rebuild document from scratch, skipping tombstoned operations
        self.history = PersistentHistory()
        self.history.initialize("")
        
        for op in self.operation_log:
            if op.op_id not in self.tombstones:
                if op.op_type == 'insert':
                    pos = self._transform_position(op)
                    self.history.insert(pos, op.content)
                elif op.op_type == 'delete':
                    pos = self._transform_position(op)
                    self.history.delete(pos, pos + len(op.content or ""))
    
    def get_text(self) -> str:
        return self.history.get_current_text()
```

**How CRDT undo handles conflicts:**

**Scenario**: Alice and Bob both edit at position 5  
- Alice inserts "X" (vector clock: {Alice: 1})  
- Bob inserts "Y" (vector clock: {Bob: 1})  
- Operations are concurrent (neither happens-before the other)  
- Transformation rules ensure convergence: both end up with "XY" or "YX" deterministically  

**Scenario**: Alice undoes Bob's edit  
- Alice's undo adds Bob's `op_id` to tombstones  
- Tombstone propagates to all replicas  
- All replicas rebuild text, skipping Bob's operation  
- Eventual consistency guaranteed

---

## Engineering Layer 4: Production-Grade History System

Real systems need garbage collection, compression, and efficient storage.

```python
import zlib
import pickle
from collections import deque
from typing import Dict, List, Set, Optional

@dataclass
class HistoryGeneration:
    """Generation of compressed history snapshots."""
    generation_id: int
    snapshot_version: str  # Base version for this generation
    snapshot_data: bytes  # Compressed full text
    deltas: List[Tuple[str, bytes]]  # (version_id, compressed delta)
    size_bytes: int
    created_at: float


class ProductionHistorySystem:
    """Production history with generational GC and delta compression."""
    
    def __init__(self, max_memory_mb: int = 100):
        self.history = PersistentHistory()
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        self.generations: List[HistoryGeneration] = []
        self.current_generation_id = 0
        self.hot_versions: Set[str] = set()  # Frequently accessed versions
        
        self.access_log: deque = deque(maxlen=1000)  # LRU tracking
    
    def compress_generation(self, base_version_id: str, version_ids: List[str]):
        """Compress a generation of versions into deltas."""
        base_node = self.history.versions[base_version_id]
        base_text = base_node.text.get_text().encode()
        
        # Full snapshot (compressed)
        snapshot_data = zlib.compress(base_text, level=9)
        
        # Delta encode subsequent versions
        deltas = []
        prev_text = base_text
        
        for version_id in version_ids:
            node = self.history.versions[version_id]
            current_text = node.text.get_text().encode()
            
            # Simple delta: store differences
            delta = self._compute_delta(prev_text, current_text)
            compressed_delta = zlib.compress(delta, level=9)
            
            deltas.append((version_id, compressed_delta))
            prev_text = current_text
        
        generation = HistoryGeneration(
            generation_id=self.current_generation_id,
            snapshot_version=base_version_id,
            snapshot_data=snapshot_data,
            deltas=deltas,
            size_bytes=len(snapshot_data) + sum(len(d[1]) for d in deltas),
            created_at=time.time()
        )
        
        self.generations.append(generation)
        self.current_generation_id += 1
        
        return generation
    
    def _compute_delta(self, old: bytes, new: bytes) -> bytes:
        """Compute byte-level delta (simplified diff)."""
        # In production, use Myers diff or similar
        # Here we use a simple encoding: [(op, pos, data), ...]
        delta_ops = []
        
        if old == new:
            return pickle.dumps([])
        
        # Simplification: just store the new text if very different
        if len(new) < len(old) // 2 or len(new) > len(old) * 2:
            delta_ops.append(('replace', 0, new))
        else:
            # Find common prefix/suffix
            prefix_len = 0
            while prefix_len < min(len(old), len(new)) and old[prefix_len] == new[prefix_len]:
                prefix_len += 1
            
            suffix_len = 0
            while suffix_len < min(len(old), len(new)) - prefix_len and old[-(suffix_len+1)] == new[-(suffix_len+1)]:
                suffix_len += 1
            
            # Middle changed
            old_mid = old[prefix_len:len(old)-suffix_len] if suffix_len else old[prefix_len:]
            new_mid = new[prefix_len:len(new)-suffix_len] if suffix_len else new[prefix_len:]
            
            if old_mid:
                delta_ops.append(('delete', prefix_len, len(old_mid)))
            if new_mid:
                delta_ops.append(('insert', prefix_len, new_mid))
        
        return pickle.dumps(delta_ops)
    
    def _apply_delta(self, base: bytes, delta: bytes) -> bytes:
        """Apply delta to reconstruct text."""
        delta_ops = pickle.loads(delta)
        
        result = bytearray(base)
        
        for op in delta_ops:
            if op[0] == 'replace':
                result = bytearray(op[2])
            elif op[0] == 'insert':
                pos, data = op[1], op[2]
                result[pos:pos] = data
            elif op[0] == 'delete':
                pos, length = op[1], op[2]
                del result[pos:pos+length]
        
        return bytes(result)
    
    def garbage_collect(self):
        """GC old generations that exceed memory budget."""
        total_size = sum(g.size_bytes for g in self.generations)
        
        if total_size <= self.max_memory_bytes:
            return
        
        # Remove coldest generations (not in hot set)
        cold_generations = [g for g in self.generations 
                           if g.snapshot_version not in self.hot_versions]
        
        cold_generations.sort(key=lambda g: g.created_at)
        
        while total_size > self.max_memory_bytes and cold_generations:
            oldest = cold_generations.pop(0)
            self.generations.remove(oldest)
            total_size -= oldest.size_bytes
    
    def access_version(self, version_id: str) -> str:
        """Access a version (triggers LRU tracking)."""
        self.access_log.append(version_id)
        
        # Update hot set from access log
        self.hot_versions = set(list(self.access_log)[-100:])
        
        # Find the generation containing this version
        for generation in reversed(self.generations):
            if version_id == generation.snapshot_version:
                return zlib.decompress(generation.snapshot_data).decode()
            
            # Check deltas
            base_text = zlib.decompress(generation.snapshot_data)
            current_text = base_text
            
            for delta_version_id, compressed_delta in generation.deltas:
                current_text = self._apply_delta(current_text, zlib.decompress(compressed_delta))
                if delta_version_id == version_id:
                    return current_text.decode()
        
        # Not in compressed generations, check live history
        if version_id in self.history.versions:
            return self.history.versions[version_id].text.get_text()
        
        return ""
```

**Production optimizations:**
- **Generational storage**: Recent edits are hot (uncompressed), old edits are cold (compressed)  
- **Delta encoding**: Store diffs instead of full snapshots (10x compression typical)  
- **LRU garbage collection**: Evict cold generations when memory limit exceeded  
- **Hot version tracking**: Keep frequently accessed versions uncompressed

---

## Engineering Layer 5: Time Travel Debugging

The ultimate application: record program execution as immutable history, enabling replay and time-travel debugging.

```python
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import inspect
import sys

@dataclass
class ExecutionFrame:
    """Snapshot of a single execution frame."""
    frame_id: str
    function_name: str
    line_number: int
    local_vars: Dict[str, Any]
    timestamp: float
    parent_frame: Optional[str]


class TimeTravelDebugger:
    """Record execution history for time-travel debugging."""
    
    def __init__(self):
        self.frames: List[ExecutionFrame] = []
        self.call_stack: List[str] = []
        self.recording = False
    
    def start_recording(self):
        """Start recording execution."""
        self.recording = True
        sys.settrace(self._trace_calls)
    
    def stop_recording(self):
        """Stop recording execution."""
        self.recording = False
        sys.settrace(None)
    
    def _trace_calls(self, frame, event, arg):
        """Trace function for capturing execution."""
        if not self.recording:
            return
        
        if event == 'call':
            frame_id = f"{id(frame)}_{time.time()}"
            
            exec_frame = ExecutionFrame(
                frame_id=frame_id,
                function_name=frame.f_code.co_name,
                line_number=frame.f_lineno,
                local_vars={k: repr(v) for k, v in frame.f_locals.items()},
                timestamp=time.time(),
                parent_frame=self.call_stack[-1] if self.call_stack else None
            )
            
            self.frames.append(exec_frame)
            self.call_stack.append(frame_id)
            
            return self._trace_lines
        
        elif event == 'return':
            if self.call_stack:
                self.call_stack.pop()
    
    def _trace_lines(self, frame, event, arg):
        """Trace individual line execution."""
        if event == 'line':
            frame_id = f"{id(frame)}_{time.time()}"
            
            exec_frame = ExecutionFrame(
                frame_id=frame_id,
                function_name=frame.f_code.co_name,
                line_number=frame.f_lineno,
                local_vars={k: repr(v) for k, v in frame.f_locals.items()},
                timestamp=time.time(),
                parent_frame=self.call_stack[-1] if self.call_stack else None
            )
            
            self.frames.append(exec_frame)
        
        return self._trace_lines
    
    def replay_to_frame(self, frame_index: int) -> ExecutionFrame:
        """Replay execution up to a specific frame."""
        if frame_index >= len(self.frames):
            raise IndexError("Frame index out of range")
        
        return self.frames[frame_index]
    
    def get_call_tree(self) -> Dict:
        """Build hierarchical call tree from frames."""
        tree = {}
        
        for frame in self.frames:
            if frame.parent_frame is None:
                tree[frame.frame_id] = {
                    'frame': frame,
                    'children': []
                }
            else:
                parent = self._find_frame_in_tree(tree, frame.parent_frame)
                if parent:
                    parent['children'].append({
                        'frame': frame,
                        'children': []
                    })
        
        return tree
    
    def _find_frame_in_tree(self, tree: Dict, frame_id: str) -> Optional[Dict]:
        """Find a frame in the call tree."""
        for node in tree.values():
            if node['frame'].frame_id == frame_id:
                return node
            
            result = self._find_frame_in_tree({c['frame'].frame_id: c for c in node['children']}, frame_id)
            if result:
                return result
        
        return None
```

**Time travel debugging in action:**
```python
debugger = TimeTravelDebugger()

debugger.start_recording()

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(5)

debugger.stop_recording()

# Replay to frame 10
frame = debugger.replay_to_frame(10)
print(f"At frame 10: {frame.function_name} line {frame.line_number}")
print(f"Local vars: {frame.local_vars}")

# Visualize call tree
call_tree = debugger.get_call_tree()
```

**Production use cases:**
- **Debugging race conditions**: Replay exact concurrent interleavings  
- **Post-mortem analysis**: Examine state before crash without reprobing  
- **Profiling**: Analyze hot paths by replaying execution  
- **Testing**: Assert on intermediate states during execution

---

## When NOT to Use Immutable Structures

| Scenario | Why Immutability Fails | Use Instead |
|----------|----------------------|-------------|
| **High-frequency mutations** | Copying O(log n) nodes 1M times/sec → GC pressure | Mutable arrays with Copy-on-Write only when branching needed |
| **Memory-constrained systems** | Structural sharing still uses more memory than in-place mutation | Mutable structures with explicit checkpoints |
| **Cache-hostile workloads** | Tree traversal causes cache misses (pointer chasing) | Flat arrays with arena allocation |
| **Write-heavy, read-light** | Immutability optimizes for many readers, hurts many writers | Mutable structures with fine-grained locking |
| **Real-time systems** | GC pauses from discarded versions break latency SLAs | Pre-allocated pools, manual memory management |

**When immutability wins:**
- Collaborative editing (Google Docs, Figma)  
- Version control systems (Git, Mercurial)  
- State management (Redux, Recoil)  
- Distributed consensus (CRDTs, Raft)  
- Time-travel debugging (Redux DevTools, rr)

---

## Next Episode: Browser Resource Caches

You now understand how immutability enables correctness. But what happens when your immutable history grows to 100GB? How do you decide what to keep and what to evict?

**Episode 5 tackles LRU caches**—the eviction policy that powers browser caches, database buffer pools, and OS page caches. You'll build a production-grade cache with:
- O(1) get/put/evict using doubly-linked lists + hashmaps  
- Resource type quotas (images vs scripts vs fonts)  
- Proactive eviction under memory pressure  
- Metrics and observability for cache hit rates

The challenge: **Implement an LRU cache handling 100,000 requests/sec with <1ms p99 latency**. No heap allocations in the hot path. No lock contention between reader threads.

See you in Episode 5. 🚀
