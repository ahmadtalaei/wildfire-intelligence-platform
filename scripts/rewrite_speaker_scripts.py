#!/usr/bin/env python3
"""
Rewrite speaker scripts in CHALLENGE_1_FIRE_DATA_PRESENTATION.md for TTS-friendly narration.
Preserves all structure, diagrams, and visual content.
"""

import re
import sys

def expand_for_tts(text):
    """Apply TTS-friendly transformations to text."""

    # Replace colons with natural connecting words (context-dependent)
    # Pattern: "word/phrase:" -> "word/phrase is"
    text = re.sub(r'([A-Za-z0-9\s\-]+):\s*([A-Z])', r'\1 is \2', text)
    text = re.sub(r'([A-Za-z0-9\s\-]+):\s*([a-z])', r'\1 provides \2', text)

    # Replace arrows
    text = text.replace(' → ', ' leads to ')
    text = text.replace('→', ' results in ')

    # Replace equals
    text = text.replace(' = ', ' is equal to ')
    text = text.replace('=', ' equals ')

    # Expand percentages
    def expand_percent(match):
        num = match.group(1)
        try:
            val = float(num)
            if '.' in num:
                # Keep decimals for precision
                return f"{num} percent"
            else:
                return f"{num} percent"
        except:
            return match.group(0)

    text = re.sub(r'(\d+\.?\d*)%', expand_percent, text)

    # Expand times: 3x -> three times
    times_map = {
        '1x': 'one time',
        '2x': 'two times',
        '3x': 'three times',
        '4x': 'four times',
        '5x': 'five times',
        '6x': 'six times',
        '7x': 'seven times',
        '8x': 'eight times',
        '9x': 'nine times',
        '10x': 'ten times',
        '12x': 'twelve times',
        '14x': 'fourteen times',
        '15x': 'fifteen times',
        '20x': 'twenty times',
        '50x': 'fifty times',
        '100x': 'one hundred times',
        '200x': 'two hundred times',
        '345x': 'three hundred forty-five times',
    }

    for old, new in times_map.items():
        text = text.replace(old, new)

    # Expand common numbers in specific patterns
    # Spell out numbers with commas
    def spell_number(match):
        num_str = match.group(0).replace(',', '')
        try:
            num = int(num_str)
            if num < 20:
                words = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
                        'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
                        'seventeen', 'eighteen', 'nineteen']
                return words[num]
            elif num < 100:
                tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
                if num percent 10 == 0:
                    return tens[num // 10]
                else:
                    return tens[num // 10] + '-' + words[num percent 10]
            elif num < 1000:
                hundreds = num // 100
                remainder = num percent 100
                result = words[hundreds] + ' hundred'
                if remainder > 0:
                    result += ' ' + spell_number(type('obj', (object,), {'group': lambda i: str(remainder)})())
                return result
            elif num < 10000:
                thousands = num // 1000
                remainder = num percent 1000
                result = words[thousands] + ' thousand'
                if remainder > 0:
                    result += ' ' + spell_number(type('obj', (object,), {'group': lambda i: str(remainder)})())
                return result
            else:
                # For larger numbers, spell out digit by digit with commas
                return num_str  # Keep as-is for very large numbers
        except:
            return match.group(0)

    # Expand MB/GB
    text = re.sub(r'(\d+)\s*MB', r'\1 megabytes', text)
    text = re.sub(r'(\d+)\s*GB', r'\1 gigabytes', text)

    # Expand milliseconds
    text = re.sub(r'(\d+)ms', r'\1 milliseconds', text)

    # Expand specific technical codes
    text = text.replace('SHA-256', 'S H A two fifty-six')
    text = text.replace('p95', 'p ninety-five')
    text = text.replace('p99', 'p ninety-nine')
    text = text.replace('p50', 'p fifty')

    # Expand currency
    def expand_currency(match):
        amount = match.group(1).replace(',', '')
        return f"{amount} dollars"

    text = re.sub(r'\$([0-9,]+)', expand_currency, text)

    return text

def rewrite_speaker_script(script_text):
    """Rewrite a speaker script section to be TTS-friendly."""

    lines = script_text.split('\n')
    rewritten = []

    for line in lines:
        # Skip empty lines initially
        if not line.strip():
            rewritten.append('')
            continue

        # Apply TTS transformations
        line = expand_for_tts(line)

        # Remove excessive header repetition
        # (Will be done manually for context-specific cases)

        rewritten.append(line)

    return '\n'.join(rewritten)

def process_file(input_file, output_file):
    """Process the entire file, rewriting only speaker scripts."""

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all speaker script sections
    # Pattern: ## 🎤 **Speaker Script** followed by content until next ## or ---
    pattern = r'(## 🎤 \*\*Speaker Script\*\*\n)(.*?)(\n---|\n## [^🎤]|\Z)'

    def replace_script(match):
        header = match.group(1)
        script_content = match.group(2)
        footer = match.group(3)

        # Rewrite the script content
        rewritten_script = rewrite_speaker_script(script_content)

        return header + rewritten_script + footer

    # Replace all speaker scripts
    new_content = re.sub(pattern, replace_script, content, flags=re.DOTALL)

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✅ Processed {input_file}")
    print(f"✅ Output written to {output_file}")

if __name__ == '__main__':
    input_file = r'C:\dev\wildfire\docs\CHALLENGE_1_FIRE_DATA_PRESENTATION.md'
    output_file = r'C:\dev\wildfire\docs\CHALLENGE_1_FIRE_DATA_PRESENTATION_TTS.md'

    process_file(input_file, output_file)
