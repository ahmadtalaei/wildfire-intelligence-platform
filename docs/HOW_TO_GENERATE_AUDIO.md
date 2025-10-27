# How to Generate AI Voice from Speaker Scripts

This guide shows you how to convert speaker scripts to professional AI voice audio using OpenAI's Text-to-Speech API.

## 📋 Prerequisites

✅ OpenAI API key (already configured in `.env`)
✅ Node.js installed (already available)
✅ Speaker scripts ready:
- `docs/CHALLENGE1_DASHBOARD_SPEAKER_SCRIPT.md`
- `docs/CHALLENGE3_CLEARING_HOUSE_SPEAKER_SCRIPT.md`
- `docs/PLATFORM_HOMEPAGE_SPEAKER_SCRIPT.md`

## 🚀 Quick Start - Generate Single Audio

### Option 1: Use the script directly

```bash
cd C:\dev\wildfire\presentation

# Generate Challenge 1 Dashboard audio
node generate_dashboard_audio.js ../docs/CHALLENGE1_DASHBOARD_SPEAKER_SCRIPT.md
```

### Option 2: Generate all at once

```bash
cd C:\dev\wildfire\presentation
generate_all_dashboards.bat
```

This will generate all three audio files automatically.

## 📁 Output Location

All audio files are saved to:
```
C:\dev\wildfire\presentation\audio\
```

Expected output files:
- `challenge1_dashboard.mp3` (~5-6 minutes)
- `challenge3_portal.mp3` (~15-18 minutes)
- `platform_homepage.mp3` (~12-15 minutes)

## 💰 Cost

Estimated cost per script:
- Challenge 1 Dashboard: **$0.15**
- Challenge 3 Clearing House: **$0.36**
- Platform Homepage: **$0.30**

**Total: ~$0.81** for all three

## 🎙️ Voice Settings

Current configuration (in `presentation/.env`):
```
TTS_VOICE=alloy          # Professional, neutral voice
TTS_MODEL=tts-1-hd       # High quality audio
TTS_SPEED=1.05           # Slightly faster than normal
```

### Available Voices:
- **alloy** - Neutral, clear (recommended for technical demos)
- **nova** - Warm, engaging
- **onyx** - Deep, authoritative
- **echo** - Clear, professional
- **fable** - British accent
- **shimmer** - Energetic, upbeat

To change voice, edit `presentation/.env`:
```
TTS_VOICE=nova
```

## 📝 Step-by-Step Instructions

### Step 1: Navigate to presentation folder
```bash
cd C:\dev\wildfire\presentation
```

### Step 2: Generate audio for a specific script

For Challenge 1 Dashboard:
```bash
node generate_dashboard_audio.js ../docs/CHALLENGE1_DASHBOARD_SPEAKER_SCRIPT.md challenge1_dashboard.mp3
```

For Challenge 3 Clearing House:
```bash
node generate_dashboard_audio.js ../docs/CHALLENGE3_CLEARING_HOUSE_SPEAKER_SCRIPT.md challenge3_portal.mp3
```

For Platform Homepage:
```bash
node generate_dashboard_audio.js ../docs/PLATFORM_HOMEPAGE_SPEAKER_SCRIPT.md platform_homepage.mp3
```

### Step 3: Review the audio

Open the generated MP3 file:
```bash
start audio\challenge1_dashboard.mp3
```

Or navigate to `C:\dev\wildfire\presentation\audio\` and double-click the file.

## 🔧 What the Script Does

1. **Reads the markdown file** - Loads your speaker script
2. **Extracts narration text** - Removes headers, metadata, usage instructions
3. **Splits into chunks** - Breaks long scripts into 4000-character chunks (API limit is 4096)
4. **Generates audio** - Calls OpenAI TTS API for each chunk
5. **Combines parts** - Merges all chunks into single seamless MP3 file
6. **Shows progress** - Displays real-time status and cost estimates

## 📊 Example Output

```
============================================================
GENERATING DASHBOARD AUDIO
============================================================
Input: CHALLENGE1_DASHBOARD_SPEAKER_SCRIPT.md
Output: challenge1_dashboard.mp3
Voice: alloy
Model: tts-1-hd
Speed: 1.05x
============================================================

📝 Extracted 5,247 characters of narration text

🎙️  Generating challenge1_dashboard.mp3 (5,247 chars)...
✅ challenge1_dashboard.mp3 generated successfully!
   Size: 1.2 MB (1,234 KB)
   Characters: 5,247
   Estimated duration: ~5.5 minutes

============================================================
GENERATION COMPLETE
============================================================
💰 Estimated cost: $0.157
📂 Audio saved to: presentation/audio/challenge1_dashboard.mp3
============================================================
```

## ❌ Troubleshooting

### Problem: "OPENAI_API_KEY not set"

**Solution:** Check that `.env` file exists in `presentation/` folder with valid API key.

### Problem: "Script file not found"

**Solution:** Verify the path is correct:
```bash
ls ../docs/CHALLENGE1_DASHBOARD_SPEAKER_SCRIPT.md
```

### Problem: "File already exists"

**Solution:** Delete the old file first:
```bash
rm audio/challenge1_dashboard.mp3
```

Then regenerate:
```bash
node generate_dashboard_audio.js ../docs/CHALLENGE1_DASHBOARD_SPEAKER_SCRIPT.md
```

### Problem: Rate limit error

**Solution:** Wait 1 minute and try again. The script includes automatic delays to avoid rate limiting.

## 🎯 Use Cases

### For Competition Submission
Generate audio narration to accompany dashboard screenshots and demo videos.

### For Presentations
Play audio during live demos to explain features while showing the actual dashboards.

### For Training Materials
Create professional voice-over for internal documentation and training videos.

### For Video Production
Use as voice track for promotional videos and technical walkthroughs.

## 🔄 Updating Audio

If you modify a speaker script:

1. Delete the old audio file
2. Regenerate with the same command
3. New audio will reflect your changes

```bash
rm audio/challenge1_dashboard.mp3
node generate_dashboard_audio.js ../docs/CHALLENGE1_DASHBOARD_SPEAKER_SCRIPT.md
```

## 📚 Additional Resources

- **Full guide:** `presentation/GENERATE_DASHBOARD_AUDIO_GUIDE.md`
- **OpenAI TTS docs:** https://platform.openai.com/docs/guides/text-to-speech
- **Speaker scripts:** `docs/CHALLENGE*_SPEAKER_SCRIPT.md`

---

**Created for:** Wildfire Intelligence Platform - CAL FIRE Challenge
**Last Updated:** October 2025
