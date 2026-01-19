# Episode 2: Finding the Merge Base
## From LeetCode #160 to 100M Commits

**Comprehensive Storyboard — Merging Chapters 2.a + 2.b**

---

## 🎯 Presenter's Intent

**Core message**: "Every `git merge` solves a graph problem. The LeetCode solution takes 50 seconds. Production Git does it in milliseconds. Monorepo Git does it across 100M commits in under 200ms. Let's see the engineering journey."

**Audience**: Senior engineers who will ask:
- "Isn't this just LCA in a DAG?" → Yes, addressed in Act 1
- "What about commit-graph?" → Act 4
- "How does this scale to Google/Meta monorepos?" → Acts 5-7

**Duration**: 30-35 minutes (can be split into two 15-min sessions)

---

## Narrative Arc

```
ACT 1-2: The Problem & LeetCode Foundation (7 min)
    ↓
ACT 3: Scale Break #1 — Storage Costs (5 min)
    ↓
ACT 4: Scale Break #2 — Commit-Graph Acceleration (4 min)
    ↓
ACT 5: Scale Break #3 — Distributed Systems (5 min)
    ↓
ACT 6: Scale Break #4 — Probabilistic Data Structures (5 min)
    ↓
ACT 7: The Complete Architecture (4 min)
    ↓
EPILOGUE: Patterns Everywhere (3 min)
```

---

## ACT 1: The Problem Statement (3 minutes)

### Slide 1: Opening Hook

> "Every time you run `git merge main`, Git solves a graph theory problem that would take 50 seconds with a naive algorithm. At Google scale, that same problem spans 100 million commits. It still completes in under 200ms. Let's see how."

**Visual**: Terminal showing `git merge main` completing instantly

---

### Slide 2: What Git Actually Does

```
You run:     git merge main

Git does:    1. Find merge-base (common ancestor)  ← TODAY'S FOCUS
             2. Three-way diff: base → yours, base → theirs
             3. Combine changes, flag conflicts
             4. Create merge commit
```

**Key point**: "Without the merge base, Git can't tell the difference between a change and a deletion."

---

### Slide 3: The DAG Reality

**Animation**: Build up a commit DAG

```
        A───B───C  (main)
       /         \
      D           ?  (merge commit needs merge-base!)
       \         /
        E───F───G  (feature)

Merge base of C and G = ?
```

**Say explicitly**: "Git's history is a DAG (Directed Acyclic Graph), not a simple linked list. Merge commits have multiple parents. But when walking a single branch, we traverse a linked-list-like parent chain."

**This earns credibility immediately.**

---

### Slide 4: Why Merge Base Matters

**Visual**: Three-way merge example

```
Base (merge-base):  "hello world"
Theirs (main):      "hello beautiful world"  ← added "beautiful"
Ours (feature):     "hello world!"           ← added "!"

Result:             "hello beautiful world!" ← both changes merged!
```

**Without merge base**: "You'd have to manually compare every line. Conflicts become unsolvable."

---

## ACT 2: The LeetCode Foundation (4 minutes)

### Slide 5: LeetCode #160 — Intersection of Two Linked Lists

**Animation**: Two linked lists converging at intersection point

```
List A:  a1 → a2 → a3 ↘
                       c1 → c2 → c3
List B:       b1 → b2 ↗

Find c1 (the intersection node)
```

**Say**: "This is exactly the merge-base problem! Two branches that diverged from a common commit share a 'tail' of history."

---

### Slide 6: The Naive O(n²) Approach

```python
# For each node in A, check every node in B
for node_a in list_a:        # n iterations
    for node_b in list_b:    # m iterations
        if node_a is node_b:
            return node_a

# 100K commits × 50K commits = 5 billion comparisons
# At 10ns each = 50 seconds. UNACCEPTABLE.
```

**Visual**: Progress bar crawling

---

### Slide 7: The Elegant O(n+m) Solution

**Animation**: Length measurement → alignment → parallel walk

```python
def find_intersection(headA, headB):
    # Step 1: Measure lengths
    lenA = get_length(headA)  # O(n)
    lenB = get_length(headB)  # O(m)
    
    # Step 2: Align starting points
    if lenA > lenB:
        headA = skip(headA, lenA - lenB)
    else:
        headB = skip(headB, lenB - lenA)
    
    # Step 3: Walk together until they meet
    while headA and headB:
        if headA is headB:
            return headA  # Found intersection!
        headA = headA.next
        headB = headB.next
    
    return None
```

**Key insight**: "If lists share a tail, aligning them by length puts both pointers equidistant from intersection."

---

