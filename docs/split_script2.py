import re

# Read the file
with open(r'C:\dev\wildfire\docs\CHALLENGE_2_FIRE_DATA_PRESENTATION.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Separate slides and speaker notes
slides_lines = []
speaker_notes = ['# Challenge 2: Data Storage - Speaker Notes\n\n']

in_speaker_section = False
current_speakers = []
slide_buffer = []

for line in lines:
    # Check if we hit a speaker section
    if line.startswith('## 🎤'):
        in_speaker_section = True
        current_speakers.append([])
        continue
    
    # Check if we hit a slide separator
    if line.strip() == '---':
        # Process any accumulated speaker notes
        if current_speakers:
            # Combine first 2 speaker scripts
            combined_text = []
            diagram_note = None
            
            for i, speaker_lines in enumerate(current_speakers):
                speaker_text = ''.join(speaker_lines).strip()
                
                if i < 2:
                    combined_text.append(speaker_text)
                elif i == 2:
                    # Check for diagram/chart/architecture/graph mentions
                    if re.search(r'\b(diagram|chart|architecture|graph)\b', speaker_text, re.IGNORECASE):
                        if 'diagram' in speaker_text.lower():
                            diagram_note = 'Now this diagram ' + speaker_text[0].lower() + speaker_text[1:]
                        elif 'chart' in speaker_text.lower():
                            diagram_note = 'Next, this chart ' + speaker_text[0].lower() + speaker_text[1:]
                        elif 'architecture' in speaker_text.lower():
                            diagram_note = 'Now this architecture ' + speaker_text[0].lower() + speaker_text[1:]
                        elif 'graph' in speaker_text.lower():
                            diagram_note = 'Next, this graph ' + speaker_text[0].lower() + speaker_text[1:]
            
            # Add combined paragraph
            if combined_text:
                speaker_notes.append(' '.join(combined_text) + '\n\n')
            
            # Add diagram note if exists
            if diagram_note:
                speaker_notes.append(diagram_note + '\n\n')
        
        # Add slide separator to slides
        if not in_speaker_section:
            slides_lines.append(line)
        
        # Reset
        in_speaker_section = False
        current_speakers = []
        continue
    
    # Add line to appropriate buffer
    if in_speaker_section:
        if current_speakers:
            current_speakers[-1].append(line)
    else:
        slides_lines.append(line)

# Handle any remaining speaker notes at end
if current_speakers:
    combined_text = []
    diagram_note = None
    
    for i, speaker_lines in enumerate(current_speakers):
        speaker_text = ''.join(speaker_lines).strip()
        
        if i < 2:
            combined_text.append(speaker_text)
        elif i == 2:
            if re.search(r'\b(diagram|chart|architecture|graph)\b', speaker_text, re.IGNORECASE):
                if 'diagram' in speaker_text.lower():
                    diagram_note = 'Now this diagram ' + speaker_text[0].lower() + speaker_text[1:]
                elif 'chart' in speaker_text.lower():
                    diagram_note = 'Next, this chart ' + speaker_text[0].lower() + speaker_text[1:]
                elif 'architecture' in speaker_text.lower():
                    diagram_note = 'Now this architecture ' + speaker_text[0].lower() + speaker_text[1:]
                elif 'graph' in speaker_text.lower():
                    diagram_note = 'Next, this graph ' + speaker_text[0].lower() + speaker_text[1:]
    
    if combined_text:
        speaker_notes.append(' '.join(combined_text) + '\n\n')
    
    if diagram_note:
        speaker_notes.append(diagram_note + '\n\n')

# Write slides only file
with open(r'C:\dev\wildfire\docs\CHALLENGE_2_SLIDES_ONLY.md', 'w', encoding='utf-8') as f:
    f.writelines(slides_lines)

# Write speaker notes file
with open(r'C:\dev\wildfire\docs\CHALLENGE_2_SPEAKER_NOTES.md', 'w', encoding='utf-8') as f:
    f.write(''.join(speaker_notes))

print('Files created successfully!')
print(f'Slides: {len(slides_lines)} lines')
print(f'Speaker notes: {len(speaker_notes)} paragraphs')
