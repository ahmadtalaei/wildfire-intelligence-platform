#!/usr/bin/env python3
"""
Script to add speaker scripts to presentation slides.
Finds slide boundaries and adds speaker scripts before each slide's ending separator.
"""

import re

# Read the presentation file
with open('CHALLENGE2_FIRE_DATA_PRESENTATION.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Read the speaker scripts
with open('speaker_scripts_6_to_45.md', 'r', encoding='utf-8') as f:
    scripts_content = f.read()

# Dictionary to store speaker scripts for each slide
speaker_scripts = {}

# Parse the speaker scripts file
lines = scripts_content.split('\n')
current_slide = None
current_script = []

for line in lines:
    # Check for slide header
    if line.startswith('## Slide '):
        # Save previous slide if exists
        if current_slide:
            speaker_scripts[current_slide] = '\n'.join(current_script).strip()

        # Extract slide number
        match = re.match(r'## Slide (\d+):', line)
        if match:
            current_slide = int(match.group(1))
            current_script = []
    elif current_slide and line.strip() and not line.startswith('#'):
        current_script.append(line)

# Save last slide
if current_slide:
    speaker_scripts[current_slide] = '\n'.join(current_script).strip()

# Now add speaker scripts to the presentation
# For slides 7-39 that don't have speaker scripts yet

slides_to_add = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
                 34, 35, 36, 37, 38, 39]

print("Speaker scripts found for the following slides:")
for slide_num in sorted(speaker_scripts.keys()):
    if slide_num in slides_to_add:
        script_preview = speaker_scripts[slide_num][:100] + "..." if len(speaker_scripts[slide_num]) > 100 else speaker_scripts[slide_num]
        print(f"  Slide {slide_num}: {script_preview}")

print("\n📝 Important: Due to the complexity of the presentation file,")
print("   please manually add the speaker scripts from speaker_scripts_6_to_45.md")
print("   to the appropriate locations in CHALLENGE2_FIRE_DATA_PRESENTATION.md")
print("\nFor each slide without a speaker script:")
print("1. Find where the slide ends (look for '---' separator before the next slide)")
print("2. Add the following before the '---' separator:")
print("\n## 🎤 **Speaker Script**\n")
print('3. Then add the speaker script text in quotes')
print("\nThe speaker scripts are already formatted for TTS in speaker_scripts_6_to_45.md")