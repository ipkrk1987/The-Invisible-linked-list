# Episode 6 Storyboard: Distributed Caches at Scale
## From Single-Machine LRU to Global CDNs

**Series**: From LeetCode to Production  
**Season**: 1 - The Invisible Linked List  
**Episode**: S1E06  
**Duration**: 25 minutes  
**Release Target**: [TBD]

---

## Executive Summary

This episode scales the LRU cache from Episode 5 to distributed systems spanning thousands of servers globally. We cover distributed systems fundamentals (horizontal scaling, consistency spectrum, data partitioning), implement consistent hashing for data distribution, build a multi-tier caching system (RAM → SSD → Network), explore CDN architecture, and dive deep into cache invalidation strategies. Real-world case studies include Facebook's TAO, Twitter's Manhattan, and Netflix's EVCache.

---

## 🎯 Presenter's Intent

**Core message**: "Episode 5 mastered caching on one machine. Now we scale to 10,000 machines across 6 continents. The LRU algorithm stays the same—the engineering explodes. Consistent hashing, replication, multi-tier caching, and the hardest problem in computer science: cache invalidation."

**Audience**: Senior engineers who will ask:
- "Why not just hash mod N?" → Addressed in Act 2 (99% rehash problem)
- "How many virtual nodes should I use?" → Act 3 + FAQ
- "How do CDNs handle invalidation at scale?" → Acts 6-7 + FAQ
- "What about thundering herd?" → FAQ
- "How do I choose between Memcached and Redis?" → FAQ

**Duration**: 25 minutes (can be split into two 12-13 min sessions)

---

## Act Structure

### Act 1: The Single-Server Limit (Slides 1-5) [4 min]
- **Hook**: Single server limits (256GB max, 100K QPS)
- **Reality Check**: Twitter, Netflix, Facebook scale requirements
- **Scaling Options**: Vertical vs horizontal
- **The Distributed Challenge**: Coordination, consistency, failures

### Act 2: Distributed Systems Fundamentals (Slides 6-11) [5 min]
- **Horizontal vs Vertical**: Cost, limits, complexity tradeoffs
- **Consistency Spectrum**: Strong vs eventual vs causal
- **Data Partitioning**: Why `hash % N` breaks on scaling
- **Consistent Hashing**: Virtual nodes, minimal reshuffling

### Act 3: Building Consistent Hashing (Slides 12-16) [5 min]
- **Theory**: Hash ring, clockwise routing, virtual nodes
- **Implementation**: ConsistentHashRing class
- **Replication**: Primary + replicas for fault tolerance
- **Load Balancing**: Virtual nodes for even distribution

### Act 4: Distributed Cache Cluster (Slides 17-21) [4 min]
- **Node Architecture**: DistributedCacheNode with local LRU
- **Cluster Coordination**: DistributedCacheCluster
- **Operations**: Put with replication, get with fallback
- **Rebalancing**: Adding/removing nodes gracefully

### Act 5: Multi-Tier Caching (Slides 22-26) [4 min]
- **Architecture**: L1 (RAM) → L2 (SSD) → L3 (Network)
- **Implementation**: MultiTierCache with promotion/demotion
- **SSD Cache**: Log-structured storage, compression
- **Prefetching**: Predicting related keys

### Act 6: CDN Architecture (Slides 27-31) [3 min]
- **Global Scale**: Edge nodes worldwide
- **Routing**: DNS-based geo-routing
- **Caching Semantics**: Cache-Control, ETags, invalidation
- **Optimization**: Anycast, TLS termination, image optimization

### Act 7: Cache Invalidation & Case Studies (Slides 32-37) [4 min]
- **Invalidation Strategies**: TTL, write-through, write-behind, versioning
- **Consistency Models**: Strong, eventual, causal, read-your-writes
- **Case Study: Facebook TAO**: Graph-oriented caching
- **Case Study: Netflix EVCache**: Multi-region personalization

### Act 8: Monitoring & Season Finale (Slides 38-40) [1 min]
- **Observability**: Metrics, alerts, autoscaling
- **Season 1 Recap**: Complete journey from linked lists to CDNs
- **Season 2 Teaser**: Trees, graphs, search engines

---

## Detailed Slide Breakdown

### Slide 1: Title Card
**Visual**: Global network map with cache nodes pulsing
**Text**: 
- "Episode 6: Distributed Caches at Scale"
- "From Single-Machine LRU to Global CDNs"
- "When One Server Isn't Enough"
**Duration**: 15 seconds