### Slide 8: Complexity Achieved

| Metric | Naive | Aligned Walk |
|--------|-------|--------------|
| Time | O(n × m) | O(n + m) |
| Space | O(1) | O(1) |
| 100K commits | 50 seconds | 150 milliseconds |

**Say**: "Algorithmic victory! But production has complications..."

---

## ACT 3: Scale Break #1 — Storage Costs (5 minutes)

### Slide 9: The Hidden Cost of `.parent`

**Visual**: Drill-down animation from code to storage layers

```python
# In LeetCode (RAM):
node.next  →  10 nanoseconds

# In Git (disk):
commit.parent  →  10 microseconds to 100 milliseconds

# WHY? Commits live on disk, not RAM!
```

---

### Slide 10: Git's Storage Hierarchy

**Animation**: Layered diagram with latency numbers

```
┌─────────────────────────────────────────────┐
│  Memory Cache      │ 10 ns    │ ~10K commits │
├────────────────────┼──────────┼──────────────┤
│  Commit-Graph      │ 100 ns   │ memory-mapped│
├────────────────────┼──────────┼──────────────┤
│  Packfiles         │ 1 ms     │ compressed   │
├────────────────────┼──────────┼──────────────┤
│  Loose Objects     │ 10 ms    │ filesystem   │
├────────────────────┼──────────┼──────────────┤
│  Network Fetch     │ 100 ms+  │ remote       │
└────────────────────┴──────────┴──────────────┘
```

**Say**: "Our O(n) algorithm just became O(n × disk_seeks). 150K seeks at 1ms each = 150 seconds. **Worse than the naive approach!**"

---

### Slide 11: The Fix — Batched I/O

**Animation**: Sequential reads (slow) vs batched reads (fast)

```python
# BEFORE: Read one at a time
for sha in ancestors:
    commit = read_from_disk(sha)  # SEEK, READ, SEEK, READ...

# AFTER: Batch reads
batch = collect_next_100_shas(queue)
commits = batch_read(batch)  # ONE SEEK, MANY READS
```

**Result**: 
- 150,000 individual reads → 1,500 batched reads
- 150 seconds → 1.5 seconds

---

### Slide 12: Bidirectional BFS

**Animation**: Two frontiers expanding toward each other

```python
def bidirectional_bfs(sha1, sha2):
    """Meet in the middle — halves the search space!"""
    queue1, queue2 = deque([sha1]), deque([sha2])
    visited1, visited2 = {sha1}, {sha2}
    
    while queue1 and queue2:
        # Expand smaller frontier (optimization)
        if len(queue1) <= len(queue2):
            result = expand_frontier(queue1, visited1, visited2)
        else:
            result = expand_frontier(queue2, visited2, visited1)
        
        if result:
            return result  # Frontiers met!
    
    return None
```

**Key insight**: "Instead of walking 100K commits from one side, walk 316 from each (√100K). Search space reduced 316x!"

---

## ACT 4: Scale Break #2 — Commit-Graph Acceleration (4 minutes)

### Slide 13: What If We Precomputed Ancestry?

**Visual**: `.git/objects/info/commit-graph` file

```
Commit-graph contains:
├── All commit SHAs (sorted)
├── Parent pointers (indexed)
├── Generation numbers (topological depth)
├── Bloom filters (path queries)
└── Memory-mapped for instant access
```

**Say**: "This single file transforms merge-base from seconds to microseconds."

---

### Slide 14: Generation Numbers — The Pruning Trick

**Animation**: DAG with generation numbers, branches being pruned

```
Commit    Gen#
──────    ────
   G       6     ← If looking for merge-base of G and C...
   F       5
   C       4     ← ...and gen(X) > gen(C), X can't be ancestor of C
   E       4
   B       3     ← Skip entire branches instantly!
   D       2
   A       1
```

**Key insight**: "If gen(X) > gen(Y), then X cannot be an ancestor of Y. Prune entire branches without traversing them."

---

### Slide 15: Performance Comparison

| Approach | Time | Why |
|----------|------|-----|
| Naive O(n²) | 50 sec | Check everything |
| Aligned O(n) | 150 sec | Disk seeks kill us |
| Batched BFS | 1.5 sec | Amortize I/O |
| Bidirectional | 200 ms | Meet in middle |
| **Commit-graph** | **< 1 ms** | Precomputed + mmap |

**Say**: "Same algorithm. 50,000x faster. But what happens at 100 million commits?"

---

## ACT 5: Scale Break #3 — Distributed Systems (5 minutes)

### Slide 16: The Monorepo Crisis

