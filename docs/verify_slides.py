#!/usr/bin/env python3
"""
Verify all 45 slides have speaker scripts in the presentation file.
"""

import re

# Read the presentation file
with open('CHALLENGE2_FIRE_DATA_PRESENTATION.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Split into slides
slide_pattern = r'^## Slide (\d+):'
slides = re.split(slide_pattern, content, flags=re.MULTILINE)

# slides[0] is content before first slide
# slides[1] = '1', slides[2] = content of slide 1
# slides[3] = '2', slides[4] = content of slide 2, etc.

print("=" * 80)
print("SLIDE SPEAKER SCRIPT VERIFICATION")
print("=" * 80)

missing_scripts = []
slides_with_scripts = []
slide_details = []

for i in range(1, len(slides), 2):
    slide_num = int(slides[i])
    slide_content = slides[i+1] if i+1 < len(slides) else ""

    # Count speaker scripts in this slide
    speaker_script_count = slide_content.count("Speaker Script")

    # Extract slide title (first line after slide number)
    title_match = re.search(r'^([^\n]+)', slide_content.strip())
    title = title_match.group(1) if title_match else "Unknown"

    has_script = speaker_script_count > 0

    if has_script:
        slides_with_scripts.append(slide_num)
        status = f"✅ {speaker_script_count} script(s)"
    else:
        missing_scripts.append(slide_num)
        status = "❌ NO SCRIPT"

    slide_details.append({
        'num': slide_num,
        'title': title[:60],
        'scripts': speaker_script_count,
        'has_script': has_script
    })

    print(f"Slide {str(slide_num).rjust(2)}: {status:20} | {title[:60]}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total slides: 45")
print(f"Slides with speaker scripts: {len(slides_with_scripts)}")
print(f"Slides missing speaker scripts: {len(missing_scripts)}")
print(f"Total speaker script sections: {sum(d['scripts'] for d in slide_details)}")

if missing_scripts:
    print(f"\n❌ MISSING SPEAKER SCRIPTS: Slides {', '.join(map(str, missing_scripts))}")
else:
    print(f"\n✅ ALL SLIDES HAVE SPEAKER SCRIPTS!")

print("=" * 80)

# Additional checks
print("\nSLIDES WITH MULTIPLE DIAGRAMS (3+ speaker scripts):")
for d in slide_details:
    if d['scripts'] >= 3:
        print(f"  Slide {d['num']}: {d['scripts']} scripts - {d['title']}")

print("\nSLIDES WITH SINGLE SCRIPT:")
for d in slide_details:
    if d['scripts'] == 1:
        print(f"  Slide {d['num']}: {d['title']}")
