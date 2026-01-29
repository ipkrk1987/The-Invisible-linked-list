# Episode 2.3: Ring Buffers - When Your Logs Go in Circles

## Overview
**LeetCode Problem:** #33 - Search in Rotated Sorted Array  
**Production System:** Circular Log Buffer / Ring Buffer for Production Monitoring  
**Core Insight:** Ring buffers wrap around - the "rotation point" is where newest meets oldest. Binary search still works if you find where the order breaks!

---

## PART 1: THE PRODUCTION PROBLEM

### The 2 AM Crisis

```
Scene: A monitoring dashboard. An SRE stares at a ring buffer visualization
showing memory metrics. The buffer is lying about what happened.

SRE:      "The memory spike that crashed our service - I need to find when
          it started. Our ring buffer stores the last 1000 data points."

Manager:  "So search for the timestamp when memory crossed 80%."

SRE:      "I tried binary search. It says the spike started at index 342.
          But that timestamp is from YESTERDAY."

Manager:  "That's impossible. We restarted the service 2 hours ago."

SRE:      "Here's the thing: it's a RING buffer. It wraps around.
          Index 0 isn't the oldest entry anymore - index 847 is."

Manager:  "So the data looks sorted but it's actually rotated?"

SRE:      "Exactly. Entries 847-999 are older than entries 0-846.
          Normal binary search doesn't know about the wrap point."

Manager:  "Can't you just linear scan?"

SRE:      "With a million-entry buffer and queries every 100ms?
          That's how we got into this mess - I need O(log n)."
```

### What IS a Ring Buffer?

Think of a circular track with 8 positions. Data goes in one end and pushes out the other:

```
Step 1: Write A, B, C
        [A][B][C][ ][ ][ ][ ][ ]
         ↑ head             

Step 2: Write D, E, F, G, H
        [A][B][C][D][E][F][G][H]
         ↑ head              ↑ tail (about to wrap)

Step 3: Write I (WRAPS AROUND!)
        [I][B][C][D][E][F][G][H]
            ↑ oldest   ↑ newest

Now: Index 0 has the NEWEST data, index 1 has the OLDEST!
```

**The Problem:** Data is sorted by time... but it WRAPS. Binary search breaks!

---

## PART 2: THE LEETCODE CORE

### LeetCode #33: Search in Rotated Sorted Array

```python
# The array was sorted, then "rotated" at some pivot:
# Original: [0, 1, 2, 4, 5, 6, 7]
# Rotated:  [4, 5, 6, 7, 0, 1, 2]  (rotated at index 4)
#                    ↑ pivot - where order "breaks"

def search_rotated(nums, target):
    left, right = 0, len(nums) - 1
    
    while left <= right:
        mid = left + (right - left) // 2
        
        if nums[mid] == target:
            return mid
            
        # KEY INSIGHT: One half is ALWAYS normally sorted!
        if nums[left] <= nums[mid]:
            # Left half is sorted [left...mid]
            if nums[left] <= target < nums[mid]:
                right = mid - 1  # Target in sorted left half
            else:
                left = mid + 1   # Target in rotated right half
        else:
            # Right half is sorted [mid...right]
            if nums[mid] < target <= nums[right]:
                left = mid + 1   # Target in sorted right half
            else:
                right = mid - 1  # Target in rotated left half
                
    return -1
```

### The Conceptual Leap

**Ring Buffer = Rotated Array**

When a ring buffer wraps, the timestamps ARE still sorted... just rotated at the wrap point!

```
Ring buffer state (timestamps in ms):
[1500, 1550, 1600, 1650, 900, 950, 1000, 1050, 1100]
                        ↑ wrap point (newest wrote here)

This is EXACTLY like:
[4, 5, 6, 7, 0, 1, 2, 3]  ← rotated sorted array!
```

Search for "when did timestamp 1000 occur?" = Rotated binary search!

---

## PART 3: THE NAIVE IMPLEMENTATION (That Everyone Writes First)

```python
class BrokenRingBuffer:
    def __init__(self, capacity=1000):
        self.capacity = capacity
        self.buffer = [None] * capacity
        self.write_index = 0
        
    def write(self, timestamp, value):
        self.buffer[self.write_index] = (timestamp, value)
        self.write_index = (self.write_index + 1) % self.capacity
        
    def search_timestamp(self, target_ts):
        """Find entry closest to target timestamp"""
        # Naive binary search - ASSUMES buffer is sorted!
        left, right = 0, self.capacity - 1
        
        while left <= right:
            mid = (left + right) // 2
            if self.buffer[mid] is None:
                right = mid - 1
                continue
                
            if self.buffer[mid][0] == target_ts:
                return mid
            elif self.buffer[mid][0] < target_ts:
                left = mid + 1
            else:
                right = mid - 1
                
        return -1  # WRONG ANSWER when buffer has wrapped!
```

### Why This Breaks

