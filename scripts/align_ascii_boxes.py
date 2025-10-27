#!/usr/bin/env python3
"""
Script to align right-side borders of ASCII art boxes in markdown files.
Ensures all │ characters on the right side are vertically aligned.
"""

import re
from typing import List, Tuple

def find_box_sections(lines: List[str]) -> List[Tuple[int, int]]:
    """Find start and end indices of ASCII box sections."""
    sections = []
    in_box = False
    start_idx = None

    for i, line in enumerate(lines):
        # Detect start of ASCII box (top border)
        if line.strip().startswith('┌') and '─' in line:
            in_box = True
            start_idx = i
        # Detect end of ASCII box (bottom border)
        elif in_box and line.strip().startswith('└') and '─' in line:
            sections.append((start_idx, i))
            in_box = False
            start_idx = None

    return sections

def get_max_content_width(lines: List[str], start: int, end: int) -> int:
    """Calculate the maximum content width needed for a box section."""
    max_width = 0

    for i in range(start, end + 1):
        line = lines[i]
        # Skip empty lines
        if not line.strip():
            continue

        # Remove leading/trailing box characters to get content
        # Handle different box line types
        if line.strip().startswith(('┌', '├', '└')):
            # Border lines - get the width from the dashes
            content = line.strip()
            max_width = max(max_width, len(content))
        elif '│' in line:
            # Content lines - measure from first │ to last │
            first_bar = line.find('│')
            last_bar = line.rfind('│')
            if first_bar != -1 and last_bar != -1 and first_bar != last_bar:
                width = last_bar - first_bar + 1
                max_width = max(max_width, width)

    return max_width

def normalize_box_line(line: str, target_width: int) -> str:
    """Normalize a single line of an ASCII box to target width."""
    stripped = line.strip()

    # Handle empty lines
    if not stripped:
        return line

    # Handle top/bottom borders
    if stripped.startswith('┌'):
        return '┌' + '─' * (target_width - 2) + '┐'
    elif stripped.startswith('├'):
        return '├' + '─' * (target_width - 2) + '┤'
    elif stripped.startswith('└'):
        return '└' + '─' * (target_width - 2) + '┘'

    # Handle content lines with │
    if '│' in stripped:
        # Find all │ positions
        bars = [i for i, c in enumerate(stripped) if c == '│']

        if len(bars) < 2:
            return line  # Can't normalize single bar lines

        # Get content between first and last │
        first_bar = bars[0]
        last_bar = bars[-1]

        # Extract the content between the bars
        content = stripped[first_bar:last_bar+1]

        # Calculate padding needed
        content_width = last_bar - first_bar + 1
        padding_needed = target_width - content_width

        if padding_needed > 0:
            # Find the position of the last │ in content
            # Add padding before the last │
            left_part = content[:-1]  # Everything except last │
            right_part = content[-1]  # The last │

            # Add spaces before the last │
            normalized = left_part + ' ' * padding_needed + right_part
            return normalized
        else:
            return content

    return line

def align_ascii_boxes(file_path: str) -> None:
    """Main function to align all ASCII boxes in a file."""
    print(f"Reading {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Remove trailing newlines but remember them
    original_lines = lines.copy()
    lines = [line.rstrip('\n\r') for line in lines]

    # Find all box sections
    sections = find_box_sections(lines)
    print(f"Found {len(sections)} ASCII box sections")

    if not sections:
        print("No ASCII boxes found!")
        return

    # Process each section
    for idx, (start, end) in enumerate(sections):
        print(f"Processing box {idx + 1}/{len(sections)} (lines {start+1}-{end+1})...")

        # Determine the target width for this box
        # Use the width of the top border line
        top_line = lines[start].strip()
        target_width = len(top_line)

        if target_width == 0:
            continue

        print(f"  Target width: {target_width} characters")

        # Normalize each line in this section
        for i in range(start, end + 1):
            original = lines[i]
            normalized = normalize_box_line(lines[i], target_width)

            if normalized != original:
                lines[i] = normalized

        print(f"  ✓ Box {idx + 1} aligned")

    # Write back to file
    print(f"\nWriting aligned content back to {file_path}...")
    with open(file_path, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')

    print("✓ All ASCII boxes aligned successfully!")

if __name__ == '__main__':
    file_path = r'C:\dev\wildfire\docs\CHALLENGE2_FIRE_DATA_PRESENTATION.md'
    align_ascii_boxes(file_path)