---

### Slide 2: The Single-Server Limit
**Visual**: Server with capacity gauges maxed out
```python
class SingleServerReality:
    max_ram = 256 * (1024**3)  # 256GB (high-end: $50k)
    max_qps = 100_000          # ~100K requests/second
    max_bandwidth = 10 Gbps    # Network limit
```
**Narration**: "Episode 5 mastered caching on one machine. But what happens when you need more?"
**Duration**: 35 seconds

---

### Slide 3: Real-World Scale Requirements
**Visual**: Company logos with scale numbers
- **Twitter**: 300M users, 500M tweets/day
- **Netflix**: 2B hours watched/month, 4K @ 25 Mbps
- **Facebook**: 2B users, 4PB of photos
**Punchline**: "One server is 1000x too small!"
**Duration**: 40 seconds

---

### Slide 4: When Single Server Fails
**Visual**: List of failure scenarios
**Problems When Cache Needs to Scale**:
- Hot data is **terabytes** (won't fit in one server's RAM)
- Need **millions of requests per second**
- Users are **globally distributed** (latency unacceptable)
- Servers **fail** (need redundancy)
**Solution**: Distributed caching
**Duration**: 45 seconds

---

### Slide 5: New Problems Introduced
**Visual**: Question marks around distributed nodes
**Distributed Caching Challenges**:
- Which server stores which data?
- How do we stay consistent?
- What happens when servers crash?
- How do we avoid hot spots?
**Narration**: "The algorithm is the same. The engineering explodes."
**Duration**: 35 seconds

---

### Slide 6: Horizontal vs Vertical Scaling
**Visual**: Side-by-side comparison diagram
| Approach | How It Works | Pros | Cons |
|----------|-------------|------|------|
| **Vertical** | Bigger server | Simple | Expensive, hard limits |
| **Horizontal** | More servers | Cheaper, no limit | Complex coordination |
**Modern Choice**: Horizontal (commodity hardware is cheap, cloud makes it easy)
**Duration**: 45 seconds

---

### Slide 7: The Consistency Spectrum
**Visual**: Slider from strong to eventual
**Strong Consistency**:
```python
write(key="user:123", value="Alice")
wait_for_replicas(timeout=100ms)  # Block until all confirm
# Now all reads see "Alice"
```
- ✅ Simple reasoning, no stale data
- ❌ Slow, unavailable if replicas down

**Eventual Consistency**:
```python
write(key="user:123", value="Alice")
# Return immediately, replicas updated async
# Readers might see stale data temporarily
```
- ✅ Fast, available
- ❌ Stale reads possible
**Duration**: 55 seconds

---

### Slide 8: Why Caches Use Eventual Consistency
**Visual**: Cache characteristics diagram
**Three Reasons**:
1. Stale cache data is acceptable (worst case: cache miss)
2. Speed matters more than perfect consistency
3. Availability is critical (cache must always respond)
**Narration**: "For most caches, speed and availability trump consistency."
**Duration**: 35 seconds

---

### Slide 9: Naive Partitioning Breaks
**Visual**: Animation showing key redistribution
```python
# Naive approach: hash(key) % num_servers
key = "user:123"
server = hash(key) % 100  # server 42

# Add server 101:
server = hash(key) % 101  # server 87 - MOVED!

# 99 out of 100 keys rehash to different servers!
# = Cache storm (100M misses simultaneously)
# = Database dies from load
```
**Duration**: 50 seconds

---

### Slide 10: Consistent Hashing Theory
**Visual**: Hash ring diagram
**Key Insight**: Map both servers AND keys to points on a circle (0-2³²)
```
Hash space circle:
         0°
    ┌───────┐
    |   ●   |      ● = Server A at 45°
    |       |      ◆ = Server B at 180°  
    |   ◆   |      □ = Key at 75°
    └───────┘
       180°
```
**Rule**: Key goes to first server clockwise from its hash position
**Duration**: 50 seconds

---

### Slide 11: Consistent Hashing Benefits
**Visual**: Before/after adding server comparison
**Adding Server C at 120°**:
- Keys between 45°-120° move from B to C
- All other keys stay put
- Only ~1/n keys move (not 99%!)

