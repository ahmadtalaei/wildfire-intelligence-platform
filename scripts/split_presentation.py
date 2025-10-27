#!/usr/bin/env python3
"""
Script to split CHALLENGE_2_FIRE_DATA_PRESENTATION.md into:
1. Slides-only file (remove all speaker notes)
2. Speaker notes file (combine first 2 scripts, add transitions)
"""

import re
from pathlib import Path

# Transition phrases to vary the language
TRANSITIONS = [
    "This slide presents",
    "The next slide shows",
    "Moving forward, this slide displays",
    "Now we turn to",
    "Let's examine",
    "This slide demonstrates",
    "The following slide reveals",
    "Next, we see",
    "This slide highlights",
    "Moving to the next slide, we find",
    "The upcoming slide illustrates",
    "Let's now explore",
    "This slide covers",
    "Turning our attention to",
    "The next slide details"
]

def read_file(filepath):
    """Read the presentation file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def extract_slides_and_scripts(content):
    """
    Parse the content and extract slides with their speaker scripts.
    Returns a list of dicts with 'slide_content' and 'speaker_scripts'
    """
    # Split by slide headers (## Slide N:)
    slide_pattern = r'^## Slide \d+:'
    slides = []

    # Find all slide positions
    slide_matches = list(re.finditer(slide_pattern, content, re.MULTILINE))

    for i, match in enumerate(slide_matches):
        start_pos = match.start()
        # End is the start of next slide, or end of file
        end_pos = slide_matches[i + 1].start() if i + 1 < len(slide_matches) else len(content)

        slide_text = content[start_pos:end_pos]

        # Extract slide content (everything before first speaker script)
        speaker_script_pattern = r'^## 🎤.*?$'
        first_script_match = re.search(speaker_script_pattern, slide_text, re.MULTILINE)

        if first_script_match:
            slide_content = slide_text[:first_script_match.start()].rstrip()
        else:
            slide_content = slide_text.rstrip()

        # Extract all speaker scripts for this slide
        speaker_scripts = []
        script_matches = list(re.finditer(speaker_script_pattern, slide_text, re.MULTILINE))

        for j, script_match in enumerate(script_matches):
            script_start = script_match.start()
            # Script ends at next script header or at end of slide
            if j + 1 < len(script_matches):
                script_end = script_matches[j + 1].start()
            else:
                script_end = len(slide_text)

            script_header = script_match.group(0)
            script_content = slide_text[script_start:script_end].strip()

            # Extract just the text content (remove the header and extract quoted text)
            script_text = script_content[len(script_header):].strip()

            # Remove leading/trailing quotes if present
            script_text = script_text.strip('"\'')

            speaker_scripts.append({
                'header': script_header,
                'content': script_text
            })

        slides.append({
            'slide_content': slide_content,
            'speaker_scripts': speaker_scripts,
            'slide_number': i + 1
        })

    return slides

def create_slides_only(slides):
    """Create slides-only content (remove all speaker scripts)"""
    # Get everything before first slide (table of contents, etc)
    slides_content = []

    for slide in slides:
        slides_content.append(slide['slide_content'])

    return '\n\n---\n\n'.join(slides_content)

def create_speaker_notes(slides):
    """
    Create speaker notes file with:
    - Combined first 2 scripts from each slide
    - Transition phrases between slides
    - 3rd script separate if about diagram/chart
    """
    speaker_notes = []
    transition_idx = 0

    for slide_idx, slide in enumerate(slides):
        scripts = slide['speaker_scripts']
        slide_num = slide['slide_number']

        # Extract slide title from slide content
        title_match = re.search(r'^## Slide \d+: (.+?)$', slide['slide_content'], re.MULTILINE)
        slide_title = title_match.group(1) if title_match else f"Slide {slide_num}"

        # Start with slide header
        speaker_notes.append(f"\n## Slide {slide_num}: {slide_title}\n")

        if len(scripts) == 0:
            speaker_notes.append("(No speaker notes for this slide)\n")
            continue

        # Combine first 2 scripts if there are 2 or more
        if len(scripts) >= 2:
            combined_text = scripts[0]['content'] + "\n\n" + scripts[1]['content']
            speaker_notes.append(combined_text.strip())
        elif len(scripts) == 1:
            speaker_notes.append(scripts[0]['content'].strip())

        # Add transition phrase for next slide (except for last slide)
        if slide_idx < len(slides) - 1:
            transition = TRANSITIONS[transition_idx % len(TRANSITIONS)]
            next_title_match = re.search(r'^## Slide \d+: (.+?)$', slides[slide_idx + 1]['slide_content'], re.MULTILINE)
            next_title = next_title_match.group(1) if next_title_match else "the next topic"

            speaker_notes.append(f"\n\n{transition} {next_title.lower()}.\n")
            transition_idx += 1

        # If there's a 3rd script, check if it's about diagram/chart
        if len(scripts) >= 3:
            third_script = scripts[2]['content']
            # Check if it's about a diagram or chart
            is_diagram = any(word in scripts[2]['header'].lower() or word in third_script.lower()[:100]
                           for word in ['diagram', 'chart', 'graph', 'architecture', 'visualization', 'flow'])

            if is_diagram:
                # Add with "Now this diagram..." prefix
                diagram_intros = ["Now this diagram", "Next, this chart", "This visualization",
                                "The diagram below", "This architectural diagram"]
                intro = diagram_intros[transition_idx % len(diagram_intros)]
                speaker_notes.append(f"\n{intro} {third_script[0].lower()}{third_script[1:]}")
            else:
                speaker_notes.append(f"\n\n{third_script}")

    return '\n'.join(speaker_notes)

def main():
    # File paths
    input_file = Path(r"C:\dev\wildfire\docs\CHALLENGE_2_FIRE_DATA_PRESENTATION.md")
    slides_only_file = Path(r"C:\dev\wildfire\docs\CHALLENGE_2_SLIDES_ONLY.md")
    speaker_notes_file = Path(r"C:\dev\wildfire\docs\CHALLENGE_2_SPEAKER_NOTES.md")

    print(f"Reading {input_file}...")
    content = read_file(input_file)

    # Extract header content (everything before first slide)
    first_slide_match = re.search(r'^## Slide 1:', content, re.MULTILINE)
    if first_slide_match:
        header_content = content[:first_slide_match.start()].rstrip()
    else:
        header_content = ""

    print("Parsing slides and speaker scripts...")
    slides = extract_slides_and_scripts(content)
    print(f"Found {len(slides)} slides")

    # Create slides-only version
    print("Creating slides-only version...")
    slides_only_content = header_content + "\n\n---\n\n" + create_slides_only(slides)

    with open(slides_only_file, 'w', encoding='utf-8') as f:
        f.write(slides_only_content)
    print(f"Created {slides_only_file}")

    # Create speaker notes
    print("Creating speaker notes...")
    speaker_notes_header = f"""# Challenge 2: Data Storage - Speaker Notes
## CAL FIRE Space-Based Data Acquisition, Storage and Dissemination Challenge

This document contains the speaker notes for the Challenge 2 presentation.

---
"""
    speaker_notes_content = speaker_notes_header + create_speaker_notes(slides)

    with open(speaker_notes_file, 'w', encoding='utf-8') as f:
        f.write(speaker_notes_content)
    print(f"Created {speaker_notes_file}")

    print("\nDone! Files created:")
    print(f"  - {slides_only_file}")
    print(f"  - {speaker_notes_file}")

if __name__ == "__main__":
    main()
