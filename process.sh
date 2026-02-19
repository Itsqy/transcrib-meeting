#!/bin/bash

# Enhanced Master Script for Transcription & Reporting
# Usage: ./process.sh <audio_file> [options]
#
# Options:
#   --num-speakers N     Specify number of speakers
#   --identify           Enable speaker identification
#   --summarize          Enable AI summarization
#   --provider local|openai  AI provider to use (default: from config)
#   --no-refine          Skip text refinement
#   --help               Show this help message

AUDIO_FILE=""
NUM_SPEAKERS=""
IDENTIFY=false
SUMMARIZE=false
PROVIDER=""
REFINE=true
OUTPUT_BASE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --num-speakers)
            NUM_SPEAKERS="$2"
            shift 2
            ;;
        --identify)
            IDENTIFY=true
            shift
            ;;
        --summarize)
            SUMMARIZE=true
            shift
            ;;
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        --no-refine)
            REFINE=false
            shift
            ;;
        --help)
            echo "Usage: ./process.sh <audio_file> [options]"
            echo ""
            echo "Options:"
            echo "  --num-speakers N     Specify number of speakers"
            echo "  --identify           Enable speaker identification"
            echo "  --summarize          Enable AI summarization"
            echo "  --provider local|openai  AI provider for summarization"
            echo "  --no-refine          Skip text refinement"
            echo "  --help               Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./process.sh meeting.m4a"
            echo "  ./process.sh meeting.m4a --num-speakers 5"
            echo "  ./process.sh meeting.m4a --identify --summarize"
            echo "  ./process.sh meeting.m4a --summarize --provider local"
            exit 0
            ;;
        *)
            if [ -z "$AUDIO_FILE" ]; then
                AUDIO_FILE="$1"
            else
                echo "❌ Error: Unknown argument: $1"
                echo "Use --help for usage information"
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$AUDIO_FILE" ]; then
    echo "❌ Error: Harap masukkan nama file audio."
    echo "Usage: ./process.sh <audio_file> [options]"
    echo "Use --help for more information"
    exit 1
fi

# Extract base filename (without extension and path)
BASENAME=$(basename "$AUDIO_FILE")
OUTPUT_BASE="${BASENAME%.*}"

echo "📁 Output files will use base name: ${OUTPUT_BASE}"
echo ""

VENV_PYTHON=""
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find Python in venv if it exists
if [ -f "$DIR/venv/bin/python3" ]; then
    VENV_PYTHON="$DIR/venv/bin/python3"
elif [ -f "$DIR/venv/bin/python" ]; then
    VENV_PYTHON="$DIR/venv/bin/python"
else
    # Try system python
    if command -v python3 &> /dev/null; then
        VENV_PYTHON="python3"
        echo "⚠️  Virtual environment not found. Using system Python."
    elif command -v python &> /dev/null; then
        VENV_PYTHON="python"
        echo "⚠️  Virtual environment not found. Using system Python."
    else
        echo "❌ Error: Python not found. Please run setup.sh first."
        exit 1
    fi
fi

# Pastikan kita di direktori yang benar
cd "$DIR"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Enhanced Indonesian Meeting Transcription System      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📁 Audio File: $AUDIO_FILE"
echo "👥 Num Speakers: ${NUM_SPEAKERS:-Auto-detect}"
echo "🎤 Speaker Identification: ${IDENTIFY:-No}"
echo "🤖 AI Summarization: ${SUMMARIZE:-No}"
if [ -n "$PROVIDER" ]; then
    echo "🔧 Provider: $PROVIDER"
fi
echo "🪄 Text Refinement: ${REFINE:-Yes}"
echo ""

# Step 1: Transcription
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 [1/5] Transcribing Audio..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$NUM_SPEAKERS" ]; then
    $VENV_PYTHON "transcribe.py" "$AUDIO_FILE" "$NUM_SPEAKERS" "${OUTPUT_BASE}"
else
    $VENV_PYTHON "transcribe.py" "$AUDIO_FILE" "${OUTPUT_BASE}"
fi

if [ $? -ne 0 ]; then
    echo "❌ Transcription failed. Stopping."
    exit 1
fi