**Virtual Nodes**:
```python
for i in range(100):
    position = hash(f"ServerA-{i}")
    ring[position] = "ServerA"
```
- Improves load distribution
- Avoids hot spots when servers hash to nearby positions
**Duration**: 50 seconds

---

### Slide 12: ConsistentHashRing Implementation
**Visual**: Class structure diagram
```python
class ConsistentHashRing:
    def __init__(self, virtual_nodes_per_server=100):
        self.virtual_nodes_per_server = virtual_nodes_per_server
        self.ring = {}  # hash -> server_id
        self.sorted_hashes = []  # For binary search
    
    def _hash(self, key):
        import hashlib
        return int(hashlib.md5(str(key).encode()).hexdigest(), 16)
```
**Duration**: 40 seconds

---

### Slide 13: Adding/Removing Servers
**Visual**: Ring manipulation animation
```python
def add_server(self, server_id):
    for i in range(self.virtual_nodes_per_server):
        virtual_key = f"{server_id}-{i}"
        hash_val = self._hash(virtual_key)
        self.ring[hash_val] = server_id
        self.sorted_hashes.append(hash_val)
    self.sorted_hashes.sort()

def remove_server(self, server_id):
    hashes_to_remove = [h for h, s in self.ring.items() if s == server_id]
    for hash_val in hashes_to_remove:
        del self.ring[hash_val]
        self.sorted_hashes.remove(hash_val)
```
**Duration**: 45 seconds

---

### Slide 14: Key Lookup with Binary Search
**Visual**: Binary search on sorted hashes
```python
def get_server(self, key):
    key_hash = self._hash(key)
    
    # Binary search for first hash >= key_hash
    import bisect
    idx = bisect.bisect_left(self.sorted_hashes, key_hash)
    
    # Wrap around if at end
    if idx == len(self.sorted_hashes):
        idx = 0
    
    return self.ring[self.sorted_hashes[idx]]
```
**Animation**: Show key hashing and clockwise search
**Duration**: 45 seconds

---

### Slide 15: Replication Strategy
**Visual**: Diagram showing primary + replicas on ring
```python
def get_replicas(self, key, replication_factor=2):
    key_hash = self._hash(key)
    idx = bisect.bisect_left(self.sorted_hashes, key_hash)
    
    servers = []
    seen = set()
    
    while len(servers) < replication_factor:
        if idx >= len(self.sorted_hashes):
            idx = 0
        server_id = self.ring[self.sorted_hashes[idx]]
        if server_id not in seen:
            servers.append(server_id)
            seen.add(server_id)
        idx += 1
    
    return servers  # [Primary, Replica1, Replica2]
```
**Duration**: 50 seconds

---

### Slide 16: Consistent Hashing in Production
**Visual**: Company logos with usage
**Used By**:
- **DynamoDB**: Partition keys
- **Cassandra**: Token ring
- **Akamai CDN**: Content routing
- **Discord**: Sharding guilds
**Key Properties**:
- Minimal reshuffling on scale events
- Load distribution with virtual nodes
- Natural replication (next N servers on ring)
**Duration**: 40 seconds

---

### Slide 17: Distributed Cache Node
**Visual**: Single node architecture
```python
class DistributedCacheNode:
    def __init__(self, node_id, capacity_mb=1024):
        self.node_id = node_id
        self.capacity_bytes = capacity_mb * 1024 * 1024
        
        # Local LRU cache (Episode 5!)
        self.cache = {}
        self.access_order = []
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
```
**Narration**: "Each node is the LRU cache from Episode 5, coordinated by consistent hashing."
**Duration**: 40 seconds

---

### Slide 18: Local Get/Put Operations
**Visual**: LRU operations within a node
```python
def get_local(self, key):
    if key in self.cache:
        value, size, _ = self.cache[key]
        # Update LRU
        self.access_order.remove(key)
        self.access_order.append(key)
        self.hits += 1
        return value
    self.misses += 1
    return None

def put_local(self, key, value):
    # LRU eviction if needed
    while self.current_size + size > self.capacity_bytes:
        lru_key = self.access_order.pop(0)
        del self.cache[lru_key]
        self.evictions += 1
    
    self.cache[key] = (value, size, time.time())
```
**Duration**: 45 seconds

---

