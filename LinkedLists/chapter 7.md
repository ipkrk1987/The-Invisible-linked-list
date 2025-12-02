Perfect! Episode 7 as the season finale focusing on ring buffers and streaming is absolutely the right move. Let's build it:

---

SEASON: 1 — The Invisible Linked List

EPISODE: 7 (Season Finale)

TITLE: When Data Never Stops: Ring Buffers, Logs, and Real-Time Systems

(0:00 - The Problem That Never Ends)

[Visual: Streaming data - stock tickers, video frames, log entries, network packets]

Narration: "We've mastered storing data (linked lists), finding intersections (merge-base), navigating history (browser), and caching (LRU). But what happens when data never stops arriving? When you're processing stock trades at 100,000/sec, video frames at 60fps, or logs from 10,000 servers?"

```python
class InfiniteStreamProblem:
    """The challenge of never-ending data."""
    
    def __init__(self):
        self.data_rates = {
            'stock_tickers': 100_000,  # trades/second
            'video_stream': 60,        # frames/second (4K: 8MB/frame!)
            'server_logs': 10_000,     # log lines/second
            'network_packets': 1_000_000,  # packets/second
        }
        
        # The problem: Infinite data, finite memory
        # Can't store everything
        # Can't stop to process
        # Must keep up in real-time
        
# Previous episodes gave us tools:
# Episode 1: Store linear history (Git)
# Episode 2: Find intersections in history
# Episode 3: Navigate history (back/forward)
# Episode 4: Travel through time (undo/redo)
# Episode 5: Decide what to keep (LRU)
# Episode 6: Distribute across systems

# Now: Handle infinite streams with finite buffers
```

(2:00 - The Data Structure: Ring Buffer / Circular Queue)

Narration: "The solution is deceptively simple: a ring buffer (circular queue). A fixed-size array that wraps around, overwriting old data. Let's build it from scratch:"

```python
class RingBuffer:
    """Fixed-size circular buffer - the foundation of streaming."""
    
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        
        self.capacity = capacity
        self.buffer = [None] * capacity
        self.head = 0  # Next write position
        self.tail = 0  # Next read position
        self.size = 0  # Current number of elements
        self.total_written = 0  # Total elements ever written
    
    def push(self, item) -> bool:
        """Add item, return True if successful, False if full."""
        if self.size == self.capacity:
            return False  # Buffer full (could also overwrite)
        
        self.buffer[self.head] = item
        self.head = (self.head + 1) % self.capacity
        self.size += 1
        self.total_written += 1
        
        return True
    
    def pop(self):
        """Remove and return oldest item, or None if empty."""
        if self.size == 0:
            return None
        
        item = self.buffer[self.tail]
        self.buffer[self.tail] = None  # Clear reference
        self.tail = (self.tail + 1) % self.capacity
        self.size -= 1
        
        return item
    
    def peek(self):
        """Return oldest item without removing it."""
        if self.size == 0:
            return None
        return self.buffer[self.tail]
    
    def is_empty(self) -> bool:
        return self.size == 0
    
    def is_full(self) -> bool:
        return self.size == self.capacity
    
    def clear(self):
        """Clear buffer."""
        for i in range(self.capacity):
            self.buffer[i] = None
        self.head = 0
        self.tail = 0
        self.size = 0
    
    def __iter__(self):
        """Iterate from oldest to newest."""
        for i in range(self.size):
            idx = (self.tail + i) % self.capacity
            yield self.buffer[idx]
    
    def __repr__(self):
        items = list(self)
        return f"RingBuffer(capacity={self.capacity}, size={self.size}, items={items})"

# Visual example:
# Buffer: [A, B, C, D, E]  capacity=5
# After push(F) when full:
# Option 1: Reject F (maintains all history)
# Option 2: Overwrite A (keeps most recent)

# The invisible invariants:
# 1. 0 ≤ size ≤ capacity
# 2. head points to next write
# 3. tail points to next read
# 4. When head == tail: either empty or full (use size to distinguish)
```

(5:00 - The Overwrite Variant: When Old Data Must Die)

Narration: "For streaming systems, we often want to overwrite old data when full. This creates a 'sliding window' of the most recent data:"

