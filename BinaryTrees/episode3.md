Episode 2.3: "Rotated Search - Managing Multiple Timelines"

The 2 AM Canary Deployment Disaster

The alert screams at 2 AM: "Error rate spiking to 40%." You just rolled out a new payment processor to 10% of users, and something's catastrophically wrong.

You trigger the rollback immediately. But 15 minutes later, the errors keep pouring in. Some users in the 10% group aren't reverting. Others outside the 10% are suddenly seeing the broken feature. Your monitoring shows multiple overlapping realities across your user base.

This isn't just a deployment bug. It's not even a configuration problem. This is a search problem. You're trying to answer: "Which version should this user see?" when users exist in multiple overlapping timelines.

The algorithm that unlocks this? LeetCode #33: Search in Rotated Sorted Array.

---

LeetCode Core: The Rotated Search Mindset

LeetCode #33 presents a fascinating constraint: what if your sorted array has been rotated at an arbitrary pivot?

```python
# Classic rotated array: [4, 5, 6, 7, 0, 1, 2]
# Original sorted: [0, 1, 2, 4, 5, 6, 7], rotated at index 4

def search_rotated(nums, target):
    left, right = 0, len(nums) - 1
    
    while left <= right:
        mid = left + (right - left) // 2
        
        if nums[mid] == target:
            return mid
            
        # Determine which side is normally sorted
        if nums[left] <= nums[mid]:  # Left half is normally sorted
            if nums[left] <= target < nums[mid]:
                right = mid - 1  # Target in normally sorted left half
            else:
                left = mid + 1   # Target in rotated right half
        else:  # Right half is normally sorted
            if nums[mid] < target <= nums[right]:
                left = mid + 1   # Target in normally sorted right half
            else:
                right = mid - 1  # Target in rotated left half
                
    return -1
```

The conceptual leap: This algorithm teaches us how to search in partially ordered spaces where the sort order exists but starts at an arbitrary pivot point.

Think about feature rollouts:

· Users 0-9%: See Feature X
· Users 10-100%: See Feature Y

The user space is "sorted" by a consistent hash, but the "pivot" at 10% creates a rotated view of which feature each user sees. Searching for "which version does user 45 get?" is exactly determining which side of the pivot they fall on.

---

The Naive Implementation (That Everyone Starts With)

```python
# What most engineers write first (and regret later)
class BrokenFeatureFlag:
    def __init__(self):
        self.config = {
            "new_payment": {
                "enabled_percentage": 10,
                "enabled": True
            }
        }
    
    def is_enabled(self, user_id, feature_name):
        config = self.config.get(feature_name)
        if not config:
            return False
            
        # Simple percentage check
        return hash(user_id) % 100 < config["enabled_percentage"]
```

The critical insight: The problem isn't the hash distribution. The problem is non-stickiness during configuration changes.

```
Day 1: Rollout 10% → Users 0-9 get feature
Day 2: Increase to 50% → Users 10-49 get feature
Day 3: Roll back to 10% → Users 10-49 LOSE the feature

User experience: "Why did this feature disappear and reappear?"
```

This flip-flopping creates terrible user experiences and breaks stateful features.

---

The Rotated Search Solution

What we actually want: a consistent mapping that respects rollout order. Think of user buckets 0-99 as a sorted array, rotated at the rollout percentage:

```
Visualizing user space as a sorted array:
[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, ... 99]

When rollout = 30%:
Users 0-29: See Feature B (new version)
Users 30-99: See Feature A (old version)

This creates a "rotated" view:
[B, B, B, ..., B, A, A, A, ..., A]
 ↑ 30% pivot point
```

Searching for user 45: Which side of the pivot are they on? That's rotated search.

Building the Core Engine

```python
class RotatedRolloutEngine:
    """
    Core concept: User space as a sorted array rotated at percentage pivot
    """
    
    def __init__(self):
        self.features = {
            "new_payment": {
                "pivot": 30,      # 30% rollout
                "left_of_pivot": "new",   # Users < pivot
                "right_of_pivot": "old"   # Users >= pivot
            }
        }
    
    def _get_user_bucket(self, user_id):
        """Consistent hash to 0-99"""
        return (mmh3.hash(str(user_id)) & 0x7fffffff) % 100
    
    def get_version(self, user_id, feature_name):
        """Which side of the pivot is this user on?"""
        feature = self.features.get(feature_name)
        if not feature:
            return "old"
            
        bucket = self._get_user_bucket(user_id)
        pivot = feature["pivot"]
        
        # This is the rotated search decision:
        if bucket < pivot:
            return feature["left_of_pivot"]   # Left of pivot (new)
        else:
            return feature["right_of_pivot"]  # Right of pivot (old)
```

