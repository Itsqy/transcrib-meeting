# Enhanced Indonesian Meeting Transcription System

A powerful, AI-powered meeting transcription system with:
- 🎤 **High-quality Indonesian transcription** (Whisper large-v3-turbo)
- 👥 **Speaker diarization** (identifies different speakers)
- 🎯 **Speaker identification** (recognize known speakers by name)
- 🤖 **AI-powered summarization** (Free with Ollama or paid with OpenAI)
- 📝 **Action item extraction** (Task, PIC, Deadline)
- 📊 **Multiple output formats** (Markdown, JSON, TXT)

## Quick Start

### Option 1: Free AI Summarization (Recommended) 🆓

**100% free, runs locally, no API keys needed!**

```bash
# 1. Clone and setup
git clone <repository-url>
cd transcrib

# 2. Run setup script
./setup.sh

# When prompted, select "Ollama (FREE)" for AI summarization

# 3. Configure HuggingFace token (for speaker diarization)
# Get token at: https://hf.co/settings/tokens
# Accept licenses at:
#   - https://hf.co/pyannote/speaker-diarization-3.1
#   - https://hf.co/pyannote/segmentation-3.0
echo "HF_TOKEN=your_token_here" > .env

# 4. Activate virtual environment
source venv/bin/activate

# 5. Transcribe audio
./process.sh meeting.m4a --summarize
```

### Option 2: Paid OpenAI Summarization 💳

**Faster, cloud-based, requires API key**

```bash
# Follow steps 1-3 above, but select "OpenAI (Paid)" during setup

# Configure both API keys
echo "HF_TOKEN=your_token_here" > .env
echo "OPENAI_API_KEY=your_key_here" >> .env

# Transcribe
./process.sh meeting.m4a --summarize
```

---

## Ollama Setup Guide

### What is Ollama?

Ollama is a free, open-source tool that runs Large Language Models (LLMs) locally on your computer. It's completely free and works offline.

**Comparison:**

| Feature | Ollama (Free) | OpenAI (Paid) |
|---------|---------------|---------------|
| Cost | **100% FREE** | ~$0.02/meeting |
| Privacy | **Runs locally** | Data sent to API |
| Speed | Fast (local) | Faster (cloud) |
| Internet | **Not required** | Required |
| Setup | One-time install | API key needed |

### Installation

#### macOS (Recommended)

```bash
# Using Homebrew (easiest)
brew install ollama

# Or download from website
# Visit: https://ollama.ai/download
```

#### Linux

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Windows

Download from: https://ollama.ai/download

### Setup

```bash
# 1. Start Ollama service
ollama serve
# Runs in background on http://localhost:11434

# 2. Download a model (one-time, takes a few minutes)
# Recommended: LLaMA 3.1 (4.7GB - good balance)
ollama pull llama3.1

# Or for faster/smaller model (2.2GB - less accurate)
ollama pull phi3

# 3. Verify installation
./scripts/check_ollama.sh
```

### Automated Setup

Use the provided automated script:

```bash
chmod +x scripts/setup_ollama.sh
./scripts/setup_ollama.sh
```

This script will:
- Install Ollama (if not installed)
- Start the service
- Download the model
- Update configuration

### Checking Ollama Status

```bash
./scripts/check_ollama.sh
```

This will verify:
- ✅ Ollama is installed
- ✅ Service is running
- ✅ Model is available
- ✅ API is responding

---

## Usage

### Basic Transcription

```bash
# Activate virtual environment
source venv/bin/activate

# Transcribe audio file
python scripts/cli.py transcribe meeting.m4a

# Or use the convenience script
./process.sh meeting.m4a
```

### Transcription with Summarization

```bash
# Using default provider (set in config)
./process.sh meeting.m4a --summarize

# Specify provider explicitly
./process.sh meeting.m4a --summarize --provider local    # Free (Ollama)
./process.sh meeting.m4a --summarize --provider openai   # Paid
```

### Enrolling Speakers

```bash
# Enroll a speaker with voice samples
python scripts/cli.py enroll-speaker "Pak Budi" sample1.wav sample2.wav sample3.wav

# The system will now recognize "Pak Budi" in future transcriptions
```

### CLI Commands

```bash
# View all available commands
python scripts/cli.py --help

# Transcribe with options
python scripts/cli.py transcribe meeting.m4a \
  --model large-v3-turbo \
  --language id \
  --diarization \
  --summarize \
  --provider local

# Summarize existing transcript
python scripts/cli.py summarize transcript.txt --provider local

# List enrolled speakers
python scripts/cli.py list-speakers

# Identify speaker from audio
python scripts/cli.py identify-speaker audio_sample.wav
```

---

## Configuration

The system is configured via `config/config.yaml`:

### Summarization Settings

```yaml
summarization:
  enabled: true

  # Provider: "local" (free) or "openai" (paid)
  provider: "local"

  # OpenAI settings (only if provider: "openai")
  openai:
    model: "gpt-4o-mini"
    api_key: null  # Set via OPENAI_API_KEY env var
    temperature: 0.3
    max_tokens: 2000

  # Local LLM settings (only if provider: "local")
  local:
    model: "llama3.1"  # Model to use
    base_url: "http://localhost:11434"  # Ollama API
    temperature: 0.3

  # Summary language
  language: "id"  # Indonesian
```