```python
class OverwritingRingBuffer(RingBuffer):
    """Ring buffer that overwrites oldest data when full."""
    
    def push(self, item) -> bool:
        """Always succeeds, overwriting if necessary."""
        if self.size == self.capacity:
            # Buffer full - overwrite oldest
            self.buffer[self.head] = item
            self.head = (self.head + 1) % self.capacity
            self.tail = (self.tail + 1) % self.capacity  # Move tail too
            # size stays the same
        else:
            # Normal push
            self.buffer[self.head] = item
            self.head = (self.head + 1) % self.capacity
            self.size += 1
        
        self.total_written += 1
        return True
    
    def get_recent(self, n: int):
        """Get N most recent items (newest first)."""
        if n <= 0:
            return []
        
        n = min(n, self.size)
        result = []
        
        # Start from most recent (head-1) and go backwards
        for i in range(n):
            idx = (self.head - 1 - i) % self.capacity
            result.append(self.buffer[idx])
        
        return result
    
    def get_window(self, start_index: int, length: int):
        """Get items by their 'global' index (total_written-based)."""
        # Useful for time-series: "Get data from timestamp X to Y"
        result = []
        
        for i in range(length):
            global_idx = start_index + i
            if global_idx < self.total_written - self.size:
                # Too old - already overwritten
                result.append(None)
            elif global_idx >= self.total_written:
                # Future - doesn't exist yet
                break
            else:
                # Map global index to buffer position
                buffer_idx = global_idx % self.capacity
                result.append(self.buffer[buffer_idx])
        
        return result

# Use cases:
# 1. Real-time metrics: Keep last 5 minutes of data
# 2. Audio processing: Fixed-size sample buffer
# 3. Game state: Recent positions for lag compensation
# 4. Logging: Last N log entries for debugging
```

(8:00 - Producer-Consumer: The Classic Concurrency Pattern)

Narration: "Ring buffers shine in concurrent systems. One thread produces data, another consumes it. This is the producer-consumer pattern, and ring buffers solve it elegantly with backpressure:"

```python
import threading
import time
from collections import deque

class BoundedBlockingQueue:
    """Thread-safe bounded queue using condition variables."""
    
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        
        self.capacity = capacity
        self.queue = deque()  # Using deque for efficiency
        self.lock = threading.Lock()
        self.not_empty = threading.Condition(self.lock)  # Wait when empty
        self.not_full = threading.Condition(self.lock)   # Wait when full
        
        # Statistics
        self.operations = 0
        self.waits = 0
    
    def put(self, item, block=True, timeout=None):
        """Add item, blocking if full."""
        with self.not_full:
            if not block and len(self.queue) == self.capacity:
                raise Full("Queue is full")
            
            # Wait for space if needed
            while len(self.queue) == self.capacity:
                self.waits += 1
                if not self.not_full.wait(timeout=timeout):
                    raise Full("Queue is full")
            
            # Add item
            self.queue.append(item)
            self.operations += 1
            
            # Notify waiting consumers
            self.not_empty.notify()
        
        return True
    
    def get(self, block=True, timeout=None):
        """Remove and return item, blocking if empty."""
        with self.not_empty:
            if not block and not self.queue:
                raise Empty("Queue is empty")
            
            # Wait for data if needed
            while not self.queue:
                self.waits += 1
                if not self.not_empty.wait(timeout=timeout):
                    raise Empty("Queue is empty")
            
            # Get item
            item = self.queue.popleft()
            self.operations += 1
            
            # Notify waiting producers
            self.not_full.notify()
            
            return item
    
    def qsize(self):
        with self.lock:
            return len(self.queue)
    
    def empty(self):
        with self.lock:
            return len(self.queue) == 0
    
    def full(self):
        with self.lock:
            return len(self.queue) == self.capacity

class ProducerConsumerSystem:
    """Complete producer-consumer system with ring buffer."""
    
    def __init__(self, buffer_capacity=1000):
        self.buffer = BoundedBlockingQueue(buffer_capacity)
        self.producers = []
        self.consumers = []
        self.running = False
        
        # Monitoring
        self.produced_count = 0
        self.consumed_count = 0
        self.backpressure_events = 0
    
    def start(self, num_producers=2, num_consumers=3):
        """Start producers and consumers."""
        self.running = True
        
        # Create producers
        for i in range(num_producers):
            producer = threading.Thread(
                target=self._producer_worker,
                args=(f"Producer-{i}",),
                daemon=True
            )
            self.producers.append(producer)
            producer.start()
        
        # Create consumers
        for i in range(num_consumers):
            consumer = threading.Thread(
                target=self._consumer_worker,
                args=(f"Consumer-{i}",),
                daemon=True
            )
            self.consumers.append(consumer)
            consumer.start()
    
    def _producer_worker(self, name):
        """Producer: generates data and pushes to buffer."""
        item_id = 0
        
        while self.running:
            # Generate data
            item = {
                'id': item_id,
                'producer': name,
                'timestamp': time.time(),
                'data': f"Item {item_id} from {name}"
            }
            item_id += 1
            
            # Try to put with timeout (simulating backpressure)
            try:
                self.buffer.put(item, timeout=0.1)  # 100ms timeout
                self.produced_count += 1
            except Full:
                # Buffer full - backpressure!
                self.backpressure_events += 1
                # Options:
                # 1. Wait and retry (what we're doing)
                # 2. Drop item
                # 3. Scale up consumers
                time.sleep(0.01)  # Small backoff
            
            time.sleep(0.001)  # Simulate work
    
    def _consumer_worker(self, name):
        """Consumer: processes data from buffer."""
        while self.running:
            try:
                item = self.buffer.get(timeout=1.0)
                self.consumed_count += 1
                
                # Process item
                self._process_item(item, name)
                
            except Empty:
                # No data - could be idle or system stopping
                continue
    
    def _process_item(self, item, consumer_name):
        """Simulate processing."""
        # Real processing would go here
        # Simulate variable processing time
        import random
        time.sleep(random.uniform(0.001, 0.01))
        
        # Log completion
        latency = time.time() - item['timestamp']
        if latency > 0.1:  # 100ms threshold
            print(f"High latency: {latency:.3f}s for item {item['id']}")

# This pattern appears everywhere:
# 1. Web servers: Request queues
# 2. Databases: Connection pools  
# 3. Log processors: Batched writes
# 4. Video encoding: Frame buffers
# 5. Trading systems: Order matching
```