The elegance: Changing the pivot point from 10 → 50 smoothly expands the "new" zone without affecting users already in it. Going from 50 → 10 smoothly contracts it.

---

The Five Real-World Failure Modes

1. The Canary Cascade

Roll out Feature X to 10%. Works. Roll out to 50%. Errors spike. Why? The 10% and 50% weren't nested—users in 40-50% got different configurations than the original 10%.

2. Configuration Drift

Server A: pivot = 30%
Server B(replication lag): pivot = 31%
Result:Users at the boundary get different experiences.

3. Rollback Inconsistency

Rolling back from 50% to 10% must preserve the exact same 10% as before. Otherwise, users see features disappear and reappear randomly.

4. Multi-Dimensional Rotations

Need: 10% of all users + all employees + except EU users. Each rule creates a different "rotation" in user space.

5. Stateful Feature Flip-Flop

User gets feature → creates data → loses feature → gets it back → data gone. Features with user state need sticky assignments.

---

Production Hardening: The Gradual Rollout Engine

Layer 1: Monotonic Rollouts with Version History

```python
class VersionedRollout:
    def __init__(self):
        self.history = []  # Timeline of pivot changes
        
    def set_pivot(self, new_pivot, version="new"):
        # Rule: Pivot only increases (unless explicit rollback)
        current = self.current_pivot()
        if new_pivot < current:
            raise ExplicitRollbackRequired()
            
        self.history.append({
            "timestamp": time.time(),
            "pivot": new_pivot,
            "version": version
        })
```

Why this matters: Users never randomly lose features during normal rollout progression.

Layer 2: Sticky Assignments

```python
class StickyRollout(RotatedRolloutEngine):
    def __init__(self):
        super().__init__()
        self.sticky_map = {}  # user_id -> version
        
    def get_version(self, user_id, feature_name):
        # Once assigned, stick forever (until explicit override)
        if user_id in self.sticky_map:
            return self.sticky_map[user_id]
            
        # Otherwise use normal pivot logic
        version = super().get_version(user_id, feature_name)
        
        # "Stick" the assignment
        self.sticky_map[user_id] = version
        return version
```

Visual timeline:

```
Day 1: User@5% → NEW (stuck as NEW)
Day 2: Rollout 50% → User stays NEW
Day 3: Rollback 10% → User stays NEW (not affected)
```

Layer 3: Consistent Hashing Rings

Instead of simple percentages, use a consistent hashing ring that preserves assignments:

```python
class ConsistentRolloutRing:
    def __init__(self, slots=1000):
        self.slots = slots
        self.ring = [None] * slots
        self.pivot_point = 0  # Slots 0..pivot_point-1 get new version
        
    def set_pivot(self, percentage):
        # Always allocate from slot 0 outward
        new_pivot = int(self.slots * percentage / 100)
        
        # Only update unassigned slots (preserve existing)
        for slot in range(self.pivot_point, new_pivot):
            if self.ring[slot] is None:
                self.ring[slot] = "new"
                
        self.pivot_point = new_pivot
```

The guarantee: User bucket → slot mapping never changes, so assignments persist.

Layer 4: Multi-Dimensional Decision Tree

For complex rollout rules, we need to evaluate multiple "rotations":

```python
class MultiDimensionalRollout:
    RULE_TYPES = [
        "explicit_override",  # Specific users first
        "exclusion",          # GDPR, geo blocks
        "percentage",         # Our rotated search
        "default"             # Fallback
    ]
    
    def evaluate(self, user, feature):
        for rule_type in self.RULE_TYPES:
            rule = self.get_rule(feature, rule_type)
            if rule and self.matches(user, rule):
                return rule.version
        return "old"
    
    def matches(self, user, rule):
        if rule.type == "percentage":
            # Our rotated search
            bucket = self._get_user_bucket(user.id)
            return bucket < rule.pivot
        elif rule.type == "exclusion":
            return user.region not in rule.excluded_regions
        # ... other rule types
```

The insight: Each dimension creates its own "rotation" in user space. We search through them in priority order.

---

[Advanced Pattern] Gossip-Based Configuration

(This is bonus content for large-scale systems)

For massive deployments, we use gossip protocols to avoid central configuration bottlenecks:

```python
class GossipedFeatureFlags:
    def __init__(self):
        self.configs = {}
        self.peers = []
        self.versions = {}  # feature -> version number
        
    def update(self, feature, pivot):
        # Increment version
        self.versions[feature] = self.versions.get(feature, 0) + 1
        
        # Store with version stamp
        self.configs[feature] = {
            "pivot": pivot,
            "version": self.versions[feature]
        }
        
        # Gossip to random peers
        for peer in random.sample(self.peers, 3):
            self._send_update(peer, feature)
```

Why gossip matters: No single point of failure, works during network partitions, eventually consistent.

---

ProductionX: The Complete Gradual Rollout Engine

```python
class GradualRolloutEngine:
    """
    Production feature flag system with:
    1. Versioned history for audit and rollback
    2. Consistent hashing with sticky assignments
    3. Multi-dimensional rules (%, geo, user lists)
    4. Metrics and monitoring hooks
    """
    
    def __init__(self):
        self.rings = {}  # feature -> ConsistentRolloutRing
        self.history = VersionHistory()
        self.overrides = StickyAssignmentStore()
        self.metrics = RolloutMetrics()
        
    def rollout(self, feature, percentage, version="new"):
        """Safely increase rollout percentage"""
        # 1. Validate monotonic (unless explicit rollback)
        current = self.get_current_percentage(feature)
        if percentage < current:
            raise ExplicitRollbackRequired(percentage)
            
        # 2. Update the ring
        ring = self.rings[feature]
        ring.set_pivot(percentage)
        
        # 3. Record in history
        self.history.record(feature, {
            "timestamp": time.time(),
            "percentage": percentage,
            "version": version
        })
        
        # 4. Emit metrics
        self.metrics.emit_rollout_change(feature, percentage)
        
    def get_version(self, user, feature):
        """Main query: What should this user see?"""
        
        # Priority 1: Explicit overrides
        if self.overrides.has_override(user.id, feature):
            return self.overrides.get_override(user.id, feature)
            
        # Priority 2: Exclusions
        if self.exclusions.is_excluded(user, feature):
            return "disabled"
            
        # Priority 3: Percentage rollout (rotated search)
        ring = self.rings[feature]
        return ring.get_version_for_user(user.id)
```

Production Guarantees:

· ✅ Monotonic rollouts (no accidental rollbacks)
· ✅ Sticky assignments (no user flip-flop)
· ✅ Consistent hashing (same user, same bucket)
· ✅ Fast rollbacks (to any historical version)
· ✅ Real-time metrics (adoption, errors by version)

---

The Next Constraint: When Order Itself Is Dynamic

Our rotated search system elegantly handles feature rollouts. But what happens when the feature itself needs to maintain sorted order dynamically?

Consider: You're building a real-time leaderboard. Users constantly get new scores. You need to:

1. Find a user's position (search in sorted scores)
2. Insert new scores (maintain sorted order)
3. Get top N users (range query)

This is Binary Search Tree territory. But in production, your BST lives in memory—and memory fails. How do we persist sorted trees? How do we keep them balanced under millions of concurrent updates?

In Episode 2.4, we'll take LeetCode #98 (Validate BST) and #701 (Insert into BST) and build an in-memory ordered key-value store that survives process crashes, handles millions of ops/second, and scales beyond RAM using disk-backed structures.

The journey so far:

· 2.1: Search static sorted data on disk
· 2.2: Search ranges in changing data
· 2.3: Search rotated/partitioned spaces
· 2.4: Maintain sorted order dynamically as data constantly changes

---

Key Takeaways

1. Feature rollouts = rotated search: Mapping users to versions is determining which side of a pivot they fall on.
2. Stickiness is non-negotiable: Once a user gets a feature, they should keep it (unless explicitly removed).
3. Monotonic rollouts prevent chaos: Percentage should only increase unless you explicitly call a rollback method.
4. Multi-dimensional rollouts stack: Each rule type creates a different "rotation" in user space that must be searched in priority order.
5. Version everything: Rollback requires knowing exactly what was deployed when. History is your audit trail.

The production insight: Sometimes data isn't just sorted—it's sorted from an arbitrary starting point. Recognizing that "rotation" and building systems that preserve consistency across those boundaries is what separates toy projects from production systems.

---

Next time: We leave the world of static searches and enter dynamic order maintenance with Binary Search Trees, building a production-ready ordered key-value store that must stay sorted even as the world changes around it.