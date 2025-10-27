# TTS Speaker Script Rewrite - Complete Package

## Overview

This package provides everything needed to rewrite all speaker scripts in `CHALLENGE_1_FIRE_DATA_PRESENTATION.md` for natural AI voice narration compatible with OpenAI Text-to-Speech API.

## What's Included

### 1. **Comprehensive Guide** 📚
**File**: `TTS_SPEAKER_SCRIPT_REWRITE_GUIDE.md`

Complete transformation rules with:
- Quick reference tables for all conversions
- Detailed before/after examples
- 12 categories of transformation rules
- Step-by-step process options
- Verification checklist
- Common pitfalls to avoid

### 2. **Quality Reference Samples** ✨
**File**: `TTS_SAMPLE_REWRITES.md`

First 3 slides fully rewritten showing:
- Professional quality output
- Natural conversational flow
- Proper number/measurement expansion
- Visual references with positioning
- Natural pauses and pacing

Use this as your template for the remaining 40 scripts.

### 3. **Python Automation Script** 🤖
**File**: `C:\dev\wildfire\scripts\rewrite_tts_scripts.py`

Automated processing tool that:
- Identifies all 43 speaker script sections
- Applies core TTS transformations
- Preserves all diagrams and structure
- Outputs to new file for review

### 4. **This README** 📋
Quick start guide and decision tree.

## Quick Start

### Recommended Approach: Hybrid Method

**Best for**: High quality with reasonable time investment

1. **Run automated script** (10 minutes)
   ```bash
   # Option 1: If Python is installed locally
   python C:\dev\wildfire\scripts\rewrite_tts_scripts.py

   # Option 2: Using Docker
   cd C:\dev\wildfire
   docker run --rm -v ${PWD}:/workspace python:3.11-slim python /workspace/scripts/rewrite_tts_scripts.py
   ```

   This creates: `C:\dev\wildfire\docs\CHALLENGE_1_FIRE_DATA_PRESENTATION_TTS.md`

2. **Manual quality review** (1-2 hours)
   - Open generated file in VS Code
   - Search for each `## 🎤 **Speaker Script**` (43 total)
   - Compare with quality samples in `TTS_SAMPLE_REWRITES.md`
   - Refine for naturalness and flow
   - Add contextual improvements the script can't handle

3. **Test sample with OpenAI TTS** (10 minutes)
   ```python
   from openai import OpenAI
   client = OpenAI()

   # Test Slide 1 script
   with open('docs/CHALLENGE_1_FIRE_DATA_PRESENTATION_TTS.md') as f:
       content = f.read()
       # Extract first script for testing...

   response = client.audio.speech.create(
       model="tts-1",
       voice="onyx",
       input=script_text
   )
   response.stream_to_file("test.mp3")
   ```

4. **Iterate based on listening** (30 minutes)
   - Listen to generated audio
   - Note awkward phrasing
   - Refine problem areas
   - Re-test until satisfied

**Total Time**: ~2-3 hours
**Quality**: Professional, production-ready

---

## Alternative Approaches

### Option A: Fully Manual (Highest Quality)

**Best for**: Maximum control over every word

**Time**: 3-4 hours
**Quality**: Excellent

**Process**:
1. Open `CHALLENGE_1_FIRE_DATA_PRESENTATION.md` in VS Code
2. Use `TTS_SAMPLE_REWRITES.md` as reference
3. Manually rewrite all 43 speaker scripts
4. Follow `TTS_SPEAKER_SCRIPT_REWRITE_GUIDE.md` rules
5. Test samples with TTS periodically

**Pros**:
- Complete creative control
- Best contextual awareness
- Most natural results

**Cons**:
- Time-intensive
- Requires sustained focus
- Risk of inconsistency

---

### Option B: Fully Automated (Fastest)

**Best for**: Quick first pass or tight deadlines

**Time**: 10-15 minutes
**Quality**: Good baseline, needs refinement

**Process**:
1. Run Python script
2. Quick visual scan of output
3. Save and use

**Pros**:
- Extremely fast
- Consistent application of rules
- Good starting point

**Cons**:
- May miss contextual nuances
- Less natural in places
- Still needs human review for production

---

## Decision Tree

```
Do you have Python installed locally?
│
├─ YES ──> Run: python scripts/rewrite_tts_scripts.py
│          Then: Manual review (1-2 hours)
│          Total time: 2-3 hours
│
└─ NO
   │
   ├─ Do you have Docker?
   │  │
   │  ├─ YES ──> Run via Docker container
   │  │          Then: Manual review (1-2 hours)
   │  │          Total time: 2-3 hours
   │  │
   │  └─ NO ──> Fully Manual Process
   │             Use TTS_SAMPLE_REWRITES.md as template
   │             Follow TTS_SPEAKER_SCRIPT_REWRITE_GUIDE.md
   │             Total time: 3-4 hours
```

## File Locations