### Slide 19: Cluster Coordinator
**Visual**: Cluster architecture diagram
```python
class DistributedCacheCluster:
    def __init__(self, replication_factor=2):
        self.nodes = {}  # node_id -> DistributedCacheNode
        self.hash_ring = ConsistentHashRing()
        self.replication_factor = replication_factor
    
    def add_node(self, node_id, capacity_mb=1024):
        node = DistributedCacheNode(node_id, capacity_mb)
        self.hash_ring.add_server(node_id)
        self.nodes[node_id] = node
        self._trigger_rebalance()
```
**Duration**: 40 seconds

---

### Slide 20: Distributed Get with Fallback
**Visual**: Flow diagram showing primary → replica fallback
```python
def get(self, key):
    # Try primary
    primary = self.hash_ring.get_server(key)
    value = self.nodes[primary].get_local(key)
    
    if value is not None:
        return value
    
    # Primary miss - try replicas
    replicas = self.hash_ring.get_replicas(key, self.replication_factor)
    for replica_id in replicas[1:]:
        value = self.nodes[replica_id].get_local(key)
        if value is not None:
            # Cache warming: copy to primary
            self.nodes[primary].put_local(key, value)
            return value
    
    return None  # All misses
```
**Duration**: 50 seconds

---

### Slide 21: Distributed Put with Replication
**Visual**: Write fan-out diagram
```python
def put(self, key, value):
    replicas = self.hash_ring.get_replicas(key, self.replication_factor)
    
    # Write to all replicas
    success_count = 0
    for server_id in replicas:
        if self.nodes[server_id].put_local(key, value):
            success_count += 1
    
    return success_count > 0  # Or: quorum-based
```
**Narration**: "Write to all replicas. In production, use quorum writes for better consistency."
**Duration**: 40 seconds

---

### Slide 22: Multi-Tier Caching Architecture
**Visual**: Three-tier pyramid
**L1: In-Memory (fastest, smallest)**
- ~100ns access, 10GB capacity
- Hot data, decoded objects

**L2: Local SSD (slower, larger)**
- ~100µs access, 1TB capacity
- Warm data, compressed

**L3: Remote Cluster (slowest, largest)**
- ~1ms access, 100TB capacity
- Cold data, distributed
**Duration**: 45 seconds

---

### Slide 23: MultiTierCache Implementation
**Visual**: Class structure with promotion arrows
```python
class MultiTierCache:
    def __init__(self):
        self.l1_cache = LRUCache(capacity=10000)   # RAM
        self.l2_cache = SSDCache(max_size_gb=100)  # SSD
        self.l3_cluster = DistributedCacheCluster()  # Network
    
    def get(self, key):
        # Try L1
        if (value := self.l1_cache.get(key)) != -1:
            return value
        
        # Try L2, promote to L1
        if (value := self.l2_cache.get(key)):
            self.l1_cache.put(key, value)
            return value
        
        # Try L3, promote to L2 and L1
        if (value := self.l3_cluster.get(key)):
            self.l2_cache.put(key, value)
            self.l1_cache.put(key, value)
            return value
```
**Duration**: 50 seconds

---

### Slide 24: SSD Cache with Log-Structured Storage
**Visual**: Append-only log diagram
```python
class SSDCache:
    def put(self, key, value):
        # Compress if large
        if len(value) > 4096:
            value = zlib.compress(value)
        
        # Append to data file (no random writes!)
        offset = self.data_file.seek(0, 2)  # End
        self.data_file.write(value)
        
        # Update in-memory index
        self.index[key] = (offset, len(value), time.time())
```
**Key Insight**: "We don't delete from SSD file - garbage collection runs periodically."
**Duration**: 45 seconds

---

### Slide 25: Predictive Prefetching
**Visual**: Related keys prefetch diagram
```python
def _prefetch_related(self, key):
    """Prefetch keys likely to be accessed next."""
    if key.startswith('user:'):
        user_id = key.split(':')[1]
        related_keys = [
            f"user:{user_id}:profile",
            f"user:{user_id}:settings",
            f"user:{user_id}:friends"
        ]
        for related_key in related_keys:
            self._async_prefetch(related_key)
```
**Narration**: "If you access a user, you'll probably need their profile next."
**Duration**: 40 seconds

---

### Slide 26: Multi-Tier in Production
**Visual**: Production stack examples
**Real-World Multi-Tier Systems**:
- **CPU**: L1 → L2 → L3 → RAM → SSD
- **CDN**: Edge → Regional → Origin
- **Facebook TAO**: RAM → SSD → Database
- **Google Bigtable**: Memtable → SSTable → GFS
**Duration**: 35 seconds

