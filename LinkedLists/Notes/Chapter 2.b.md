# Episode 2b: Distributed Merge Base at Scale
## When 100M Commits Break Your Algorithm

**Season 1 — The Invisible Linked List (Advanced Follow-Up)**

---

## The Crisis

Episode 2a solved merge-base for single-machine Git repositories. We optimized from O(n²) to bidirectional BFS. Victory!

Then your company's monorepo hits **100 million commits**. Everything breaks.

```python
# The numbers that break Episode 2a:
REPO_SIZE = 100_000_000  # 100M commits
DAILY_MERGES = 50_000
LONGEST_BRANCH = 2_000_000  # 2M commits deep

# Bidirectional BFS:
# Worst case: 2M depth × 2 = 4M node visits
# At 10µs/visit = 40 seconds per merge
# At 50k merges/day = 555 days of CPU time!

# Memory: Commit-graph for 100M commits?
# 100M × 100 bytes = 10GB RAM
# Can't memory-map that on every developer laptop
```

This isn't about finding a better algorithm. This is about **distributed systems, probabilistic data structures, and trading perfect accuracy for speed**.

---

## Part 1: Distributed Systems Fundamentals

### Why 100M Commits Can't Live on One Machine

**The physics**:
- RAM is expensive: 1TB RAM server = $50,000+
- Network is slow: 100ns (RAM) vs 50ms (cross-region) = 500,000x difference
- Disks fail: 4% annual failure rate for HDDs
- Developers are global: Syncing 10GB on every `git fetch` is unacceptable

**Solution**: Shard data across multiple machines

```
Machine 1: Commits 0-25M
Machine 2: Commits 25M-50M  
Machine 3: Commits 50M-75M
Machine 4: Commits 75M-100M
```

### The CAP Theorem Trade-off

**CAP Theorem**: In a distributed system with network partitions, you can have at most 2 of:
1. **Consistency**: All nodes see the same data
2. **Availability**: Every request gets a response
3. **Partition tolerance**: System works despite network failures

