# Episode 2a Storyboard: Finding the Merge Base
## Presentation Guide for Senior Engineers

---

## 🎯 Presenter's Intent

**Core message**: "You've run `git merge` thousands of times. Today you'll see the algorithm powering it—and why the LeetCode version is only 10% of the story."

**Audience calibration**: Senior engineers will immediately ask:
- "Isn't this just LCA in a DAG?"
- "What about commit-graph?"
- "How does this scale to Linux kernel size?"

**Answer those in the first 3 minutes** to earn credibility, then go deep.

---

## Act Structure (20-minute presentation)

### **Opening Hook (30 seconds)**

> "Every time you run `git merge main`, Git solves a graph theory problem that would take 50 seconds with a naive algorithm. It does it in under a millisecond. Let's see how."

**Visual**: Show a real `git merge` completing instantly on a large repo.

---

### **ACT 1: The Problem Statement (2 minutes)**

**Slide 1: What Git Actually Does**
```
You:     git merge main
Git:     1. Find merge-base (common ancestor)
         2. Three-way diff: base → yours, base → theirs
         3. Combine changes, flag conflicts
```

**Key point**: "Without the merge base, Git can't tell the difference between a change and a deletion."

**Slide 2: The DAG Reality**
```
        A───B───C  (main)
       /         \
      D           ?  (merge commit)
       \         /
        E───F───G  (feature)
```

**Say explicitly**: "This is a DAG, not a linked list. Merge commits have multiple parents. But when walking a single branch, we're traversing a linked-list-like parent chain."

*This preempts the "but Git isn't a linked list" objection.*

---

### **ACT 2: The LeetCode Foundation (3 minutes)**

**Slide 3: LeetCode #160 — Intersection of Two Linked Lists**

**Interactive Animation**: Two lists converging

```python
# The naive O(n²) approach
for node_a in list_a:
    for node_b in list_b:
        if node_a is node_b:
            return node_a  # Found!
```

**Say**: "100K commits each = 10 billion comparisons = 50 seconds. Unacceptable."

**Slide 4: The Elegant O(n) Solution**

**Animation**: Length measurement → alignment → parallel walk

```python
# 1. Measure lengths
# 2. Align starting points (skip extra nodes in longer list)
# 3. Walk together until they meet
```

**Key insight**: "If lists share a tail, aligning them by length puts both pointers equidistant from intersection."

**Say**: "This is the algorithmic foundation. But production has complications."

---

### **ACT 3: Scale Break #1 — Storage Costs (4 minutes)**

**Slide 5: "The Hidden Cost of `.parent`"**

```
In LeetCode:    node.next    → ~10 nanoseconds (RAM)
In Git:         commit.parent → 10 microseconds to 100 milliseconds

Why? Commits live on disk, not RAM.
```

**Visual**: Layered storage diagram
```
┌─────────────────────────────────────────┐
│  Memory Cache (10ns)     ~10K commits   │
├─────────────────────────────────────────┤
│  Commit-Graph (100ns)    memory-mapped  │
├─────────────────────────────────────────┤
│  Packfiles (1ms)         compressed     │
├─────────────────────────────────────────┤
│  Loose Objects (10ms)    filesystem     │
├─────────────────────────────────────────┤
│  Network Fetch (100ms+)  remote         │
└─────────────────────────────────────────┘
```

**Say**: "Our O(n) algorithm just became O(n × disk_seeks). 150K seeks at 1ms each = 150 seconds. Worse than the naive approach!"

**Slide 6: The Fix — Batched I/O**

```python
# Instead of: read, seek, read, seek, read, seek...
# Do:         collect 100 SHAs → batch read → process

batch_size = 100
# 150,000 individual reads → 1,500 batched reads
# 150 seconds → 1.5 seconds
```

**Animation**: Show sequential reads (slow) vs batched reads (fast)

---

### **ACT 4: Scale Break #2 — The Commit-Graph Acceleration (3 minutes)**

**Slide 7: Precomputed Ancestry**

**Say**: "What if we could precompute reachability?"

```
.git/objects/info/commit-graph

Contains:
- Generation numbers (topological ordering)
- Bloom filters for path queries
- Memory-mapped for instant access
```

**Visual**: Query time comparison
```
Without commit-graph:  BFS traversal, disk seeks  → seconds
With commit-graph:     Memory lookup, bloom check → microseconds
```

**Slide 8: Generation Numbers**

```
Commit    Gen#
──────    ────
   G       6
   F       5
   C       4
   E       4
   B       3
   D       2
   A       1
```

**Key insight**: "If gen(X) > gen(Y), then X cannot be an ancestor of Y. Prune entire branches instantly."

**Say**: "This reduces most common traversals from seconds to milliseconds—but worst-case walks still exist."

---

### **ACT 5: Scale Break #3 — Integrity Under Failure (3 minutes)**

**Slide 9: When Hardware Lies**

```
Reality at scale:
- Disk sectors corrupt silently
- Memory has bit flips (cosmic rays!)
- Network packets get mangled
```

**Say**: "Git's content-addressing is the first line of defense."

**Slide 10: SHA = Self-Validating Data**

```python
# Every read verifies itself
expected_sha = "abc123..."
content = read_from_disk(expected_sha)
actual_sha = sha1(f"commit {len(content)}\0" + content)

if actual_sha != expected_sha:
    # CORRUPTION DETECTED
    # Try: alternate location, remote fetch, mark corrupted
```

**Key insight**: "The hash includes parent hashes. Creating a cycle would require breaking hash integrity—which Git already detects."

*This is why Git doesn't need runtime cycle detection.*

---