---

### Slide 27: CDN Global Architecture
**Visual**: World map with edge locations
```python
class GlobalCDN:
    def __init__(self):
        self.edge_nodes = {
            'us-east-1': CDNEdgeNode(500GB),
            'us-west-2': CDNEdgeNode(500GB),
            'eu-west-1': CDNEdgeNode(300GB),
            'ap-southeast-1': CDNEdgeNode(200GB),
        }
        
        self.geo_routing = {
            'US': ['us-east-1', 'us-west-2'],
            'EU': ['eu-west-1'],
            'AP': ['ap-southeast-1'],
        }
```
**Duration**: 40 seconds

---

### Slide 28: CDN Edge Node
**Visual**: Edge node internal architecture
```python
class CDNEdgeNode:
    def get_asset(self, url, request_headers):
        cache_key = self._normalize_url(url)
        
        if cache_key in self.asset_cache:
            content, headers, expiry = self.asset_cache[cache_key]
            
            if time.time() < expiry:
                # Cache hit!
                headers['X-CDN-Cache'] = 'HIT'
                return content, headers
        
        # Cache miss - fetch from origin
        content, headers = self._fetch_from_origin(url)
        
        # Cache if allowed by headers
        max_age = self._parse_cache_control(headers)
        if max_age > 0:
            self._cache_asset(cache_key, content, headers, max_age)
```
**Duration**: 50 seconds

---

### Slide 29: DNS-Based Geo-Routing
**Visual**: DNS resolution flow diagram
```python
def route_request(self, client_ip, url):
    # Determine client region from IP
    region = self._ip_to_region(client_ip)
    
    # Get candidate edge nodes
    candidates = self.geo_routing.get(region, ['us-east-1'])
    
    # Choose node (by load, health, etc.)
    edge = self.edge_nodes[candidates[0]]
    
    return edge.get_asset(url)
```
**Duration**: 40 seconds

---

### Slide 30: CDN Optimizations
**Visual**: Feature icons with descriptions
**Production CDN Features**:
1. **Anycast routing**: Same IP everywhere, BGP routes to nearest
2. **TLS termination**: HTTPS at edge, HTTP to origin
3. **Image optimization**: Resize, compress, WebP conversion
4. **DDoS protection**: Rate limiting, bot detection
5. **WAF**: Web Application Firewall at edge
**Duration**: 40 seconds

---

### Slide 31: CDN Cache Headers
**Visual**: HTTP headers flow diagram
**Key Headers**:
- `Cache-Control: public, max-age=3600` → Cache for 1 hour
- `ETag: "abc123"` → Version identifier for revalidation
- `Vary: Accept-Encoding` → Different cache by compression
- `CDN-Cache-Control` → CDN-specific override
**Duration**: 35 seconds

---

### Slide 32: Cache Invalidation Strategies
**Visual**: Strategy comparison diagram
| Strategy | Mechanism | Best For | Risk |
|----------|-----------|----------|------|
| **TTL** | Expires after time | Simple cases | Stale data until TTL |
| **Write-through** | Update cache + DB sync | Consistency critical | Slow writes |
| **Write-behind** | Update cache, async DB | Performance | Data loss on crash |
| **Versioning** | ETags, timestamps | Large objects | Complexity |
**Duration**: 50 seconds

---

### Slide 33: Consistency Models in Practice
**Visual**: Consistency level selector
```python
def get(self, key, read_consistency='eventual'):
    if read_consistency == 'strong':
        # Read from quorum (majority of replicas)
        return self._get_strong(key)
    elif read_consistency == 'eventual':
        # Read from any replica (fastest)
        return self._get_eventual(key)
    elif read_consistency == 'causal':
        # Track causality with vector clocks
        return self._get_causal(key)
```
**Narration**: "Strong for banking, eventual for social media, causal for collaboration."
**Duration**: 45 seconds

---

### Slide 34: Case Study - Facebook TAO
**Visual**: TAO architecture diagram
```python
class TAOCache:
    """Facebook's graph cache for social data."""
    
    # Two-layer: memcache (RAM) + MySQL (persistent)
    # Graph-oriented: objects + associations
    
    def get_object(self, obj_id):
        if obj_id in self.cache:
            return self.cache[obj_id]
        return self._load_from_mysql(obj_id)
    
    def create_association(self, from_id, type, to_id):
        # Friend requests, likes, comments
        self.associations[(from_id, type)].append(to_id)
        self._invalidate_related(from_id, type)
```
**Key Insight**: "Graph-oriented caching for social data - objects AND relationships."
**Duration**: 50 seconds

