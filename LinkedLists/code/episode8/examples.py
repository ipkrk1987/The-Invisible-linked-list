"""
Episode 1.8 - Real-World Task Queue Examples
Practical Usage Patterns for Production Systems

These examples show how you'd use the task queue in real applications:
- Web scraping with rate limiting
- Data pipeline with dependencies
- Notification system with retries
- Background job processing

Each example demonstrates different aspects of the 5-layer system.
"""

import time
from task_queue import ProductionTaskQueue, TaskPriority


def example_1_web_scraping():
    """
    Example 1: Web Scraping with Rate Limiting
    
    Real-world scenario: Scraping product data from an e-commerce site
    - Rate limit: 60 requests per minute (respect robots.txt)
    - Priority: High for featured products, low for regular products
    - Retry: Handles temporary network failures
    
    This is how tools like Scrapy manage request queues!
    """
    print("=" * 60)
    print("EXAMPLE 1: Web Scraping with Rate Limiting")
    print("=" * 60)
    
    # Create queue with strict rate limiting (60 req/min = 1/sec)
    queue = ProductionTaskQueue(rate_limit=60, max_retries=3)
    
    # Featured products (high priority)
    featured_urls = [
        "https://shop.com/iphone-15-pro",
        "https://shop.com/macbook-pro-m3",
        "https://shop.com/airpods-pro",
    ]
    
    for url in featured_urls:
        queue.submit(
            task_id=f"scrape_{url.split('/')[-1]}",
            data={"url": url, "type": "product"},
            priority=TaskPriority.HIGH
        )
    
    # Regular products (low priority, process after featured)
    regular_urls = [
        "https://shop.com/usb-cable",
        "https://shop.com/phone-case",
        "https://shop.com/screen-protector",
    ]
    
    for url in regular_urls:
        queue.submit(
            task_id=f"scrape_{url.split('/')[-1]}",
            data={"url": url, "type": "product"},
            priority=TaskPriority.LOW
        )
    
    print("\nProcessing scraping tasks...")
    processed = queue.process_all()
    
    print(f"\n✅ Scraped {processed} products")
    print(f"📊 Stats: {queue.get_stats()}")
    print()


def example_2_data_pipeline():
    """
    Example 2: Data Pipeline with Dependencies
    
    Real-world scenario: ETL pipeline for analytics
    1. Extract data from database
    2. Transform data (depends on extract)
    3. Load to data warehouse (depends on transform)
    4. Update dashboard (depends on load)
    
    This is how tools like Apache Airflow manage task dependencies!
    """
    print("=" * 60)
    print("EXAMPLE 2: Data Pipeline with Dependencies")
    print("=" * 60)
    
    queue = ProductionTaskQueue(rate_limit=100)
    
    # Define pipeline stages with dependencies
    pipeline_stages = [
        # Stage 1: Extract (no dependencies)
        ("extract_users", "Extract user data from PostgreSQL", [], TaskPriority.HIGH),
        ("extract_orders", "Extract order data from PostgreSQL", [], TaskPriority.HIGH),
        
        # Stage 2: Transform (depends on extract)
        ("transform_users", "Clean and normalize user data", ["extract_users"], TaskPriority.MEDIUM),
        ("transform_orders", "Aggregate order metrics", ["extract_orders"], TaskPriority.MEDIUM),
        
        # Stage 3: Join (depends on both transforms)
        ("join_data", "Join users and orders", ["transform_users", "transform_orders"], TaskPriority.MEDIUM),
        
        # Stage 4: Load (depends on join)
        ("load_warehouse", "Load to Snowflake", ["join_data"], TaskPriority.HIGH),
        
        # Stage 5: Report (depends on load)
        ("update_dashboard", "Refresh Tableau dashboard", ["load_warehouse"], TaskPriority.LOW),
        ("send_report", "Email daily report", ["load_warehouse"], TaskPriority.LOW),
    ]
    
    print("\nSubmitting pipeline tasks...")
    for task_id, description, deps, priority in pipeline_stages:
        queue.submit(
            task_id=task_id,
            data={"description": description},
            priority=priority,
            dependencies=deps
        )
    
    print("\nProcessing pipeline (respects dependencies)...")
    processed = queue.process_all()
    
    print(f"\n✅ Completed {processed} pipeline stages")
    print(f"📊 Stats: {queue.get_stats()}")
    print()


def example_3_notification_system():
    """
    Example 3: Notification System with Retries
    
    Real-world scenario: Send notifications to users
    - Email notifications (high priority with retries)
    - SMS notifications (high priority, expensive - rate limited)
    - Push notifications (medium priority, best effort)
    
    This is how services like SendGrid and Twilio handle delivery!
    """
    print("=" * 60)
    print("EXAMPLE 3: Notification System with Retries")
    print("=" * 60)
    
    # Strict rate limiting for SMS (expensive API calls)
    queue = ProductionTaskQueue(rate_limit=10, max_retries=3)
    
    # Critical notifications (email with retries)
    critical_notifications = [
        ("email_password_reset", "Password reset for user@example.com", TaskPriority.HIGH),
        ("email_2fa_code", "2FA code for admin@example.com", TaskPriority.HIGH),
        ("email_payment_receipt", "Payment confirmation", TaskPriority.HIGH),
    ]
    
    for task_id, description, priority in critical_notifications:
        queue.submit(task_id=task_id, data=description, priority=priority)
    
    # SMS notifications (rate limited)
    sms_notifications = [
        ("sms_verification", "Send verification code", TaskPriority.HIGH),
        ("sms_alert", "Security alert", TaskPriority.HIGH),
    ]
    
    for task_id, description, priority in sms_notifications:
        queue.submit(task_id=task_id, data=description, priority=priority)
    
    # Push notifications (best effort, low priority)
    push_notifications = [
        ("push_new_message", "New message notification", TaskPriority.LOW),
        ("push_friend_request", "Friend request", TaskPriority.LOW),
    ]
    
    for task_id, description, priority in push_notifications:
        queue.submit(task_id=task_id, data=description, priority=priority)
    
    print("\nProcessing notifications...")
    processed = queue.process_all()
    
    print(f"\n✅ Sent {processed} notifications")
    print(f"📊 Stats: {queue.get_stats()}")
    print()


