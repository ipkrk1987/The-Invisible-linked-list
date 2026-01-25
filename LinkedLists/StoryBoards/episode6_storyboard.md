# Episode 6 Storyboard: Distributed Caches at Scale
## When One Server Isn't Enough

**Series**: From LeetCode to Production  
**Season**: 1 - The Invisible Linked List  
**Episode**: S1E06  
**Duration**: 15 minutes  
**Release Target**: [TBD]

---

## Executive Summary

Episode 5 mastered caching on one machine. This episode scales it to thousands of servers. We open with a disaster: adding a server causes 99% of cached data to move, crashing the database. The solution—consistent hashing—uses a circular linked structure to minimize data movement. We build the algorithm, show multi-tier caching (L1→L2→L3), and end with a glimpse of CDN architecture.

---

## 🎯 Presenter's Intent

**Core message**: "The LRU algorithm stays the same—the engineering explodes. The key insight? A circular ring structure (linked list!) that minimizes chaos when servers come and go."

**The ONE thing viewers should remember**: "Consistent hashing = only 1/N keys move when you add a server, not 99%."

---

## Act Structure (5 Acts, ~15 minutes)

### Act 1: The 99% Disaster (3 min)
- **Hook**: Adding one server crashes everything
- **The Math**: hash % N → 99% keys move
- **The Pain**: Database dies from thundering herd

### Act 2: The Ring Insight (3 min)  
- **Visual**: Hash ring (circular linked structure)
- **Rule**: Keys go clockwise to first server
- **Magic**: Adding server moves only ~1/N keys

### Act 3: Building Consistent Hashing (4 min)
- **Pseudocode**: Ring operations
- **Code**: One clean implementation
- **Virtual Nodes**: Even distribution trick

### Act 4: Multi-Tier Caching (3 min)
- **Architecture**: L1 (RAM) → L2 (SSD) → L3 (Network)
- **Promotion**: Miss at L1 → fetch from L2 → promote up
- **Real world**: Every CDN uses this pattern

### Act 5: The Hardest Problem (2 min)
- **Cache Invalidation**: "The two hardest problems..."
- **Strategies**: TTL, versioning, purge
- **Season Recap**: Journey from linked list to global CDN

---

## Detailed Slide Breakdown

### Slide 1: Title Card
**Visual**: Global network map with cache nodes
**Text**: 
- "Episode 6: Distributed Caches at Scale"
- "When One Server Isn't Enough"
**Duration**: 15 seconds

---

## ACT 1: THE 99% DISASTER

### Slide 2: The Scene
**Visual**: Ops dashboard, 3 AM alert
**Disaster Box**:
```
🔥 INCIDENT: Cache cluster expansion
   Time: 3:47 AM
   Action: Added 1 server to 100-server cluster
   Result: DATABASE DOWN
```
**Narration**: "You added ONE server. Everything broke."
**Duration**: 30 seconds

---

### Slide 3: What Happened?
**Visual**: Before/after server routing
**The Naive Approach**:
```
server = hash(key) % num_servers

Before: hash("user:123") % 100 = 42  → Server 42
After:  hash("user:123") % 101 = 87  → Server 87

Key moved! Cache miss! Database query!
```
**Duration**: 40 seconds

---

### Slide 4: The Math That Killed Us
**Visual**: Table showing key movement
| Servers | Keys That Move | Cache Misses |
|---------|---------------|--------------|
| 100 → 101 | **99%** | 99 million |
| 100 → 102 | **98%** | 98 million |

**Punchline**: "Adding ONE server invalidated 99% of your cache."
**Duration**: 35 seconds

---

### Slide 5: The Death Spiral  
**Visual**: Timeline of disaster
```
3:47 AM — Server 101 joins cluster
3:47:01 — 99M keys now "missing"
3:47:02 — 99M database queries begin
3:47:05 — Database connection pool exhausted
3:47:10 — Site down, revenue: $0
```
**Question**: "How do we add servers WITHOUT this chaos?"
**Duration**: 40 seconds

---

## ACT 2: THE RING INSIGHT

### Slide 6: The Key Idea
**Visual**: Circle (hash ring) with servers as points
**Insight Box**:
```
Instead of: hash(key) % N
Use:        hash(key) → position on a RING
            Key goes to first server CLOCKWISE
```
**Duration**: 35 seconds

