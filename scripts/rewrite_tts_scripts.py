#!/usr/bin/env python3
"""
TTS Speaker Script Rewriter
Rewrites speaker scripts in CHALLENGE_1_FIRE_DATA_PRESENTATION.md for natural AI voice narration
"""

import re
from pathlib import Path


def expand_number(match):
    """Convert numbers to words for TTS"""
    num = match.group(0).replace(',', '')
    try:
        n = int(num)
        if n == 0:
            return "zero"
        # Simple number expansion (extend as needed)
        ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
        teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
                 "sixteen", "seventeen", "eighteen", "nineteen"]
        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

        if n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
        elif n < 1000:
            return ones[n // 100] + " hundred" + (" " + expand_number(type('obj', (object,), {'group': lambda self, x: str(n % 100)})()) if n % 100 != 0 else "")
        elif n < 1000000:
            thousands = n // 1000
            remainder = n % 1000
            result = expand_number(type('obj', (object,), {'group': lambda self, x: str(thousands)})()) + " thousand"
            if remainder:
                result += " " + expand_number(type('obj', (object,), {'group': lambda self, x: str(remainder)})())
            return result
        else:
            return num  # Return original for very large numbers
    except:
        return num


def rewrite_speaker_script(script_text):
    """Rewrite a single speaker script section for TTS"""

    # Remove bold markers that aren't needed for TTS
    script_text = re.sub(r'\*\*(.*?)\*\*', r'\1', script_text)

    # Replace technical patterns for better TTS
    replacements = {
        # Arrows
        r'→': ' leads to ',
        r'->': ' leads to ',

        # Technical abbreviations that need spelling
        r'\bSHA-256\b': 'S H A two fifty-six',
        r'\bp95\b': 'p ninety-five',
        r'\bp99\b': 'p ninety-nine',
        r'\bp50\b': 'p fifty',

        # Units
        r'(\d+)\s*ms\b': lambda m: f"{m.group(1)} milliseconds",
        r'(\d+)\s*MB\b': lambda m: f"{m.group(1)} megabytes",
        r'(\d+)\s*GB\b': lambda m: f"{m.group(1)} gigabytes",
        r'(\d+)\s*KB\b': lambda m: f"{m.group(1)} kilobytes",

        # Percentages - convert to words
        r'(\d+(?:\.\d+)?)\%': lambda m: f"{m.group(1)} percent",

        # Times multiplication
        r'(\d+)x\b': lambda m: f"{m.group(1)} times",

        # Currency
        r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b': lambda m: f"{m.group(1)} dollars",

        # Port numbers
        r'Port (\d+)': lambda m: f"Port {m.group(1)}",

        # Remove markdown headers inside scripts
        r'^###\s+': '',

        # Clean up common TTS-unfriendly patterns
        r'\bM Q T T\b': 'M Q T T',
        r'\bM L\b': 'M L',
        r'\bC S V\b': 'C S V',
        r'\bJ SON\b': 'JSON',
    }

    for pattern, replacement in replacements.items():
        if callable(replacement):
            script_text = re.sub(pattern, replacement, script_text)
        else:
            script_text = re.sub(pattern, replacement, script_text)

    # Convert standalone numbers to words (be conservative)
    # script_text = re.sub(r'\b\d{1,4}\b', expand_number, script_text)

    # Add natural pauses with ellipses where appropriate
    # Add ellipsis after transition words if not already present
    transition_words = ['First', 'Second', 'Third', 'Next', 'Then', 'Also', 'Plus', 'Meanwhile', 'Finally']
    for word in transition_words:
        script_text = re.sub(rf'\b{word}\.\.\.', f'{word}...', script_text)
        script_text = re.sub(rf'\b{word}(?!\.\.\.)', f'{word}...', script_text)

    # Clean up excessive whitespace while preserving intentional line breaks
    script_text = re.sub(r'\n\n\n+', '\n\n', script_text)

    return script_text


def process_file(input_file, output_file):
    """Process the entire presentation file"""

    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all speaker script sections
    # Pattern: ## 🎤 **Speaker Script** followed by content until next ## heading
    pattern = r'(## 🎤 \*\*Speaker Script\*\*\n)(.*?)(?=\n##[^#]|\Z)'

    def replace_script(match):
        header = match.group(1)
        script_content = match.group(2)
        rewritten = rewrite_speaker_script(script_content)
        return header + rewritten

    print("Rewriting speaker scripts...")
    # Use DOTALL flag to match across newlines
    new_content = re.sub(pattern, replace_script, content, flags=re.DOTALL)

    # Count how many scripts were processed
    script_count = len(re.findall(r'## 🎤 \*\*Speaker Script\*\*', new_content))

    print(f"Processed {script_count} speaker scripts")
    print(f"Writing to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("✅ Complete!")
    print(f"Output saved to: {output_file}")


def main():
    # File paths
    docs_dir = Path(__file__).parent.parent / 'docs'
    input_file = docs_dir / 'CHALLENGE_1_FIRE_DATA_PRESENTATION.md'
    output_file = docs_dir / 'CHALLENGE_1_FIRE_DATA_PRESENTATION_TTS.md'

    if not input_file.exists():
        print(f"❌ Error: Input file not found: {input_file}")
        return

    process_file(input_file, output_file)


if __name__ == '__main__':
    main()
