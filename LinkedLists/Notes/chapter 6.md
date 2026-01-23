# Episode 6: Distributed Caches at Scale
## From Single-Machine LRU to Global CDNs

**Season 1 — The Invisible Linked List**

---

## The Single-Server Limit

Episode 5 mastered LRU caching on one machine. But what happens when:
- Your cache needs to serve **millions of requests per second**
- Hot data is **terabytes** (won't fit in one server's RAM)
- Users are **globally distributed** (latency to one datacenter is unacceptable)
- Servers **fail** (need redundancy)

**The hard truth**: One server can't handle this.

```python
# Single-server limits:
class SingleServerReality:
    max_ram = 256 * (1024**3)  # 256GB (high-end server: $50k)
    max_qps = 100_000  # ~100K requests/second
    max_bandwidth = 10 * (1024**3)  # 10 Gbps network
    
    # Real-world scale:
    # Twitter: 300M users, 500M tweets/day
    # Netflix: 2B hours watched/month, 4K video = 25 Mbps
    # Facebook: 2B users, 4PB of photos
    
    # One server is 1000x too small!
```

We need **distributed caching**. But this introduces new problems: Which server stores which data? How do we stay consistent? What happens when servers crash?

---

## Part 1: Distributed Systems Fundamentals

### Horizontal vs Vertical Scaling

| Approach | How It Works | Pros | Cons |
|----------|-------------|------|------|
| **Vertical scaling** | Buy bigger server (more RAM/CPU) | Simple, no code changes | Expensive, hard limits (1TB RAM = $200k+), single point of failure |
| **Horizontal scaling** | Add more servers | Cheaper, no theoretical limit | Complex, requires coordination |

**Modern systems use horizontal scaling** because:
1. Commodity hardware is cheap (128GB server = $2k)
2. No single point of failure
3. Can scale incrementally
4. Cloud providers (AWS, GCP) make it easy

### The Consistency Spectrum

When data is on multiple machines, how do we keep it consistent?

**Strong consistency** (all nodes see same data immediately):
```python
# Write to primary, replicate synchronously
write(key="user:123", value="Alice")
# Block until all replicas confirm
wait_for_replicas(timeout=100ms)
# Now all reads see "Alice"
```

**Pros**: Simple reasoning, no stale data  
**Cons**: Slow (waits for network), unavailable if replicas down  
**Use**: Banking (account balances), inventory (stock counts)

**Eventual consistency** (nodes converge over time):
```python
# Write to primary, replicate asynchronously  
write(key="user:123", value="Alice")
# Return immediately
# Replicas get updated "eventually" (1-100ms typical)
```

**Pros**: Fast, available even if replicas down  
**Cons**: Readers might see stale data temporarily  
**Use**: Social media (likes, views), caches (stale is acceptable)

**Caches typically use eventual consistency** because:
1. Stale cache data is acceptable (worst case: cache miss)
2. Speed matters more than perfect consistency
3. Availability is critical (cache must always respond)

### Data Partitioning: Which Server Gets Which Key?

**Problem**: 100M keys, 100 servers. How do we decide where to store each key?

**Naive approach**: `server_id = hash(key) % num_servers`

```python
key = "user:123"
server = hash(key) % 100  # server 42
```

**What breaks**: Add server 101 → **99% of keys move to different servers!**

```python
# Before (100 servers):
hash("user:123") % 100 = 42

# After (101 servers):
hash("user:123") % 101 = 87  # MOVED!

# 99 out of 100 keys rehash to different servers
# = Cache storm (100M cache misses simultaneously)
# = Database dies from load
```

**Solution**: **Consistent hashing** (only ~1% of keys move)

### Consistent Hashing Theory

**Key insight**: Map both servers AND keys to points on a circle (0-2^32).

```
Hash space circle:
         0
    359°   1°
   ┌───────┐
350°|       | 10°
   |   ●   |      ● = Server A at 45°
   |       |      ◆ = Server B at 180°  
   |   ◆   |      □ = Key "user:123" at 75°
   └───────┘
 270°       90°
   180°
```

**Rule**: Key goes to first server clockwise from its hash position.

