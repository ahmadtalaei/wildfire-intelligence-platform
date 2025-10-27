#!/usr/bin/env python3
"""
Comprehensive script to align all ASCII box right borders in markdown files.
Ensures all │ characters on the right side are vertically aligned for professional appearance.
"""

import re
import sys

def align_ascii_boxes_in_file(file_path):
    """Read file, fix all ASCII boxes, write back."""
    print(f"Reading {file_path}...")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return False

    # Split into lines
    lines = content.split('\n')
    total_lines = len(lines)
    print(f"Total lines in file: {total_lines}")

    # Find all ASCII box blocks
    i = 0
    box_count = 0
    fixed_count = 0

    while i < len(lines):
        line = lines[i]

        # Detect box start
        if line.strip().startswith('┌') and '─' in line:
            box_start = i
            box_width = len(line.strip())

            # Find box end
            j = i + 1
            while j < len(lines):
                if lines[j].strip().startswith('└') and '─' in lines[j]:
                    box_end = j
                    break
                j += 1
            else:
                # No matching end found
                i += 1
                continue

            box_count += 1
            print(f"\nBox {box_count}: lines {box_start+1}-{box_end+1}, width {box_width}")

            # Fix all lines in this box
            needs_fix = False
            for k in range(box_start, box_end + 1):
                original = lines[k]
                fixed = align_box_line(lines[k], box_width)
                if fixed != original:
                    needs_fix = True
                    lines[k] = fixed

            if needs_fix:
                fixed_count += 1
                print(f"  ✓ Fixed")
            else:
                print(f"  - Already aligned")

            # Move past this box
            i = box_end + 1
        else:
            i += 1

    print(f"\n{'='*70}")
    print(f"Total boxes found: {box_count}")
    print(f"Boxes fixed: {fixed_count}")
    print(f"Boxes already aligned: {box_count - fixed_count}")
    print(f"{'='*70}\n")

    # Write back
    print(f"Writing aligned content to {file_path}...")
    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))

    print("✓ All ASCII boxes aligned successfully!")
    return True

def align_box_line(line, target_width):
    """Align a single line of an ASCII box to target width."""
    stripped = line.strip()

    if not stripped:
        return line

    # Handle top border
    if stripped.startswith('┌') and stripped.endswith('┐'):
        return '┌' + '─' * (target_width - 2) + '┐'

    # Handle middle separator
    if stripped.startswith('├') and stripped.endswith('┤'):
        return '├' + '─' * (target_width - 2) + '┤'

    # Handle bottom border
    if stripped.startswith('└') and stripped.endswith('┘'):
        return '└' + '─' * (target_width - 2) + '┘'

    # Handle content lines with │
    if '│' in stripped:
        # Find first and last │
        first_bar = stripped.find('│')
        last_bar = stripped.rfind('│')

        if first_bar == last_bar:
            # Only one │, likely at the end
            return line

        # Get content between first and last │
        content = stripped[first_bar:last_bar+1]
        current_width = len(content)

        if current_width < target_width:
            # Need to pad
            # Add spaces before the last │
            left_part = content[:-1]  # Everything except last │
            padding = ' ' * (target_width - current_width)
            return left_part + padding + '│'
        elif current_width == target_width:
            # Already correct
            return content
        else:
            # Line is too wide (shouldn't happen with proper boxes)
            return content[:target_width-1] + '│'

    return line

if __name__ == '__main__':
    # Check if file path provided as argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Default to Challenge 3 file
        file_path = r'C:\dev\wildfire\docs\CHALLENGE3_SLIDES_18_40_COMPLETE.md'

    print("="*70)
    print("ASCII BOX ALIGNMENT TOOL")
    print("="*70)
    print()

    success = align_ascii_boxes_in_file(file_path)

    if not success:
        sys.exit(1)