### Available Ollama Models

```bash
# List downloaded models
ollama list

# Download additional models
ollama pull llama3.1      # Recommended (4.7GB)
ollama pull phi3          # Faster (2.2GB)
ollama pull llama3.1:70b  # Best quality (40GB)

# Use specific model in config:
# local:
#   model: "phi3"
```

---

## Output

The system generates multiple output files:

### Files Generated

```
output/
├── meeting_transcript.md      # Full transcript with speakers
├── meeting_transcript.txt      # Plain text transcript
├── meeting_summary.json        # Structured summary (JSON)
└── meeting_summary.md         # Formatted summary (Markdown)
```

### Transcript Format (Markdown)

```markdown
# Meeting Transcript

**Date:** 2024-02-15 14:00
**Duration:** 45 minutes
**Speakers:** 3 detected

## Transcript

### [00:00:15] Speaker 1
Selamat pagi, kita akan mulai rapat ini...

### [00:00:30] Pak Budi
Terima kasih, saya akan mempresentasikan...

...

## Ringkasan Rapat

### Ringkasan Eksekutif
Rapat membahas...

### Topik Utama
- Topik 1
- Topik 2
- Topik 3

### Keputusan
- **Topik**: Keputusan (oleh ...)
- **Topik**: Keputusan (oleh ...)

### Action Items
| Tugas | PIC | Deadline | Prioritas |
|-------|-----|----------|-----------|
| ... | ... | ... | ... |
```

---

## Troubleshooting

### Ollama Issues

**Problem: "Ollama not installed"**
```bash
# Install Ollama
brew install ollama  # macOS
# Or download from https://ollama.ai/download
```

**Problem: "Ollama service not running"**
```bash
# Start the service
ollama serve

# Or run in background
nohup ollama serve > /tmp/ollama.log 2>&1 &
```

**Problem: "Model not found"**
```bash
# Download the model
ollama pull llama3.1

# Verify with check script
./scripts/check_ollama.sh
```

**Problem: "Connection timeout"**
- Make sure Ollama is running: `ollama serve`
- Check if service is accessible: `curl http://localhost:11434/api/tags`
- The model may still be loading (wait a few minutes after first download)

### HuggingFace Issues

**Problem: "HF_TOKEN not found"**
```bash
# Get token at https://hf.co/settings/tokens
echo "HF_TOKEN=your_token_here" > .env
```

**Problem: "Model license not accepted"**
- Visit: https://hf.co/pyannote/speaker-diarization-3.1
- Click "Agree and access repository"
- Repeat for: https://hf.co/pyannote/segmentation-3.0

### General Issues

**Problem: Out of memory during transcription**
- Use a smaller model in config: `model: "base"` or `model: "small"`
- Or use CPU instead of GPU: `device: "cpu"`

**Problem: Slow transcription**
- Use faster model: `model: "large-v3-turbo"`
- Enable VAD in config to skip silence
- Use GPU if available: `device: "cuda"`

---

## System Requirements

### Minimum

- **CPU:** Modern processor (Intel i5 or equivalent)
- **RAM:** 8GB (16GB recommended)
- **Storage:** 10GB free space
- **OS:** macOS, Linux, Windows

### Recommended (for Ollama)

- **CPU:** Apple Silicon (M1/M2/M3) or modern multi-core
- **RAM:** 16GB or more
- **Storage:** 20GB free space (for models)
- **OS:** macOS or Linux

---

## Advanced Usage

### Custom Speaker Profiles

```bash
# Enroll speaker with multiple samples
python scripts/cli.py enroll-speaker "Pak Budi" \
  recordings/sample1.wav \
  recordings/sample2.wav \
  recordings/sample3.wav

# View enrolled speakers
python scripts/cli.py list-speakers

# Identify speaker from unknown audio
python scripts/cli.py identify-speaker unknown.wav
```

### Batch Processing

```bash
# Process multiple files
for file in meetings/*.m4a; do
  ./process.sh "$file" --summarize --provider local
done
```

### Custom Configuration

Create a custom config file:

```yaml
# custom_config.yaml
transcription:
  model: "large-v3-turbo"
  language: "id"

summarization:
  provider: "local"
  local:
    model: "llama3.1"
```

Use custom config:

```bash
python scripts/cli.py transcribe meeting.m4a --config custom_config.yaml
```

---

## Cost Comparison

### Ollama (Free)
- **Initial setup:** 5 minutes
- **Model download:** 4.7GB (one-time)
- **Per meeting:** **$0.00**
- **Annual cost (100 meetings):** **$0.00**

### OpenAI (Paid)
- **Initial setup:** 2 minutes
- **Model download:** None
- **Per meeting:** ~$0.02
- **Annual cost (100 meetings):** ~$2.00

**Recommendation:** Use Ollama for free, unlimited summarization!

---

## License

This project is provided as-is for personal and commercial use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

---

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Run `./scripts/check_ollama.sh` to verify Ollama setup
3. Check logs in `transcription.log`
4. Review configuration in `config/config.yaml`

---

**Enjoy free, unlimited AI-powered meeting summarization! 🎉**