---

### Slide 7: Hash Ring Visualization
**Visual**: Animated ring diagram
```
         0°
    ┌─────────┐
    │    A    │   Server A at 45°
 270°│        │90°  Server B at 180°
    │    B    │   Key X at 75° → goes to B (clockwise)
    └─────────┘
        180°
```
**Rule**: "Walk clockwise from key's position until you hit a server."
**Duration**: 45 seconds

---

### Slide 8: Adding a Server (The Magic)
**Visual**: Ring before/after adding Server C
**Before**: A at 45°, B at 180°
**After**: A at 45°, C at 120°, B at 180°

**What moves?**
- Keys between 45°-120° move from B → C
- Everything else stays put!
- Only **~33%** keys move (not 99%)

**Duration**: 50 seconds

---

### Slide 9: The Math That Saves Us
**Visual**: Comparison table
| Method | Keys That Move |
|--------|---------------|
| hash % N | **99%** |
| Consistent Hashing | **~1/N** (~1%) |

**Narration**: "From 99 million cache misses to 1 million. That's the difference between a crash and a smooth deployment."
**Duration**: 35 seconds

---

## ACT 3: BUILDING CONSISTENT HASHING

### Slide 10: The Algorithm (Pseudocode)
**Visual**: Clean pseudocode box
```
HASH RING STRUCTURE:
  ring = sorted circular list of (hash_position, server_id)

ADD_SERVER(server):
  position = hash(server)
  insert into ring at position

GET_SERVER(key):
  position = hash(key)
  walk clockwise until first server
  return that server

REMOVE_SERVER(server):
  remove from ring
  keys automatically route to next server clockwise
```
**Duration**: 50 seconds

---

### Slide 11: Python Implementation
**Visual**: Real code block
```python
class ConsistentHashRing:
    def __init__(self):
        self.ring = {}          # hash -> server_id
        self.sorted_keys = []   # for binary search
    
    def add_server(self, server_id):
        h = self._hash(server_id)
        self.ring[h] = server_id
        self.sorted_keys = sorted(self.ring.keys())
    
    def get_server(self, key):
        h = self._hash(key)
        # Binary search for first hash >= key hash
        for server_hash in self.sorted_keys:
            if server_hash >= h:
                return self.ring[server_hash]
        return self.ring[self.sorted_keys[0]]  # wrap around
```
**Repo Link**: 📁 Full code: github.com/your-repo/consistent-hashing
**Duration**: 50 seconds

---

### Slide 12: The Virtual Nodes Trick
**Visual**: Ring with multiple points per server
**Problem**: What if servers hash to nearby positions? Uneven load!

**Solution**: Each server gets 100+ positions on the ring
```python
def add_server(self, server_id, virtual_nodes=100):
    for i in range(virtual_nodes):
        h = self._hash(f"{server_id}-{i}")
        self.ring[h] = server_id
```
**Result**: Even distribution, handles hot spots
**Duration**: 45 seconds

---

### Slide 13: Who Uses This?
**Visual**: Company logos
- **DynamoDB**: Partition keys
- **Cassandra**: Token ring  
- **Discord**: Guild sharding
- **Akamai CDN**: Content routing

**Punchline**: "The same algorithm powers your database AND your Netflix stream."
**Duration**: 30 seconds

---

## ACT 4: MULTI-TIER CACHING

### Slide 14: The Cache Hierarchy
**Visual**: Three-tier pyramid
```
        ┌─────────────┐
        │  L1: RAM    │  ← 100ns, 10GB
        │  (hot data) │
        ├─────────────┤
        │  L2: SSD    │  ← 100µs, 1TB
        │ (warm data) │
        ├─────────────┤
        │ L3: Network │  ← 1ms, 100TB
        │ (cold data) │
        └─────────────┘
```
**Duration**: 35 seconds

---

### Slide 15: The Promotion Pattern
**Visual**: Request flow animation
```
GET "user:123":

1. Check L1 (RAM)     → MISS
2. Check L2 (SSD)     → MISS  
3. Check L3 (Network) → HIT!
4. Promote to L2
5. Promote to L1
6. Return to user

Next request: L1 HIT (100ns!)
```
**Duration**: 45 seconds

