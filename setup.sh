#!/bin/bash

# Enhanced Indonesian Meeting Transcription System - Setup Script
# This script guides you through the initial setup process

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Enhanced Indonesian Meeting Transcription System      ║"
echo "║                        Setup v2.0                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Detect Python
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python found: $($PYTHON_CMD --version)"
echo ""

# Check if virtual environment exists
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "✅ Virtual environment created: $VENV_DIR"
else
    echo "✅ Virtual environment already exists: $VENV_DIR"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
echo "📥 Installing dependencies..."
echo "   This may take a few minutes..."

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "⚠️  Warning: requirements.txt not found"
fi

echo ""

# Ask about AI summarization preference
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 AI Summarization Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Choose your AI summarization provider:"
echo ""
echo "1) Ollama (FREE - Recommended)"
echo "   • 100% free, runs locally"
echo "   • No API keys needed"
echo "   • Works offline"
echo "   • Requires Ollama installation (~5GB download)"
echo ""
echo "2) OpenAI (Paid)"
echo "   • Paid API (≈$0.02/meeting)"
echo "   • Requires API key"
echo "   • Faster processing"
echo "   • Requires internet"
echo ""
read -p "Select option (1 or 2) [default: 1]: " SUMMARIZATION_CHOICE

echo ""

case $SUMMARIZATION_CHOICE in
    2|"2")
        echo "✅ Selected: OpenAI (Paid)"
        echo ""
        echo "📝 You'll need to configure OPENAI_API_KEY in .env file"

        # Update config to use OpenAI
        if [ -f "config/config.yaml" ]; then
            sed -i '' 's/provider: "local"/provider: "openai"/' config/config.yaml
            echo "✅ Config updated: provider set to 'openai'"
        fi
        ;;
    *)
        echo "✅ Selected: Ollama (FREE)"
        echo ""

        # Check if Ollama is already installed
        if command -v ollama &> /dev/null; then
            echo "✅ Ollama is already installed"
            echo "   Version: $(ollama --version)"
            echo ""

            # Check if service is running
            if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
                echo "✅ Ollama service is running"
            else
                echo "⚠️  Ollama service is not running"
                echo "   Start with: ollama serve"
            fi
        else
            echo "📦 Ollama not found on your system"
            echo ""
            read -p "Install Ollama now? (y/N) " INSTALL_OLLAMA

            if [[ "$INSTALL_OLLAMA" =~ ^[Yy]$ ]]; then
                chmod +x scripts/setup_ollama.sh
                ./scripts/setup_ollama.sh
            else
                echo ""
                echo "⚠️  You'll need to install Ollama later:"
                echo "   ./scripts/setup_ollama.sh"
                echo ""
                echo "   Or manually:"
                echo "   brew install ollama"
                echo "   ollama serve"
                echo "   ollama pull llama3.1"
            fi
        fi

        # Update config to use local
        if [ -f "config/config.yaml" ]; then
            sed -i '' 's/provider: "openai"/provider: "local"/' config/config.yaml 2>/dev/null || true
            echo "✅ Config updated: provider set to 'local'"
        fi
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "🔐 Setting up environment variables..."

    # Copy example if exists
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
    else
        # Create basic .env
        cat > .env << EOF
# Enhanced Indonesian Meeting Transcription System
# Environment Variables

# HuggingFace Token (required for pyannote.audio)
HF_TOKEN=

# OpenAI API Key (optional - only needed if using OpenAI instead of Ollama)
# If using Ollama (free local AI), leave this empty
OPENAI_API_KEY=
EOF
        echo "✅ Created .env file"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 ACTION REQUIRED: Configure API Keys"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "To use this system, you need to configure API keys:"
    echo ""
    echo "1️⃣  HuggingFace Token (for pyannote.audio) - Required"
    echo "   - Get your token at: https://hf.co/settings/tokens"
    echo "   - Accept model licenses at:"
    echo "     • https://hf.co/pyannote/speaker-diarization-3.1"
    echo "     • https://hf.co/pyannote/segmentation-3.0"
    echo ""
    echo "2️⃣  OpenAI API Key (for AI summarization) - Optional"
    echo "   - Only needed if using OpenAI instead of Ollama"
    echo "   - If using Ollama (free), you can skip this"
    echo "   - Get your API key at: https://platform.openai.com/api-keys"
    echo ""
    echo "Add these keys to the .env file:"
    echo "   HF_TOKEN=your_token_here"
    echo "   OPENAI_API_KEY=your_key_here  # Optional (skip if using Ollama)"
    echo ""
    echo "💡 Tip: Using Ollama? You only need HF_TOKEN!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p output
mkdir -p speakers/profiles
echo "✅ Directories created"

# Initialize speaker database
echo "🎤 Initializing speaker database..."
if [ ! -f "speakers/database.json" ]; then
    cat > speakers/database.json << EOF
{
  "version": "1.0",
  "speakers": [],
  "created_at": null,
  "updated_at": null
}
EOF
    echo "✅ Speaker database initialized"
else
    echo "✅ Speaker database already exists"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Quick Start:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Configure API keys in .env file (HF_TOKEN is required)"
echo ""
if [[ "$SUMMARIZATION_CHOICE" == "2" ]] || [[ "$SUMMARIZATION_CHOICE" == "2" ]]; then
    echo "3. Configure OpenAI API key in .env file"
    echo ""
    echo "4. Transcribe audio:"
else
    echo "3. (If using Ollama) Make sure Ollama is running:"
    echo "   ollama serve"
    echo ""
    echo "   Check Ollama status:"
    echo "   ./scripts/check_ollama.sh"
    echo ""
    echo "4. Transcribe audio:"
fi
echo "   ./process.sh audio.m4a"
echo ""
echo "   Or use the CLI:"
echo "   python scripts/cli.py transcribe audio.m4a"
echo ""
echo "5. (Optional) Enroll speakers for identification:"
echo "   python scripts/cli.py enroll-speaker \"Pak Budi\" sample1.wav sample2.wav sample3.wav"
echo ""
echo "For more information:"
echo "   python scripts/cli.py --help"
echo ""
