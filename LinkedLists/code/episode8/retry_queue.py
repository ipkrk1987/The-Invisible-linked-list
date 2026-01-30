"""
Episode 1.8 - Layer 5: Retry Queue with Exponential Backoff
Production Implementation of Retry Logic and Dead Letter Queue

Real-world systems like AWS SQS, RabbitMQ, and Kubernetes use exponential backoff
to handle transient failures gracefully. This prevents cascading failures and
allows systems to recover from temporary issues.

Time Complexity:
- schedule_retry(): O(1) - add to retry queue
- move_to_dlq(): O(1) - move to dead letter queue
- get_retryable_tasks(): O(n) - scan all retry tasks

Connection to Earlier Episodes:
- Uses BasicQueue from Layer 1 (Episode 8, Slide 5)
- Builds on priority queue concepts (Episode 8, Slide 7)
"""

import time
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field


@dataclass
class Task:
    """Represents a task in the queue system."""
    id: str
    data: Any
    retry_count: int = 0
    max_retries: int = 3
    next_retry_time: float = 0.0
    created_at: float = field(default_factory=time.time)
    errors: List[str] = field(default_factory=list)
    
    def add_error(self, error: str):
        """Record an error for this task."""
        self.errors.append(f"{time.time():.2f}: {error}")


class Node:
    """Node for linked list implementation."""
    def __init__(self, task: Task):
        self.task = task
        self.next = None


class RetryQueue:
    """
    Production-ready retry queue with exponential backoff.
    
    Features:
    - Exponential backoff: wait time = base_delay * (2 ^ retry_count)
    - Configurable max retries
    - Dead Letter Queue (DLQ) for permanently failed tasks
    - Task tracking with error history
    
    Real-world Pattern:
    - AWS SQS: Visibility timeout with exponential backoff
    - Celery: Retry with countdown
    - Kubernetes: Backoff for failed pod restarts
    """
    
    def __init__(self, base_delay: float = 1.0, max_retries: int = 3):
        self.retry_queue_head = None
        self.retry_queue_tail = None
        self.dlq_head = None  # Dead Letter Queue
        self.dlq_tail = None
        self.base_delay = base_delay
        self.max_retries = max_retries
        self.retry_count = 0
        self.dlq_count = 0
        self.tasks_by_id: Dict[str, Task] = {}
    
    def schedule_retry(self, task: Task, error: str) -> bool:
        """
        Schedule a task for retry with exponential backoff.
        
        Returns True if scheduled for retry, False if moved to DLQ.
        
        Exponential Backoff Formula:
        wait_time = base_delay * (2 ^ retry_count)
        
        Example with base_delay=1.0:
        - Retry 1: wait 1 second  (1 * 2^0)
        - Retry 2: wait 2 seconds (1 * 2^1)
        - Retry 3: wait 4 seconds (1 * 2^2)
        """
        task.add_error(error)
        task.retry_count += 1
        
        if task.retry_count > self.max_retries:
            # Too many retries - move to Dead Letter Queue
            self.move_to_dlq(task)
            return False
        
        # Calculate exponential backoff
        wait_time = self.base_delay * (2 ** (task.retry_count - 1))
        task.next_retry_time = time.time() + wait_time
        
        # Add to retry queue
        node = Node(task)
        if not self.retry_queue_tail:
            self.retry_queue_head = self.retry_queue_tail = node
        else:
            self.retry_queue_tail.next = node
            self.retry_queue_tail = node
        
        self.retry_count += 1
        self.tasks_by_id[task.id] = task
        return True
    
    def move_to_dlq(self, task: Task):
        """
        Move a task to Dead Letter Queue (DLQ).
        
        DLQ is for tasks that have exhausted all retries.
        These need manual investigation or special handling.
        """
        node = Node(task)
        if not self.dlq_tail:
            self.dlq_head = self.dlq_tail = node
        else:
            self.dlq_tail.next = node
            self.dlq_tail = node
        
        self.dlq_count += 1
        print(f"⚠️  Task {task.id} moved to DLQ after {task.retry_count} retries")
    
    def get_retryable_tasks(self) -> List[Task]:
        """
        Get all tasks ready for retry (retry time has passed).
        
        Time Complexity: O(n) where n = tasks in retry queue
        """
        current_time = time.time()
        retryable = []
        
        current = self.retry_queue_head
        while current:
            if current.task.next_retry_time <= current_time:
                retryable.append(current.task)
            current = current.next
        
        return retryable
    
    def remove_from_retry_queue(self, task_id: str) -> Optional[Task]:
        """Remove and return a task from the retry queue."""
        if not self.retry_queue_head:
            return None
        
        # Handle head removal
        if self.retry_queue_head.task.id == task_id:
            task = self.retry_queue_head.task
            self.retry_queue_head = self.retry_queue_head.next
            if not self.retry_queue_head:
                self.retry_queue_tail = None
            self.retry_count -= 1
            return task
        
        # Handle middle/tail removal
        prev = self.retry_queue_head
        current = self.retry_queue_head.next
        
        while current:
            if current.task.id == task_id:
                task = current.task
                prev.next = current.next
                if current == self.retry_queue_tail:
                    self.retry_queue_tail = prev
                self.retry_count -= 1
                return task
            prev = current
            current = current.next
        
        return None
    
    def get_dlq_tasks(self) -> List[Task]:
        """Get all tasks in the Dead Letter Queue."""
        tasks = []
        current = self.dlq_head
        while current:
            tasks.append(current.task)
            current = current.next
        return tasks
    
    def stats(self) -> Dict[str, Any]:
        """Get retry queue statistics."""
        return {
            "retry_queue_size": self.retry_count,
            "dlq_size": self.dlq_count,
            "base_delay": self.base_delay,
            "max_retries": self.max_retries,
        }