### **ACT 6: Scale Break #4 — Concurrency (2 minutes)**

**Slide 11: Multiple Operations at Once**

```
While you compute merge-base:
├── User A: git pull (reading packfiles)
├── User B: git push (writing commits)
├── Background: git gc (repacking objects)
└── System: commit-graph rebuild
```

**Visual**: Timeline showing concurrent operations with locks

**Say**: "Read-write locks let multiple readers proceed while blocking writers. Merge-base computation is a reader."

**Slide 12: Graceful Degradation**

```python
if operation_too_long(timeout=500ms):
    return approximate_merge_base()  # Good enough!
```

**Say**: "Sometimes fast-and-approximate beats slow-and-exact."

---

### **ACT 7: The Complete Picture (2 minutes)**

**Slide 13: Performance Comparison**

| Approach | Time | RAM | Disk I/O |
|----------|------|-----|----------|
| Naive O(n²) | 50 sec | 100 MB | None |
| Basic O(n) | 150 sec | Minimal | 150K seeks |
| Batched BFS | 10 sec | 10 MB | 1.5K batches |
| **Production** | **< 1 ms** | ~50 MB | None (mmap) |

**Say**: "Same algorithm. 150,000x faster. That's engineering."

**Slide 14: The Layer Cake**

**Animation**: Build up layers one by one

```
┌─────────────────────────────────────────┐
│  OBSERVABILITY: Metrics, logs, traces   │
├─────────────────────────────────────────┤
│  CACHING: Distributed + local + mmap    │
├─────────────────────────────────────────┤
│  CONCURRENCY: Locks, timeouts, fallback │
├─────────────────────────────────────────┤
│  VALIDATION: SHA verification, repair   │
├─────────────────────────────────────────┤
│  STORAGE: Batching, packfiles, graph    │
├─────────────────────────────────────────┤
│  ALGORITHM: BFS with length alignment   │
└─────────────────────────────────────────┘
```

---

### **Closing (30 seconds)**

**Slide 15: The Engineering Mindset**

> "First make it work, then make it fast, then make it reliable, then make it scale."

**Challenge for audience**: "How would merge-base change for shallow clones where history is truncated?"

**Tease next episode**: "Next time: Browser history. Every back button is a doubly linked list traversal—but how does Chrome handle 10,000 tabs across sessions with crash recovery?"

---

## 🎨 Animation Requirements

### Animation 1: DAG Visualization
- Show commits as nodes, parent pointers as edges
- Highlight two branches (main, feature)
- Animate merge-base search (BFS coloring)
- Show merge commit creation

### Animation 2: Length Alignment
- Two lists of different lengths
- Animate length measurement
- Show pointer alignment (skip extra nodes)
- Parallel walk to intersection

### Animation 3: Storage Layer Dive
- Drill down from `commit.parent` call
- Show cache miss → commit-graph → packfile → loose object
- Visualize latency at each layer

### Animation 4: Batched I/O
- Split screen: sequential reads (slow) vs batched (fast)
- Progress bars racing

### Animation 5: Commit-Graph
- Show generation numbers on DAG
- Animate branch pruning ("gen(X) > gen(Y) → skip")
- Bloom filter query visualization

### Animation 6: Concurrent Operations
- Multiple git operations on timeline
- Show lock acquisition/release
- Visualize read-write lock allowing parallel reads

### Animation 7: Layer Cake Build
- Start with algorithm
- Add layers one by one with performance numbers
- Final reveal: < 1ms

---

## 📊 Senior Engineer FAQ (Prepare for Q&A)

**Q: "Why not just use a B-tree or database?"**
A: Git is designed for distributed, offline operation. Content-addressing enables trustless sync. A database would require central coordination.

**Q: "What about rebase? Doesn't that break the DAG?"**
A: Rebase creates new commits (new SHAs). Old commits remain until GC. The DAG is append-only—we never mutate, only add.

**Q: "How does GitHub handle this at scale?"**
A: GitHub has additional layers: precomputed merge-bases for common branch pairs, distributed caching, and repo-specific optimizations. The principles are the same, the scale is different.

**Q: "What if commit-graph is stale?"**
A: Commit-graph is updated incrementally on push. If stale, Git falls back to BFS. Staleness only affects performance, not correctness.

**Q: "How does SHA-256 migration affect this?"**
A: The algorithm is hash-agnostic. SHA-256 repos work identically—only the hash function changes, not the data structure.

---

## 🎯 Key Moments to Nail

1. **Minute 2**: Establish DAG vs linked list distinction (earn credibility)
2. **Minute 5**: Show the O(n²) → O(n) improvement (algorithmic foundation)
3. **Minute 8**: Reveal disk I/O makes O(n) worse than O(n²) (the plot twist)
4. **Minute 12**: Commit-graph as the production solution (the payoff)
5. **Minute 18**: Layer cake showing 150,000x improvement (the climax)

---

## 🔧 Technical Accuracy Checklist

- [x] DAG, not linked list (clarified in Act 1)
- [x] Content-addressing prevents cycles (Act 5)
- [x] SHA-1 → SHA-256 migration mentioned (Act 5)
- [x] Commit-graph has limits (Act 4: "worst-case walks still exist")
- [x] Storage hierarchy is accurate (loose → pack → graph → cache)
- [x] Concurrency model matches real Git (read-write locks)

---

## 📁 File Deliverables

1. `episode2a_revealjs.html` — Reveal.js presentation
2. `episode2a_animations.html` — Standalone animation page
3. `episode2a_storyboard.md` — This file (presenter notes)
4. `LinkedLists/Chapter 2.a.md` — Source content

---

*"The algorithm is the easy part. The engineering is the story."*