**Visual**: Numbers that break everything

```python
# Google/Meta scale:
REPO_SIZE = 100_000_000  # 100M commits
DAILY_MERGES = 50_000
LONGEST_BRANCH = 2_000_000  # 2M commits deep

# Even with commit-graph:
# 100M commits × 100 bytes = 10GB
# Can't memory-map that on every laptop!
```

**Say**: "At this scale, the problem isn't algorithmic. It's architectural."

---

### Slide 17: Why Distributed?

```
The physics of scale:
├── RAM is expensive: 1TB server = $50,000+
├── Network is slow: RAM (100ns) vs cross-region (50ms) = 500,000x
├── Disks fail: 4% annual failure rate
└── Developers are global: Can't sync 10GB on every fetch
```

**Solution**: Shard data across machines

```
Shard 0: Commits 0-25M
Shard 1: Commits 25M-50M
Shard 2: Commits 50M-75M
Shard 3: Commits 75M-100M
```

---

### Slide 18: The Network Cost Problem

**Animation**: Cross-shard calls multiplying

```python
def distributed_merge_base(sha1, sha2):
    shard1 = locate_shard(sha1)  # Network: 1ms
    commit1 = shard1.get(sha1)   # Network: 1ms
    
    for parent in commit1.parents:
        shard_p = locate_shard(parent)  # Network: 1ms
        # ... repeat for 2M ancestors
    
    # 2M network calls × 1ms = 2,000 seconds!
```

**Say**: "Cross-shard communication is the new disk seek. We need a way to answer 'probably no common ancestor' without traversing."

---

## ACT 6: Scale Break #4 — Probabilistic Data Structures (5 minutes)

### Slide 19: The Hero — Bloom Filters

**Animation**: Bloom filter visualization (bits being set)

```
A Bloom filter answers: "Is X in this set?"

Properties:
├── No false negatives: "Not in set" = definitely not
├── Possible false positives: "In set" = probably (99% sure)
├── Space efficient: 1KB can represent millions of items
└── Speed: O(1) lookups, no disk access
```

---

### Slide 20: How Bloom Filters Work

**Interactive Animation**: Add items, check items, see false positive

```
1. Create bit array (e.g., 8192 bits = 1KB)
2. Use k hash functions (e.g., k=7)
3. To ADD item: Set k bits to 1
4. To CHECK item: Are all k bits set?

Example (simplified):
Empty:      [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

Add "abc":  hash1(abc)=3, hash2(abc)=7, hash3(abc)=12
Result:     [0,0,0,1,0,0,0,1,0,0,0,0,1,0,0,0]

Check "abc": bits 3,7,12 all set? YES → probably in set ✓
Check "xyz": bits 2,5,9 all set? NO → definitely not in set ✓
```

---

### Slide 21: Bloom Filters for Ancestry

**Visual**: Commit with 1KB ancestry summary

```python
class AncestryBloomFilter:
    """1KB summary of a commit's ENTIRE ancestry."""
    
    def __init__(self):
        self.bits = [0] * 8192  # 1KB
        self.k = 7  # hash functions
    
    def add_ancestor(self, sha):
        for i in range(self.k):
            bit = hash(sha, i) % 8192
            self.bits[bit] = 1
    
    def might_be_ancestor(self, sha):
        for i in range(self.k):
            bit = hash(sha, i) % 8192
            if self.bits[bit] == 0:
                return False  # DEFINITELY NOT
        return True  # PROBABLY YES (99%)
```

**The power**:
```
Exact ancestry:     100MB data, 10 seconds
Bloom filter:       1KB data, 100 nanoseconds
```

---

### Slide 22: The Distributed Algorithm

**Animation**: Bloom filter check → fast "no" or BFS fallback

```python
def distributed_merge_base(sha1, sha2):
    # Step 1: Fetch Bloom filters (tiny, cacheable)
    filter1 = get_ancestry_filter(sha1)  # 1KB
    filter2 = get_ancestry_filter(sha2)  # 1KB
    
    # Step 2: Quick check — do they overlap at all?
    if not filters_might_overlap(filter1, filter2):
        return None  # DEFINITELY no common ancestor!
    
    # Step 3: Bloom says "maybe" — do shard-aware BFS
    return shard_aware_bfs(sha1, sha2)
```

**Say**: "90% of merge-base queries are answered by Bloom filters in microseconds. Only 10% need actual traversal."

---

### Slide 23: SLO-Driven Strategy Selection

**Visual**: Strategy cascade with latency budgets

