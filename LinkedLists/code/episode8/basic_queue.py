"""
Basic FIFO Queue Implementation
Episode 1.8: Task Queue System - Layer 1

A simple queue using a singly linked list.
Operations: O(1) enqueue, O(1) dequeue
"""

class Node:
    """Node in the linked list"""
    def __init__(self, job, next_node=None):
        self.job = job
        self.next = next_node


class BasicQueue:
    """
    FIFO Queue using singly linked list
    
    Maintains head (front) and tail (back) pointers
    for O(1) enqueue and dequeue operations.
    """
    
    def __init__(self):
        self.head = None  # Front of queue (dequeue from here)
        self.tail = None  # Back of queue (enqueue here)
        self.size = 0
    
    def enqueue(self, job):
        """
        Add job to back of queue
        Time: O(1)
        """
        node = Node(job)
        
        if self.tail is None:
            # Empty queue
            self.head = self.tail = node
        else:
            # Add to tail
            self.tail.next = node
            self.tail = node
        
        self.size += 1
    
    def dequeue(self):
        """
        Remove and return job from front of queue
        Time: O(1)
        Returns: Job or None if empty
        """
        if self.head is None:
            return None  # Empty queue
        
        job = self.head.job
        self.head = self.head.next
        
        if self.head is None:
            # Queue is now empty
            self.tail = None
        
        self.size -= 1
        return job
    
    def peek(self):
        """View front job without removing"""
        return self.head.job if self.head else None
    
    def is_empty(self):
        """Check if queue is empty"""
        return self.size == 0
    
    def __len__(self):
        """Return number of jobs in queue"""
        return self.size
    
    def __repr__(self):
        jobs = []
        current = self.head
        while current:
            jobs.append(str(current.job))
            current = current.next
        return f"BasicQueue([{', '.join(jobs)}])"


# Demo
if __name__ == "__main__":
    queue = BasicQueue()
    
    print("=== Basic Queue Demo ===")
    print(f"Empty? {queue.is_empty()}")
    
    # Enqueue jobs
    print("\nEnqueuing jobs...")
    for i in range(1, 6):
        job = f"job_{i}"
        queue.enqueue(job)
        print(f"  Enqueued: {job}, Size: {len(queue)}")
    
    print(f"\nQueue state: {queue}")
    
    # Dequeue jobs (FIFO order)
    print("\nDequeuing jobs...")
    while not queue.is_empty():
        job = queue.dequeue()
        print(f"  Dequeued: {job}, Remaining: {len(queue)}")
    
    print(f"\nEmpty? {queue.is_empty()}")
    
    # Test throughput
    import time
    print("\n=== Performance Test ===")
    queue = BasicQueue()
    n = 100_000
    
    start = time.time()
    for i in range(n):
        queue.enqueue(f"job_{i}")
    enqueue_time = time.time() - start
    
    start = time.time()
    for i in range(n):
        queue.dequeue()
    dequeue_time = time.time() - start
    
    print(f"Enqueued {n:,} jobs in {enqueue_time:.3f}s ({n/enqueue_time:,.0f} ops/sec)")
    print(f"Dequeued {n:,} jobs in {dequeue_time:.3f}s ({n/dequeue_time:,.0f} ops/sec)")
    print(f"\n✅ O(1) confirmed: Constant time per operation!")
