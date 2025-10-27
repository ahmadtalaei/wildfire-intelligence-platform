# TTS Speaker Script Rewrite Guide

This guide provides complete instructions for rewriting speaker scripts in `CHALLENGE_1_FIRE_DATA_PRESENTATION.md` for natural AI voice narration compatible with OpenAI Text-to-Speech API.

## Overview

- **Total Slides**: 43
- **Total Speaker Scripts**: 43
- **File Size**: 8,399 lines (558 KB)
- **Target**: Natural, conversational TTS-ready narration

## Quick Reference: Transformation Rules

### Numbers & Measurements

| Original | Rewritten |
|----------|-----------|
| `870ms` | "eight hundred seventy milliseconds" |
| `3,247` | "three thousand two hundred forty-seven" |
| `99.92%` | "ninety-nine point nine two percent" |
| `10x` | "ten times" |
| `$350,440` | "three hundred fifty thousand four hundred forty dollars" |
| `487 MB` | "four hundred eighty-seven megabytes" |
| `Port 3001` | "Port three thousand one" |

### Technical Terms

| Original | Rewritten |
|----------|-----------|
| `SHA-256` | "S H A two fifty-six" |
| `p95` | "p ninety-five" |
| `MQTT` | "M Q T T" (keep as-is) |
| `API` | "API" (keep as-is) |
| `JSON` | "JSON" (keep as-is) |
| `CSV` | "CSV" (keep as-is) |

### Symbols & Operators

| Original | Rewritten |
|----------|-----------|
| `→` | "leads to" or "results in" |
| `:` (after labels) | "is" or "includes" or "provides" |
| `=` | "is equal to" |
| `vs` | "versus" |

## Before & After Examples

### Example 1: Slide 1 Speaker Script

**BEFORE:**
```
"Let me start by showing you **why we built this system the way we did**...

**

### Point to OUR SOLUTION section

**

**First... Unified Data Ingestion**:
- **All data sources** integrated in one pipeline, including:
- NASA FIRMS satellite fire detection.
- Historical fire database.
```

**AFTER:**
```
Let me start by showing you why we built this system the way we did...

Looking at the OUR SOLUTION section at the top...

First... Unified Data Ingestion...

All data sources are integrated in one pipeline... including...

NASA FIRMS satellite fire detection...

Historical fire database...
```

### Example 2: Technical Metrics

**BEFORE:**
```
We track the failure count for every request...

Typical latency is 200 to 500 milliseconds for NASA FIRMS API calls...

After 5 consecutive failures, we immediately trip the circuit breaker to OPEN...

Latency drops to less than 1 millisecond - essentially instant...
```

**AFTER:**
```
We track the failure count for every request...

Typical latency is two hundred to five hundred milliseconds for NASA FIRMS API calls...

After five consecutive failures... we immediately trip the circuit breaker to OPEN...

Latency drops to less than one millisecond... essentially instant...
```

### Example 3: Storage and Cost

**BEFORE:**
```
HOT Tier uses PostgreSQL with PostGIS...
Covers zero to seven days...
Query latency under one hundred milliseconds... actual performance is eighty-seven milliseconds at p95...

TOTAL SAVINGS: $350,440/year (98.6% cost reduction)
```

**AFTER:**
```
HOT Tier uses PostgreSQL with PostGIS...

Covers zero to seven days...

Query latency under one hundred milliseconds... actual performance is eighty-seven milliseconds at p ninety-five...

TOTAL SAVINGS... three hundred fifty thousand four hundred forty dollars per year... that's ninety-eight point six percent cost reduction...
```

## Detailed Transformation Rules

### 1. Structure & Flow

✅ **Keep ALL unchanged:**
- Mermaid diagrams
- Code blocks
- ASCII art boxes
- Section headers
- Slide titles

✅ **Preserve:**
- Bullet point formatting
- Blank lines between sections

✅ **Remove:**
- Bold markers (`**text**` → `text`)
- Markdown headers inside scripts (`### Point to` → `Looking at`)
- Excessive punctuation

### 2. Visual References

**Add positional descriptors:**

❌ Before: "Point to OUR SOLUTION section"
✅ After: "Looking at the OUR SOLUTION section at the top..."

❌ Before: "This diagram shows"
✅ After: "On the right... this diagram shows..."

**Use directional language:**
- "at the top"
- "on the left side"
- "in the center"
- "in the second row"
- "in the box labeled"