```
C:\dev\wildfire\
├── docs\
│   ├── CHALLENGE_1_FIRE_DATA_PRESENTATION.md          ← Original file
│   ├── CHALLENGE_1_FIRE_DATA_PRESENTATION_TTS.md      ← Output file (generated)
│   ├── TTS_SPEAKER_SCRIPT_REWRITE_GUIDE.md            ← Complete rules & examples
│   ├── TTS_SAMPLE_REWRITES.md                         ← Quality reference (Slides 1-3)
│   └── TTS_REWRITE_README.md                          ← This file
└── scripts\
    └── rewrite_tts_scripts.py                         ← Automation script
```

## Transformation Quick Reference

| Type | Example Original | Example Rewritten |
|------|-----------------|-------------------|
| **Numbers** | `3,247` | "three thousand two hundred forty-seven" |
| **Percent** | `99.92%` | "ninety-nine point nine two percent" |
| **Time** | `870ms` | "eight hundred seventy milliseconds" |
| **Currency** | `$350,440` | "three hundred fifty thousand four hundred forty dollars" |
| **Times** | `10x` | "ten times" |
| **Data** | `487 MB` | "four hundred eighty-seven megabytes" |
| **Ports** | `Port 8003` | "Port eight thousand three" |
| **Tech** | `SHA-256` | "S H A two fifty-six" |
| **Metrics** | `p95` | "p ninety-five" |
| **Arrows** | `→` | "leads to" |
| **Structure** | `**: `** | "is" / "includes" / "provides" |

## Verification Checklist

Before considering the rewrite complete:

- [ ] All 43 speaker scripts processed
- [ ] No mermaid diagrams altered
- [ ] No code blocks changed
- [ ] No ASCII art boxes modified
- [ ] All section headers preserved
- [ ] Numbers spelled out throughout
- [ ] Percentages expanded (e.g., "ninety-nine point nine two percent")
- [ ] Currency in words (e.g., "three hundred fifty thousand dollars")
- [ ] Measurements in words (e.g., "eight hundred seventy milliseconds")
- [ ] Technical codes spelled (e.g., "S H A two fifty-six")
- [ ] Natural pauses with ellipses added
- [ ] Visual references include position (e.g., "at the top", "on the left")
- [ ] Transition words enhanced (First... Next... Then...)
- [ ] Short, clear sentences throughout
- [ ] No bold markers (`**`) in narration
- [ ] No colons after labels
- [ ] Tested sample with actual TTS engine

## Testing Output

### Quick Test with OpenAI TTS

```python
from openai import OpenAI
from pathlib import Path

client = OpenAI()

# Read a speaker script section
doc_path = Path('docs/CHALLENGE_1_FIRE_DATA_PRESENTATION_TTS.md')
with open(doc_path) as f:
    content = f.read()

# Extract first speaker script (between markers)
import re
scripts = re.findall(
    r'## 🎤 \*\*Speaker Script\*\*(.*?)(?=\n##[^#]|\Z)',
    content,
    re.DOTALL
)

if scripts:
    test_script = scripts[0].strip()[:4000]  # First 4000 chars for testing

    response = client.audio.speech.create(
        model="tts-1-hd",  # Higher quality
        voice="onyx",      # Professional male voice
        input=test_script,
        speed=0.95         # Slightly slower for clarity
    )

    response.stream_to_file("output/slide_1_test.mp3")
    print("✅ Test audio generated: output/slide_1_test.mp3")
```

### What to Listen For

✅ **Good signs:**
- Natural pacing and rhythm
- Clear pronunciation of numbers
- Appropriate pauses
- Professional tone
- Easy to follow along with slides

❌ **Problems to fix:**
- Robotic reading
- Mispronounced numbers
- Awkward phrasing
- Run-on sentences
- Missing pauses

## Support & Questions

If you encounter issues:

1. **Check the guide**: `TTS_SPEAKER_SCRIPT_REWRITE_GUIDE.md` has detailed examples
2. **Reference samples**: `TTS_SAMPLE_REWRITES.md` shows professional quality
3. **Test iteratively**: Use OpenAI TTS to hear how changes sound
4. **Prioritize naturalness**: When in doubt, optimize for how it sounds, not how it reads

## Final Notes

**Goal**: Create natural, engaging narration that sounds like a professional presenter delivering the presentation, not a robot reading text.

**Remember**:
- The guide provides rules, but your ear is the final judge
- Test frequently with actual TTS
- The samples show the target quality level
- It's okay to deviate from strict rules if it sounds better

**Success Criteria**:
When someone listens to the generated audio while viewing the slides, it should feel like attending a professional conference presentation - clear, engaging, and easy to follow.

---

## Ready to Start?

1. Choose your approach (Recommended: Hybrid)
2. Review `TTS_SAMPLE_REWRITES.md` for quality target
3. Keep `TTS_SPEAKER_SCRIPT_REWRITE_GUIDE.md` open for reference
4. Start rewriting!
5. Test often with OpenAI TTS
6. Iterate until it sounds natural

**Good luck!** 🎤

---

**Package Version**: 1.0
**Created**: 2025-01-26
**For**: CHALLENGE_1_FIRE_DATA_PRESENTATION.md TTS Conversion
**File Count**: 43 speaker scripts (8,399 lines total)