(12:00 - Real System #1: Logging & Metrics Buffers)

Narration: "Let's see our first production application: logging and metrics. Systems generate millions of log lines per second. We can't write each to disk immediately - we buffer them:"

```python
class LogBufferSystem:
    """In-memory log buffer with batch writing."""
    
    def __init__(self, buffer_capacity=10000, flush_threshold=1000, flush_interval=5.0):
        self.buffer = OverwritingRingBuffer(buffer_capacity)
        self.flush_threshold = flush_threshold
        self.flush_interval = flush_interval
        self.last_flush = time.time()
        
        # Batch storage for efficiency
        self.batch = []
        self.batch_lock = threading.Lock()
        
        # Statistics
        self.logs_received = 0
        self.logs_written = 0
        self.batches_written = 0
        self.logs_dropped = 0
        
        # Start flusher thread
        self.flusher = threading.Thread(target=self._flusher_worker, daemon=True)
        self.running = True
        self.flusher.start()
    
    def log(self, level: str, message: str, **kwargs):
        """Add log entry to buffer."""
        log_entry = {
            'timestamp': time.time(),
            'level': level,
            'message': message,
            **kwargs
        }
        
        # Try to add to buffer
        if self.buffer.push(log_entry):
            self.logs_received += 1
            
            # Add to batch
            with self.batch_lock:
                self.batch.append(log_entry)
                
                # Check if we should flush
                if len(self.batch) >= self.flush_threshold:
                    self._flush_batch()
        else:
            # Buffer full - log dropped
            self.logs_dropped += 1
    
    def _flusher_worker(self):
        """Background thread that flushes periodically."""
        while self.running:
            time.sleep(0.1)  # Check frequently
            
            current_time = time.time()
            
            # Time-based flush
            if current_time - self.last_flush >= self.flush_interval:
                self._flush_batch()
    
    def _flush_batch(self):
        """Flush current batch to disk/network."""
        if not self.batch:
            return
        
        with self.batch_lock:
            batch_to_write = self.batch
            self.batch = []
        
        if not batch_to_write:
            return
        
        try:
            # Write batch (simulated)
            self._write_to_destination(batch_to_write)
            
            self.logs_written += len(batch_to_write)
            self.batches_written += 1
            self.last_flush = time.time()
            
        except Exception as e:
            # Write failed - put back in buffer (simplified)
            print(f"Write failed: {e}")
            # In reality: retry, dead letter queue, etc.
    
    def _write_to_destination(self, batch):
        """Simulate writing to disk/network."""
        # Real implementation would:
        # 1. Write to file
        # 2. Send to log aggregator (ELK, Splunk)
        # 3. Write to database
        
        # Simulate I/O
        import random
        time.sleep(random.uniform(0.001, 0.01) * len(batch))
    
    def get_recent_logs(self, count=100):
        """Get most recent logs for debugging."""
        return self.buffer.get_recent(count)
    
    def shutdown(self):
        """Graceful shutdown - flush remaining logs."""
        self.running = False
        self.flusher.join(timeout=2.0)
        self._flush_batch()  # Final flush

class MetricsBuffer:
    """Ring buffer for time-series metrics."""
    
    def __init__(self, window_seconds=300, resolution_ms=1000):
        # Store 5 minutes of data at 1-second resolution
        self.window_size = window_seconds * 1000 // resolution_ms
        self.resolution_ms = resolution_ms
        
        # Circular buffers for different metrics
        self.timestamps = OverwritingRingBuffer(self.window_size)
        self.values = {}  # metric_name -> OverwritingRingBuffer
        
        # Aggregation
        self.current_bucket = {}
        self.bucket_start = self._current_bucket_time()
    
    def record(self, metric_name: str, value: float):
        """Record a metric value."""
        current_time = time.time() * 1000  # ms
        bucket_time = self._current_bucket_time()
        
        # Check if we need to flush current bucket
        if bucket_time != self.bucket_start:
            self._flush_bucket()
            self.bucket_start = bucket_time
        
        # Aggregate in current bucket
        if metric_name not in self.current_bucket:
            self.current_bucket[metric_name] = {
                'sum': 0.0,
                'count': 0,
                'min': float('inf'),
                'max': -float('inf')
            }
        
        stats = self.current_bucket[metric_name]
        stats['sum'] += value
        stats['count'] += 1
        stats['min'] = min(stats['min'], value)
        stats['max'] = max(stats['max'], value)
    
    def _flush_bucket(self):
        """Flush aggregated bucket to ring buffers."""
        if not self.current_bucket:
            return
        
        timestamp = self.bucket_start
        
        # Store timestamp
        self.timestamps.push(timestamp)
        
        # Store each metric
        for metric_name, stats in self.current_bucket.items():
            if metric_name not in self.values:
                self.values[metric_name] = OverwritingRingBuffer(self.window_size)
            
            # Store average for this bucket
            avg = stats['sum'] / stats['count']
            self.values[metric_name].push(avg)
        
        # Clear bucket
        self.current_bucket = {}
    
    def get_time_series(self, metric_name, start_time=None, end_time=None):
        """Get time series data for a metric."""
        if metric_name not in self.values:
            return []
        
        # Find indices in buffer
        # (Simplified - real implementation would handle time boundaries)
        timestamps = list(self.timestamps)
        values = list(self.values[metric_name])
        
        # Both should be same length
        result = list(zip(timestamps, values))
        
        # Filter by time range if specified
        if start_time is not None:
            result = [(t, v) for t, v in result if t >= start_time]
        if end_time is not None:
            result = [(t, v) for t, v in result if t <= end_time]
        
        return result
    
    def _current_bucket_time(self):
        """Get current bucket timestamp."""
        current_ms = int(time.time() * 1000)
        return current_ms - (current_ms % self.resolution_ms)

# Used in:
# 1. Application logging (Python logging, Log4j)
# 2. Metrics collection (Prometheus, StatsD)
# 3. APM (Application Performance Monitoring)
# 4. Business metrics dashboards
```

(16:00 - Real System #2: Audio/Video Streaming Buffers)

Narration: "Now let's look at real-time media. Video players, voice chat, live streaming - all use ring buffers to smooth out variable network latency:"

```python
class MediaBuffer:
    """Buffer for audio/video streaming with jitter compensation."""
    
    def __init__(self, buffer_ms=200, max_buffer_ms=1000):
        # Buffer size in milliseconds
        self.target_buffer_ms = buffer_ms
        self.max_buffer_ms = max_buffer_ms
        
        # Ring buffer for frames/packets
        self.buffer = RingBuffer(capacity=1000)  # Enough for worst case
        
        # Timing information
        self.frame_times = {}  # frame_id -> (arrival_time, decode_time)
        self.next_frame_id = 0
        self.next_output_id = 0
        
        # Statistics for adaptive buffering
        self.network_jitter_ms = 0
        self.late_frames = 0
        self.dropped_frames = 0
        
        # Clock drift compensation
        self.clock_offset = 0
        self.clock_drift = 1.0  # 1.0 = perfect clock
    
    def receive_packet(self, packet):
        """Receive network packet containing media data."""
        frame_id = packet['frame_id']
        timestamp = packet['timestamp']  # Sender's clock
        data = packet['data']
        
        # Calculate network jitter
        arrival_time = time.time()
        network_delay = arrival_time - (timestamp + self.clock_offset)
        
        # Update jitter estimate (simplified)
        self.network_jitter_ms = 0.9 * self.network_jitter_ms + 0.1 * network_delay
        
        # Store frame
        if not self.buffer.push({
            'frame_id': frame_id,
            'data': data,
            'timestamp': timestamp,
            'arrival_time': arrival_time
        }):
            # Buffer full - need to drop something
            self._handle_buffer_full()
        
        # Update next expected frame
        self.next_frame_id = max(self.next_frame_id, frame_id + 1)
    
    def get_next_frame(self, current_time):
        """Get next frame to render/play."""
        if self.buffer.is_empty():
            return None  # Buffer underflow
        
        # Check if we should output next frame
        peek = self.buffer.peek()
        frame_id = peek['frame_id']
        
        # Calculate when this frame should be displayed
        # Based on sender timestamp + our buffer delay
        display_time = peek['timestamp'] + self.clock_offset + (self.target_buffer_ms / 1000.0)
        
        if current_time >= display_time or frame_id < self.next_output_id:
            # Time to display this frame (or it's old)
            frame = self.buffer.pop()
            self.next_output_id = frame_id + 1
            
            # Check if frame is late
            if current_time > display_time:
                self.late_frames += 1
                # Could skip frame or play catch-up
            
            return frame['data']
        
        # Not time yet
        return None
    
    def _handle_buffer_full(self):
        """Handle buffer full condition."""
        # Options:
        # 1. Increase buffer size (temporarily)
        # 2. Drop oldest frames
        # 3. Drop newest frames
        # 4. Request lower quality
        
        # For now: drop oldest
        dropped = self.buffer.pop()
        self.dropped_frames += 1
        
        # Log for debugging
        print(f"Buffer full, dropped frame {dropped['frame_id']}")
    
    def adjust_buffer_size(self, network_conditions):
        """Adaptively adjust buffer size based on network."""
        if network_conditions['jitter_ms'] > 50:
            # High jitter - increase buffer
            self.target_buffer_ms = min(
                self.max_buffer_ms,
                self.target_buffer_ms * 1.2
            )
        elif network_conditions['jitter_ms'] < 10:
            # Low jitter - decrease buffer for lower latency
            self.target_buffer_ms = max(
                50,  # Minimum 50ms
                self.target_buffer_ms * 0.9
            )

class VideoPlayerBuffer:
    """Simplified video player buffer."""
    
    def __init__(self):
        # Triple buffering for smooth playback
        self.buffers = [
            MediaBuffer(buffer_ms=100),  # Decode buffer
            MediaBuffer(buffer_ms=50),   # Render buffer  
            MediaBuffer(buffer_ms=150),  # Network buffer
        ]
        
        # Frame states
        self.frames = {
            'decoding': None,
            'rendering': None,
            'next': None
        }
        
        # Timing
        self.frame_rate = 60  # fps
        self.frame_interval = 1.0 / self.frame_rate
        
    def decode_worker(self):
        """Decoder thread: reads from network, decodes frames."""
        while True:
            # Get from network buffer
            packet = self._get_network_packet()
            if packet:
                self.buffers[0].receive_packet(packet)
            
            # Decode if buffer has data
            if not self.buffers[0].buffer.is_empty():
                frame = self._decode_frame()
                self.buffers[1].receive_packet({
                    'frame_id': frame['id'],
                    'data': frame['data'],
                    'timestamp': frame['timestamp']
                })
    
    def render_worker(self):
        """Renderer thread: displays frames at correct time."""
        next_frame_time = time.time()
        
        while True:
            current_time = time.time()
            
            # Get frame to render
            frame_data = self.buffers[1].get_next_frame(current_time)
            
            if frame_data:
                # Render frame
                self._render_frame(frame_data)
                next_frame_time += self.frame_interval
            else:
                # No frame ready - repeat last frame or show blank
                pass
            
            # Sleep until next frame time
            sleep_time = next_frame_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

# Used in:
# 1. Video players (YouTube, Netflix)
# 2. Video conferencing (Zoom, Teams)
# 3. Live streaming (Twitch)
# 4. Game streaming (Stadia, GeForce Now)
# 5. VoIP (Voice over IP)
```

(19:00 - From Ring Buffers to Distributed Logs: Kafka-Style Systems)

Narration: "Now let's scale up. A single machine's ring buffer becomes a distributed log in systems like Kafka. The concept is the same: append-only, bounded retention, multiple consumers:"

```python
class DistributedLogPartition:
    """Single partition of a distributed log (Kafka-style)."""
    
    def __init__(self, partition_id, max_segments=10, segment_size=1000000):
        self.partition_id = partition_id
        self.max_segments = max_segments
        self.segment_size = segment_size
        
        # Segments are like larger ring buffer chunks
        self.segments = []  # List of segment files
        self.current_segment = None
        self.current_offset = 0  # Next write offset
        
        # Consumer offsets
        self.consumer_offsets = {}  # consumer_group -> offset
        
        # Retention policy
        self.retention_hours = 168  # 7 days
        self.retention_bytes = 10 * 1024**3  # 10GB
        
        # Start new segment
        self._rotate_segment()
    
    def append(self, key, value, headers=None):
        """Append message to log."""
        message = {
            'offset': self.current_offset,
            'timestamp': time.time(),
            'key': key,
            'value': value,
            'headers': headers or {}
        }
        
        # Write to current segment
        self.current_segment.write(message)
        
        # Update offset
        self.current_offset += 1
        
        # Rotate segment if full
        if self.current_segment.size >= self.segment_size:
            self._rotate_segment()
        
        return self.current_offset - 1  # Return offset of written message
    
    def read(self, consumer_group, batch_size=100, timeout_ms=100):
        """Read messages for consumer group."""
        # Get consumer's current offset
        start_offset = self.consumer_offsets.get(consumer_group, 0)
        
        # Find which segment contains this offset
        segment, segment_offset = self._find_segment_for_offset(start_offset)
        
        if not segment:
            return []  # Offset too old (data deleted)
        
        # Read from segment
        messages = segment.read_from(segment_offset, batch_size)
        
        if messages:
            # Update consumer offset
            last_offset = messages[-1]['offset']
            self.consumer_offsets[consumer_group] = last_offset + 1
        
        return messages
    
    def _rotate_segment(self):
        """Create new segment, archive old if needed."""
        # Close current segment if exists
        if self.current_segment:
            self.current_segment.close()
            self.segments.append(self.current_segment)
        
        # Create new segment
        self.current_segment = LogSegment(
            base_offset=self.current_offset,
            max_size=self.segment_size
        )
        
        # Enforce retention
        self._enforce_retention()
    
    def _enforce_retention(self):
        """Delete old segments based on retention policy."""
        current_time = time.time()
        
        # Time-based retention
        while self.segments:
            oldest = self.segments[0]
            if current_time - oldest.created_at > self.retention_hours * 3600:
                # Delete segment
                oldest.delete()
                self.segments.pop(0)
            else:
                break
        
        # Size-based retention
        total_size = sum(s.size for s in self.segments)
        while total_size > self.retention_bytes and self.segments:
            oldest = self.segments[0]
            total_size -= oldest.size
            oldest.delete()
            self.segments.pop(0)

class LogSegment:
    """A segment of the log (like a ring buffer chunk)."""
    
    def __init__(self, base_offset, max_size):
        self.base_offset = base_offset
        self.max_size = max_size
        self.size = 0
        self.created_at = time.time()
        
        # In production: memory-mapped file
        self.messages = []
    
    def write(self, message):
        """Write message to segment."""
        self.messages.append(message)
        self.size += len(str(message))
    
    def read_from(self, offset, limit):
        """Read messages starting from offset within segment."""
        if offset < self.base_offset:
            return []  # Offset before this segment
        
        start_idx = offset - self.base_offset
        if start_idx >= len(self.messages):
            return []  # Offset beyond this segment
        
        return self.messages[start_idx:start_idx + limit]
    
    def close(self):
        """Close segment (flush to disk)."""
        # In production: fsync, create index file
        pass
    
    def delete(self):
        """Delete segment files."""
        # In production: delete .log and .index files
        pass

class DistributedLogSystem:
    """Complete distributed log system (Kafka-like)."""
    
    def __init__(self, num_partitions=3, replication_factor=2):
        self.partitions = [
            DistributedLogPartition(i) 
            for i in range(num_partitions)
        ]
        
        self.replication_factor = replication_factor
        
        # Partition assignment
        self.partitioner = HashPartitioner()
        
        # Replication
        self.replicas = []  # List of replica nodes
        self.leader_for_partition = {}  # partition -> leader_node
        
        # Consumer groups
        self.consumer_groups = {}
    
    def produce(self, topic, key, value):
        """Produce message to topic."""
        # Choose partition
        partition_id = self.partitioner.partition(key, len(self.partitions))
        
        # Append to partition
        offset = self.partitions[partition_id].append(key, value)
        
        # Replicate to followers (async)
        self._replicate_message(partition_id, offset, key, value)
        
        return {'partition': partition_id, 'offset': offset}
    
    def consume(self, topic, consumer_group, batch_size=100):
        """Consume messages from topic."""
        # Get partitions assigned to this consumer
        assigned_partitions = self._get_assigned_partitions(
            consumer_group, topic
        )
        
        messages = []
        
        for partition_id in assigned_partitions:
            partition_messages = self.partitions[partition_id].read(
                consumer_group, batch_size
            )
            messages.extend(partition_messages)
        
        # Sort by timestamp (for cross-partition ordering)
        messages.sort(key=lambda m: m['timestamp'])
        
        return messages[:batch_size]

# Key concepts from Kafka:
# 1. Partitions = sharded ring buffers
# 2. Offsets = positions in the ring
# 3. Consumer groups = independent read positions
# 4. Retention = automatic cleanup of old data
# 5. Replication = fault tolerance
```

(22:00 - Backpressure Strategies & Failure Modes)

Narration: "When data arrives faster than we can process it, we need backpressure strategies. Different systems make different tradeoffs:"

```python
class BackpressureStrategies:
    """Different strategies for handling overload."""
    
    @staticmethod
    def blocking_backpressure(buffer, item):
        """Block producer until space available."""
        # Used in: Database connections, thread pools
        # Pros: No data loss
        # Cons: Can cause cascading failures
        
        while buffer.is_full():
            time.sleep(0.001)  # Busy wait (in reality: condition variable)
        
        buffer.push(item)
        return True
    
    @staticmethod
    def drop_oldest(buffer, item):
        """Drop oldest item when buffer full."""
        # Used in: Metrics, logs, real-time analytics
        # Pros: Keeps most recent data, bounded memory
        # Cons: Data loss
        
        if buffer.is_full():
            buffer.pop()  # Drop oldest
        
        buffer.push(item)
        return True
    
    @staticmethod  
    def drop_newest(buffer, item):
        """Reject new items when buffer full."""
        # Used in: Order processing, financial transactions
        # Pros: Preserves in-flight data
        # Cons: New data lost
        
        if buffer.is_full():
            return False  # Reject
        
        buffer.push(item)
        return True
    
    @staticmethod
    def sampling(buffer, item, sample_rate=0.1):
        """Randomly sample items (keep only N%)."""
        # Used in: High-volume metrics, debugging
        # Pros: Statistical representation, bounded load
        # Cons: Missing individual events
        
        import random
        if random.random() > sample_rate:
            return False  # Skip this item
        
        if buffer.is_full():
            buffer.pop()  # Make space
        
        buffer.push(item)
        return True
    
    @staticmethod
    def dynamic_scaling(buffer, item, scaling_threshold=0.8):
        """Dynamically increase buffer size."""
        # Used in: Cloud systems with elastic resources
        # Pros: Adapts to load
        # Cons: Can mask underlying problems
        
        if buffer.size / buffer.capacity > scaling_threshold:
            # Increase capacity
            buffer.capacity = int(buffer.capacity * 1.5)
            # In reality: Add more servers, increase memory
            
        return buffer.push(item)

class AdaptiveBufferSystem:
    """Buffer system that adapts strategy based on conditions."""
    
    def __init__(self, initial_capacity=1000):
        self.buffer = RingBuffer(initial_capacity)
        self.strategy = 'blocking'  # Default
        
        # Monitor conditions
        self.producer_rate = 0  # items/second
        self.consumer_rate = 0  # items/second
        self.latency_p99 = 0  # 99th percentile latency
        
        # Adaptation rules
        self.rules = [
            (lambda: self.latency_p99 > 1.0, 'drop_oldest'),  # High latency
            (lambda: self.producer_rate > self.consumer_rate * 2, 'sampling'),  # Overload
            (lambda: self.buffer.size / self.buffer.capacity > 0.9, 'dynamic_scaling'),  # Full
        ]
    
    def push(self, item):
        """Push with adaptive strategy."""
        # Choose strategy based on current conditions
        self._adapt_strategy()
        
        # Apply strategy
        if self.strategy == 'blocking':
            return BackpressureStrategies.blocking_backpressure(self.buffer, item)
        elif self.strategy == 'drop_oldest':
            return BackpressureStrategies.drop_oldest(self.buffer, item)
        elif self.strategy == 'drop_newest':
            return BackpressureStrategies.drop_newest(self.buffer, item)
        elif self.strategy == 'sampling':
            return BackpressureStrategies.sampling(self.buffer, item, 0.1)
        elif self.strategy == 'dynamic_scaling':
            return BackpressureStrategies.dynamic_scaling(self.buffer, item)
        
        return False
    
    def _adapt_strategy(self):
        """Adapt strategy based on current conditions."""
        for condition, new_strategy in self.rules:
            if condition():
                if self.strategy != new_strategy:
                    print(f"Switching strategy from {self.strategy} to {new_strategy}")
                    self.strategy = new_strategy
                break

# Failure modes to watch for:
# 1. Buffer bloat: Memory exhaustion
# 2. Producer slow-down: Cascading backpressure  
# 3. Consumer lag: Falling behind permanently
# 4. Head-of-line blocking: One slow item blocks all
# 5. Clock drift: Time-based systems get out of sync
```

(24:00 - Season Finale: The Invisible Linked List Complete)

[Visual: Complete Season 1 journey]

Narration: "Let's look back at our complete journey through The Invisible Linked List:"

```
EPISODE 1: SINGLY LINKED LISTS
  Problem: How to store history?
  Solution: Commit chains in Git
  Key insight: Time as a linear sequence

EPISODE 2: LIST INTERSECTION  
  Problem: Where do histories meet?
  Solution: Git merge-base
  Key insight: Finding convergence in timelines

EPISODE 3: DOUBLY LINKED LISTS
  Problem: How to navigate history?
  Solution: Browser back/forward
  Key insight: Bidirectional time travel

EPISODE 4: IMMUTABLE STRUCTURES
  Problem: How to rewind time?
  Solution: Redux, undo/redo systems
  Key insight: Preserving history through copies

EPISODE 5: LRU CACHE
  Problem: What history to keep?
  Solution: Browser caches, Redis eviction
  Key insight: Recent predicts future

EPISODE 6: DISTRIBUTED CACHING
  Problem: Where to keep history at scale?
  Solution: CDNs, distributed caches
  Key insight: Geographic distribution of time

EPISODE 7: RING BUFFERS
  Problem: How to handle infinite time?
  Solution: Streaming systems, logs
  Key insight: Bounded windows on infinite streams
```

The Big Picture: Time as a Data Structure

Narration: "Every system we built deals with time:"

```python
# The universal pattern:
class TimeOrientedSystem:
    """All systems manage time-oriented data."""
    
    def __init__(self):
        # 1. Store time (linked lists, arrays)
        self.history = []
        
        # 2. Navigate time (forward/backward pointers)
        self.current_position = 0
        
        # 3. Select what to keep (eviction policies)
        self.retention_policy = 'recent'
        
        # 4. Distribute across space (servers, locations)
        self.distribution = 'centralized'
        
        # 5. Handle infinite streams (bounded buffers)
        self.buffer_capacity = 1000

# Whether it's:
# - Git commits (linked list)
# - Browser history (doubly linked list)
# - Cache entries (LRU)
# - Log entries (ring buffer)
# The pattern is the same: managing sequences over time
```

Key Engineering Principles from Season 1:

1. Choose the right time representation (list vs ring vs DAG)
2. Balance memory vs completeness (LRU vs keep-all)
3. Design for navigation (forward/backward, random access)
4. Plan for distribution (single machine → global)
5. Handle infinity gracefully (streaming, bounded buffers)

(25:00 - Season 2 Teaser: Trees, Graphs, and Beyond)

[Visual: Tree structures, graph networks, search indices]

Narration: "We've mastered linear time. But real systems are multi-dimensional. Relationships form trees (file systems, HTML DOM), graphs (social networks, recommendations), and complex indices (search engines, databases)."


Final Message: "Remember: Data structures aren't abstract concepts. They're the invisible foundations of every digital system you use. Master them, and you don't just pass interviews - you build better systems."

---

SEASON 1 COMPLETE 🎬

The Invisible Linked List: From LeetCode to Production

1. Episode 1: Singly Linked Lists → Git Commit History
2. Episode 2: List Intersection → Git Merge-Base
3. Episode 3: Doubly Linked Lists → Browser History
4. Episode 4: Immutable Structures → Time Travel & Undo/Redo
5. Episode 5: LRU Cache → Browser & Database Caching
6. Episode 6: Distributed Caching → CDNs & Global Systems
7. Episode 7: Ring Buffers → Streaming & Real-Time Systems