### 3. Numbers

**Spell out all numbers:**

```
0 → zero
1 → one
2 → two
5 → five
7 → seven
10 → ten
12 → twelve
15 → fifteen
20 → twenty
24 → twenty-four
30 → thirty
50 → fifty
87 → eighty-seven
100 → one hundred
247 → two hundred forty-seven
500 → five hundred
870 → eight hundred seventy
1,000 → one thousand
3,247 → three thousand two hundred forty-seven
10,847 → ten thousand eight hundred forty-seven
100,000 → one hundred thousand
350,440 → three hundred fifty thousand four hundred forty
```

**For decimals:**
```
0.9 → zero point nine
0.95 → zero point nine five
99.92 → ninety-nine point nine two
98.7 → ninety-eight point seven
```

### 4. Percentages

Always expand with "percent":
```
99.92% → ninety-nine point nine two percent
0.08% → zero point zero eight percent
98.7% → ninety-eight point seven percent
70% → seventy percent
```

### 5. Times/Multipliers

```
3x → three times
5x → five times
10x → ten times
100x → one hundred times
50-100x → fifty to one hundred times
```

### 6. Measurements

**Time:**
```
1s → one second
2s → two seconds
30s → thirty seconds
870ms → eight hundred seventy milliseconds
50-100ms → fifty to one hundred milliseconds
<1ms → less than one millisecond
<100ms → under one hundred milliseconds
```

**Data Size:**
```
1 MB → one megabyte
487 MB → four hundred eighty-seven megabytes
106 MB → one hundred six megabytes
20 MB → twenty megabytes
2 GB → two gigabytes
10 TB → ten terabytes
```

**Ports:**
```
Port 8003 → Port eight thousand three
Port 3001 → Port three thousand one
Port 5432 → Port five thousand four hundred thirty-two
```

### 7. Currency

```
$10 → ten dollars
$50 → fifty dollars
$350 → three hundred fifty dollars
$1,000 → one thousand dollars
$10,800 → ten thousand eight hundred dollars
$47,500 → forty-seven thousand five hundred dollars
$211,140 → two hundred eleven thousand one hundred forty dollars
$350,440 → three hundred fifty thousand four hundred forty dollars
```

### 8. Technical Codes

```
SHA-256 → S H A two fifty-six
p50 → p fifty
p95 → p ninety-five
p99 → p ninety-nine
```

### 9. Acronyms (Keep As-Is)

These are commonly understood and should NOT be expanded:
- API
- JSON
- CSV
- SQL
- NASA
- NOAA
- MQTT
- FIRMS
- ML
- IoT
- RBAC
- AWS
- S3
- KMS
- IAM

**Exception - Spell out when clarity needed:**
- M Q T T (when first introducing)
- I O T (when emphasizing)

### 10. Natural Speech Patterns

**Add ellipses for pauses:**
```
First... (pause before main point)
Next... (transition)
Also... (addition)
Plus... (extra point)
Then... (sequence)
Meanwhile... (concurrent)
Finally... (conclusion)
```

**Short, clear sentences:**

❌ "The Data Storage Service consumes messages from Kafka and then PostgreSQL INSERT operations succeed ninety-nine point nine percent of the time and success metrics are recorded in Prometheus."

✅ "The Data Storage Service consumes messages from Kafka... PostgreSQL INSERT operations succeed ninety-nine point nine percent of the time... Success metrics are recorded in Prometheus..."

**Remove parentheses - integrate naturally:**

❌ "Circuit breaks during testing: 3 times (NASA API outages)"
✅ "Circuit breaker activated three times during testing... These were actual NASA API outages..."

### 11. Connectors & Transitions

Replace colons and technical structure with natural language:

❌ "Fire Chief Dashboard, React, Port 3001:"
✅ "Fire Chief Dashboard is built with React on Port three thousand one..."

❌ "Rate limiting:"
✅ "Rate limiting is set at..."

❌ "Storage tiers:"
✅ "Our storage tiers include..."

### 12. Arrows & Symbols

```
→ → "leads to" or "results in"
< → "less than"
> → "greater than"
= → "is equal to" or "equals"
/ → "per" or "slash"
- → "to" (in ranges like "0-7 days" → "zero to seven days")
```

## Step-by-Step Manual Rewrite Process

### Option A: Find & Replace in VS Code