def demo_retry_logic():
    """Demonstrate retry queue with exponential backoff."""
    print("=== Retry Queue Demo ===\n")
    
    retry_queue = RetryQueue(base_delay=0.5, max_retries=3)
    
    # Create a task that will fail multiple times
    task1 = Task(id="task_1", data="Process payment")
    
    print("Simulating task failures with exponential backoff:\n")
    
    # Failure 1
    success = retry_queue.schedule_retry(task1, "Connection timeout")
    print(f"Retry 1: Scheduled={success}, Wait={0.5 * (2**0)}s, Next retry at {task1.next_retry_time:.2f}")
    
    # Simulate time passing
    time.sleep(0.6)
    
    # Failure 2
    success = retry_queue.schedule_retry(task1, "Database locked")
    print(f"Retry 2: Scheduled={success}, Wait={0.5 * (2**1)}s, Next retry at {task1.next_retry_time:.2f}")
    
    # Simulate time passing
    time.sleep(1.1)
    
    # Failure 3
    success = retry_queue.schedule_retry(task1, "Service unavailable")
    print(f"Retry 3: Scheduled={success}, Wait={0.5 * (2**2)}s, Next retry at {task1.next_retry_time:.2f}")
    
    # Simulate time passing
    time.sleep(2.1)
    
    # Failure 4 - exceeds max retries
    success = retry_queue.schedule_retry(task1, "Permanent failure")
    print(f"Retry 4: Scheduled={success} (moved to DLQ)")
    
    print(f"\nFinal Stats: {retry_queue.stats()}")
    print(f"\nError History for {task1.id}:")
    for error in task1.errors:
        print(f"  - {error}")
    
    # Show DLQ contents
    dlq_tasks = retry_queue.get_dlq_tasks()
    print(f"\nDead Letter Queue ({len(dlq_tasks)} tasks):")
    for task in dlq_tasks:
        print(f"  - {task.id}: {task.data} (failed {task.retry_count} times)")


if __name__ == "__main__":
    demo_retry_logic()
