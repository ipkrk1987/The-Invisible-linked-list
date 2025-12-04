Episode 2.2 Rewrite: "Bound Search - The Infinite Scroll Algorithm"

The Spine of This Episode

How lower_bound and upper_bound become cursor-based pagination in a live, changing feed.

(This is what we're building - everything else supports this core concept)


---

0:00 - Hook: The Social Media Pagination Bug

Every engineer has seen this: you're scrolling through Twitter or Reddit, hit "Load More," and suddenly you see duplicate posts. Or you jump back in time. Or posts appear and disappear between pages.

This isn't a UI bug. It's a fundamental failure of how we paginate sorted, changing data. Today, we're going from LeetCode #34 to building bulletproof pagination that handles millions of concurrent users scrolling through feeds that update in real-time.


---

2:00 - LeetCode Core: Lower Bound and Upper Bound

Let's start with LeetCode #34: "Find First and Last Position in Sorted Array."

# The algorithm itself is simple  
def find_boundaries(nums, target, find_first=True):  
    left, right = 0, len(nums) - 1  
    result = -1  
      
    while left <= right:  
        mid = left + (right - left) // 2  
          
        if nums[mid] == target:  
            result = mid  
            if find_first:  
                right = mid - 1  # Keep searching left  
            else:  
                left = mid + 1   # Keep searching right  
        elif nums[mid] < target:  
            left = mid + 1  
        else:  
            right = mid - 1  
              
    return result

But here's the critical reframing:

· lower_bound(target) = "Where does the range ≥ target begin?"
· upper_bound(target) = "Where does the range ≤ target end?"

In production terms:

· lower_bound(2024-01-15) = "First post from January 15th or later"
· upper_bound(2024-01-15) = "Last post from January 15th or earlier"

The insight: Pagination is just repeatedly moving your lower_bound as you scroll through sorted data.


---

4:00 - The Naive Approach (That Breaks)

Most junior engineers start with offset pagination:

-- Page 1  
SELECT * FROM posts   
ORDER BY timestamp DESC   
LIMIT 20 OFFSET 0;  
  
-- Page 2    
SELECT * FROM posts   
ORDER BY timestamp DESC   
LIMIT 20 OFFSET 20;

Visualize why this breaks:

Timeline: [N1, N2, N3, P1, P2, P3, P4, P5, ... P100]  
          ↑ New posts  ↑ Old posts  
            
User loads Page 1: sees P1-P20  
New posts arrive: N1, N2, N3 appear at the top  
User loads Page 2 (OFFSET 20): now sees P3-P22  
  
Result: P1-P3 shown twice, P21-P22 never shown

The problem: OFFSET means "skip N rows," not "continue from position X." When new rows are inserted at the top, everything shifts.


---

6:00 - Cursor Pagination: The Correct Foundation

A cursor is a stable pointer to a specific position in sorted data. Instead of "give me rows 20-40," we say "give me rows after this specific row."

def get_page_after_cursor(cursor, limit=20):  
    # cursor = (last_timestamp, last_post_id)  
    # This is essentially lower_bound(cursor_timestamp)  
    start_position = find_first_post_after(cursor.timestamp)  
      
    # Then read sequentially from that position  
    return read_posts_sequentially(start_position, limit)

Visualizing cursor stability:

Same timeline: [N1, N2, N3, P1, P2, P3, P4, P5, ...]  
Cursor after Page 1: points to P20  
  
User loads Page 2: "give me 20 posts older than P20"  
Result: P21-P40 (correct, even with N1-N3 inserted)

The algorithm connection: Finding "posts older than P20" is exactly lower_bound(P20.timestamp) on the sorted timeline.


---

8:00 - Building on Episode 2.1: SSTable Range Queries

In Episode 2.1, we built SSTables for single-key lookups. Now we extend them for range queries.

class SSTableWithRanges(SSTableFromEpisode21):  
    def range_query(self, start_key, end_key, limit=None):  
        """  
        Core insight:   
        1. One binary search to find the start (lower_bound)  
        2. Then sequential reads (fast on disk)  
        """  
          
        # Step 1: Binary search to find starting block  
        start_block = self._binary_search_for_key(start_key)  
          
        # Step 2: Sequential scan from that point  
        return self._sequential_scan_from(start_block, end_key, limit)

The performance insight: Binary search gives us O(log n) to find the starting point, then sequential disk reads (which are extremely fast) give us the range.


---

10:00 - Scale Break #1: Real-Time Updates Break Even Cursors

Here's where it gets interesting. What if new posts arrive while you're scrolling?

User loads Page 1: sees P1-P20  
New posts arrive: N1, N2 insert at the top  
User loads Page 2 (cursor at P20): sees P21-P40  
  
Problem: The user never sees N1, N2

The UX constraint: For social feeds, new posts should appear at the top, not be injected into your historical scroll. This is a product decision, not a technical one.

The technical solution: MVCC Snapshots.


---

12:00 - Production Pattern: MVCC Snapshots (Facebook/Twitter Style)

MVCC (Multi-Version Concurrency Control) gives each reader a consistent snapshot of the data at a specific point in time.

class FeedSnapshot:  
    def __init__(self, timestamp):  
        self.timestamp = timestamp  
        self.posts = get_posts_as_of(timestamp)  # Frozen view  
          
    def get_page(self, cursor=None, limit=20):  
        # All reads come from the same frozen snapshot  
        # No new posts will appear during pagination  
        if cursor is None:  
            start = self.posts.lower_bound(self.timestamp)  
        else:  
            start = self.posts.lower_bound(cursor.timestamp)  
              
        return self.posts.range_query(start, limit=limit)

The mental model: Each "Load More" walks through a frozen moment in time. New posts appear in a newer snapshot at the top of your feed.


---

14:00 - Production Pattern: Composite Cursors

A production cursor needs to encode more than just a position:

class CompositeCursor:  
    def __init__(self, snapshot_id, last_key):  
        self.snapshot_id = snapshot_id  # Which frozen timeline  
        self.last_key = last_key        # Where we left off  
          
    def encode(self):  
        return base64_encode(f"{snapshot_id}:{last_key}")

Why this matters: It solves multi-device sync. Your phone and laptop can share the same snapshot, so they see consistent data.


---

16:00 - [Advanced Bonus] Cursor Security & Performance

In production, we add two more layers:

1. Security: Sign cursors to prevent tampering



cursor_with_hmac = f"{cursor_data}.{hmac_signature(cursor_data)}"

2. Performance: Shard by user_id to avoid hot partitions



shard_id = hash(user_id) % 1024  # Distribute load

(We'll cover these in depth in future episodes - today they're bonus patterns)


---

18:00 - The Complete Production Flow

Putting it all together:

def production_get_feed_page(user_id, encoded_cursor, limit=20):  
    # 1. Decode and verify cursor  
    cursor = decode_cursor(encoded_cursor)  
      
    # 2. Choose the right snapshot  
    snapshot = get_snapshot_for_user(user_id, cursor)  
      
    # 3. Range query from cursor position  
    posts = snapshot.posts.range_query(  
        start_key=cursor.last_key if cursor else None,  
        limit=limit + 1  # Fetch one extra to check has_more  
    )  
      
    # 4. Build next cursor  
    has_more = len(posts) > limit  
    if has_more:  
        posts = posts[:limit]  
        last_post = posts[-1]  
        next_cursor = CompositeCursor(  
            snapshot_id=snapshot.id,  
            last_key=(last_post.timestamp, last_post.id)  
        )  
    else:  
        next_cursor = None  
          
    return {  
        'posts': posts,  
        'next_cursor': next_cursor.encode() if next_cursor else None,  
        'has_more': has_more  
    }


---

20:00 - When to Use This Pattern

Use cursor-based pagination with MVCC when:

· Data is sorted (by time, score, etc.)
· Real-time updates happen during pagination
· Consistency matters (no duplicates/skips)
· Clients need stateless pagination

Don't use it when:

· Data fits in memory (just load it all)
· Order doesn't matter (random sampling is fine)
· Simpler solutions work (sometimes offset is okay!)


---

22:00 - Next Constraint: When "Sorted" Isn't Straightforward

We now have robust pagination for sorted data. But what if the sort order itself isn't static? What if different users see different "rotations" of the same data?

Example: Feature flag rollouts:

· User A (10% cohort) sees: [NewFeature, OldFeature]
· User B (90% cohort) sees: [OldFeature, NewFeature]

The data is sorted, but the starting point rotates based on user attributes.

This is exactly LeetCode #33: Search in Rotated Sorted Array. The algorithm for finding data when the sort order has been pivoted.

In Episode 2.3, we'll build a feature flag system that manages canary deployments, progressive rollouts, and instant rollbacks. We'll learn how to search through rotated timelines and maintain consistency across distributed configuration stores.


---

24:00 - Recap & Key Takeaways

1. Offset pagination breaks with real-time inserts. Use cursor-based pagination instead.


2. Cursors are just lower_bound operations on sorted data. Each "next page" moves your lower bound forward.


3. MVCC snapshots solve consistency during real-time updates. Each scroll walks through a frozen moment in time.


4. Binary search + sequential reads = efficient range queries in persistent storage (building on Episode 2.1).


5. Production cursors encode state (snapshot ID + position) for consistent multi-device experiences.



The journey today: From finding ranges in sorted arrays (lower_bound/upper_bound) to building Twitter/Facebook-style infinite scroll that handles millions of concurrent users on constantly updating feeds.


---

Next episode: We rotate our perspective (literally) and handle the case where sorted data doesn't start at the same point for everyone.