```python
STRATEGIES = [
    ('commit_graph',    0.1 ms,  99% accurate),
    ('bloom_filter',    1 ms,    99% accurate),
    ('generation_skip', 10 ms,   98% accurate),
    ('sampled_bfs',     50 ms,   95% accurate),
    ('exact_bfs',       200 ms,  100% accurate),
]

def find_merge_base(sha1, sha2, max_latency=200):
    for strategy, latency, accuracy in STRATEGIES:
        if latency <= remaining_budget:
            result = strategy(sha1, sha2)
            if result:
                return result
    
    return approximate_fallback()
```

**Key insight**: "Sometimes 95% accurate in 50ms beats 100% accurate in 40 seconds."

---

## ACT 7: The Complete Architecture (4 minutes)

### Slide 24: Production Architecture

**Animation**: Build up layers one by one

```
┌─────────────────────────────────────────────────┐
│           MONOREPO MERGE BASE SERVICE           │
├─────────────────────────────────────────────────┤
│  OBSERVABILITY                                  │
│  • Metrics (latency, hit rates, errors)         │
│  • Distributed tracing (cross-shard calls)      │
│  • Alerting (SLO violations)                    │
├─────────────────────────────────────────────────┤
│  RELIABILITY                                    │
│  • Circuit breakers (fail fast on overload)     │
│  • Retry policies (exponential backoff)         │
│  • Graceful degradation (approximate fallback)  │
├─────────────────────────────────────────────────┤
│  COMPUTATION                                    │
│  • Strategy engine (SLO-driven selection)       │
│  • Bloom filter index (probabilistic checks)    │
│  • Generation numbers (branch pruning)          │
├─────────────────────────────────────────────────┤
│  STORAGE                                        │
│  • Sharded commits (10+ shards)                 │
│  • Edge caches (geographically distributed)     │
│  • LRU memory cache (hot commits)               │
├─────────────────────────────────────────────────┤
│  ALGORITHM                                      │
│  • Bidirectional BFS with batching              │
│  • Length-aligned traversal (LeetCode #160!)    │
└─────────────────────────────────────────────────┘
```

---

### Slide 25: The Full Performance Journey

| Scale | Approach | Time | Key Innovation |
|-------|----------|------|----------------|
| 1K commits | Naive O(n²) | 10 ms | None needed |
| 100K commits | Aligned O(n) | 50 sec → 150 ms | Algorithm |
| 1M commits | Commit-graph | 150 ms → 1 ms | Precomputation |
| 100M commits | Distributed + Bloom | 1 ms → 0.1 ms | Architecture |

**Say**: "Same fundamental algorithm. 500,000x faster. That's engineering."

---

## EPILOGUE: Patterns Everywhere (3 minutes)

### Slide 26: This Pattern Repeats

**Visual**: Side-by-side comparisons

| Domain | Graph Type | Algorithm | Scale Trick |
|--------|-----------|-----------|-------------|
| **Git merge-base** | DAG | BFS + alignment | Bloom filters |
| **DNA sequencing** | Tree/DAG | Dynamic programming | Sampling |
| **Social networks** | Graph | Community detection | Probabilistic |
| **Fraud detection** | Transaction graph | Pattern matching | Streaming |

**Say**: "Once you see graph traversal + probabilistic indexing + approximation in Git, you'll recognize it everywhere."

---

### Slide 27: The Engineering Mindset

**Quote on screen**:

> "First make it work, then make it fast, then make it reliable, then make it scale."

**Progression**:
```
LeetCode:     Works ✓
+ Storage:    Fast ✓
+ Validation: Reliable ✓
+ Distributed: Scales ✓
```

---

### Slide 28: Key Takeaways

1. **Algorithms are the foundation** — but only 10% of production code
2. **Storage costs dominate** — disk seeks can make O(n) worse than O(n²)
3. **Probabilistic beats exact** — when speed matters more than perfection
4. **Architecture enables scale** — sharding, caching, fallbacks
5. **Patterns repeat** — Git, DNA, social networks share techniques

---

### Slide 29: Challenge for the Audience

> "How would merge-base computation change for shallow clones where history is truncated?"

**Hint**: What happens when Bloom filters have incomplete ancestry?

---

### Slide 30: What's Next

**Episode 3**: The Invisible Tree — How Git stores your entire codebase with structural sharing

**Tease**: "What if you could store 1000 versions of a file using only 1.1x the space? That's content-defined chunking, and it powers everything from Git to Dropbox to backup systems."

---

## 🎨 Animation Requirements

### Animation 1: DAG Visualization
- Build commit graph node by node
- Show parent pointers as arrows
- Highlight merge-base candidate
- Animate BFS frontiers expanding