```
Buffer after wrap:
Index:  [0]    [1]    [2]    [3]    [4]    [5]
Data:   1600   1700   1800   1200   1300   1400
                        ↑ wrap point

Search for 1300:
- mid = 2, buffer[2] = 1800
- 1300 < 1800, so search LEFT...
- BUT 1300 is actually to the RIGHT (after wrap point)!

Binary search assumes: if buffer[mid] > target, target is LEFT
Ring buffer reality: target might be after the wrap point!
```

---

## PART 4: THE ROTATED SEARCH SOLUTION

### Finding the Wrap Point First

```python
def find_wrap_point(buffer):
    """Find where the buffer wraps (minimum timestamp)"""
    left, right = 0, len(buffer) - 1
    
    while left < right:
        mid = (left + right) // 2
        
        if buffer[mid] > buffer[right]:
            # Wrap point is in right half
            left = mid + 1
        else:
            # Wrap point is in left half (or mid IS the wrap)
            right = mid
            
    return left  # Index of oldest (smallest) timestamp
```

### The Production Ring Buffer

```python
class RotatedRingBuffer:
    """Ring buffer with O(log n) search using rotated binary search"""
    
    def __init__(self, capacity=1000):
        self.capacity = capacity
        self.buffer = [None] * capacity
        self.write_index = 0
        self.count = 0  # Track how many entries exist
        
    def write(self, timestamp, value):
        self.buffer[self.write_index] = (timestamp, value)
        self.write_index = (self.write_index + 1) % self.capacity
        self.count = min(self.count + 1, self.capacity)
        
    def _get_wrap_point(self):
        """Where does oldest data start?"""
        if self.count < self.capacity:
            return 0  # Not wrapped yet
        return self.write_index  # Oldest is right after newest
        
    def search(self, target_ts):
        """O(log n) search in rotated buffer"""
        if self.count == 0:
            return -1
            
        wrap = self._get_wrap_point()
        
        if wrap == 0:
            # Not wrapped - normal binary search
            return self._binary_search(0, self.count - 1, target_ts)
            
        # Wrapped - use rotated search
        return self._rotated_search(target_ts, wrap)
        
    def _rotated_search(self, target_ts, wrap):
        """Binary search on rotated array"""
        left, right = 0, self.count - 1
        
        while left <= right:
            mid = (left + right) // 2
            mid_ts = self.buffer[mid][0]
            
            if mid_ts == target_ts:
                return mid
                
            # Is LEFT half sorted? (no wrap in left half)
            left_ts = self.buffer[left][0]
            if left_ts <= mid_ts:
                # Left is sorted
                if left_ts <= target_ts < mid_ts:
                    right = mid - 1
                else:
                    left = mid + 1
            else:
                # Right is sorted
                right_ts = self.buffer[right][0]
                if mid_ts < target_ts <= right_ts:
                    left = mid + 1
                else:
                    right = mid - 1
                    
        return -1
```

---

## PART 5: THE FIVE REAL-WORLD FAILURE MODES

### 1. The Midnight Wrap

```
Problem: Buffer wraps at exactly midnight. Timestamp comparison 
         crosses date boundary.

23:59:59.999 → 00:00:00.001

Binary search sees: 86399999ms > 1ms → goes wrong direction!

Solution: Use monotonic timestamps (system uptime, not wall clock)
```

### 2. The Partial Fill

```
Problem: Buffer isn't full yet. Some indices are None.

[1000, 1100, 1200, None, None, None, None, None]
                    ↑ search hits None, crashes

Solution: Track count separately, limit search to valid range
```

### 3. The Duplicate Timestamp

```
Problem: Two events at same millisecond. Which one?

[1000, 1100, 1100, 1100, 1200]  ← three entries at 1100

Binary search finds ONE, but you needed the FIRST.

Solution: After finding match, scan backward to find first occurrence
```

### 4. The Range Query

```
Problem: "Find all entries between timestamp A and B"

Can't just iterate [indexA...indexB] - they might span the wrap!

Index:  [0]    [1]    [2]    [3]    [4]    [5]
Data:   1600   1700   1800   1200   1300   1400
        ←newer              ↑wrap   ←older

Range 1250-1650 spans indices: [4, 5, 0] (wraps around!)

Solution: Handle wrap-aware range iteration
```

### 5. The Concurrent Write

```
Problem: Reader searches while writer overwrites.

Thread 1 (reader): Binary search, mid = 500
Thread 2 (writer): Overwrites index 500
Thread 1 (reader): Reads garbage

Solution: Copy-on-write or sequence locks
```

---

## PART 6: PRODUCTION HARDENING

### Layer 1: Monotonic Timestamps

```python
class MonotonicRingBuffer(RotatedRingBuffer):
    """Use monotonic clock to avoid midnight wrap issues"""
    
    def __init__(self, capacity):
        super().__init__(capacity)
        self.start_time = time.monotonic_ns()
        
    def _get_monotonic_ts(self):
        """Nanoseconds since buffer creation"""
        return time.monotonic_ns() - self.start_time
        
    def write(self, value):
        ts = self._get_monotonic_ts()
        super().write(ts, value)
```

### Layer 2: Range Queries with Wrap Awareness