def example_4_background_jobs():
    """
    Example 4: Background Job Processing
    
    Real-world scenario: Video processing platform
    1. Upload video (user-initiated, high priority)
    2. Generate thumbnails (depends on upload)
    3. Transcode to multiple formats (depends on upload, CPU-intensive)
    4. Generate subtitles (depends on transcode, can fail and retry)
    
    This is how platforms like YouTube process uploaded videos!
    """
    print("=" * 60)
    print("EXAMPLE 4: Background Job Processing (Video Platform)")
    print("=" * 60)
    
    queue = ProductionTaskQueue(rate_limit=50, max_retries=2)
    
    # Simulate multiple video uploads
    videos = [
        ("video_001", "Travel Vlog - Day 1"),
        ("video_002", "Cooking Tutorial - Pasta"),
        ("video_003", "Product Review - Laptop"),
    ]
    
    for video_id, title in videos:
        # 1. Upload task
        upload_task = f"upload_{video_id}"
        queue.submit(
            task_id=upload_task,
            data={"title": title, "stage": "upload"},
            priority=TaskPriority.HIGH
        )
        
        # 2. Generate thumbnails (fast, depends on upload)
        thumbnail_task = f"thumbnail_{video_id}"
        queue.submit(
            task_id=thumbnail_task,
            data={"title": title, "stage": "thumbnail"},
            priority=TaskPriority.MEDIUM,
            dependencies=[upload_task]
        )
        
        # 3. Transcode (slow, depends on upload)
        transcode_tasks = []
        for fmt in ["720p", "1080p", "4K"]:
            transcode_task = f"transcode_{video_id}_{fmt}"
            transcode_tasks.append(transcode_task)
            queue.submit(
                task_id=transcode_task,
                data={"title": title, "stage": f"transcode_{fmt}"},
                priority=TaskPriority.MEDIUM,
                dependencies=[upload_task]
            )
        
        # 4. Generate subtitles (depends on transcode completing)
        subtitle_task = f"subtitles_{video_id}"
        queue.submit(
            task_id=subtitle_task,
            data={"title": title, "stage": "subtitles"},
            priority=TaskPriority.LOW,
            dependencies=transcode_tasks
        )
    
    print("\nProcessing video jobs...")
    processed = queue.process_all()
    
    print(f"\n✅ Processed {processed} video jobs")
    print(f"📊 Stats: {queue.get_stats()}")
    print()


def example_5_real_world_comparison():
    """
    Example 5: How Our Queue Compares to Real Systems
    
    Shows how our 5-layer implementation maps to production tools.
    """
    print("=" * 60)
    print("EXAMPLE 5: Real-World System Comparison")
    print("=" * 60)
    
    comparisons = [
        {
            "system": "Redis Queue (RQ)",
            "our_layer": "Layer 1 (Basic Queue) + Layer 5 (Retry)",
            "features": "FIFO queue with worker pools and retry logic",
        },
        {
            "system": "Celery",
            "our_layer": "All 5 Layers",
            "features": "Priority queues, rate limiting, dependencies (Canvas), retries",
        },
        {
            "system": "AWS SQS",
            "our_layer": "Layer 1 + Layer 5 (DLQ)",
            "features": "FIFO queues with Dead Letter Queue",
        },
        {
            "system": "RabbitMQ",
            "our_layer": "Layer 1 + Layer 2 (Priorities)",
            "features": "Priority queues with exchange routing",
        },
        {
            "system": "Apache Kafka",
            "our_layer": "Layer 1 (at scale)",
            "features": "Distributed FIFO queues (partitions) for high throughput",
        },
        {
            "system": "Azure Service Bus",
            "our_layer": "Layer 2 + Layer 5",
            "features": "Priority queues with retry and DLQ",
        },
    ]
    
    print("\nHow Our Task Queue Maps to Production Systems:\n")
    for comp in comparisons:
        print(f"📦 {comp['system']}")
        print(f"   Maps to: {comp['our_layer']}")
        print(f"   Features: {comp['features']}")
        print()
    
    print("💡 Key Takeaway: The linked list patterns we learned are the")
    print("   foundation of EVERY major task queue system in production!")
    print()


def run_all_examples():
    """Run all examples in sequence."""
    print("\n")
    print("🎬" * 30)
    print("PRODUCTION TASK QUEUE EXAMPLES")
    print("🎬" * 30)
    print("\n")
    
    example_1_web_scraping()
    input("Press Enter to continue to Example 2...")
    
    example_2_data_pipeline()
    input("Press Enter to continue to Example 3...")
    
    example_3_notification_system()
    input("Press Enter to continue to Example 4...")
    
    example_4_background_jobs()
    input("Press Enter to continue to Example 5...")
    
    example_5_real_world_comparison()
    
    print("\n")
    print("🎉" * 30)
    print("All examples completed!")
    print("🎉" * 30)
    print("\n")


if __name__ == "__main__":
    run_all_examples()
