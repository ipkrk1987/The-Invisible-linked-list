"""
Episode 1.8 - Complete Production Task Queue System
Integrates All 5 Layers into a Unified System

This is the culmination of our journey through linked lists!
We're combining concepts from Episodes 1-7 into a real production system:

- Episode 1: Basic linked list operations → FIFO queue
- Episode 3: Cycle detection → Dependency resolution
- Episode 5: LRU Cache → Rate limiting
- Episode 8 Layer 1: Basic queue
- Episode 8 Layer 2: Priority scheduling
- Episode 8 Layer 3: Rate limiting
- Episode 8 Layer 4: Dependency management
- Episode 8 Layer 5: Retry logic

Real-world systems like Redis Queue, Celery, AWS SQS, and RabbitMQ
use these exact patterns. This is how production task queues actually work!
"""

import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

# Import our layer implementations
from basic_queue import BasicQueue
from priority_queue import PriorityQueue
from rate_limiter import RateLimiter
from dependency_resolver import DependencyResolver
from retry_queue import RetryQueue, Task


class TaskStatus(Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DLQ = "dlq"


class TaskPriority(Enum):
    """Task priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TaskDefinition:
    """Extended task definition with all production features."""
    id: str
    data: Any
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    max_retries: int = 3
    timeout: float = 30.0
    callback: Optional[Callable] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None


class ProductionTaskQueue:
    """
    Production-ready distributed task queue system.
    
    Combines all 5 layers:
    1. Basic FIFO queue (Layer 1)
    2. Priority scheduling (Layer 2)
    3. Rate limiting (Layer 3)
    4. Dependency resolution (Layer 4)
    5. Retry with exponential backoff (Layer 5)
    
    Features:
    - Multi-priority task scheduling
    - Rate limiting per task type
    - Dependency-aware execution
    - Automatic retry with exponential backoff
    - Dead Letter Queue for failed tasks
    - Task lifecycle tracking
    - Performance metrics
    
    This is how real systems like Celery, RQ, and AWS SQS work!
    """
    
    def __init__(
        self,
        rate_limit: int = 100,  # tasks per minute
        base_retry_delay: float = 1.0,
        max_retries: int = 3
    ):
        # Layer 2: Priority queue
        self.priority_queue = PriorityQueue()
        
        # Layer 3: Rate limiter
        self.rate_limiter = RateLimiter(max_requests=rate_limit, window_seconds=60)
        
        # Layer 4: Dependency resolver
        self.dependency_resolver = DependencyResolver()
        
        # Layer 5: Retry queue
        self.retry_queue = RetryQueue(base_delay=base_retry_delay, max_retries=max_retries)
        
        # Task registry
        self.tasks: Dict[str, TaskDefinition] = {}
        self.completed_tasks: Dict[str, TaskDefinition] = {}
        
        # Metrics
        self.total_enqueued = 0
        self.total_completed = 0
        self.total_failed = 0
        self.total_rate_limited = 0
    
    def submit(
        self,
        task_id: str,
        data: Any,
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: Optional[List[str]] = None
    ) -> bool:
        """
        Submit a task to the queue.
        
        Returns True if task was queued, False if rejected (rate limited or has cycles).
        """
        # Create task definition
        task_def = TaskDefinition(
            id=task_id,
            data=data,
            priority=priority,
            dependencies=dependencies or []
        )
        
        # Add to dependency graph
        for dep_id in task_def.dependencies:
            self.dependency_resolver.add_dependency(task_id, dep_id)
        
        # Check for circular dependencies
        if self.dependency_resolver.has_cycle():
            print(f"❌ Task {task_id} rejected: circular dependency detected")
            task_def.status = TaskStatus.FAILED
            task_def.error = "Circular dependency"
            return False
        
        # Check rate limit
        if not self.rate_limiter.allow_request(f"task_type_{priority.value}"):
            print(f"⏸️  Task {task_id} rate limited")
            self.total_rate_limited += 1
            # Could optionally queue for later instead of rejecting
            return False
        
        # Add to task registry
        self.tasks[task_id] = task_def
        
        # Check if dependencies are satisfied
        if self.dependency_resolver.can_run(task_id):
            # Enqueue based on priority
            task_def.status = TaskStatus.QUEUED
            if priority == TaskPriority.HIGH:
                self.priority_queue.enqueue_high(task_def)
            elif priority == TaskPriority.MEDIUM:
                self.priority_queue.enqueue_medium(task_def)
            else:
                self.priority_queue.enqueue_low(task_def)
            
            self.total_enqueued += 1
            print(f"✅ Task {task_id} queued with {priority.value} priority")
            return True
        else:
            # Wait for dependencies
            task_def.status = TaskStatus.PENDING
            print(f"⏳ Task {task_id} waiting for dependencies: {task_def.dependencies}")
            return True
    
    def process_next(self) -> Optional[TaskDefinition]:
        """
        Process the next task from the queue.
        
        Returns the task that was processed, or None if queue is empty.
        """
        # Check retry queue first
        retryable_tasks = self.retry_queue.get_retryable_tasks()
        if retryable_tasks:
            task_obj = retryable_tasks[0]
            task_def = self.tasks.get(task_obj.id)
            if task_def:
                print(f"🔄 Retrying task {task_def.id} (attempt {task_obj.retry_count + 1})")
                self.retry_queue.remove_from_retry_queue(task_obj.id)
                return self._execute_task(task_def)
        
        # Get next task from priority queue
        task_def = self.priority_queue.dequeue()
        if not task_def:
            return None
        
        return self._execute_task(task_def)
    
    def _execute_task(self, task_def: TaskDefinition) -> TaskDefinition:
        """Execute a task (simulate with success/failure)."""
        task_def.status = TaskStatus.RUNNING
        task_def.started_at = time.time()
        
        print(f"▶️  Executing task {task_def.id}: {task_def.data}")
        
        # Simulate task execution
        # In real system, this would call the actual task function
        success = True  # Simulate success (would be actual execution result)
        
        if success:
            task_def.status = TaskStatus.COMPLETED
            task_def.completed_at = time.time()
            task_def.result = f"Result for {task_def.id}"
            self.completed_tasks[task_def.id] = task_def
            self.total_completed += 1
            
            # Mark dependency as complete
            self.dependency_resolver.mark_complete(task_def.id)
            
            # Check if any pending tasks can now run
            self._check_pending_tasks()
            
            print(f"✅ Task {task_def.id} completed in {task_def.completed_at - task_def.started_at:.3f}s")
        else:
            # Task failed - schedule retry
            task_obj = Task(
                id=task_def.id,
                data=task_def.data,
                max_retries=task_def.max_retries
            )
            
            if self.retry_queue.schedule_retry(task_obj, "Execution failed"):
                task_def.status = TaskStatus.RETRYING
                print(f"🔄 Task {task_def.id} scheduled for retry")
            else:
                task_def.status = TaskStatus.DLQ
                self.total_failed += 1
                print(f"❌ Task {task_def.id} moved to DLQ after exhausting retries")
        
        return task_def
    
    def _check_pending_tasks(self):
        """Check if any pending tasks can now be queued."""
        for task_id, task_def in list(self.tasks.items()):
            if task_def.status == TaskStatus.PENDING:
                if self.dependency_resolver.can_run(task_id):
                    # Dependencies satisfied - queue the task
                    task_def.status = TaskStatus.QUEUED
                    if task_def.priority == TaskPriority.HIGH:
                        self.priority_queue.enqueue_high(task_def)
                    elif task_def.priority == TaskPriority.MEDIUM:
                        self.priority_queue.enqueue_medium(task_def)
                    else:
                        self.priority_queue.enqueue_low(task_def)
                    
                    print(f"✅ Task {task_id} dependencies satisfied, now queued")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "total_enqueued": self.total_enqueued,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "total_rate_limited": self.total_rate_limited,
            "pending_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
            "queued_tasks": self.priority_queue.size(),
            "retry_queue": self.retry_queue.stats(),
            "rate_limiter_stats": self.rate_limiter.stats(),
        }
    
    def process_all(self):
        """Process all tasks in the queue."""
        processed = 0
        while True:
            task = self.process_next()
            if not task:
                break
            processed += 1
        return processed


def demo_production_queue():
    """Demonstrate the complete production task queue."""
    print("=== Production Task Queue Demo ===\n")
    
    queue = ProductionTaskQueue(rate_limit=10, max_retries=2)
    
    # Example 1: Basic task submission with priorities
    print("--- Example 1: Priority Scheduling ---")
    queue.submit("task_1", "Low priority work", TaskPriority.LOW)
    queue.submit("task_2", "High priority work", TaskPriority.HIGH)
    queue.submit("task_3", "Medium priority work", TaskPriority.MEDIUM)
    queue.submit("task_4", "Another high priority", TaskPriority.HIGH)
    print()
    
    # Example 2: Tasks with dependencies
    print("--- Example 2: Dependency Management ---")
    queue.submit("load_data", "Load user data", TaskPriority.HIGH)
    queue.submit("process_data", "Process user data", TaskPriority.MEDIUM, dependencies=["load_data"])
    queue.submit("save_results", "Save processed data", TaskPriority.MEDIUM, dependencies=["process_data"])
    print()
    
    # Example 3: Process all tasks
    print("--- Example 3: Processing Tasks ---")
    processed = queue.process_all()
    print(f"\nProcessed {processed} tasks")
    print()
    
    # Show final statistics
    print("--- Final Statistics ---")
    stats = queue.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    demo_production_queue()
