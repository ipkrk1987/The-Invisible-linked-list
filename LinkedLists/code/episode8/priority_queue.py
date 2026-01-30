"""
Priority Queue Implementation
Episode 1.8: Task Queue System - Layer 2

Multiple queues for different priority levels with fair scheduling.
"""

from basic_queue import BasicQueue


class PriorityQueue:
    """
    Priority-based task queue with fair scheduling
    
    Maintains separate queues for each priority level.
    Implements weighted round-robin to prevent starvation.
    """
    
    def __init__(self):
        self.high = BasicQueue()
        self.medium = BasicQueue()
        self.low = BasicQueue()
        self.dequeue_counter = 0  # For fair scheduling
    
    def enqueue(self, job, priority="MEDIUM"):
        """
        Add job to appropriate priority queue
        
        Args:
            job: Job to enqueue
            priority: "HIGH", "MEDIUM", or "LOW"
        """
        priority = priority.upper()
        
        if priority == "HIGH":
            self.high.enqueue(job)
        elif priority == "MEDIUM":
            self.medium.enqueue(job)
        elif priority == "LOW":
            self.low.enqueue(job)
        else:
            raise ValueError(f"Invalid priority: {priority}")
    
    def dequeue(self):
        """
        Dequeue using weighted round-robin: 3 high, 2 medium, 1 low
        
        This prevents starvation of low-priority jobs while
        still prioritizing high-priority work.
        
        Returns: Job or None if all queues empty
        """
        # Pattern: H H H M M L (repeats)
        position = self.dequeue_counter % 6
        self.dequeue_counter += 1
        
        if position < 3:  # Positions 0, 1, 2: Try HIGH
            job = self.high.dequeue()
            if job:
                return job
        elif position < 5:  # Positions 3, 4: Try MEDIUM
            job = self.medium.dequeue()
            if job:
                return job
        else:  # Position 5: Try LOW
            job = self.low.dequeue()
            if job:
                return job
        
        # Fallback: Try any available queue
        for queue in [self.high, self.medium, self.low]:
            job = queue.dequeue()
            if job:
                return job
        
        return None  # All queues empty
    
    def dequeue_strict(self):
        """
        Strict priority: Always dequeue highest priority available
        WARNING: Can starve low-priority jobs!
        """
        for queue in [self.high, self.medium, self.low]:
            job = queue.dequeue()
            if job:
                return job
        return None
    
    def is_empty(self):
        """Check if all queues are empty"""
        return (self.high.is_empty() and 
                self.medium.is_empty() and 
                self.low.is_empty())
    
    def size_by_priority(self):
        """Return dict of queue sizes by priority"""
        return {
            "HIGH": len(self.high),
            "MEDIUM": len(self.medium),
            "LOW": len(self.low)
        }
    
    def __repr__(self):
        sizes = self.size_by_priority()
        return f"PriorityQueue(H:{sizes['HIGH']}, M:{sizes['MEDIUM']}, L:{sizes['LOW']})"


# Demo
if __name__ == "__main__":
    import random
    
    print("=== Priority Queue Demo ===")
    pq = PriorityQueue()
    
    # Enqueue mixed priorities
    print("\n1. Enqueuing mixed priority jobs...")
    jobs = [
        ("high_job_1", "HIGH"),
        ("medium_job_1", "MEDIUM"),
        ("low_job_1", "LOW"),
        ("high_job_2", "HIGH"),
        ("medium_job_2", "MEDIUM"),
        ("low_job_2", "LOW"),
        ("high_job_3", "HIGH"),
    ]
    
    for job, priority in jobs:
        pq.enqueue(job, priority)
        print(f"  Enqueued {job:15} [{priority:6}] -> {pq}")
    
    # Dequeue with fair scheduling
    print("\n2. Dequeuing with fair scheduling (3H:2M:1L pattern)...")
    dequeue_order = []
    while not pq.is_empty():
        job = pq.dequeue()
        dequeue_order.append(job)
        print(f"  Dequeued: {job:15} -> {pq}")
    
    print(f"\nDequeue order: {dequeue_order}")
    print("Notice: HIGH jobs prioritized, but MEDIUM/LOW not starved!")
    
    # Compare with strict priority
    print("\n3. Comparing with STRICT priority...")
    pq2 = PriorityQueue()
    for job, priority in jobs:
        pq2.enqueue(job, priority)
    
    strict_order = []
    while not pq2.is_empty():
        job = pq2.dequeue_strict()
        strict_order.append(job)
    
    print(f"Strict order: {strict_order}")
    print("All HIGH jobs first -> can starve LOW jobs!")
    
    # Starvation demonstration
    print("\n4. Starvation Test (continuous HIGH arrivals)...")
    pq3 = PriorityQueue()
    pq3.enqueue("low_job", "LOW")
    
    dequeue_count = 0
    for i in range(20):
        # Keep adding HIGH jobs
        pq3.enqueue(f"high_job_{i}", "HIGH")
        
        # Try to dequeue
        job = pq3.dequeue()
        dequeue_count += 1
        if "low" in job:
            print(f"  LOW job finally dequeued after {dequeue_count} operations!")
            break
    else:
        print(f"  Fair scheduling: LOW job dequeued within {dequeue_count} operations ✅")
    
    # Performance test
    print("\n=== Performance Test ===")
    pq = PriorityQueue()
    n = 50_000
    
    import time
    start = time.time()
    for i in range(n):
        priority = random.choice(["HIGH", "MEDIUM", "LOW"])
        pq.enqueue(f"job_{i}", priority)
    enqueue_time = time.time() - start
    
    start = time.time()
    while not pq.is_empty():
        pq.dequeue()
    dequeue_time = time.time() - start
    
    print(f"Enqueued {n:,} jobs in {enqueue_time:.3f}s ({n/enqueue_time:,.0f} ops/sec)")
    print(f"Dequeued {n:,} jobs in {dequeue_time:.3f}s ({n/dequeue_time:,.0f} ops/sec)")