**For Git at scale**:
- **Partition tolerance**: Required (network failures happen)
- **Consistency**: Desired (commits are immutable, easier than mutable data)
- **Availability**: Needed (developers can't wait)

**Trade-off**: Use **eventual consistency** with optimistic replication. Commits propagate asynchronously. Merge-base might use slightly stale data, but it converges.

### Data Partitioning Strategies

| Strategy | How It Works | Pro | Con |
|----------|-------------|-----|-----|
| **Range partitioning** | Commits 0-25M on shard 0 | Sequential access fast | Hot spots (recent commits) |
| **Hash partitioning** | SHA hash % N = shard ID | Uniform distribution | Poor locality (parents on different shards) |
| **Graph partitioning** | Keep related commits together | Minimizes cross-shard queries | Complex rebalancing |
| **Hybrid** | Hash for storage, replicate hot commits | Balanced load + locality | Higher storage cost |

**Git at scale uses hybrid**: Hash-partition for storage, cache hot commits (recent merges, active branches) locally.

### The Network Cost Problem

Finding merge-base in a distributed system:

```python
class DistributedReality:
    def find_merge_base(self, commit_a, commit_b):
        # Step 1: Which shard has commit_a?
        shard_a = self.locate(commit_a)  # Network call: 1ms
        
        # Step 2: Fetch commit_a
        data_a = shard_a.get(commit_a)  # Network call: 1ms
        
        # Step 3: For each parent of commit_a:
        for parent in data_a.parents:
            shard_p = self.locate(parent)  # Network call: 1ms
            # ... and so on
        
        # Problem: Bidirectional BFS on 2M-depth branch
        # = 2M network calls = 2,000 seconds!
```

**Key insight**: We must minimize cross-shard communication. We need **probabilistic approximations** that give "good enough" answers fast.

---

## Part 2: Probabilistic Data Structures Theory

### The Space-Time-Accuracy Trade-off

Exact algorithms require:
- **Space**: Store complete ancestry information
- **Time**: Traverse entire graph
- **Accuracy**: 100% correct answer

Probabilistic algorithms trade accuracy for speed:
- **Space**: Store compact summaries (1KB instead of 100MB)
- **Time**: O(1) lookups instead of O(n) traversals  
- **Accuracy**: 99.9% correct (with tunable false positive rate)

### Bloom Filters: The Foundation

A **Bloom filter** is a space-efficient probabilistic data structure that answers: **"Is X in the set?"**

**Properties**:
- **No false negatives**: If it says "not in set", definitely not in set
- **Possible false positives**: If it says "in set", probably in set (1% chance wrong)
- **Space efficiency**: 1KB can represent millions of items
- **Speed**: O(1) lookups, no disk access

**How it works**:
```
1. Create bit array of size m (e.g., 8192 bits = 1KB)
2. Use k hash functions (e.g., k=7)
3. To add item: Set k bits to 1
4. To check item: Check if all k bits are 1
```

**Example** (simplified with 16 bits, 3 hash functions):
```
Empty filter:     [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

Add "commit-abc":
  hash1(abc) % 16 = 3
  hash2(abc) % 16 = 7  
  hash3(abc) % 16 = 12
  
After:            [0,0,0,1,0,0,0,1,0,0,0,0,1,0,0,0]

Add "commit-xyz":
  hash1(xyz) % 16 = 1
  hash2(xyz) % 16 = 7  (collision!)
  hash3(xyz) % 16 = 14
  
After:            [0,1,0,1,0,0,0,1,0,0,0,0,1,0,1,0]

Check "commit-abc": bits 3,7,12 all set? YES → probably in set ✓
Check "commit-xyz": bits 1,7,14 all set? YES → probably in set ✓  
Check "commit-foo": bits 2,8,9 all set? NO → definitely not in set ✓
Check "commit-bar": bits 1,7,12 all set? YES → FALSE POSITIVE! ✗
```

**False positive probability**:
```
P(false_positive) = (1 - e^(-kn/m))^k

Where:
  k = number of hash functions
  n = number of items inserted
  m = number of bits

Optimal k = (m/n) * ln(2) ≈ 0.7 * (m/n)
```

For 1% false positive rate with 1M items: need ~1.2MB

### Why Bloom Filters Win for Git Ancestry

**Problem**: Does commit A have commit B as an ancestor?

**Exact solution**:
- Store full ancestry list: 100MB per commit
- Traverse graph: 10,000+ disk seeks
- Time: 10 seconds

**Bloom filter solution**:
- Store 1KB summary of ancestry
- Check bits: 7 memory accesses
- Time: 100 nanoseconds
- Accuracy: 99% (1% false positives acceptable for merge-base hints)

Now let's implement it.

---

## Part 3: Building Ancestry Bloom Filters

```python
class AncestryBloomFilter:
    """
    1KB summary of a commit's entire ancestry.
    False positives possible, but no false negatives.
    """
    
    def __init__(self, size_bits=8192):  # 1KB
        self.bits = [0] * size_bits
        self.hash_functions = 7  # Optimal for 1% false positive rate
    
    def add_commit(self, sha):
        """Add a commit to the filter."""
        for i in range(self.hash_functions):
            hash_val = self.hash(sha, i)
            bit_pos = hash_val % len(self.bits)
            self.bits[bit_pos] = 1
    
    def might_contain(self, sha):
        """Check if commit might be in ancestry."""
        for i in range(self.hash_functions):
            hash_val = self.hash(sha, i)
            bit_pos = hash_val % len(self.bits)
            if self.bits[bit_pos] == 0:
                return False  # Definitely not in ancestry
        return True  # Probably in ancestry (1% chance wrong)
    
    def merge(self, other_filter):
        """Combine two ancestry filters (OR operation)."""
        # Used to build parent ancestry filters
        for i in range(len(self.bits)):
            self.bits[i] = self.bits[i] or other_filter.bits[i]

# The power: Instead of 100MB ancestor list → 1KB filter
# Check for common ancestry: Merge two filters, check bits
# Answer: "Definitely no" or "Probably yes"
```

Narration: "Each shard precomputes Bloom filters for its commits. When we need a merge base, we first check filters: if they don't overlap, definitely no common ancestor. Game over in microseconds."

(7:00 - Building the Filter Hierarchy)

[Visual: Tree showing filters built bottom-up from commits]

Narration: "We build these filters incrementally and cache aggressively:"

```python
def build_ancestry_filters(shard):
    """Bottom-up filter construction (like dynamic programming)."""
    # Process commits in topological order (oldest first)
    for commit in topological_sort(shard.commits):
        if not commit.parents:
            # Root commit: filter contains only itself
            filter = BloomFilter()
            filter.add_commit(commit.sha)
        else:
            # Merge parents' filters, add self
            filter = merge_parent_filters(commit.parents)
            filter.add_commit(commit.sha)
        
        # Cache this filter
        cache_filter(commit.sha, filter)
        
        # Also update shard-level aggregates
        shard.ancestry_filter.merge(filter)
    
    return shard.ancestry_filter

# The beauty: Filters are computed once, reused forever
# Storage: 100M commits × 1KB = 100GB of filters
# But: Heavily compressed, stored on fast SSDs
# And: Hot filters stay in memory (LRU cache)
```

(9:00 - Act II: Shard-Aware BFS)

[Visual: Diagram showing BFS expanding within shards before crossing boundaries]

Narration: "When Bloom filters say 'maybe', we need the exact answer. But we need a BFS that minimizes cross-shard chatter."

```python
def shard_aware_bfs(sha1, sha2, shard_map):
    """
    BFS that expands within shards before crossing boundaries.
    """
    # Find which shards hold our commits
    shard1 = shard_map.locate_primary(sha1)
    shard2 = shard_map.locate_primary(sha2)
    
    # If same shard, easy local BFS
    if shard1 == shard2:
        return shard1.local_bfs(sha1, sha2)
    
    # Different shards: coordinated BFS
    frontiers = {
        'a': {'shard': shard1, 'queue': [sha1], 'visited': set()},
        'b': {'shard': shard2, 'queue': [sha2], 'visited': set()}
    }
    
    # Expand level by level, prefer intra-shard expansion
    for level in range(MAX_DEPTH):
        # Try to find intersection within current frontiers
        intersection = check_intersection(frontiers)
        if intersection:
            return intersection
        
        # Expand each frontier one level
        for key in ['a', 'b']:
            frontier = frontiers[key]
            new_parents = []
            
            # Get next batch of commits from this shard
            for sha in frontier['queue']:
                commit = frontier['shard'].get_commit(sha)
                for parent in commit.parents:
                    parent_shard = shard_map.locate_primary(parent)
                    
                    if parent_shard == frontier['shard']:
                        # Same shard - cheap
                        new_parents.append(parent)
                    else:
                        # Cross-shard - expensive, defer
                        defer_cross_shard(parent, parent_shard, key)
            
            frontier['queue'] = new_parents
        
        # Process deferred cross-shard expansions
        process_cross_shard_expansions(frontiers)
    
    return None  # Too deep, give up
```

Narration: "The key insight: batch operations within shards, minimize cross-shard calls. Each cross-shard round trip is 1000x more expensive than local memory access."

(12:00 - SLO-Driven Approximation Strategies)

[Visual: Dashboard showing SLOs: p99 latency 200ms, accuracy target 95%]

Narration: "At this scale, sometimes 'close enough' is better than 'exact but late'. We need multiple strategies with different accuracy/latency tradeoffs."

```python
class MergeBaseStrategies:
    """Different algorithms for different constraints."""
    
    STRATEGIES = [
        # Fastest to slowest, approximate to exact
        {
            'name': 'commit_graph',
            'latency_ms': 0.1,
            'accuracy': 0.99,
            'method': self.use_commit_graph
        },
        {
            'name': 'generation_skip',
            'latency_ms': 5,
            'accuracy': 0.98,
            'method': self.skip_with_generations
        },
        {
            'name': 'sampled_ancestry',
            'latency_ms': 50,
            'accuracy': 0.95,
            'method': self.sample_1000_ancestors
        },
        {
            'name': 'bidirectional_bfs',
            'latency_ms': 200,
            'accuracy': 1.0,
            'method': self.exact_bfs
        }
    ]
    
    def find_with_slo(self, sha1, sha2, max_latency_ms=200):
        """Try strategies until SLO met."""
        start = time.time()
        
        for strategy in self.STRATEGIES:
            # Check time budget
            elapsed = (time.time() - start) * 1000
            if elapsed > max_latency_ms:
                return self.final_fallback(sha1, sha2)
            
            result = strategy['method'](sha1, sha2)
            if result:
                return result
        
        return self.final_fallback(sha1, sha2)
    
    def skip_with_generations(self, sha1, sha2):
        """Use precomputed generation numbers to skip levels."""
        # Generation = distance from root (approximate)
        gen1 = self.get_generation(sha1)  # Precomputed, cached
        gen2 = self.get_generation(sha2)
        
        # Jump to similar generation
        if gen1 > gen2:
            sha1 = self.jump_up(sha1, steps=gen1 - gen2)
        else:
            sha2 = self.jump_up(sha2, steps=gen2 - gen1)
        
        # Now BFS from similar depth (much smaller search)
        return self.limited_bfs(sha1, sha2, depth_limit=1000)
    
    def sample_1000_ancestors(self, sha1, sha2):
        """Random sampling when exact is too expensive."""
        # Sample 1000 random ancestors from each
        sample1 = self.sample_ancestors(sha1, k=1000)
        sample2 = self.sample_ancestors(sha2, k=1000)
        
        # Find intersection in samples
        common = set(sample1) & set(sample2)
        if not common:
            return None
        
        # Return deepest common (highest generation)
        return max(common, key=lambda sha: self.get_generation(sha))
```

Narration: "Notice the pattern: progressively more expensive, more accurate strategies. We try the fast ones first, fall back to slower ones if needed. This is how production systems meet SLOs."

(15:00 - Act III: The Complete Production Architecture)

[Visual: Architecture diagram with 4 layers]

Narration: "Let's see how this all fits together in a real monorepo service:"

```
┌─────────────────────────────────────────────────┐
│            MONOREPO MERGE BASE SERVICE          │
├─────────────────────────────────────────────────┤
│  STORAGE LAYER                                  │
│  • Sharded commit storage (10+ shards)          │
│  • CDN edge caches (geographically distributed) │
│  • LRU memory cache (hot commits only)          │
├─────────────────────────────────────────────────┤
│  COMPUTATION LAYER                              │
│  • Bloom filter index (probabilistic checks)    │
│  • Generation number service (depth estimates)  │
│  • Strategy engine (SLO-driven execution)       │
├─────────────────────────────────────────────────┤
│  RELIABILITY LAYER                              │
│  • Circuit breakers (fail fast on overload)     │
│  • Retry policies (exponential backoff)         │
│  • Consistency manager (eventual consistency)   │
├─────────────────────────────────────────────────┤
│  OBSERVABILITY LAYER                            │
│  • Distributed metrics (Prometheus)             │
│  • Request tracing (Jaeger)                     │
│  • Dynamic logging (structured, sampled)        │
└─────────────────────────────────────────────────┘
```

Narration: "Each layer has a specific responsibility. The storage layer knows where data lives. The computation layer chooses the right algorithm. The reliability layer handles failures. The observability layer tells us what's happening."

```python
# Key metrics for this service:
METRICS = {
    'merge_base_requests_total': 'Total requests',
    'merge_base_duration_seconds': 'Histogram of latency',
    'strategy_used_count': 'Which strategies succeeded',
    'bloom_filter_hits': 'How often Bloom filters helped',
    'cross_shard_calls': 'Expensive network operations',
    'cache_hit_ratio': 'Effectiveness of caching',
    'timeout_errors': 'Requests exceeding SLO',
}

# Alert conditions:
ALERTS = {
    'p99_latency > 200ms': 'Latency SLO violation',
    'error_rate > 1%': 'Reliability issue',
    'cache_hit_ratio < 80%': 'Cache ineffective',
    'cross_shard_calls > 1000/sec': 'Sharding issue',
}
```

(18:00 - The DNA Alignment Connection)

[Visual: Side-by-side: Git commit graph and phylogenetic tree]

Narration: "Here's a beautiful connection: Finding common ancestors in Git is mathematically similar to finding common subsequences in DNA."

```python
# Both problems: Find common ancestors in directed graphs
# Git: Commits with parent pointers
# Biology: Species with evolutionary ancestors

def smith_waterman_alignment(seq1, seq2):
    """
    Dynamic programming for sequence alignment.
    Similar to finding merge bases in DAGs.
    """
    # Initialize DP table
    dp = [[0] * (len(seq2) + 1) for _ in range(len(seq1) + 1)]
    
    for i in range(1, len(seq1) + 1):
        for j in range(1, len(seq2) + 1):
            if seq1[i-1] == seq2[j-1]:
                # Match = common ancestor found
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                # Mismatch = take best parent
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    return dp[-1][-1]  # Length of longest common subsequence

# The insight: Many ancestry problems reduce to
# dynamic programming on directed graphs.
# Git merge-base, biological phylogenetics,
# version control, even plagiarism detection!
```

[Visual: Table comparing the domains]

```
DOMAIN           | GRAPH TYPE     | ALGORITHM          | SCALE CHALLENGE
─────────────────|────────────────|────────────────────|─────────────────
Git Merge Base   | DAG            | BFS + Bloom filters| 100M+ commits
DNA Alignment    | Tree/DAG       | Dynamic Programming| Billions of bases
Code Plagiarism  | AST DAG        | Tree matching      | Millions of files
Social Networks  | Graph          | Community detection| Billions of users
```

Narration: "The patterns repeat: graph traversal, probabilistic indexing, approximation for scale. Once you see it in Git, you'll recognize it in biology, social networks, even fraud detection."

(21:00 - Recap & Takeaways)

[Visual: Three key takeaways on screen]

Narration: "Let's recap what we've learned about scaling merge-base to monorepo scale:"

1. Probabilistic data structures are production secrets

· Bloom filters give us 1000x speedup for "no common ancestor" cases
· 1% false positive rate is acceptable when we fall back to exact algorithms
· Precomputation and caching make them feasible

2. Architecture beats algorithm at scale

· Shard-aware BFS minimizes expensive cross-machine calls
· SLO-driven strategy selection meets latency targets
· Layered architecture (storage, compute, reliability, observability) enables scaling

3. This pattern appears everywhere

· From Git to DNA to social networks
· Dynamic programming on DAGs is a fundamental pattern
· Bloom filters and sampling work across domains

(23:00 - Next Steps & Episode 3 Teaser)

Narration: "Today we scaled merge-base to 100M commits. But what if history isn't immutable? What if commits can be rewritten with git rebase or git filter-branch?"

[Visual: Git history being rewritten, branches moving]

Narration: "That's the story of mutable history — where your nice algorithms meet the chaos of human collaboration. We'll explore content-defined chunking, structural sharing, and how tools like git replace create parallel universes of commit history."

Narration: "Until then, remember: Production problems aren't about finding the perfect algorithm. They're about finding the right tradeoffs for your constraints. Sometimes 95% accurate in 200ms beats 100% accurate in 40 seconds."

---

Why This Episode 2.b Works:

1. Clear positioning: Advanced follow-up, not core curriculum
2. Crisis-driven narrative: Immediately establishes stakes
3. One hero concept: Bloom filters as the breakthrough
4. Supporting cast: Shard-aware BFS, SLO strategies
5. Architecture focus: Systems thinking over raw algorithms
6. Pattern recognition: Connects to other domains (DNA alignment)
7. Appropriate length: ~25 minutes of dense, advanced content

For Implementation:

· First 7 minutes: Crisis + Bloom filters (the hero)
· Next 8 minutes: Shard-aware BFS + SLO strategies
· Next 6 minutes: Architecture + DNA connection
· Final 4 minutes: Recap + teaser