```python
def range_query(self, start_ts, end_ts):
    """Get all entries in timestamp range, handling wrap"""
    if self.count == 0:
        return []
        
    results = []
    wrap = self._get_wrap_point()
    
    # Iterate from oldest to newest
    for i in range(self.count):
        idx = (wrap + i) % self.capacity
        entry = self.buffer[idx]
        
        if entry and start_ts <= entry[0] <= end_ts:
            results.append(entry)
            
    return results
```

### Layer 3: Concurrent Access Safety

```python
class ConcurrentRingBuffer:
    """Thread-safe ring buffer with sequence locks"""
    
    def __init__(self, capacity):
        self.capacity = capacity
        self.buffer = [None] * capacity
        self.write_index = 0
        self.sequence = 0  # Incremented on each write
        
    def write(self, timestamp, value):
        # Odd sequence = write in progress
        self.sequence += 1  
        
        self.buffer[self.write_index] = (timestamp, value)
        self.write_index = (self.write_index + 1) % self.capacity
        
        # Even sequence = write complete
        self.sequence += 1  
        
    def read_consistent(self, index):
        """Read with consistency check"""
        while True:
            seq_before = self.sequence
            if seq_before % 2 == 1:
                continue  # Write in progress, retry
                
            value = self.buffer[index]
            
            seq_after = self.sequence
            if seq_before == seq_after:
                return value  # Consistent read
            # Else: write happened during read, retry
```

### Layer 4: The Complete Production Buffer

```python
class ProductionRingBuffer:
    """
    Production-ready ring buffer with:
    1. O(log n) rotated search
    2. Monotonic timestamps
    3. Range queries
    4. Concurrent access safety
    5. Metrics and monitoring
    """
    
    def __init__(self, capacity, name="default"):
        self.capacity = capacity
        self.name = name
        self.buffer = [None] * capacity
        self.write_index = 0
        self.count = 0
        self.sequence = 0
        self.start_time = time.monotonic_ns()
        self.metrics = BufferMetrics(name)
        
    def write(self, value):
        """Thread-safe write with metrics"""
        ts = time.monotonic_ns() - self.start_time
        
        self.sequence += 1  # Mark write start
        
        self.buffer[self.write_index] = (ts, value)
        self.write_index = (self.write_index + 1) % self.capacity
        self.count = min(self.count + 1, self.capacity)
        
        self.sequence += 1  # Mark write complete
        
        self.metrics.record_write()
        
    def search(self, target_ts):
        """O(log n) search with wrap handling"""
        self.metrics.record_search()
        
        # Wait for consistent read window
        while self.sequence % 2 == 1:
            pass
            
        wrap = self._get_wrap_point()
        
        if wrap == 0 or self.count < self.capacity:
            return self._binary_search(0, self.count - 1, target_ts)
        else:
            return self._rotated_search(target_ts)
            
    def get_recent(self, n):
        """Get n most recent entries (efficient: no search needed)"""
        results = []
        for i in range(min(n, self.count)):
            idx = (self.write_index - 1 - i) % self.capacity
            if self.buffer[idx]:
                results.append(self.buffer[idx])
        return results
```

---

## PART 7: PRODUCTION GUARANTEES

| Guarantee | How We Achieve It |
|-----------|-------------------|
| O(log n) search | Rotated binary search algorithm |
| No midnight bugs | Monotonic timestamps |
| Thread safety | Sequence locks for reads |
| Range queries | Wrap-aware iteration |
| No data corruption | Atomic write index updates |
| Observability | Metrics on every operation |

---

## KEY TAKEAWAYS

1. **Ring buffers = Rotated arrays**: When they wrap, data is still sorted... just rotated at the wrap point.

2. **Normal binary search breaks on wrapped buffers**: It doesn't know the rotation point.

3. **The key insight**: One half is ALWAYS sorted. Use that to decide which half contains your target.

4. **Production concerns beyond the algorithm**:
   - Monotonic timestamps (avoid clock issues)
   - Concurrent access (sequence locks)
   - Range queries (wrap-aware iteration)
   - Partial fills (track count separately)

5. **Where you've seen ring buffers**:
   - Log aggregators (last N errors)
   - System monitoring (CPU/memory history)
   - Network packet capture
   - Audio/video streaming buffers

---

## TEASER: EPISODE 2.4

Our ring buffer stores data... but what if we need SORTED data that changes dynamically?

Consider a real-time leaderboard:
- Millions of score updates per second
- "What's player X's rank?" needs to be FAST
- Top 100 query runs constantly

Static arrays won't work - we need dynamic sorted structures. That's **Binary Search Trees**.

Next time: LeetCode #98 (Validate BST) and #701 (Insert into BST) become the foundation for an in-memory ordered key-value store.

---

## Animation Notes

1. **Ring Buffer Visualization**: Show circular buffer with head/tail pointers, wrap animation
2. **Binary Search Failure**: Animate search going wrong direction after wrap
3. **Rotated Search Success**: Show algorithm identifying sorted half, converging correctly
4. **Range Query Wrap**: Visualize query spanning the wrap point
5. **Concurrent Access**: Show sequence number protecting reads during writes
