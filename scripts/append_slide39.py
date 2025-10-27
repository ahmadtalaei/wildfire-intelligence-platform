#!/usr/bin/env python
"""Append Slide 39 to Challenge 2 presentation"""
import re

# Read the redesign file
with open(r'C:\dev\wildfire\docs\CHALLENGE_2_SLIDE_39_REDESIGN.md', 'r', encoding='utf-8') as f:
    redesign_content = f.read()

# Extract content starting from '## Slide 39:'
match = re.search(r'(## Slide 39:.*)', redesign_content, re.DOTALL)
if match:
    slide39_content = match.group(1)

    # Read the main presentation
    with open(r'C:\dev\wildfire\docs\CHALLENGE_2_FIRE_DATA_PRESENTATION.md', 'r', encoding='utf-8') as f:
        main_content = f.read()

    # Append Slide 39 with separators
    new_content = main_content + '\n\n---\n\n' + slide39_content

    # Write back
    with open(r'C:\dev\wildfire\docs\CHALLENGE_2_FIRE_DATA_PRESENTATION.md', 'w', encoding='utf-8') as f:
        f.write(new_content)

    print('✅ Slide 39 successfully added to Challenge 2 presentation!')
    print(f'Added {len(slide39_content)} characters')
    print(f'New presentation total length: {len(new_content)} characters')
else:
    print('❌ Could not find Slide 39 in redesign file')