---

### Slide 35: Case Study - Netflix EVCache
**Visual**: Multi-region diagram
```python
class EVCache:
    """Netflix's distributed cache for personalization."""
    
    # Multi-region replication
    regions = ['us-east', 'eu-west', 'ap-southeast']
    
    def get_recommendations(self, user_id):
        # Try local region first
        recs = self._get_local(key)
        if recs:
            return recs
        
        # Try other regions
        for region in self.regions:
            recs = self._get_from_region(region, key)
            if recs:
                self._replicate_locally(key, recs)
                return recs
```
**Key Insight**: "SSD-backed for large datasets, predictive caching based on viewing patterns."
**Duration**: 50 seconds

---

### Slide 36: Case Study - Twitter Manhattan
**Visual**: Timeline architecture
**Key Design Decisions**:
- **Fan-out on write**: Pre-compute timelines for followers
- **Read repair**: Fix inconsistencies during reads
- **Timeline cache**: Hot timelines always in memory
**Tradeoff**: Writes are expensive (celebrity posts), reads are fast
**Duration**: 40 seconds

---

### Slide 37: Production Monitoring
**Visual**: Dashboard mockup
```python
class CacheMonitoring:
    metrics = {
        'hit_ratio': gauge,      # Should be > 90%
        'latency_p99': histogram, # Should be < 10ms
        'eviction_rate': counter, # Should be stable
        'memory_usage': gauge,   # Should be < 80%
    }
    
    alerts = [
        (hit_ratio < 0.9, "Low hit ratio - increase cache"),
        (latency_p99 > 10, "High latency - check network"),
        (memory_usage > 0.8, "Memory pressure - scale up"),
    ]
```
**Export To**: Prometheus, DataDog, CloudWatch
**Duration**: 40 seconds

---

### Slide 38: Autoscaling Cache Clusters
**Visual**: Scale up/down diagram
```python
class CacheAutoscaler:
    scale_up_threshold = 0.8   # 80% memory
    scale_down_threshold = 0.3  # 30% memory
    
    def evaluate_scaling(self):
        if avg_memory > self.scale_up_threshold:
            self.add_node()
        elif avg_memory < self.scale_down_threshold:
            self.remove_node()
```
**Kubernetes Integration**: HPA (Horizontal Pod Autoscaler)
**Duration**: 40 seconds

---

### Slide 39: Season 1 Complete Journey
**Visual**: Episode progression timeline
```
Episode 1: Singly Linked Lists → Git Commits
Episode 2: List Intersection → Git Merge-Base
Episode 3: Doubly Linked Lists → Browser History
Episode 4: Immutable Structures → Time Travel
Episode 5: LRU Cache → Browser & DB Caching
Episode 6: Distributed Caching → Global CDNs
```
**Narration**: "From a single linked list to a global distributed system. The data structure is the same - the engineering scales exponentially."
**Duration**: 45 seconds

---

### Slide 40: Season 2 Preview
**Visual**: Trees, graphs, search indices
**Coming in Season 2**:
- **B-trees** in databases
- **Graph algorithms** in social networks
- **Bloom filters** in distributed systems
- **Search engines** and recommendation systems
**Closing**: "Data structures aren't just interview questions. They're the invisible foundation of every system you use daily."
**Duration**: 40 seconds

---

## Animation Requirements

### Animation 1: Hash Ring Visualization (Slides 10-11)
**Type**: Interactive circular diagram
**Elements**:
- Circle with degree markers (0-360)
- Server nodes as colored dots
- Key insertion with clockwise arrow
- Server addition showing minimal key movement
**Interaction**: Click to add servers, drag to add keys

### Animation 2: Consistent Hashing Key Distribution (Slide 14)
**Type**: Step-through binary search
**States**:
1. Key hashed to position on ring
2. Binary search through sorted hashes
3. First server clockwise selected
4. Replicas selected (next N unique servers)
**Interaction**: Click to step through