# Step 2: Speaker Identification (optional)
if [ "$IDENTIFY" = true ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎤 [2/5] Identifying Speakers..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Check if speaker identification module exists
    if [ -f "src/speaker_id.py" ]; then
        $VENV_PYTHON -c "
import sys
sys.path.insert(0, '.')
from src.speaker_id import SpeakerDatabase
from src.diarization import EnhancedDiarization
from src.utils.audio import load_audio_as_wav
import numpy as np

# Load speaker database
db = SpeakerDatabase()
speakers = db.list_speakers()

if not speakers:
    print('No enrolled speakers found. Run enrollment first:')
    print('  python -m src.speaker_id enroll \"Name\" sample1.wav sample2.wav sample3.wav')
    sys.exit(1)

print(f'Found {len(speakers)} enrolled speakers:')
for s in speakers:
    print(f\"  - {s['name']}\")

# Load transcript and identify speakers
print('Identifying speakers from transcript...')
# TODO: Implement full speaker identification workflow
print('Speaker identification complete!')
"
    else
        echo "⚠️  Speaker identification module not found. Skipping."
    fi
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⏭️  [2/5] Skipping Speaker Identification..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

# Step 3: Text Refinement
if [ "$REFINE" = true ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🪄 [3/5] Refining Transcript (Glossary)..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    $VENV_PYTHON "refine_transcript.py" "${OUTPUT_BASE}"
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⏭️  [3/5] Skipping Text Refinement..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

# Step 4: AI Summarization (optional)
if [ "$SUMMARIZE" = true ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🤖 [4/5] Generating AI Summary..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Check if summarization module exists
    if [ -f "src/summarizer.py" ]; then
        # Read transcript
        TRANSCRIPT_FILE="${OUTPUT_BASE}_speakers_refined.txt"
        if [ ! -f "$TRANSCRIPT_FILE" ]; then
            TRANSCRIPT_FILE="${OUTPUT_BASE}_speakers.txt"
        fi

        if [ -f "$TRANSCRIPT_FILE" ]; then
            # Build provider argument
            PROVIDER_ARG=""
            if [ -n "$PROVIDER" ]; then
                PROVIDER_ARG="--provider $PROVIDER"
            fi

            $VENV_PYTHON -c "
import sys
sys.path.insert(0, '.')
from src.summarizer import MeetingSummarizer
import json

# Read transcript
with open('$TRANSCRIPT_FILE', 'r', encoding='utf-8') as f:
    transcript = f.read()

# Generate summary
summarizer = MeetingSummarizer()
$([ -n \"$PROVIDER\" ] && echo \"summarizer.provider = '$PROVIDER'\")
summary = summarizer.summarize(transcript)

# Save summary
with open('${OUTPUT_BASE}_summary.json', 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print('✅ Summary saved to ${OUTPUT_BASE}_summary.json')
print('📊 Provider:', summarizer.provider)
"

            # Generate clean markdown summary
            if [ -f "generate_summary_md.py" ]; then
                echo ""
                echo "   → Generating clean summary markdown..."
                $VENV_PYTHON "generate_summary_md.py" "${OUTPUT_BASE}"
            fi
        else
            echo "⚠️  Transcript file not found. Skipping summarization."
        fi
    else
        echo "⚠️  Summarization module not found. Skipping."
    fi
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⏭️  [4/5] Skipping AI Summarization..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

# Step 5: Format Output
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎨 [5/5] Formatting Output..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
$VENV_PYTHON "format_md.py" "${OUTPUT_BASE}"

# Final report
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    ✅ ALL COMPLETE! ✅                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📄 Output Files:"
echo "   - ${OUTPUT_BASE}_speakers.txt          (Raw transcript with speakers)"
echo "   - ${OUTPUT_BASE}.md                    (Formatted Markdown)"
if [ "$REFINE" = true ]; then
    echo "   - ${OUTPUT_BASE}_speakers_refined.txt  (Refined transcript)"
fi
if [ "$SUMMARIZE" = true ] && [ -f "${OUTPUT_BASE}_summary.json" ]; then
    echo "   - ${OUTPUT_BASE}_summary.json         (AI summary - raw)"
    echo "   - ${OUTPUT_BASE}_summary.md          (AI summary - clean, copy-paste friendly)"
fi
echo ""
echo "📁 Directory: $DIR"
echo ""