---

### Slide 16: Multi-Tier Pseudocode
**Visual**: Clean pseudocode
```
GET(key):
  if key in L1: return L1[key]           # 100ns
  
  if key in L2:
    L1[key] = L2[key]                    # promote
    return L2[key]
  
  if key in L3:
    L2[key] = L3[key]                    # promote
    L1[key] = L3[key]                    # promote
    return L3[key]
  
  return MISS → fetch from database
```
**Duration**: 40 seconds

---

### Slide 17: This Pattern Is Everywhere
**Visual**: Examples grid
| System | L1 | L2 | L3 |
|--------|----|----|-----|
| **CPU** | L1 cache | L2 cache | RAM |
| **CDN** | Edge | Regional | Origin |
| **Browser** | Memory | Disk | Network |

**Insight**: "Every fast system uses tiered caching."
**Duration**: 35 seconds

---

## ACT 5: THE HARDEST PROBLEM

### Slide 18: Cache Invalidation
**Visual**: Famous quote
> "There are only two hard things in Computer Science: cache invalidation and naming things."
> — Phil Karlton

**The Problem**: When data changes, how do you update the cache?
**Duration**: 30 seconds

---

### Slide 19: Invalidation Strategies
**Visual**: Strategy comparison
| Strategy | How It Works | Tradeoff |
|----------|-------------|----------|
| **TTL** | Expires after time | Stale until expiry |
| **Write-through** | Update cache on every write | Slower writes |
| **Versioned URLs** | `/v2/style.css` | No invalidation needed |
| **Purge API** | Explicit delete | Propagation delay |

**Real world**: CDNs use all four depending on content type
**Duration**: 45 seconds

---

### Slide 20: Season 1 Journey Complete
**Visual**: Episode progression
```
Ep 1: Singly Linked List → Git Commits
Ep 2: List Intersection  → Git Merge-Base  
Ep 3: Doubly Linked List → Browser History
Ep 4: Immutable Lists    → Time Travel Debugging
Ep 5: LRU Cache          → Browser & DB Caching
Ep 6: Consistent Hashing → Global CDNs
         ↑
    Circular linked structure!
```
**Duration**: 40 seconds

---

### Slide 21: The Invisible Linked List
**Visual**: Callback to season theme
**Closing Statement**:
> "From a single `node.next` pointer to a global network serving billions.
> The linked list isn't just an interview question—
> it's the invisible foundation of every system you use."

**Season 2 Teaser**: "Next season: Trees, Graphs, and Search Engines"
**Duration**: 45 seconds

---

## Code Summary

| Type | Count | Purpose |
|------|-------|---------|
| Pseudocode | 3 | Algorithm explanation |
| Real Python | 1 | ConsistentHashRing implementation |
| Disaster code | 2 | hash % N problem |

**Total: ~6 code blocks** (vs 18 in original)

---

## Animation Requirements

### Animation 1: Hash Ring (Slides 7-8)
- Circle with server nodes
- Key insertion with clockwise arrow
- Server addition showing minimal key movement

### Animation 2: Multi-Tier Flow (Slide 15)
- Request moving through L1 → L2 → L3
- Promotion arrows on miss

---

## Key Moments to Nail

| Time | Moment | Why |
|------|--------|-----|
| 0:30 | "Adding ONE server broke everything" | Disaster hook |
| 2:00 | "99% of keys moved" | The aha moment |
| 4:00 | Hash ring visualization | Core insight |
| 6:00 | "Only 1/N keys move" | The payoff |
| 10:00 | L1 → L2 → L3 promotion | Universal pattern |
| 14:00 | "Invisible foundation" | Season wrap |

---

## 📁 Deliverables

1. **episode6_revealjs.html** — Reveal.js presentation (~21 slides)
2. **episode6_storyboard.md** — This file
3. **consistent_hashing.py** — Reference implementation

---

## Comparison: Before vs After

| Metric | Original | Rewritten |
|--------|----------|-----------|
| Duration | 25 min | 15 min |
| Slides | 40 | 21 |
| Code blocks | 18 | 6 |
| Acts | 8 | 5 |
| Case studies | 3 | 0 (logos only) |
| Disaster hook | Weak | Strong |