### Animation 3: Multi-Tier Cache Flow (Slide 23)
**Type**: Request flow animation
**Elements**:
- Three cache layers (L1, L2, L3)
- Request arrow moving through layers
- Cache hit/miss indicators
- Promotion arrows on miss
**Interaction**: Toggle hit/miss at each level

### Animation 4: CDN Geo-Routing (Slide 29)
**Type**: World map with request routing
**Elements**:
- Globe with edge locations
- User request from different regions
- DNS resolution animation
- Edge selection based on proximity
**Interaction**: Click different regions to see routing

---

## Interactive Code Demos

### Demo 1: Consistent Hashing
```python
# Show minimal reshuffling
ring = ConsistentHashRing(virtual_nodes_per_server=100)
ring.add_server("server-1")
ring.add_server("server-2")
ring.add_server("server-3")

# Track key distribution
for i in range(1000):
    server = ring.get_server(f"key-{i}")
    print(f"key-{i} → {server}")

# Add server and show only ~33% keys move
ring.add_server("server-4")
```

### Demo 2: Multi-Tier Cache
```python
cache = MultiTierCache()

# First access: L3 hit, promotes to L1 and L2
cache.l3_cluster.put("user:123", profile_data)
result = cache.get("user:123")  # L3 → L2 → L1

# Second access: L1 hit
result = cache.get("user:123")  # L1 hit!

print(cache.get_stats())  # Show tier hit rates
```

### Demo 3: CDN Cache Headers
```python
# Simulate CDN caching based on headers
cdn = CDNEdgeNode(capacity_gb=10)

response = cdn.get_asset(
    url="https://example.com/image.png",
    headers={"Cache-Control": "public, max-age=3600"}
)
print(response.headers["X-CDN-Cache"])  # "MISS"

# Second request
response = cdn.get_asset("https://example.com/image.png")
print(response.headers["X-CDN-Cache"])  # "HIT"
```

---

## Senior Engineer FAQ

### Q1: How does consistent hashing handle hot keys?
**A**: Hot keys (celebrity users, viral content) can overwhelm a single node. Solutions:
- **Read replicas**: Spread reads across multiple replicas
- **Local caching**: Cache hot keys in application memory
- **Key splitting**: Split hot key across multiple sub-keys
- **Virtual hot key**: Append random suffix, merge on read

### Q2: What's the difference between Memcached and Redis clusters?
**A**:
- **Memcached**: Client-side sharding, simple key-value, no replication
- **Redis Cluster**: Server-side sharding, rich data types, automatic failover
- **Redis Sentinel**: Master-slave with automatic failover
- Choose Memcached for simple caching, Redis for data structures/persistence

### Q3: How do CDNs handle cache invalidation at scale?
**A**: CDNs use:
- **Purge API**: Explicit invalidation (takes seconds to propagate)
- **Soft purge**: Mark stale but serve while revalidating
- **Surrogate keys**: Tag content, invalidate by tag
- **Versioned URLs**: `/v2/style.css` - no invalidation needed

### Q4: What happens during a "thundering herd" scenario?
**A**: When a popular cache key expires, thousands of requests hit the database simultaneously. Solutions:
- **Request coalescing**: First request fetches, others wait
- **Probabilistic early expiration**: Refresh before actual expiry
- **Background refresh**: Proactive refresh before expiry
- **Circuit breaker**: Fail fast if database overloaded

### Q5: How do you debug cache inconsistency across regions?
**A**: 
- **Trace IDs**: Track request across all cache layers
- **Version vectors**: Detect conflicting writes
- **Read-your-writes consistency**: Sticky sessions or explicit routing
- **Eventual consistency monitoring**: Track replication lag

---

## Technical Accuracy Checklist

- [ ] Consistent hashing minimizes reshuffling to 1/n on server changes
- [ ] Virtual nodes improve load distribution (100-150 recommended)
- [ ] Redis uses 16384 hash slots, not arbitrary ring
- [ ] Cassandra uses Murmur3 partitioner
- [ ] CDN Cache-Control directives match HTTP spec
- [ ] Facebook TAO uses MySQL as persistent store
- [ ] Netflix EVCache is built on Memcached

---

## Production Code Repository Structure