1. Open `C:\dev\wildfire\docs\CHALLENGE_1_FIRE_DATA_PRESENTATION.md`
2. Press `Ctrl+H` for Find & Replace
3. Enable Regex mode (click `.*` button)
4. Search for: `## 🎤 \*\*Speaker Script\*\*`
5. For each match (43 total):
   - Read the script section
   - Apply transformation rules above
   - Rewrite in natural, conversational style
   - Keep all structure outside scripts unchanged
6. Save as `CHALLENGE_1_FIRE_DATA_PRESENTATION_TTS.md`

**Time Estimate**: 3-4 hours

### Option B: Python Automation Script

The script `C:\dev\wildfire\scripts\rewrite_tts_scripts.py` has been created.

To run:
```bash
# From project root
python scripts/rewrite_tts_scripts.py

# Or if docker is available
docker run --rm -v ${PWD}:/workspace python:3.11-slim python /workspace/scripts/rewrite_tts_scripts.py
```

Output: `CHALLENGE_1_FIRE_DATA_PRESENTATION_TTS.md`

**Time Estimate**: 10 minutes script + 1-2 hours manual review

### Option C: Section-by-Section Manual Edit

1. Duplicate the original file
2. Search for each `## 🎤 **Speaker Script**` marker
3. Rewrite that section only
4. Move to next section
5. Track progress (43 sections total)

**Time Estimate**: 4-5 hours

## Verification Checklist

After rewriting, verify:

- [ ] All 43 speaker scripts rewritten
- [ ] All mermaid diagrams unchanged
- [ ] All code blocks (```) unchanged
- [ ] All ASCII boxes unchanged
- [ ] All section headers preserved
- [ ] No bold markers in narration (`**`)
- [ ] No colons after labels
- [ ] All numbers spelled out
- [ ] All percentages expanded
- [ ] All currency in words
- [ ] All measurements in words
- [ ] Ellipses added for natural pauses
- [ ] Short, clear sentences throughout
- [ ] Visual references include position
- [ ] Transitions use connecting words

## Testing TTS Output

To test a sample script with OpenAI TTS:

```python
from openai import OpenAI
client = OpenAI()

script = """
Let me start by showing you why we built this system the way we did...

Looking at the OUR SOLUTION section at the top...

First... Unified Data Ingestion...

All data sources are integrated in one pipeline...
"""

response = client.audio.speech.create(
  model="tts-1",
  voice="onyx",  # or alloy, echo, fable, nova, shimmer
  input=script
)

response.stream_to_file("test_output.mp3")
```

Listen for:
- ✅ Natural pacing
- ✅ Clear pronunciation
- ✅ Proper pauses
- ❌ Awkward phrasing
- ❌ Mispronounced numbers
- ❌ Unnatural rhythm

## Common Pitfalls to Avoid

### ❌ Don't Do This:

1. **Repeating Headers**
   - ❌ "Layer One: Presentation Layer. The Presentation Layer is..."
   - ✅ "Layer One: Presentation Layer... At the top, we have..."

2. **Reading Code/Diagrams**
   - ❌ Don't read mermaid code aloud
   - ✅ Describe what the diagram shows

3. **Technical Jargon Overload**
   - ❌ "The DLQ ELT ETL processes via the API..."
   - ✅ "The Dead Letter Queue processes data through the API..."

4. **Run-on Sentences**
   - ❌ "The system uses PostgreSQL for storage and Kafka for streaming and Redis for caching and..."
   - ✅ "The system uses PostgreSQL for storage... Kafka for streaming... and Redis for caching..."

5. **Missing Visual Context**
   - ❌ "This shows the architecture"
   - ✅ "On the left side... this diagram shows the architecture..."

## Final Notes

- **Goal**: Natural, human-like narration that sounds like a professional presenter
- **Tone**: Conversational yet professional
- **Pacing**: Allow for breathing with ellipses and short sentences
- **Clarity**: Numbers and technical terms must be crystal clear
- **Engagement**: Reference visuals to keep audience oriented

## Questions?

If you encounter edge cases or need clarification:
1. Prioritize naturalness over technical precision
2. When in doubt, spell it out
3. Test with actual TTS to hear how it sounds
4. Iterate based on listening experience

---

**Document Version**: 1.0
**Last Updated**: 2025-01-26
**For**: CHALLENGE_1_FIRE_DATA_PRESENTATION.md TTS Conversion
