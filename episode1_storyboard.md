# Episode 1: The Invisible Linked List — Storyboard

---

## Slide 1: Title
**Visual:** Bold title, subtle animated background (nodes fading in)
**Text:**
> From LeetCode to Production:
> The Invisible Linked List
> *How Git Scales to 100M Developers*

**Narration:**
> "Welcome! Today, we'll journey from a simple interview question to the heart of Git's engineering magic."

**Cue:** Fade in welcome message as fragment.

---

## Slide 2: Prologue / Hook
**Visual:** Soft gradient, quote box, code snippet in background (blurred)
**Text:**
> "Every time you type `git commit`, you're walking a linked list."

**Narration:**
> "Along the way, you'll see how a humble linked list becomes the backbone of a world-class version control system. Ready to discover the hidden layers beneath your code?"

**Cue:** Reveal quote, then fade in narration.

---

## Slide 3: Act 1 — The LeetCode Foundation (Intro)
**Visual:** Act title, LeetCode logo (optional), simple node chain animation
**Text:**
> **Act 1: The LeetCode Foundation**
> LeetCode #206: Reverse Linked List
> Each commit is a node pointing to its parent.

**Narration:**
> "Let's start at the very beginning: a single linked list, the classic interview problem. But what secrets does it hold?"

**Cue:** Animate nodes appearing one by one.

---

## Slide 4: Act 1 — Feynman Box
**Visual:** Yellow callout box (Feynman style)
**Text:**
> **Why does this matter?**
> If you can reverse a linked list, you can understand how Git walks commit history. This is the core of every `git log` and `git bisect` operation!

**Narration:**
> "This is the 'aha!' moment: the interview problem is the same as the real-world tool."

**Cue:** Highlight box, pause for emphasis.

---

## Slide 5: Act 1 — Diagram Suggestion
**Visual:** Pointer Dance diagram (arrows moving step by step, "You Are Here" label)
**Text:**
> Diagram: Pointer Dance
> Show arrows and pointers moving step by step as the list is reversed.

**Narration:**
> "Watch the pointers dance as we reverse the list—just like Git traverses your commit history."

**Cue:** Animate arrows/pointers if possible.

---

## Slide 6: Act 1 — Code
**Visual:** Syntax-highlighted Python code block
**Text:**
```python
class Commit:
    def __init__(self, message, parent=None):
        self.message = message
        self.parent = parent  # Points to previous commit
        self.timestamp = time.time()

class MiniGit:
    def __init__(self):
        self.head = None  # Most recent commit

    def commit(self, message):
        new_commit = Commit(message, self.head)
        self.head = new_commit
        return new_commit
```

**Narration:**
> "Here's the code: each commit stores its parent. This is the heart of Git's data model."

**Cue:** Highlight `parent` pointer in code.

---

## Slide 7: Act 1 — Stats
**Visual:** Three stat cards (Time, Space, Lines of Code)
**Text:**
| Time Complexity | Space Complexity | Lines of Code |
|-----------------|------------------|---------------|
| O(n)            | O(1)             | 15            |

**Narration:**
> "Simple, elegant, and efficient. This is the foundation we'll build on."

**Cue:** Reveal stats with subtle animation.

---

## Slide 8: Act 2 — Scale Break (Intro)
**Visual:** Warning box, dramatic color (orange/yellow)
**Text:**
> **Act 2: Scale Break #1 — Memory Explosion**
> ⚠️ The Problem:
> Every commit stores full snapshot. 100K commits = 1-10GB naive storage.
> Without compression, Git would be unusable at scale.

**Narration:**
> "What happens when you add more commits? Suddenly, memory becomes a problem."

**Cue:** Flash warning icon, pause.

---

## Slide 9: Act 2 — Feynman Box
**Visual:** Yellow callout box
**Text:**
> **Why does this matter?**
> If Git stored every file every time, your repo would explode in size. Understanding this is key to appreciating Git's efficiency tricks.

**Narration:**
> "This is why compression and deltas are so important."

**Cue:** Highlight box.

---

## Slide 10: Act 2 — Diagram Suggestion
**Visual:** Side-by-side: Snapshot (full boxes) vs. Delta (small deltas chained)
**Text:**
> Diagram: Snapshot vs. Delta
> Left: every commit is a full box. Right: commits are small deltas chained together.

**Narration:**
> "On the left, naive storage. On the right, Git's magic: only store what changed."

**Cue:** Animate both sides, highlight savings.

---

## Slide 11: Act 2 — Interactive Demo
**Visual:** Buttons for "Add 10 Commits", "Apply Packfile Compression", "Reset"
**Text:**
> Try it yourself: add commits, then see the effect of compression.

**Narration:**
> "Let's see how compression works in action."

**Cue:** User interaction, show memory bar shrinking.

---

## Slide 12: Act 3 — Interactive Demo (Placeholder)
**Visual:** Animation canvas or placeholder
**Text:**
> [Animation Placeholder]
> Try Me button

**Narration:**
> "Here's where we'll add more interactive demos as we build out the story."

**Cue:** Reveal button, invite interaction.

---

# Notes
- Each slide should be a vertical sub-slide within its act (horizontal = acts, vertical = details).
- Fragments can be used for progressive reveal within a slide.
- Diagram suggestions can be replaced with actual SVG/canvas animations later.
- Narration can be shown as speaker notes or on-screen subtitles.

---

*Storyboard ready for review and slide migration.*
