#!/usr/bin/env python3
"""
Insert completed slides into final presentation
Replaces [TO BE COMPLETED] placeholders with actual content
"""

import re

def read_slide(filename, slide_num):
    """Extract slide content from a file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the slide section
        pattern = f'## Slide {slide_num}:.*?(?=## Slide \\d+:|This completes|$)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            return match.group(0).strip()
        return None
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None

def insert_slides():
    """Insert completed slides into final presentation"""

    final_file = r"C:\dev\wildfire\docs\CHALLENGE3_FINAL_PRESENTATION_ALL_55_SLIDES.md"
    slides_file = r"C:\dev\wildfire\docs\SLIDES_13_15_PLATFORM_COMPLETION.md"

    print("=" * 70)
    print(" INSERTING COMPLETED SLIDES INTO FINAL PRESENTATION")
    print("=" * 70)

    # Read final presentation
    print(f"\n📖 Reading: {final_file}")
    with open(final_file, 'r', encoding='utf-8') as f:
        presentation = f.read()

    # Track replacements
    replacements = 0

    # Insert slides 13, 14, 15
    for slide_num in [13, 14, 15]:
        print(f"\n🔍 Processing Slide {slide_num}...")

        # Read slide content
        slide_content = read_slide(slides_file, slide_num)

        if slide_content:
            # Find and replace placeholder
            placeholder_pattern = f'## Slide {slide_num}: \\[TO BE COMPLETED\\].*?---'

            if re.search(placeholder_pattern, presentation, re.DOTALL):
                presentation = re.sub(
                    placeholder_pattern,
                    slide_content + '\n\n---',
                    presentation,
                    flags=re.DOTALL
                )
                print(f"  ✅ Inserted Slide {slide_num}")
                replacements += 1
            else:
                print(f"  ⚠️  Placeholder not found for Slide {slide_num}")
        else:
            print(f"  ❌ Could not read Slide {slide_num} content")

    # Write updated presentation
    if replacements > 0:
        print(f"\n💾 Writing updated presentation...")
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write(presentation)
        print(f"  ✅ Saved {final_file}")

    # Count remaining placeholders
    remaining = presentation.count('[TO BE COMPLETED]')
    total_slides = 55
    completed = total_slides - remaining

    print("\n" + "=" * 70)
    print(" INSERTION COMPLETE")
    print("=" * 70)
    print(f"\n📊 Presentation Status:")
    print(f"   Total Slides:     {total_slides}")
    print(f"   Complete:         {completed}")
    print(f"   Remaining:        {remaining}")
    print(f"   Progress:         {completed * 100 // total_slides}%")
    print(f"\n✅ Inserted {replacements} slides this run")

    if remaining > 0:
        print(f"\n⚠️  Still need to complete {remaining} slides:")
        # Find which slides are missing
        missing = []
        for i in range(1, 56):
            if f'## Slide {i}: [TO BE COMPLETED]' in presentation:
                missing.append(i)
        print(f"   {missing}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    insert_slides()