**Example**:
- Server A: hash(”A") = 45°
- Server B: hash("B") = 180°
- Key "user:123": hash("user:123") = 75° → goes to Server B (first clockwise)
- Key "user:456": hash("user:456") = 200° → goes to Server A (wrap around)

**When adding Server C at 120°**:
- Keys between 45°-120° move from B to C
- All other keys stay put
- Only ~1/n keys move (where n = number of servers)

**Virtual nodes optimization**:
Instead of 1 position per server, create 100 virtual nodes:
```python
for i in range(100):
    position = hash(f"ServerA-{i}")
    ring[position] = "ServerA"
```

**Why**: Improves load distribution (avoids hot spots when servers hash to nearby positions)

### Replication Strategy

Store each key on multiple servers for fault tolerance:

```
Key "user:123" at 75°:
  Primary:   Server B (180°) ← first clockwise
  Replica 1: Server C (270°) ← second clockwise  
  Replica 2: Server A (45°)  ← third (wraps around)
```

**Replication factor** (typically 3):
- Lose 1 server: data still available
- Lose 2 servers: still available (can survive 2 simultaneous failures)
- Lose 3 servers: data lost

Now let's build it.

---

## Part 2: Implementing Consistent Hashing

```python
class ConsistentHashRing:
    """Consistent hashing for distributed cache."""
    
    def __init__(self, virtual_nodes_per_server=100):
        self.virtual_nodes_per_server = virtual_nodes_per_server
        self.ring = {}  # hash -> server_id
        self.sorted_hashes = []  # For binary search
        self.server_load = {}  # Track load for balancing
    
    def _hash(self, key):
        """MurmurHash or similar for uniform distribution."""
        import hashlib
        return int(hashlib.md5(str(key).encode()).hexdigest(), 16)
    
    def add_server(self, server_id):
        """Add a server to the ring."""
        for i in range(self.virtual_nodes_per_server):
            # Create virtual node
            virtual_key = f"{server_id}-{i}"
            hash_val = self._hash(virtual_key)
            
            # Add to ring
            self.ring[hash_val] = server_id
            self.sorted_hashes.append(hash_val)
        
        # Keep sorted for binary search
        self.sorted_hashes.sort()
        self.server_load[server_id] = 0
    
    def remove_server(self, server_id):
        """Remove a server from the ring."""
        hashes_to_remove = []
        
        for hash_val, sid in self.ring.items():
            if sid == server_id:
                hashes_to_remove.append(hash_val)
        
        for hash_val in hashes_to_remove:
            del self.ring[hash_val]
            self.sorted_hashes.remove(hash_val)
        
        del self.server_load[server_id]
    
    def get_server(self, key):
        """Get server responsible for a key."""
        if not self.ring:
            return None
        
        key_hash = self._hash(key)
        
        # Binary search for first hash >= key_hash
        import bisect
        idx = bisect.bisect_left(self.sorted_hashes, key_hash)
        
        # Wrap around if at end
        if idx == len(self.sorted_hashes):
            idx = 0
        
        server_id = self.ring[self.sorted_hashes[idx]]
        self.server_load[server_id] += 1  # Track load
        
        return server_id
    
    def get_replicas(self, key, replication_factor=2):
        """Get primary and replica servers for a key."""
        if not self.ring:
            return []
        
        key_hash = self._hash(key)
        import bisect
        idx = bisect.bisect_left(self.sorted_hashes, key_hash)
        
        servers = []
        seen = set()
        
        # Collect unique servers until we have enough replicas
        while len(servers) < replication_factor and len(seen) < len(self.server_load):
            if idx >= len(self.sorted_hashes):
                idx = 0
            
            server_id = self.ring[self.sorted_hashes[idx]]
            if server_id not in seen:
                servers.append(server_id)
                seen.add(server_id)
            
            idx += 1
        
        return servers

# Why consistent hashing wins:
# 1. Minimal reshuffling when servers added/removed
# 2. Load distribution (with virtual nodes)
# 3. Natural replication (next N servers on ring)

# Used by: DynamoDB, Cassandra, Riak, Voldemort, Akamai CDN
```

(6:00 - Building a Distributed Memcached/Redis Clone)

Narration: "Let's build a simplified distributed cache. Each server runs our LRU from Episode 5, coordinated by consistent hashing."

```python
class DistributedCacheNode:
    """A single node in distributed cache cluster."""
    
    def __init__(self, node_id, capacity_mb=1024):
        self.node_id = node_id
        self.capacity_bytes = capacity_mb * 1024 * 1024
        self.current_size = 0
        
        # Local LRU cache
        self.cache = {}  # key -> (value, size, access_time)
        self.access_order = []  # keys in access order (LRU)
        
        # For consistent hashing ring membership
        self.hash_ring = None
        self.replication_factor = 2
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def join_cluster(self, hash_ring):
        """Join a distributed cache cluster."""
        self.hash_ring = hash_ring
        self.hash_ring.add_server(self.node_id)
    
    def get_local(self, key):
        """Get from local cache (LRU)."""
        if key in self.cache:
            value, size, _ = self.cache[key]
            
            # Update LRU: move to end
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            
            # Update access time
            self.cache[key] = (value, size, time.time())
            
            self.hits += 1
            return value
        
        self.misses += 1
        return None
    
    def put_local(self, key, value):
        """Store in local cache with LRU eviction."""
        value_size = len(str(value).encode('utf-8'))
        
        # Check capacity
        while self.current_size + value_size > self.capacity_bytes and self.access_order:
            # Evict LRU
            lru_key = self.access_order.pop(0)
            lru_value, lru_size, _ = self.cache[lru_key]
            del self.cache[lru_key]
            self.current_size -= lru_size
            self.evictions += 1
        
        # Store
        self.cache[key] = (value, value_size, time.time())
        self.access_order.append(key)  # Most recent at end
        self.current_size += value_size
        
        return True

class DistributedCacheCluster:
    """Coordinator for distributed cache cluster."""
    
    def __init__(self, replication_factor=2):
        self.nodes = {}  # node_id -> DistributedCacheNode
        self.hash_ring = ConsistentHashRing()
        self.replication_factor = replication_factor
        
        # Client connection pool
        self.connections = {}
        
        # Cluster metadata
        self.health_checks = {}
    
    def add_node(self, node_id, capacity_mb=1024):
        """Add a node to the cluster."""
        node = DistributedCacheNode(node_id, capacity_mb)
        node.join_cluster(self.hash_ring)
        self.nodes[node_id] = node
        
        # Rebalance data (in background)
        self._trigger_rebalance()
        
        return node
    
    def remove_node(self, node_id):
        """Remove a node from cluster (gracefully)."""
        if node_id not in self.nodes:
            return False
        
        # 1. Stop accepting new writes to this node
        # 2. Replicate its data to other nodes
        # 3. Remove from hash ring
        # 4. Update clients
        
        node = self.nodes[node_id]
        
        # Replicate data before removal
        self._replicate_node_data(node)
        
        # Remove from hash ring
        self.hash_ring.remove_server(node_id)
        
        # Remove from cluster
        del self.nodes[node_id]
        
        # Rebalance remaining nodes
        self._trigger_rebalance()
        
        return True
    
    def get(self, key):
        """Get value from distributed cache."""
        # Determine which server(s) should have this key
        primary_server = self.hash_ring.get_server(key)
        
        if not primary_server or primary_server not in self.nodes:
            return None
        
        # Try primary
        node = self.nodes[primary_server]
        value = node.get_local(key)
        
        if value is not None:
            return value
        
        # Primary miss - try replicas
        replicas = self.hash_ring.get_replicas(key, self.replication_factor)
        
        for replica_id in replicas:
            if replica_id != primary_server and replica_id in self.nodes:
                replica_node = self.nodes[replica_id]
                value = replica_node.get_local(key)
                if value is not None:
                    # Cache warming: copy to primary
                    node.put_local(key, value)
                    return value
        
        # All misses
        return None
    
    def put(self, key, value):
        """Put value in distributed cache (write to all replicas)."""
        # Get all replica servers
        replicas = self.hash_ring.get_replicas(key, self.replication_factor)
        
        # Write to all replicas
        success_count = 0
        for server_id in replicas:
            if server_id in self.nodes:
                node = self.nodes[server_id]
                if node.put_local(key, value):
                    success_count += 1
        
        # Return success if written to at least one replica
        # (In production: quorum-based writes)
        return success_count > 0
    
    def _replicate_node_data(self, node):
        """Replicate data from a node before removal."""
        # For each key in the node...
        for key in list(node.cache.keys()):
            value, _, _ = node.cache[key]
            
            # Find new servers for this key
            replicas = self.hash_ring.get_replicas(key, self.replication_factor)
            
            # Write to new replicas (excluding the dying node)
            for server_id in replicas:
                if server_id != node.node_id and server_id in self.nodes:
                    self.nodes[server_id].put_local(key, value)
    
    def _trigger_rebalance(self):
        """Trigger data rebalancing across cluster."""
        # In background thread:
        # 1. Identify keys on wrong servers
        # 2. Move them to correct servers
        # 3. Update metadata
        
        # This is where distributed caching gets complex!
        pass

# Real distributed caches:
# 1. Memcached: Client-side sharding (simple)
# 2. Redis Cluster: Automatic sharding + replication
# 3. Aerospike: Strong consistency + cross-DC replication
# 4. Ignite: In-memory data grid with SQL
```

(9:00 - Multi-Tier Caching: Memory, SSD, Network)

Narration: "The ultimate production pattern: multi-tier caching. Hot data in RAM, warm data on SSD, cold data evicted. Let's build a 3-tier cache system."

```python
class MultiTierCache:
    """Cache spanning RAM, SSD, and remote cluster."""
    
    def __init__(self):
        # Tier 1: In-memory (fastest, smallest)
        self.l1_cache = LRUCache(capacity=10000)  # RAM
        
        # Tier 2: Local SSD (slower, larger)
        self.l2_cache = SSDCache(max_size_gb=100)  # SSD
        
        # Tier 3: Remote cluster (slowest, largest)
        self.l3_cluster = DistributedCacheCluster()  # Network
        
        # Statistics for adaptive tuning
        self.access_stats = {
            'l1_hits': 0,
            'l2_hits': 0, 
            'l3_hits': 0,
            'misses': 0,
            'promotions': 0,
            'demotions': 0
        }
        
        # Adaptive prefetching
        self.access_patterns = {}
        self.prefetch_enabled = True
    
    def get(self, key):
        """Get from fastest tier available."""
        start_time = time.time()
        
        # Tier 1: RAM
        value = self.l1_cache.get(key)
        if value != -1:
            self.access_stats['l1_hits'] += 1
            self._record_access_time(key, 'l1', time.time() - start_time)
            return value
        
        # Tier 2: SSD
        value = self.l2_cache.get(key)
        if value is not None:
            self.access_stats['l2_hits'] += 1
            # Promote to L1
            self.l1_cache.put(key, value)
            self.access_stats['promotions'] += 1
            self._record_access_time(key, 'l2', time.time() - start_time)
            
            # Prefetch related keys
            if self.prefetch_enabled:
                self._prefetch_related(key)
            
            return value
        
        # Tier 3: Remote cluster
        value = self.l3_cluster.get(key)
        if value is not None:
            self.access_stats['l3_hits'] += 1
            # Promote to L2 and L1
            self.l2_cache.put(key, value)
            self.l1_cache.put(key, value)
            self.access_stats['promotions'] += 2
            self._record_access_time(key, 'l3', time.time() - start_time)
            return value
        
        # Complete miss
        self.access_stats['misses'] += 1
        self._record_access_time(key, 'miss', time.time() - start_time)
        return None
    
    def put(self, key, value, tier='auto'):
        """Put value, optionally at specific tier."""
        if tier == 'auto':
            # Heuristic: small/frequent → L1, large/rare → L3
            value_size = len(str(value).encode('utf-8'))
            
            if value_size < 1024:  # < 1KB
                target_tier = 'l1'
            elif value_size < 1024 * 1024:  # < 1MB
                target_tier = 'l2'
            else:
                target_tier = 'l3'
        else:
            target_tier = tier
        
        # Write to target tier
        if target_tier == 'l1':
            self.l1_cache.put(key, value)
            # Write-through to lower tiers (optional)
            self.l2_cache.put(key, value)
            self.l3_cluster.put(key, value)
        elif target_tier == 'l2':
            self.l2_cache.put(key, value)
            self.l3_cluster.put(key, value)
        else:  # 'l3'
            self.l3_cluster.put(key, value)
    
    def _prefetch_related(self, key):
        """Prefetch keys likely to be accessed next."""
        # Simple pattern: if accessing user:123, prefetch user:123:profile
        if key.startswith('user:'):
            user_id = key.split(':')[1]
            related_keys = [
                f"user:{user_id}:profile",
                f"user:{user_id}:settings",
                f"user:{user_id}:friends"
            ]
            
            for related_key in related_keys:
                # Check if already in L1
                if self.l1_cache.get(related_key) == -1:
                    # Trigger async prefetch
                    self._async_prefetch(related_key)
    
    def _async_prefetch(self, key):
        """Asynchronously prefetch key to L2."""
        import threading
        
        def prefetch_task():
            # Try L3 first, then promote to L2
            value = self.l3_cluster.get(key)
            if value is not None:
                self.l2_cache.put(key, value)
        
        thread = threading.Thread(target=prefetch_task)
        thread.daemon = True
        thread.start()

class SSDCache:
    """SSD-backed cache with efficient I/O."""
    
    def __init__(self, max_size_gb=100):
        self.max_size_bytes = max_size_gb * 1024**3
        self.current_size = 0
        
        # In-memory index (fits in RAM)
        self.index = {}  # key -> (file_offset, size, access_time)
        
        # LRU list for eviction (in RAM)
        self.lru_keys = []
        
        # SSD file (append-only log)
        import os
        self.data_file = open('ssd_cache.bin', 'a+b')
        self.index_file = open('ssd_cache.idx', 'a+b')
        
        # Compression for values > 4KB
        self.compress_threshold = 4096
        
    def get(self, key):
        """Read from SSD."""
        if key not in self.index:
            return None
        
        # Update LRU in memory
        if key in self.lru_keys:
            self.lru_keys.remove(key)
        self.lru_keys.append(key)
        
        # Read from SSD
        offset, size, _ = self.index[key]
        self.data_file.seek(offset)
        data = self.data_file.read(size)
        
        # Update access time
        self.index[key] = (offset, size, time.time())
        
        return data
    
    def put(self, key, value):
        """Write to SSD (append-only)."""
        value_bytes = value if isinstance(value, bytes) else str(value).encode()
        
        # Compress if large
        if len(value_bytes) > self.compress_threshold:
            import zlib
            value_bytes = zlib.compress(value_bytes)
        
        size = len(value_bytes)
        
        # Check capacity, evict if needed
        while self.current_size + size > self.max_size_bytes and self.lru_keys:
            self._evict_one()
        
        # Append to data file
        offset = self.data_file.seek(0, 2)  # Seek to end
        self.data_file.write(value_bytes)
        self.data_file.flush()
        
        # Update in-memory index
        self.index[key] = (offset, size, time.time())
        self.current_size += size
        
        # Update LRU
        if key in self.lru_keys:
            self.lru_keys.remove(key)
        self.lru_keys.append(key)
        
        return True
    
    def _evict_one(self):
        """Evict least recently used item from SSD."""
        if not self.lru_keys:
            return
        
        lru_key = self.lru_keys.pop(0)
        if lru_key in self.index:
            offset, size, _ = self.index[lru_key]
            del self.index[lru_key]
            self.current_size -= size
            
            # Note: We don't actually delete from SSD file
            # SSD garbage collection runs periodically
            # This is called "log-structured" storage

# Production multi-tier systems:
# 1. CPU caches: L1, L2, L3, RAM, SSD
# 2. CDNs: Edge, regional, origin
# 3. Facebook's TAO: RAM + SSD + database
# 4. Google's Bigtable: Memtable + SSTable + GFS
```

(12:00 - The CDN: Caching at Global Scale)

Narration: "The most visible distributed cache: Content Delivery Networks. Akamai, Cloudflare, CloudFront - serving websites from edge locations worldwide. Let's build a simplified CDN."

```python
class CDNEdgeNode:
    """A single CDN edge location."""
    
    def __init__(self, location_id, capacity_gb=100):
        self.location_id = location_id  # e.g., "us-east-1"
        self.capacity_bytes = capacity_gb * 1024**3
        self.current_size = 0
        
        # Cache for static assets
        self.asset_cache = {}  # URL -> (content, headers, expiry)
        
        # LRU tracking
        self.access_times = {}  # URL -> last_access
        
        # Connection to origin
        self.origin_url = "https://origin.example.com"
        
        # Statistics
        self.cache_hits = 0
        self.cache_misses = 0
        self.origin_fetches = 0
        self.bandwidth_saved = 0
    
    def get_asset(self, url, request_headers):
        """Get asset from CDN edge."""
        # Normalize URL (remove query params for caching)
        cache_key = self._normalize_url(url)
        
        # Check cache
        if cache_key in self.asset_cache:
            content, headers, expiry = self.asset_cache[cache_key]
            
            # Check if expired
            if time.time() < expiry:
                # Cache hit!
                self.cache_hits += 1
                self.access_times[cache_key] = time.time()
                self.bandwidth_saved += len(content)
                
                # Add CDN headers
                headers['X-CDN-Cache'] = 'HIT'
                headers['X-CDN-Node'] = self.location_id
                
                return content, headers
        
        # Cache miss or expired
        self.cache_misses += 1
        
        # Fetch from origin
        content, headers = self._fetch_from_origin(url, request_headers)
        self.origin_fetches += 1
        
        # Determine if cacheable
        cache_control = headers.get('Cache-Control', '')
        max_age = self._parse_cache_control(cache_control)
        
        if max_age > 0:
            # Cache it
            expiry = time.time() + max_age
            
            # Check capacity
            content_size = len(content)
            while self.current_size + content_size > self.capacity_bytes:
                self._evict_oldest()
            
            # Store
            self.asset_cache[cache_key] = (content, headers, expiry)
            self.access_times[cache_key] = time.time()
            self.current_size += content_size
        
        # Add CDN headers
        headers['X-CDN-Cache'] = 'MISS'
        headers['X-CDN-Node'] = self.location_id
        
        return content, headers
    
    def _fetch_from_origin(self, url, request_headers):
        """Fetch content from origin server."""
        # Simulated origin fetch
        import random
        content = f"Content for {url}".encode()
        
        # Origin sets caching headers
        headers = {
            'Cache-Control': 'public, max-age=3600',  # 1 hour
            'Content-Type': 'text/html',
            'ETag': f'"{random.randint(1000, 9999)}"'
        }
        
        return content, headers
    
    def _evict_oldest(self):
        """Evict oldest assets when cache full."""
        if not self.access_times:
            return
        
        # Find oldest accessed asset
        oldest_url = min(self.access_times.items(), key=lambda x: x[1])[0]
        
        if oldest_url in self.asset_cache:
            content, _, _ = self.asset_cache[oldest_url]
            content_size = len(content)
            
            del self.asset_cache[oldest_url]
            del self.access_times[oldest_url]
            self.current_size -= content_size

class GlobalCDN:
    """Global CDN with multiple edge locations."""
    
    def __init__(self):
        # Edge locations worldwide
        self.edge_nodes = {
            'us-east-1': CDNEdgeNode('us-east-1', 500),
            'us-west-2': CDNEdgeNode('us-west-2', 500),
            'eu-west-1': CDNEdgeNode('eu-west-1', 300),
            'ap-southeast-1': CDNEdgeNode('ap-southeast-1', 200),
            'sa-east-1': CDNEdgeNode('sa-east-1', 100),
        }
        
        # DNS-based routing (simplified)
        self.geo_routing = {
            'US': ['us-east-1', 'us-west-2'],
            'EU': ['eu-west-1'],
            'AP': ['ap-southeast-1'],
            'SA': ['sa-east-1'],
        }
        
        # Central control plane
        self.control_plane = CDNControlPlane()
        
        # Statistics aggregation
        self.global_stats = {
            'total_requests': 0,
            'cache_hit_ratio': 0.0,
            'bandwidth_saved_gb': 0,
            'origin_load': 0.0
        }
    
    def route_request(self, client_ip, url, request_headers):
        """Route request to nearest edge location."""
        # Determine client region (simplified)
        region = self._ip_to_region(client_ip)
        
        # Get candidate edge nodes for this region
        candidate_nodes = self.geo_routing.get(region, ['us-east-1'])
        
        # Choose edge node (could be based on load, health, etc.)
        edge_id = candidate_nodes[0]
        edge_node = self.edge_nodes[edge_id]
        
        # Process request
        content, headers = edge_node.get_asset(url, request_headers)
        
        # Update global stats
        self.global_stats['total_requests'] += 1
        
        return content, headers, edge_id
    
    def prefetch_popular(self):
        """Prefetch popular content to all edges."""
        # Central control plane analyzes traffic patterns
        popular_urls = self.control_plane.get_popular_urls()
        
        for url in popular_urls[:100]:  # Top 100
            for edge_id, edge_node in self.edge_nodes.items():
                # Async prefetch to each edge
                edge_node.prefetch_url(url)
    
    def invalidate_url(self, url):
        """Invalidate URL across all edge locations."""
        # When origin content changes, invalidate CDN cache
        for edge_node in self.edge_nodes.values():
            edge_node.invalidate_url(url)
        
        # Log invalidation
        self.control_plane.log_invalidation(url)

# CDN optimizations:
# 1. Anycast routing (same IP everywhere)
# 2. TLS termination at edge
# 3. Image optimization (resize, compress, WebP)
# 4. DDoS protection
# 5. WAF (Web Application Firewall)
```

(15:00 - Cache Invalidation & Consistency Models)

Narration: "The hardest problem in computer science: cache invalidation. When data changes at the source, how do we update or invalidate caches? Let's explore strategies:"

```python
class CacheInvalidationStrategies:
    """Different cache invalidation approaches."""
    
    def __init__(self):
        self.strategies = {
            'ttl': self.ttl_based,
            'write_through': self.write_through,
            'write_behind': self.write_behind,
            'write_invalidate': self.write_invalidate,
            'version_based': self.version_based,
        }
    
    def ttl_based(self, cache, key, value, ttl_seconds=300):
        """Time-based expiration (simplest)."""
        cache.put(key, value)
        # Schedule automatic invalidation after TTL
        import threading
        timer = threading.Timer(ttl_seconds, cache.delete, args=[key])
        timer.daemon = True
        timer.start()
    
    def write_through(self, cache, db, key, value):
        """
        Write to cache and DB simultaneously.
        Cache always consistent with DB.
        """
        # Write to DB first
        db.update(key, value)
        # Then update cache
        cache.put(key, value)
    
    def write_behind(self, cache, db, key, value):
        """
        Write to cache immediately, DB later.
        Better performance, risk of data loss.
        """
        # Write to cache immediately
        cache.put(key, value)
        
        # Queue DB write for later
        import queue
        write_queue = queue.Queue()
        write_queue.put((key, value))
        
        # Background thread processes queue
        def db_writer():
            while True:
                k, v = write_queue.get()
                db.update(k, v)
                write_queue.task_done()
        
        threading.Thread(target=db_writer, daemon=True).start()
    
    def write_invalidate(self, cache, key, value):
        """
        Invalidate cache on write, reload on next read.
        Useful for expensive computations.
        """
        # Delete from cache
        cache.delete(key)
        
        # Update source
        # (Source update happens here)
        
        # Next read will recompute and cache
    
    def version_based(self, cache, key, value):
        """
        Versioned caching (like ETags).
        Client provides version, cache returns if same.
        """
        current_version = cache.get_version(key)
        new_version = self._compute_version(value)
        
        if current_version != new_version:
            cache.put(key, value, version=new_version)
        
        return new_version

class DistributedCacheWithConsistency:
    """Distributed cache with configurable consistency."""
    
    def __init__(self, consistency_level='eventual'):
        self.consistency_level = consistency_level
        self.nodes = {}
        self.versions = {}  # key -> version
        
        # For strong consistency
        self.locks = {}
        self.quorum_size = 2
    
    def get(self, key, read_consistency=None):
        """Get with configurable read consistency."""
        consistency = read_consistency or self.consistency_level
        
        if consistency == 'strong':
            return self._get_strong(key)
        elif consistency == 'eventual':
            return self._get_eventual(key)
        elif consistency == 'causal':
            return self._get_causal(key)
        else:
            return self._get_eventual(key)
    
    def put(self, key, value, write_consistency=None):
        """Put with configurable write consistency."""
        consistency = write_consistency or self.consistency_level
        
        if consistency == 'strong':
            return self._put_strong(key, value)
        elif consistency == 'eventual':
            return self._put_eventual(key, value)
        elif consistency == 'causal':
            return self._put_causal(key, value)
        else:
            return self._put_eventual(key, value)
    
    def _get_strong(self, key):
        """Strong consistency: read from quorum."""
        # Get all replicas
        replicas = self._get_replicas(key)
        
        # Read from quorum
        values = []
        for node_id in replicas[:self.quorum_size]:
            value = self.nodes[node_id].get_local(key)
            if value is not None:
                values.append(value)
        
        if not values:
            return None
        
        # Check for consistency
        # In real system: compare versions/timestamps
        return values[0]  # Return first value (simplified)
    
    def _put_strong(self, key, value):
        """Strong consistency: write to quorum."""
        # Get all replicas
        replicas = self._get_replicas(key)
        
        # Write to quorum
        success_count = 0
        for node_id in replicas[:self.quorum_size]:
            if self.nodes[node_id].put_local(key, value):
                success_count += 1
        
        # Return success only if quorum written
        return success_count >= self.quorum_size
    
    def _get_eventual(self, key):
        """Eventual consistency: read from any replica."""
        replicas = self._get_replicas(key)
        
        # Try replicas in order
        for node_id in replicas:
            value = self.nodes[node_id].get_local(key)
            if value is not None:
                return value
        
        return None
    
    def _put_eventual(self, key, value):
        """Eventual consistency: write to primary, async replication."""
        # Write to primary
        primary = self._get_primary(key)
        success = self.nodes[primary].put_local(key, value)
        
        # Async replication to others
        if success:
            self._async_replicate(key, value)
        
        return success
    
    def _async_replicate(self, key, value):
        """Asynchronously replicate to all replicas."""
        import threading
        
        def replicate_task():
            replicas = self._get_replicas(key)
            for node_id in replicas[1:]:  # Skip primary
                self.nodes[node_id].put_local(key, value)
        
        thread = threading.Thread(target=replicate_task)
        thread.daemon = True
        thread.start()

# Consistency tradeoffs:
# Strong: Linearizable (simplest to reason about)
# Eventual: Better performance, can have stale reads  
# Causal: Preserves cause-effect relationships
# Read-your-writes: Personal consistency guarantee
```

(18:00 - Real-World Case Studies)

Narration: "Let's look at how real companies implement distributed caching at massive scale:"

```python
# Case Study 1: Facebook's TAO
class TAOCache:
    """Facebook's TAO: The Associations and Objects cache."""
    
    def __init__(self):
        # Two-layer cache:
        self.cache_layer = {
            'memcache': MemcacheCluster(),  # RAM cache
            'mysql': MySQLReadReplicas(),   # Persistent storage
        }
        
        # Graph-oriented (objects + associations)
        self.objects = {}      # id -> object
        self.associations = {} # (id1, association_type) -> [id2...]
        
        # Write-through to persistent store
        self.write_through = True
        
        # Asynchronous invalidation
        self.invalidation_queue = []
    
    def get_object(self, obj_id):
        """Get object from cache or database."""
        # Check cache first
        if obj_id in self.objects:
            return self.objects[obj_id]
        
        # Cache miss - check database
        obj = self.cache_layer['mysql'].get_object(obj_id)
        if obj:
            # Populate cache
            self.objects[obj_id] = obj
        
        return obj
    
    def create_association(self, from_id, assoc_type, to_id):
        """Create association (like friend request)."""
        key = (from_id, assoc_type)
        
        if key not in self.associations:
            self.associations[key] = []
        
        self.associations[key].append(to_id)
        
        # Write to persistent store
        if self.write_through:
            self.cache_layer['mysql'].create_association(from_id, assoc_type, to_id)
        
        # Invalidate related caches
        self._invalidate_related(from_id, assoc_type)

# Case Study 2: Twitter's Manhattan
class ManhattanCache:
    """Twitter's real-time distributed database."""
    
    def __init__(self):
        # Timeline cache for home timelines
        self.timeline_cache = {}
        
        # Tweet cache
        self.tweet_cache = {}
        
        # Fan-out on write
        self.fanout_on_write = True
        
        # Read repair for consistency
        self.read_repair = True
    
    def post_tweet(self, user_id, tweet):
        """Post tweet and fan out to followers."""
        # Store tweet
        tweet_id = self._store_tweet(tweet)
        
        if self.fanout_on_write:
            # Fan out to all followers' timelines
            followers = self._get_followers(user_id)
            for follower_id in followers:
                self._add_to_timeline(follower_id, tweet_id)
        else:
            # Timeline built on read
            pass

# Case Study 3: Netflix's EVCache
class EVCache:
    """Netflix's distributed cache for personalization."""
    
    def __init__(self):
        # Multi-region replication
        self.regions = ['us-east', 'eu-west', 'ap-southeast']
        self.cross_region_replication = True
        
        # SSD-backed for large datasets
        self.ssd_backed = True
        
        # Predictive caching based on viewing patterns
        self.predictive_caching = True
    
    def get_recommendations(self, user_id):
        """Get personalized recommendations."""
        cache_key = f"recs:{user_id}"
        
        # Try local region first
        recs = self._get_local(cache_key)
        if recs:
            return recs
        
        # Try other regions
        for region in self.regions:
            recs = self._get_from_region(region, cache_key)
            if recs:
                # Replicate to local region
                self._set_local(cache_key, recs)
                return recs
        
        # Compute and cache
        recs = self._compute_recommendations(user_id)
        self._set_local(cache_key, recs)
        return recs

# Key lessons from production:
# 1. Facebook: Graph-oriented caching for social data
# 2. Twitter: Timeline caching with fan-out strategies
# 3. Netflix: Multi-region for global users
# 4. Google: Multi-tier with predictive prefetching
```

(21:00 - Monitoring, Metrics, and Autoscaling)

Narration: "At scale, caching isn't just algorithms - it's operations. Monitoring hit ratios, detecting hot keys, autoscaling based on load."

```python
class CacheMonitoring:
    """Monitoring and metrics for distributed cache."""
    
    def __init__(self, cache_cluster):
        self.cache_cluster = cache_cluster
        self.metrics = {
            'hit_ratio': 0.0,
            'latency_p50': 0.0,
            'latency_p99': 0.0,
            'memory_usage': 0.0,
            'eviction_rate': 0.0,
            'hot_keys': []
        }
        
        # Time-series database for metrics
        self.tsdb = TimeSeriesDB()
        
        # Alerting rules
        self.alerts = {
            'hit_ratio_below_90': self.alert_low_hit_ratio,
            'latency_spike': self.alert_latency_spike,
            'memory_critical': self.alert_memory_critical,
        }
    
    def collect_metrics(self):
        """Collect metrics from all nodes."""
        all_metrics = []
        
        for node_id, node in self.cache_cluster.nodes.items():
            node_metrics = {
                'hits': node.hits,
                'misses': node.misses,
                'size': node.current_size,
                'capacity': node.capacity_bytes,
                'evictions': node.evictions,
            }
            all_metrics.append((node_id, node_metrics))
        
        # Aggregate
        self._aggregate_metrics(all_metrics)
        
        # Store in time-series DB
        self.tsdb.store(self.metrics)
        
        # Check alerts
        self._check_alerts()
    
    def _aggregate_metrics(self, node_metrics):
        """Aggregate metrics across nodes."""
        total_hits = sum(m['hits'] for _, m in node_metrics)
        total_misses = sum(m['misses'] for _, m in node_metrics)
        total_requests = total_hits + total_misses
        
        self.metrics['hit_ratio'] = total_hits / total_requests if total_requests > 0 else 0
        
        # Find hot keys (keys with high access rate)
        hot_keys = self._find_hot_keys()
        self.metrics['hot_keys'] = hot_keys[:10]  # Top 10
        
        # Calculate memory usage
        total_size = sum(m['size'] for _, m in node_metrics)
        total_capacity = sum(m['capacity'] for _, m in node_metrics)
        self.metrics['memory_usage'] = total_size / total_capacity if total_capacity > 0 else 0
    
    def _find_hot_keys(self):
        """Identify hot keys (access pattern analysis)."""
        # In production: use sampling or dedicated monitoring
        # Here: simplified version
        
        hot_keys = []
        for node_id, node in self.cache_cluster.nodes.items():
            # Sample keys and their access patterns
            # Real implementation would use probabilistic data structures
            pass
        
        return hot_keys
    
    def alert_low_hit_ratio(self):
        """Alert when hit ratio drops below threshold."""
        if self.metrics['hit_ratio'] < 0.9:
            print(f"ALERT: Cache hit ratio low: {self.metrics['hit_ratio']:.2%}")
            
            # Possible actions:
            # 1. Increase cache size
            # 2. Tune eviction policy
            # 3. Add more cache nodes
            # 4. Warm cache with popular items

class CacheAutoscaler:
    """Autoscale cache cluster based on load."""
    
    def __init__(self, cache_cluster, cloud_provider):
        self.cache_cluster = cache_cluster
        self.cloud = cloud_provider
        
        # Scaling policies
        self.scale_up_threshold = 0.8  # 80% memory usage
        self.scale_down_threshold = 0.3  # 30% memory usage
        
        # Cooldown periods (avoid rapid scaling)
        self.scale_up_cooldown = 300  # 5 minutes
        self.scale_down_cooldown = 900  # 15 minutes
        
        self.last_scale_up = 0
        self.last_scale_down = 0
    
    def evaluate_scaling(self):
        """Evaluate if scaling is needed."""
        current_time = time.time()
        
        # Check memory usage across cluster
        avg_memory_usage = self._get_average_memory_usage()
        
        # Scale up if needed
        if (avg_memory_usage > self.scale_up_threshold and 
            current_time - self.last_scale_up > self.scale_up_cooldown):
            self.scale_up()
            self.last_scale_up = current_time
        
        # Scale down if needed (and safe)
        elif (avg_memory_usage < self.scale_down_threshold and
              current_time - self.last_scale_down > self.scale_down_cooldown and
              len(self.cache_cluster.nodes) > 1):  # Keep at least 1 node
            self.scale_down()
            self.last_scale_down = current_time
    
    def scale_up(self):
        """Add a new cache node."""
        print("Scaling up: Adding new cache node")
        
        # Launch new instance
        new_node_id = self.cloud.launch_instance('cache-node')
        
        # Add to cluster
        self.cache_cluster.add_node(new_node_id)
        
        # Rebalance data
        self.cache_cluster.rebalance()
    
    def scale_down(self):
        """Remove a cache node (least loaded)."""
        print("Scaling down: Removing cache node")
        
        # Find least loaded node
        least_loaded = min(
            self.cache_cluster.nodes.items(),
            key=lambda x: x[1].current_size / x[1].capacity_bytes
        )[0]
        
        # Remove from cluster (gracefully)
        self.cache_cluster.remove_node(least_loaded)
        
        # Terminate instance
        self.cloud.terminate_instance(least_loaded)
    
    def _get_average_memory_usage(self):
        """Calculate average memory usage across nodes."""
        total_usage = 0
        for node in self.cache_cluster.nodes.values():
            total_usage += node.current_size / node.capacity_bytes
        
        return total_usage / len(self.cache_cluster.nodes) if self.cache_cluster.nodes else 0

# Production monitoring stack:
# 1. Metrics: Prometheus (hit ratio, latency, memory)
# 2. Logging: ELK stack (access patterns, errors)
# 3. Tracing: Jaeger (request flow through cache layers)
# 4. Alerting: PagerDuty (SLO violations)
# 5. Auto-scaling: Kubernetes HPA, custom controllers
```

(24:00 - Recap & The Complete Caching Journey)

[Visual: Complete caching architecture diagram]

Narration: "Let's look back at our complete journey through caching:"

```
PHASE 1: SINGLE MACHINE (Episode 5)
  Algorithm: Hash map + doubly linked list (O(1) LRU)
  Applications: Browser cache, Redis, OS page cache
  Key insight: Recent access predicts future access

PHASE 2: DISTRIBUTED (Episode 6)
  Algorithm: Consistent hashing + replication
  Applications: Memcached cluster, CDN edges, database cache
  Key insight: Partition data, replicate for availability

PHASE 3: MULTI-TIER
  Architecture: RAM → SSD → Network → Database
  Applications: Global CDNs, big data systems
  Key insight: Different media for different access patterns

PHASE 4: INTELLIGENT
  Features: Predictive prefetching, adaptive eviction, auto-scaling
  Applications: Netflix recommendations, Facebook TAO
  Key insight: Caches should learn and adapt
```

Key Principles of Production Caching:

1. Cache closest to user (edge > region > origin)
2. Size matters, but algorithm matters more
3. Monitoring is non-negotiable (hit ratios, latency)
4. Consistency is a spectrum (strong vs eventual)
5. Scale horizontally, not vertically (add nodes, not RAM)

(25:00 - Series Finale Teaser)

Narration: "We've journeyed from singly linked lists in Git to global distributed caching systems. But this is just Season 1."

[Visual: Season 2 preview - Trees, Graphs, Advanced Data Structures]

Narration: "In Season 2, we'll dive deeper: B-trees in databases, graph algorithms in social networks, bloom filters in distributed systems. We'll build search engines, recommendation systems, and real-time analytics platforms."

Narration: "Remember: Data structures aren't just interview questions. They're the invisible foundation of every system you use daily. Master them, and you master scalable systems design."

---

EPISODE 6 COMPLETE (25 minutes)

Focus: Distributed caching, multi-tier architectures, production systems
Perfect capstone for Season 1: From single linked list to global CDN

Season 1 Complete:

· Episode 1: Singly linked lists → Git commit history
· Episode 2: Linked list intersection → Git merge-base
· Episode 3: Doubly linked lists → Browser history
· Episode 4: Immutable structures → Time travel/undo systems
· Episode 5: LRU Cache → Single-machine caching
· Episode 6: Distributed caching → Global CDNs

Ready for chapter 7 !!

