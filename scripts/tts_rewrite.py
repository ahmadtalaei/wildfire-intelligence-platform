#!/usr/bin/env python3
"""
Rewrite speaker scripts for TTS-friendly narration in CHALLENGE_1_FIRE_DATA_PRESENTATION.md
Preserves ALL structure, diagrams, tables, and visual content.
Only rewrites content within ## 🎤 **Speaker Script** sections.
"""

import re

def process_speaker_scripts(input_file, output_file):
    """Read file and rewrite only speaker script sections."""

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split content by speaker script sections
    # Pattern: Captures everything between "## 🎤 **Speaker Script**" and next "---" or "## " (but not "## 🎤")
    parts = []
    last_end = 0

    # Find all speaker script sections
    pattern = r'(## 🎤 \*\*Speaker Script\*\*\n)(.*?)(\n(?=---|## (?!🎤))|\Z)'

    for match in re.finditer(pattern, content, re.DOTALL):
        # Add everything before this speaker script
        parts.append(content[last_end:match.start()])

        # Add the header
        parts.append(match.group(1))

        # Process and add the rewritten script content
        script_content = match.group(2)
        rewritten_script = rewrite_script_for_tts(script_content)
        parts.append(rewritten_script)

        # Add the footer (--- or next section)
        parts.append(match.group(3))

        last_end = match.end()

    # Add any remaining content
    parts.append(content[last_end:])

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(parts))

    print(f"✅ Successfully processed {input_file}")
    print(f"✅ Output written to {output_file}")

def rewrite_script_for_tts(script):
    """Rewrite a single speaker script for TTS narration."""

    # Apply TTS transformations
    text = script

    # Replace colons with natural words (but preserve bullets and formatting)
    #text = re.sub(r'([A-Za-z0-9\-\s]+):\s+', r'\1 provides ', text)

    # Replace arrows
    text = text.replace(' → ', ' leads to ')
    text = text.replace('→', ' results in ')

    # Replace equals
    text = text.replace(' = ', ' is equal to ')

    # Expand percentages
    text = re.sub(r'(\d+\.?\d*)%', r'\1 percent', text)

    # Expand times
    times_replacements = {
        '20-50x': 'twenty to fifty times',
        '50-100x': 'fifty to one hundred times',
        '100-200x': 'one hundred to two hundred times',
        '14.6x': 'fourteen point six times',
        '345x': 'three hundred forty-five times',
        '10x': 'ten times',
        '3x': 'three times',
        '4x': 'four times',
        '5x': 'five times',
        '7x': 'seven times',
        '41x': 'forty-one times',
        '13x': 'thirteen times',
        '32x': 'thirty-two times',
    }
    for old, new in times_replacements.items():
        text = text.replace(old, new)

    # Expand MB/GB
    text = re.sub(r'(\d+)\s*MB', r'\1 megabytes', text)
    text = re.sub(r'(\d+)\s*GB', r'\1 gigabytes', text)

    # Expand milliseconds
    text = re.sub(r'(\d+)ms', r'\1 milliseconds', text)

    # Expand specific codes
    text = text.replace('SHA-256', 'S H A two fifty-six')
    text = text.replace('p95', 'p ninety-five')
    text = text.replace('p99', 'p ninety-nine')
    text = text.replace('p50', 'p fifty')

    # Expand numbers with commas
    def spell_large_number(match):
        num_str = match.group(0).replace(',', '')
        num = int(num_str)

        if num < 20:
            words = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
                    'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
                    'seventeen', 'eighteen', 'nineteen']
            return words[num]
        elif num < 100:
            tens_words = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
            ones_words = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
            return tens_words[num // 10] + ('' if num % 10 == 0 else ' ' + ones_words[num % 10])
        elif num < 1000:
            ones_words = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
            result = ones_words[num // 100] + ' hundred'
            remainder = num % 100
            if remainder > 0:
                result += ' ' + spell_large_number(type('', (), {'group': lambda i: str(remainder)})())
            return result
        elif num < 10000:
            ones_words = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
            result = ones_words[num // 1000] + ' thousand'
            remainder = num % 1000
            if remainder > 0:
                result += ' ' + spell_large_number(type('', (), {'group': lambda i: str(remainder)})())
            return result
        elif num < 100000:
            tens_part = num // 1000
            result = spell_large_number(type('', (), {'group': lambda i: str(tens_part)})()) + ' thousand'
            remainder = num % 1000
            if remainder > 0:
                result += ' ' + spell_large_number(type('', (), {'group': lambda i: str(remainder)})())
            return result
        else:
            # Keep very large numbers as-is
            return num_str

    # Apply number spelling for common patterns
    text = re.sub(r'\b\d{1,2},\d{3}\b', spell_large_number, text)
    text = re.sub(r'\b\d{4,5}\b', spell_large_number, text)

    # Expand currency
    text = re.sub(r'\$(\d+),(\d+)/year', r'\1,\2 dollars per year', text)
    text = re.sub(r'\$(\d+),(\d+)', r'\1,\2 dollars', text)
    text = re.sub(r'\$(\d+)', r'\1 dollars', text)

    # Now spell the dollar amounts
    def spell_dollar_amount(match):
        amount = match.group(1).replace(',', '')
        spelled = spell_large_number(type('', (), {'group': lambda i: amount})())
        return spelled + ' dollars' + match.group(2)

    text = re.sub(r'(\d{1,3}(?:,\d{3})*) dollars( per year)?', spell_dollar_amount, text)

    return text

if __name__ == '__main__':
    input_file = r'C:\dev\wildfire\docs\CHALLENGE_1_FIRE_DATA_PRESENTATION.md'
    output_file = r'C:\dev\wildfire\docs\CHALLENGE_1_FIRE_DATA_PRESENTATION.md'  # Overwrite

    process_speaker_scripts(input_file, output_file)
