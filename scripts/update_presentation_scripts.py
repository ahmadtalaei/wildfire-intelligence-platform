#!/usr/bin/env python3
"""
Script to update all speaker scripts in the Challenge 3 presentation with:
1. Proper header format: ## 🎤 **Speaker Script - [Slide Title]**
2. Ellipses (...) at end of lines
3. Transition words (First, Next, Meanwhile, Also, Plus, Then, In addition)
"""

import re

def update_speaker_script_header(content):
    """Update speaker script headers to include slide titles"""
    # Pattern to match current headers
    pattern = r'## 🎤 \*\*Speaker Script\*\*'

    # Find all slides
    slides = re.finditer(r'## Slide (\d+): (.+?)\n', content)

    for slide_match in slides:
        slide_num = slide_match.group(1)
        slide_title = slide_match.group(2)

        # Find the speaker script for this slide
        # Look for the next speaker script after this slide
        slide_start = slide_match.end()
        next_slide = re.search(r'\n## Slide \d+:', content[slide_start:])

        if next_slide:
            slide_end = slide_start + next_slide.start()
        else:
            slide_end = len(content)

        slide_content = content[slide_start:slide_end]

        # Update the speaker script header in this section
        updated_section = re.sub(
            r'## 🎤 \*\*Speaker Script\*\*',
            f'## 🎤 **Speaker Script - {slide_title}**',
            slide_content
        )

        # Replace in main content
        content = content[:slide_start] + updated_section + content[slide_end:]

    return content

def add_ellipses_to_lines(content):
    """Add ellipses to ends of lines in speaker scripts that don't have them"""
    lines = content.split('\n')
    updated_lines = []
    in_speaker_script = False

    for line in lines:
        # Check if we're entering a speaker script section
        if '## 🎤 **Speaker Script' in line:
            in_speaker_script = True
            updated_lines.append(line)
            continue

        # Check if we're leaving speaker script (next slide or ----)
        if in_speaker_script and (line.startswith('## Slide') or line.startswith('---')):
            in_speaker_script = False
            updated_lines.append(line)
            continue

        # If in speaker script and line has content but no ellipses
        if in_speaker_script and line.strip() and not line.startswith('##'):
            # Don't add if already has ellipses or is empty
            if not line.rstrip().endswith('...') and not line.rstrip().endswith('..'):
                line = line.rstrip() + '...'

        updated_lines.append(line)

    return '\n'.join(updated_lines)

print("Script created successfully!")
print("This script would update speaker scripts, but manual editing is safer for this task.")
print("Continuing with manual slide-by-slide updates...")
