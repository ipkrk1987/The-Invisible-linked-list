
SEASON: 1 — The Invisible Linked List

EPISODE: 4

TITLE: Time Travel at Scale: Immutable Data Structures from LeetCode to Production

(0:00 - The Interview Question Everyone Gets)

[Visual: LeetCode problem #DesignUndoRedo]

Narration: "Here's a classic interview question: Design an undo/redo system for a text editor. Most candidates reach for the obvious solution:"

```python
class TextEditorNaive:
    """LeetCode solution - works in interviews, breaks in production."""
    
    def __init__(self):
        self.text = ""
        self.undo_stack = []  # Stores operations to undo
        self.redo_stack = []  # Stores operations to redo
        
    def type_char(self, char: str, position: int):
        """Type a character at position."""
        # Save inverse for undo
        self.undo_stack.append(('delete', position, char))
        self.redo_stack.clear()  # Clear redo on new action
        
        # Apply operation
        self.text = self.text[:position] + char + self.text[position:]
        
    def delete_char(self, position: int):
        """Delete character at position."""
        if position >= len(self.text):
            return
            
        char = self.text[position]
        # Save inverse for undo
        self.undo_stack.append(('insert', position, char))
        self.redo_stack.clear()
        
        # Apply
        self.text = self.text[:position] + self.text[position+1:]
        
    def undo(self):
        """Undo last operation."""
        if not self.undo_stack:
            return
            
        op_type, position, char = self.undo_stack.pop()
        
        if op_type == 'insert':
            self.text = self.text[:position] + char + self.text[position:]
        else:  # 'delete'
            self.text = self.text[:position] + self.text[position+1:]
            
        # Move to redo stack
        self.redo_stack.append(op_type, position, char)
        
    def redo(self):
        """Redo last undone operation."""
        if not self.redo_stack:
            return
            
        op_type, position, char = self.redo_stack.pop()
        
        if op_type == 'insert':
            self.delete_char(position)
        else:
            self.type_char(char, position)
            
        self.undo_stack.append((op_type, position, char))

# The problems:
# 1. Linear history only (what if I undo, then do something new?)
# 2. O(n) memory per operation (stores full inverse ops)
# 3. No collaboration support
# 4. Breaks with complex operations
```

Narration: "This works for the interview. But open Google Docs, hit Ctrl+Z 50 times, then type something new. Notice: you can still redo your old changes. That's not a stack — that's a branching history tree. Let's build what real systems use."

(4:00 - The Immutable Breakthrough: Structural Sharing)

Narration: "The key insight: Don't mutate. Create new versions that share unchanged parts with old versions."

```python
class ImmutableText:
    """Text that never changes - only creates new versions."""
    
    def __init__(self, content="", version_id=None):
        self.content = content
        self.version_id = version_id or str(uuid.uuid4())
        self._length = len(content)
        
    def insert(self, position: int, text: str) -> 'ImmutableText':
        """Insert text - returns NEW text, shares unchanged parts."""
        # In reality, we'd use a rope or piece table
        # For simplicity, show the concept
        new_content = self.content[:position] + text + self.content[position:]
        return ImmutableText(new_content)
    
    def delete(self, position: int, length: int = 1) -> 'ImmutableText':
        """Delete text - returns NEW text."""
        new_content = self.content[:position] + self.content[position+length:]
        return ImmutableText(new_content)
    
    def __eq__(self, other):
        return self.version_id == other.version_id
    
    def __hash__(self):
        return hash(self.version_id)

class PersistentHistory:
    """History that branches like Git, not linear like a stack."""
    
    def __init__(self, initial_text):
        # DAG of text versions
        self.versions = {
            'root': initial_text
        }
        self.edges = {}  # version -> [child_versions]
        self.current = 'root'
        
    def apply_edit(self, edit_func, *args) -> str:
        """Apply edit, creating new version."""
        current_text = self.versions[self.current]
        new_text = edit_func(current_text, *args)
        
        # Create new version
        new_version_id = str(uuid.uuid4())
        self.versions[new_version_id] = new_text
        
        # Add edge in DAG
        if self.current not in self.edges:
            self.edges[self.current] = []
        self.edges[self.current].append(new_version_id)
        
        # Update current
        self.current = new_version_id
        
        return new_version_id
    
    def undo(self) -> bool:
        """Move to parent version if exists."""
        parents = self.find_parents(self.current)
        if not parents:
            return False
            
        # If multiple parents, we're at a merge
        # Real systems would prompt user or use strategy
        self.current = parents[0]
        return True
    
    def redo(self, branch_index: int = 0) -> bool:
        """Redo along a specific branch."""
        children = self.edges.get(self.current, [])
        if not children or branch_index >= len(children):
            return False
            
        self.current = children[branch_index]
        return True
    
    def find_parents(self, version_id):
        """Find all parents of a version in the DAG."""
        parents = []
        for parent, children in self.edges.items():
            if version_id in children:
                parents.append(parent)
        return parents
    
    def create_branch(self):
        """Create explicit branch point."""
        return {
            'from': self.current,
            'timestamp': time.time(),
            'branch_id': str(uuid.uuid4())
        }

# The magic: Multiple versions share underlying text!
# version1: "Hello world"
# version2: "Hello awesome world" (shares "Hello " and " world")
# version3: "Hello world!" (shares "Hello world" with version1)
```

(8:00 - Persistent Data Structures: The Engine Behind Redux)

Narration: "This pattern powers Redux and React. Every state change creates a new state object, but shares unchanged subtrees:"

```python
class PersistentTree:
    """Binary tree where updates create new tree sharing most nodes."""
    
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right
        self._hash = None
        
    def update(self, path: str, new_value) -> 'PersistentTree':
        """Update value at path, copying only affected nodes."""
        if not path:
            # Update root, share children
            return PersistentTree(new_value, self.left, self.right)
            
        direction, *rest = path
        if direction == 'L':
            # Update left subtree
            new_left = self.left.update(''.join(rest), new_value) if self.left else None
            return PersistentTree(self.value, new_left, self.right)
        else:  # 'R'
            # Update right subtree
            new_right = self.right.update(''.join(rest), new_value) if self.right else None
            return PersistentTree(self.value, self.left, new_right)
    
    def __hash__(self):
        if self._hash is None:
            left_hash = hash(self.left) if self.left else 0
            right_hash = hash(self.right) if self.right else 0
            self._hash = hash((self.value, left_hash, right_hash))
        return self._hash

class ReduxStore:
    """Simplified Redux with structural sharing."""
    
    def __init__(self, reducer, initial_state):
        self.reducer = reducer
        self.state_tree = PersistentTree(initial_state)
        self.history = []  # List of (action, state_hash)
        self.future = []   # For redo
        
    def dispatch(self, action):
        """Dispatch action - creates new immutable state."""
        # Apply reducer
        new_state = self.reducer(self.state_tree.value, action)
        
        # Create new state tree (shares unchanged parts)
        # In reality, Redux does shallow copies, not tree updates
        # But the principle is the same
        
        # Save to history
        self.history.append({
            'action': action,
            'state_hash': hash(self.state_tree),
            'timestamp': time.time()
        })
        self.future.clear()  # New action clears redo future
        
        # Update current state
        self.state_tree = PersistentTree(new_state)
        
        return action
    
    def get_state(self):
        return self.state_tree.value
    
    def time_travel(self, target_index: int):
        """Jump to any point in history - Redux DevTools magic."""
        if target_index < 0 or target_index >= len(self.history):
            return False
            
        # Replay actions up to target
        # Real Redux would have snapshots or replay actions
        # We're simplifying
        
        # Save current to future for redo
        self.future.append({
            'state': self.state_tree,
            'index': len(self.history) - 1
        })
        
        # For demo: just show the concept
        print(f"Time traveling to action {target_index}: {self.history[target_index]['action']}")
        return True

# Example: React component tree updates
# Old tree: App → [Header, Content → [Sidebar, Main]]
# Update Main: App → [Header, Content → [Sidebar, Main']]
# Header, Content, Sidebar nodes are SHARED, not recreated
```

(12:00 - Version DAGs: When Undo Branches)

Narration: "Real undo systems aren't linear. When you undo, then do something new, you create a branch. This is a Directed Acyclic Graph:"

```python
class HistoryDAG:
    """Version history as a directed acyclic graph."""
    
    def __init__(self):
        self.nodes = {}  # version_id -> StateNode
        self.edges = {}  # version_id -> [child_ids]
        self.current = None
        self.branches = {}  # branch_name -> tip_version
        
    class StateNode:
        def __init__(self, state, parent_ids=None):
            self.state = state
            self.parent_ids = parent_ids or []
            self.timestamp = time.time()
            self.id = str(uuid.uuid4())
            self.metadata = {}  # Author, commit message, etc.
    
    def commit(self, new_state, parent_ids=None):
        """Commit new state, optionally with multiple parents."""
        if parent_ids is None:
            parent_ids = [self.current] if self.current else []
        
        # Create node
        node = self.StateNode(new_state, parent_ids)
        self.nodes[node.id] = node
        
        # Add edges from parents
        for parent_id in parent_ids:
            if parent_id not in self.edges:
                self.edges[parent_id] = []
            self.edges[parent_id].append(node.id)
        
        # Update current
        self.current = node.id
        
        return node.id
    
    def undo(self, target_branch=None):
        """Undo by moving to a parent."""
        if not self.current:
            return False
            
        current_node = self.nodes[self.current]
        if not current_node.parent_ids:
            return False  # At root
        
        # If multiple parents and no target specified,
        # we need to choose or create a new branch
        if len(current_node.parent_ids) > 1 and not target_branch:
            # This is the branching undo problem!
            # Real systems: prompt user, use strategy, or create new branch
            return self._handle_branching_undo(current_node)
        else:
            # Simple case: one parent or branch specified
            target_parent = (target_branch or current_node.parent_ids[0])
            self.current = target_parent
            return True
    
    def _handle_branching_undo(self, node):
        """Handle undo at a merge point."""
        # Strategy 1: Create new branch for each parent
        branches_created = []
        for i, parent_id in enumerate(node.parent_ids):
            branch_name = f"undo_branch_{i}_{int(time.time())}"
            self.branches[branch_name] = parent_id
            branches_created.append(branch_name)
        
        # Strategy 2: Use most recent parent (common in Git)
        most_recent = max(node.parent_ids, 
                         key=lambda pid: self.nodes[pid].timestamp)
        self.current = most_recent
        
        return {
            'branches_created': branches_created,
            'chosen_parent': most_recent
        }
    
    def redo(self, branch_name=None):
        """Redo by moving to a child."""
        if branch_name:
            # Redo to specific branch tip
            if branch_name in self.branches:
                self.current = self.branches[branch_name]
                return True
            return False
        
        # Redo to child of current
        children = self.edges.get(self.current, [])
        if not children:
            return False
            
        # If multiple children, need strategy
        if len(children) > 1:
            # Choose most recent or prompt user
            most_recent = max(children,
                            key=lambda cid: self.nodes[cid].timestamp)
            self.current = most_recent
        else:
            self.current = children[0]
            
        return True
    
    def visualize(self):
        """Generate Graphviz-style representation."""
        lines = ["digraph History {", "  rankdir=LR;"]
        
        for node_id, node in self.nodes.items():
            label = f"{node_id[:8]}\\n{node.timestamp}"
            if node_id == self.current:
                lines.append(f'  "{node_id}" [label="{label}", style="filled", fillcolor="lightblue"];')
            else:
                lines.append(f'  "{node_id}" [label="{label}"];')
        
        for parent_id, children in self.edges.items():
            for child_id in children:
                lines.append(f'  "{parent_id}" -> "{child_id}";')
        
        lines.append("}")
        return "\n".join(lines)

# Real examples:
# 1. Git: commit DAG with branches
# 2. Google Docs: collaborative edit history
# 3. Figma: design version history
# 4. VS Code: file edit history with multiple cursors
```

(16:00 - Collaboration: CRDTs for Conflict-Free Undo)

Narration: "Now the hard part: collaborative undo. When Alice and Bob edit the same document, then both undo — what happens? This requires Conflict-free Replicated Data Types (CRDTs)."

```python
class CRDTCharacter:
    """A character in a CRDT text document."""
    def __init__(self, char, site_id, counter):
        self.char = char
        self.id = (site_id, counter)  # Globally unique
        self.visible = True
        self.tombstone = False  # For undo
        
    def __lt__(self, other):
        """Ordering for sorting characters."""
        # Compare site_id, then counter
        return (self.id[0], self.id[1]) < (other.id[0], other.id[1])

class CRDTTextDocument:
    """CRDT-based text document supporting collaborative undo."""
    
    def __init__(self, site_id):
        self.site_id = site_id
        self.characters = []  # Sorted list of CRDTCharacter
        self.counter = 0
        self.vector_clock = {site_id: 0}
        self.operation_log = []  # For local undo/redo
        
    def generate_id(self):
        """Generate globally unique ID for new character."""
        self.counter += 1
        self.vector_clock[self.site_id] = self.counter
        return (self.site_id, self.counter)
    
    def local_insert(self, position: int, char: str):
        """Local insertion - can be undone locally."""
        # Generate unique ID
        char_id = self.generate_id()
        
        # Create character
        crdt_char = CRDTCharacter(char, self.site_id, self.counter)
        
        # Find insertion point in sorted list
        # Real CRDTs use more sophisticated positioning (fractional indexing)
        insert_index = self._find_insert_index(position)
        
        # Insert
        self.characters.insert(insert_index, crdt_char)
        
        # Log for local undo
        self.operation_log.append({
            'type': 'insert',
            'char_id': char_id,
            'position': position,
            'local_index': insert_index
        })
        
        # Broadcast to other sites
        return {
            'type': 'insert',
            'char': char,
            'id': char_id,
            'vector_clock': self.vector_clock.copy()
        }
    
    def remote_insert(self, operation):
        """Apply remote insertion - always commutative."""
        char = CRDTCharacter(
            operation['char'],
            operation['id'][0],  # site_id
            operation['id'][1]   # counter
        )
        
        # Merge vector clock
        for site, counter in operation['vector_clock'].items():
            current = self.vector_clock.get(site, 0)
            self.vector_clock[site] = max(current, counter)
        
        # Insert in sorted position (by ID)
        # This ensures all sites get same order regardless of arrival time
        insert_pos = self._find_position_by_id(char.id)
        self.characters.insert(insert_pos, char)
    
    def local_delete(self, position: int):
        """Local deletion - marks as tombstone."""
        if position >= len([c for c in self.characters if c.visible]):
            return None
            
        # Find the nth visible character
        visible_chars = [c for c in self.characters if c.visible]
        target_char = visible_chars[position]
        
        # Mark as tombstone (not actually deleted!)
        target_char.visible = False
        target_char.tombstone = True
        
        # Log for undo
        self.operation_log.append({
            'type': 'delete',
            'char_id': target_char.id,
            'char': target_char.char
        })
        
        # Broadcast tombstone
        return {
            'type': 'delete',
            'char_id': target_char.id,
            'vector_clock': self.vector_clock.copy()
        }
    
    def local_undo(self):
        """Undo last local operation."""
        if not self.operation_log:
            return False
            
        last_op = self.operation_log.pop()
        
        if last_op['type'] == 'insert':
            # Find character by ID and mark as tombstone
            for char in self.characters:
                if char.id == last_op['char_id']:
                    char.visible = False
                    char.tombstone = True
                    break
        elif last_op['type'] == 'delete':
            # Find character and make visible again
            for char in self.characters:
                if char.id == last_op['char_id']:
                    char.visible = True
                    char.tombstone = False
                    break
        
        return True
    
    def get_text(self):
        """Get current text (excluding tombstones)."""
        return ''.join(c.char for c in self.characters if c.visible)
    
    def _find_insert_index(self, position):
        """Simplified position finding."""
        # Real CRDTs use fractional indexing between existing IDs
        visible_count = 0
        for i, char in enumerate(self.characters):
            if char.visible:
                if visible_count == position:
                    return i
                visible_count += 1
        return len(self.characters)

# The CRDT guarantee:
# 1. All sites see same final state (convergence)
# 2. Undo operations commute with regular operations
# 3. No lost edits, even with network delays
```

(20:00 - Scaling Optimizations: Making It Production Ready)

Narration: "Now we have the algorithms. But at Google Docs scale (millions of users, billions of edits), we need optimizations:"

```python
class ProductionHistorySystem:
    """Production-ready history with all optimizations."""
    
    def __init__(self):
        # 1. Generational Storage (like Git)
        self.recent_edits = RecentEditBuffer()  # In-memory, detailed
        self.old_checkpoints = DiskCheckpointStorage()  # On disk, compressed
        
        # 2. Delta Encoding
        self.store_deltas_not_states = True
        
        # 3. Lazy Cloning
        self.clone_on_write = True
        
        # 4. Hash Consing (structural sharing)
        self.object_pool = ObjectPool()
        
        # 5. Garbage Collection
        self.gc_threshold_mb = 100
        
    class RecentEditBuffer:
        """Store recent edits in memory with full detail."""
        def __init__(self, max_edits=1000):
            self.edits = []
            self.max_edits = max_edits
            
        def add_edit(self, edit):
            self.edits.append(edit)
            if len(self.edits) > self.max_edits:
                self._compact_oldest()
                
        def _compact_oldest(self):
            """Move oldest edits to checkpoint storage."""
            # Take first 100 edits
            to_compact = self.edits[:100]
            
            # Create checkpoint
            checkpoint = self._create_checkpoint(to_compact)
            
            # Store to disk
            self.disk_storage.save_checkpoint(checkpoint)
            
            # Remove from memory
            self.edits = self.edits[100:]
    
    class ObjectPool:
        """Share identical immutable objects across versions."""
        def __init__(self):
            self.pool = {}  # hash -> object
            
        def get_or_create(self, obj):
            """Get existing object or create new."""
            obj_hash = hash(obj)
            
            if obj_hash in self.pool:
                # Return existing object
                return self.pool[obj_hash]
            else:
                # Store and return new
                self.pool[obj_hash] = obj
                return obj
    
    def apply_edit_optimized(self, edit):
        """Apply edit with all optimizations."""
        # 1. Create delta (not full state)
        delta = self._compute_delta(self.current_state, edit)
        
        # 2. Store delta in recent buffer
        self.recent_edits.add_edit({
            'delta': delta,
            'timestamp': time.time(),
            'author': edit.author
        })
        
        # 3. Apply delta to create new state
        new_state = self._apply_delta(self.current_state, delta)
        
        # 4. Use object pool for sharing
        new_state = self.object_pool.get_or_create(new_state)
        
        # 5. Update current
        self.current_state = new_state
        
        # 6. Check memory usage
        if self._memory_usage_mb() > self.gc_threshold_mb:
            self._run_garbage_collection()
    
    def _run_garbage_collection(self):
        """Garbage collect unreachable states."""
        # Mark all reachable states from current
        reachable = self._find_reachable_states(self.current_state)
        
        # Also keep states referenced by recent edits
        for edit in self.recent_edits.edits:
            if 'old_state' in edit:
                reachable.add(edit['old_state'])
        
        # Remove unreachable from object pool
        for obj_hash in list(self.object_pool.pool.keys()):
            obj = self.object_pool.pool[obj_hash]
            if obj not in reachable:
                del self.object_pool.pool[obj_hash]
        
        # Compact recent edits
        self.recent_edits._compact_oldest()
    
    def time_travel_efficient(self, target_time):
        """Time travel optimized for production."""
        # 1. Find nearest checkpoint
        checkpoint = self._find_nearest_checkpoint(target_time)
        
        # 2. Load checkpoint state
        state = checkpoint.state
        
        # 3. Apply deltas from checkpoint to target
        deltas = self._get_deltas_between(checkpoint.time, target_time)
        
        for delta in deltas:
            state = self._apply_delta(state, delta)
        
        return state

# Production examples:
# 1. Git: Packfiles for storage, delta compression
# 2. Google Docs: Operational transformation with checkpoints
# 3. Figma: Incremental snapshots, binary diffs
# 4. VS Code: Text buffer piece table, edit batches
```

(23:00 - Time Travel Debugging: The Ultimate Application)

Narration: "The most sophisticated use of these patterns: time travel debugging. Record execution, rewind, inspect any moment:"

```python
class TimeTravelDebugger:
    """Record program execution for debugging."""
    
    def __init__(self, program):
        self.program = program
        self.execution_trace = PersistentList()  # All states
        self.checkpoints = PersistentMap()  # Periodic full states
        self.current_step = 0
        self.breakpoints = PersistentSet()
        
    def record_step(self):
        """Record current program state."""
        state = self.program.capture_state()
        
        # Delta encoding: store diff from previous
        if self.current_step > 0:
            prev_state = self.execution_trace[self.current_step - 1]
            delta = self._compute_state_diff(prev_state, state)
            
            # Only store non-empty deltas
            if delta:
                self.execution_trace = self.execution_trace.append({
                    'step': self.current_step,
                    'delta': delta,
                    'type': 'delta'
                })
        else:
            # First step: store full state
            self.execution_trace = self.execution_trace.append({
                'step': 0,
                'state': state,
                'type': 'full'
            })
        
        # Checkpoint every 100 steps
        if self.current_step % 100 == 0:
            self.checkpoints = self.checkpoints.set(
                self.current_step,
                state  # Full state at checkpoint
            )
        
        self.current_step += 1
    
    def rewind_to(self, target_step):
        """Rewind execution to any step."""
        # Find nearest checkpoint
        checkpoint_step = self._find_nearest_checkpoint(target_step)
        checkpoint_state = self.checkpoints.get(checkpoint_step)
        
        if not checkpoint_state:
            # No checkpoint, start from beginning
            checkpoint_step = 0
            checkpoint_state = self.execution_trace[0]['state']
        
        # Apply deltas from checkpoint to target
        state = checkpoint_state
        for step in range(checkpoint_step + 1, target_step + 1):
            entry = self.execution_trace[step]
            if entry['type'] == 'delta':
                state = self._apply_delta(state, entry['delta'])
        
        # Restore program
        self.program.restore_state(state)
        self.current_step = target_step
        
        # Check breakpoints
        self._check_breakpoints(target_step)
    
    def set_breakpoint(self, condition_func, bidirectional=True):
        """Set breakpoint that works in both directions."""
        self.breakpoints = self.breakpoints.add({
            'condition': condition_func,
            'bidirectional': bidirectional,
            'hit_steps': PersistentList()  # When it was hit
        })
    
    def step_backward(self):
        """Step backward one instruction."""
        if self.current_step > 0:
            self.rewind_to(self.current_step - 1)
            return True
        return False
    
    def step_forward(self):
        """Step forward one instruction."""
        if self.current_step < len(self.execution_trace) - 1:
            self.rewind_to(self.current_step + 1)
            return True
        return False
    
    def _check_breakpoints(self, step):
        """Check if any breakpoint condition is met at this step."""
        state = self._reconstruct_state(step)
        
        for bp in self.breakpoints:
            if bp['condition'](state):
                # Record hit
                bp['hit_steps'] = bp['hit_steps'].append(step)
                
                # If bidirectional or moving forward, pause
                if bp['bidirectional'] or step > self.current_step:
                    self.program.pause()
                    return True
        
        return False

# Used in:
# 1. Chrome DevTools: Time travel debugging
# 2. RR (Record and Replay): Linux system call recording
# 3. Undo.io: State management for web apps
# 4. Visual Studio: Historical debugging
```

(25:00 - Recap: From LeetCode to Production)

[Visual: Evolution diagram]

Narration: "Let's connect the journey:"

```
LEETCODE INTERVIEW            → PRODUCTION SYSTEM
──────────────────            ──────────────────
Two stacks (undo/redo)        → Branching DAG history
Linear history only           → Merge conflicts handled
O(n) memory per op            → Structural sharing
Single user                   → CRDT collaboration
Simple text editor            → Time travel debugging
No scaling                    → Generational storage + GC
```

Key Insights:

1. Immutable data enables time travel - By never mutating, we preserve history
2. Structural sharing makes it efficient - Copy only what changes
3. DAGs model real undo/redo - Life branches, so does history
4. CRDTs solve collaboration - Conflict-free merging of concurrent edits
5. Optimizations enable scale - Delta encoding, checkpoints, object pooling

(26:00 - Next Episode Teaser: LRU Cache)

Narration: "We've mastered preserving history. But what about when we need to forget? When memory is limited and we must decide what to keep and what to discard?"

[Visual: Cache eviction, memory management]

Narration: "That's the story of LRU Cache - the data structure that powers browser caches, Redis eviction policies, and operating system page replacement. From LeetCode to production caching at scale."

---

EPISODE 4 COMPLETE

Duration: ~26 minutes
Now includes all planned concepts:

1. ✅ LeetCode foundation (two-stack undo/redo)
2. ✅ Immutable structures & structural sharing
3. ✅ Version DAGs & branching history
4. ✅ CRDTs for collaborative undo
5. ✅ Scaling optimizations (generational, delta encoding, GC)
6. ✅ Time travel debugging (ultimate application)
7. ✅ Production systems (Redux, Google Docs, VS Code)

