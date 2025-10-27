#!/usr/bin/env python3
"""
Fix speaker script spacing: remove single blank lines between sentences,
keep single blank lines between paragraphs.
"""

import re

def fix_speaker_script_spacing(file_path):
    """Remove double spacing in speaker scripts while preserving paragraph breaks."""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split content by speaker script sections
    lines = content.split('\n')
    result_lines = []
    in_speaker_script = False
    buffer = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if entering speaker script section
        if line.startswith('## 🎤 **Speaker Script'):
            in_speaker_script = True
            result_lines.append(line)
            result_lines.append('')  # Keep one blank after header
            i += 1
            # Skip the blank line after header if present
            if i < len(lines) and lines[i] == '':
                i += 1
            continue

        # Check if leaving speaker script section (next ## heading or ---)
        if in_speaker_script and (line.startswith('## ') or line.startswith('---')):
            # Process buffered speaker script content
            if buffer:
                processed = process_speaker_buffer(buffer)
                result_lines.extend(processed)
                buffer = []
            in_speaker_script = False
            result_lines.append(line)
            i += 1
            continue

        # If in speaker script, buffer the content
        if in_speaker_script:
            buffer.append(line)
        else:
            result_lines.append(line)

        i += 1

    # Process any remaining buffer
    if buffer:
        processed = process_speaker_buffer(buffer)
        result_lines.extend(processed)

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result_lines))

    print(f"Fixed speaker script spacing in {file_path}")


def process_speaker_buffer(buffer):
    """Process speaker script content to fix spacing."""
    result = []
    i = 0

    while i < len(buffer):
        line = buffer[i]

        # If current line has content
        if line.strip():
            result.append(line)

            # Look ahead for blank lines
            blank_count = 0
            j = i + 1
            while j < len(buffer) and buffer[j] == '':
                blank_count += 1
                j += 1

            # If there are 2+ consecutive blank lines, it's a paragraph break
            # Keep one blank line
            if blank_count >= 2:
                result.append('')
            # If there's 1 blank line and the next line also has content,
            # skip it (remove single spacing between lines)
            # If it's the last content line, keep one blank
            elif blank_count == 1:
                if j < len(buffer) and buffer[j].strip():
                    # Skip the blank - sentences flow together
                    pass
                else:
                    # Keep blank at end
                    result.append('')

            # Skip past the blank lines we counted
            i = j
        else:
            # Empty line - already counted in lookahead
            i += 1

    return result


if __name__ == '__main__':
    file_path = r'C:\dev\wildfire\docs\CHALLENGE3_DATA_CONSUMPTION_PRESENTATION.md'
    fix_speaker_script_spacing(file_path)