```
episode6-distributed-caching/
├── consistent_hashing/
│   ├── hash_ring.py           # ConsistentHashRing
│   ├── virtual_nodes.py       # Virtual node optimization
│   └── test_consistent_hash.py
├── distributed_cache/
│   ├── cache_node.py          # DistributedCacheNode
│   ├── cache_cluster.py       # DistributedCacheCluster
│   ├── replication.py         # Replication strategies
│   └── test_cluster.py
├── multi_tier/
│   ├── multi_tier_cache.py    # MultiTierCache
│   ├── ssd_cache.py           # SSDCache
│   └── test_multi_tier.py
├── cdn/
│   ├── edge_node.py           # CDNEdgeNode
│   ├── global_cdn.py          # GlobalCDN
│   └── test_cdn.py
├── invalidation/
│   ├── strategies.py          # Invalidation strategies
│   ├── consistency.py         # Consistency models
│   └── test_invalidation.py
└── monitoring/
    ├── metrics.py             # CacheMonitoring
    ├── autoscaler.py          # CacheAutoscaler
    └── dashboards/
```

---

## Presenter Notes

### Key Transitions
- **Single → Distributed**: "One server is 1000x too small" (Slide 3→4)
- **Theory → Implementation**: "Now let's build it" (Slide 11→12)
- **Local → Global**: "CDN is caching at planetary scale" (Slide 26→27)
- **Technical → Case Studies**: "Let's see how real companies do it" (Slide 33→34)

### Emphasis Points
1. **99% key movement** - Make the naive partitioning problem visceral
2. **Virtual nodes** - The key optimization most people miss
3. **Promotion pattern** - L3→L2→L1 is universal
4. **Invalidation is hard** - Acknowledge the famous quote

### Common Audience Questions to Anticipate
- "How many virtual nodes should I use?" → "100-150 per server, tune based on load variance"
- "When should I use CDN vs in-memory cache?" → "CDN for static assets, in-memory for dynamic data"
- "How do I handle cache warming?" → "Preload popular keys, use read-through pattern"

---

## 📁 Deliverables

1. **episode6_revealjs.html** — Full Reveal.js presentation
2. **episode6_animations.html** — Standalone interactive animations
3. **episode6_storyboard.md** — This file (presenter notes)
4. **LinkedLists/chapter 6.md** — Source content

---

## 🎬 Suggested Session Split

**Option A: Single 25-minute session**
- Full presentation, standard pace

**Option B: Two 12-13 minute sessions**
- **Session 1** (Acts 1-4): "Distributed Fundamentals" — Consistent hashing and cluster coordination
- **Session 2** (Acts 5-8): "Global Scale" — Multi-tier, CDN, invalidation, case studies

---

## 🏆 Challenge for the Audience

> "Design a cache warming strategy for a new server joining a consistent hash ring. How do you populate it without causing a thundering herd on the database?"

**Hint**: Use gradual promotion! New server initially forwards requests to the server it's taking load from. Slowly increase the percentage of requests it handles directly. Track hit rate to know when it's "warm enough."

---

## 🎯 Key Moments to Nail

| Time | Moment | Why It Matters |
|------|--------|----------------|
| 0:30 | "One server is 1000x too small" | Scale hook |
| 3:00 | 99% key movement with hash mod N | The aha moment |
| 6:00 | Consistent hashing ring visual | Core algorithm insight |
| 9:00 | Virtual nodes optimization | Most people miss this |
| 12:00 | L1→L2→L3 promotion pattern | Universal pattern |
| 16:00 | CDN edge architecture | Global scale |
| 19:00 | "Cache invalidation" quote | Acknowledge the hard problem |
| 22:00 | Facebook TAO case study | Real-world validation |
| 25:00 | Season journey recap | Build to finale |

---

## Episode Metadata

**Prerequisites**: 
- Episode 5 (LRU Cache)
- Basic distributed systems concepts

**Key Terms Introduced**:
- Consistent hashing
- Virtual nodes
- Replication factor
- Multi-tier caching
- Cache invalidation
- CDN edge locations
- Eventual/strong/causal consistency

**Connections to Other Episodes**:
- Episode 1-2: Linked list fundamentals (history chains)
- Episode 3: Navigation patterns (browser history caching)
- Episode 4: Immutable structures for CRDT caching
- Episode 5: LRU cache is the node-level algorithm (the foundation we scale)
- Episode 7: Ring buffers for streaming cache updates

**Real-World Systems Referenced**:
- Redis Cluster, Memcached
- DynamoDB, Cassandra
- Cloudflare, Akamai, CloudFront
- Facebook TAO, Netflix EVCache, Twitter Manhattan