### Animation 2: Length Alignment
- Two lists of different lengths
- Measure phase (counters incrementing)
- Align phase (pointer skipping)
- Walk phase (parallel movement)
- Intersection discovery

### Animation 3: Storage Layer Drill-Down
- Start with `commit.parent` code
- Drill into cache → commit-graph → packfile → loose
- Show latency at each level
- Visualize cache miss cascade

### Animation 4: Batched vs Sequential I/O
- Split screen race
- Sequential: slow progress, many seeks
- Batched: fast progress, amortized seeks

### Animation 5: Bidirectional BFS
- Two colored frontiers (blue/orange)
- Expand alternately
- Meet in the middle
- Highlight when frontiers touch

### Animation 6: Commit-Graph with Generation Numbers
- DAG with gen numbers displayed
- Query: "Is X ancestor of Y?"
- Prune branches where gen too high
- Show massive speedup

### Animation 7: Bloom Filter Interactive
- Bit array visualization
- Add items (bits light up)
- Check items (probe bits)
- Show false positive scenario
- Show definite negative

### Animation 8: Distributed Shards
- Multiple machines with commit subsets
- Cross-shard query visualization
- Bloom filter shortcut
- Fallback to BFS

### Animation 9: Strategy Cascade
- Waterfall of strategies
- Each tries, passes to next
- Show latency budget decreasing
- Final result returned

### Animation 10: Architecture Layer Cake
- Build from bottom (algorithm) up
- Each layer adds capability
- Final reveal with performance numbers

---

## 📊 Senior Engineer FAQ

**Q: "Why not just use a proper graph database?"**
A: Git is designed for distributed, offline operation. Content-addressing enables trustless sync. A centralized database would require coordination that breaks the distributed model.

**Q: "What about rebase? Doesn't that break ancestry?"**
A: Rebase creates new commits with new SHAs. Old commits remain until GC. The DAG is append-only. Bloom filters are rebuilt incrementally.

**Q: "How does GitHub/GitLab handle this?"**
A: Additional layers: precomputed merge-bases for hot branch pairs, distributed caching, repo-specific optimizations. Same principles, more caching.

**Q: "What's the false positive rate in practice?"**
A: Tunable. 1% is typical. When Bloom says "maybe", we fall back to exact. False positives cost latency, not correctness.

**Q: "How do you handle Bloom filter staleness?"**
A: Filters are rebuilt on push. Staleness affects only performance (more fallbacks to exact), not correctness.

**Q: "What about merge commits with multiple parents?"**
A: BFS naturally handles multiple parents. Each parent is added to the queue. The algorithm generalizes from linked list to DAG.

---

## 🎯 Key Moments to Nail

| Time | Moment | Why It Matters |
|------|--------|----------------|
| 0:30 | "50 seconds → 200 microseconds" | Hook with concrete improvement |
| 3:00 | DAG vs linked list clarification | Earns credibility |
| 7:00 | "Disk makes O(n) worse than O(n²)" | The plot twist |
| 12:00 | Commit-graph reveal | First major solution |
| 17:00 | "100M commits breaks everything" | Stakes escalation |
| 22:00 | Bloom filter "aha" moment | The hero concept |
| 28:00 | Layer cake with 500,000x | The payoff |

---

## 🔧 Technical Accuracy Checklist

- [x] DAG, not linked list (clarified in Act 1)
- [x] Three-way merge needs merge-base (Act 1)
- [x] Bidirectional BFS halves search space (Act 3)
- [x] Commit-graph has limits at extreme scale (Act 5)
- [x] Bloom filters have false positives, not false negatives (Act 6)
- [x] SHA-1 → SHA-256 migration compatible (no algorithm change)
- [x] Content-addressing prevents cycles structurally

---

## 📁 Deliverables

1. **episode2_revealjs.html** — Full Reveal.js presentation
2. **episode2_animations.html** — Standalone interactive animations
3. **episode2_storyboard.md** — This file (presenter notes)
4. **LinkedLists/Chapter 2.a.md** — Source content (fundamentals)
5. **LinkedLists/Chapter 2.b.md** — Source content (distributed scale)

---

## 🎬 Suggested Session Split

**Option A: Single 35-minute session**
- Full presentation, move quickly through Acts 5-6

**Option B: Two 18-minute sessions**
- **Session 1** (Acts 1-4): "Merge Base Fundamentals" — LeetCode to commit-graph
- **Session 2** (Acts 5-7): "Scaling to 100M Commits" — Distributed + Bloom filters

---

*"The algorithm is the easy part. The engineering is the story."*
