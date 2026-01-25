# Storyboard Generator Prompt

Use this prompt to convert any episode script into a theatrical storyboard with animations.

---

## PROMPT TEMPLATE

```
You are a storyboard architect for a theatrical technical presentation series.

INPUT: [Paste episode markdown script here]

OUTPUT: Generate a storyboard following these rules:

---

## PHASE 1: CODE AUDIT
Scan the script and create a table:
| Block # | Description | Lines | Type | Decision |

For each code block, decide:
- **KEEP**: Core algorithm (max 1-2 per episode)
- **CONVERT**: Transform to animation
- **BRIEF**: Mention without showing full code

Target: Reduce code blocks by 70-80%

---

## PHASE 2: ANIMATION OPPORTUNITIES
Identify interactive animations for:
1. **Hook demonstration** - Show the problem visually
2. **Algorithm visualization** - Step-through with controls
3. **Before/After comparison** - Toggle between approaches
4. **Production pattern** - Real-world system demo

For each animation, specify:
- Name and emoji identifier
- What it visualizes
- User interactions (buttons, sliders, toggles)
- Connection to the narrative

---

## PHASE 3: 4-ACT STRUCTURE
Organize into exactly 4 acts:

### ACT 1: THE HOOK (2-3 slides)
- Title slide with dramatic subtitle
- Problem demonstration (preferably animated)
- Stakes: "Why should I care?"

### ACT 2: THE PROBLEM (5-7 slides)
- LeetCode problem introduction
- ONE code block (the core algorithm)
- Key insight/reframing
- Algorithm visualization animation
- Anti-pattern demonstration

### ACT 3: THE SOLUTION (6-8 slides)
- Pattern introduction
- Comparison animation (old vs new approach)
- Scale break: "But what about X?"
- Production pattern with animation
- Connection to previous episodes

### ACT 4: MASTERY (4-5 slides)
- Complete flow animation
- When to use / when not to use
- Next episode teaser
- Recap with key takeaways

---

## PHASE 4: SLIDE BREAKDOWN
For each slide, specify:
| Slide | Type | Content | Speaker Notes |

Types:
- **Title**: Episode/section title
- **CODE**: The 1-2 allowed code blocks
- **ANIMATION**: Interactive demo
- **Insight**: Key "aha" moment
- **Diagram**: Static visual
- **Recap**: Summary points

---

## PHASE 5: ANIMATION SPECIFICATIONS
For each animation, provide:

### [Animation Name]
- **Purpose**: What concept it teaches
- **Visual elements**: What appears on canvas
- **States**: List of animation states
- **Controls**: Buttons/interactions
- **Timing**: Auto-play or manual steps

---

## CONSTRAINTS

1. **Maximum 2 code blocks** shown in slides
2. **Minimum 4 animations** with interactivity
3. **22-25 slides** total
4. **Every concept** either animated OR mentioned briefly (not code-dumped)
5. **Clear narrative arc**: Problem → Failed attempt → Solution → Mastery
6. **Connection to previous/next episodes** in the series

---

## OUTPUT FORMAT

Provide the complete storyboard with:
1. Code Audit Table
2. Animation Opportunities List
3. 4-Act Structure with slide details
4. Comparison table (Original vs Storyboard metrics)
```

---

## EXAMPLE USAGE

### Input:
```
[Paste contents of episode3.md]
```

### Expected Output:
- Code audit showing 8 blocks → 2 kept
- 4-5 animation specifications
- 22 slides across 4 acts
- Clear narrative flow

---

## ANIMATION NAMING CONVENTION

Use emoji prefixes for quick identification:
- 🔴 Problem/Bug demonstration
- 🟡 Algorithm step-through
- 🟢 Solution pattern
- 🔵 Data structure visualization
- 🟣 Production system flow
- ⚪ Comparison/toggle view

---

## QUALITY CHECKLIST

After generating storyboard, verify:

- [ ] Code blocks reduced by 70%+
- [ ] At least 4 interactive animations
- [ ] Hook grabs attention in first 2 slides
- [ ] Clear "aha" moment identified
- [ ] Connection to series narrative
- [ ] Actionable speaker notes
- [ ] Next episode teaser included

---

## SERIES CONTEXT

**Season 2: Binary Trees & Production Systems**
- Episode 2.1: SSTables, Binary Search, WAL (completed)
- Episode 2.2: Cursor Pagination, MVCC, Range Queries
- Episode 2.3: Rotated Arrays, Feature Flags
- [Continue pattern...]

**Animation Style Reference:**
- Canvas-based with control panels
- Step/Auto/Reset buttons
- State transitions with visual feedback
- Color-coded elements (green=success, red=error, yellow=active)
