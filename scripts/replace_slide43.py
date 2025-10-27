"""Replace Slide 43 with redesigned version"""

# Read the redesigned slide
with open(r'C:\dev\wildfire\docs\SLIDE_43_REDESIGN.md', 'r', encoding='utf-8') as f:
    redesign_content = f.read()

# Extract just the slide content (skip the design approach section)
slide_start = redesign_content.find('## Slide 43:')
redesigned_slide = redesign_content[slide_start:]

# Read the main presentation
with open(r'C:\dev\wildfire\docs\CHALLENGE_1_FIRE_DATA_PRESENTATION.md', 'r', encoding='utf-8') as f:
    presentation = f.read()

# Find the start and end of Slide 43
slide43_start = presentation.find('## Slide 43: Why Our Solution Wins')
# Find the next section after Slide 43 (end of file)
slide43_end = len(presentation) - 1  # End at EOF

# Replace Slide 43
new_presentation = (
    presentation[:slide43_start] +
    redesigned_slide +
    '\n\n---\n\n'
)

# Write back
with open(r'C:\dev\wildfire\docs\CHALLENGE_1_FIRE_DATA_PRESENTATION.md', 'w', encoding='utf-8') as f:
    f.write(new_presentation)

print("✅ Slide 43 replacement complete!")
print(f"Old Slide 43 length: {slide43_end - slide43_start} characters")
print(f"New Slide 43 length: {len(redesigned_slide)} characters")
