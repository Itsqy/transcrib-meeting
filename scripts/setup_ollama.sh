#!/bin/bash
# Automated Ollama setup for free AI summarization

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          Setting up Ollama for Free AI Summarization       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Darwin*)    PLATFORM="macOS";;
    Linux*)     PLATFORM="Linux";;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="Windows";;
    *)          PLATFORM="Unknown"
esac

echo "🖥️  Platform: $PLATFORM"
echo ""

# Step 1: Check if Ollama is installed
if command -v ollama &> /dev/null; then
    echo "✅ Ollama already installed: $(ollama --version)"
else
    echo "📦 Installing Ollama..."

    case "${PLATFORM}" in
        macOS)
            if command -v brew &> /dev/null; then
                echo "   Installing via Homebrew..."
                brew install ollama
            else
                echo "❌ Homebrew not found"
                echo ""
                echo "Please install manually:"
                echo "   1. Visit: https://ollama.ai/download"
                echo "   2. Download and install Ollama for macOS"
                echo "   3. Run this script again"
                exit 1
            fi
            ;;
        Linux)
            echo "   Installing via official script..."
            curl -fsSL https://ollama.ai/install.sh | sh
            ;;
        Windows)
            echo "❌ Please install manually:"
            echo "   1. Visit: https://ollama.ai/download"
            echo "   2. Download and install Ollama for Windows"
            echo "   3. Run this script again"
            exit 1
            ;;
        *)
            echo "❌ Unsupported platform: $PLATFORM"
            exit 1
            ;;
    esac

    echo "✅ Ollama installed"
fi

echo ""

# Step 2: Check if service is running
echo "🚀 Checking Ollama service..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama service is already running"
else
    echo "   Starting Ollama service..."

    # Start in background
    if [[ "${PLATFORM}" == "macOS" ]] || [[ "${PLATFORM}" == "Linux" ]]; then
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        OLLAMA_PID=$!

        # Wait for service to start
        echo "   Waiting for service to start..."
        for i in {1..10}; do
            if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
                echo "   ✅ Service started successfully"
                break
            fi
            sleep 1
        done
    else
        echo "⚠️  Please start Ollama manually:"
        echo "   ollama serve"
        echo ""
        read -p "Press Enter after starting Ollama..."
    fi
fi

echo ""

# Step 3: Ask which model to download
echo "📥 Downloading LLM model..."
echo ""
echo "Available models:"
echo "   1) llama3.1       (recommended - 4.7GB - best balance)"
echo "   2) llama3.1:8b    (smaller variant - 4.7GB)"
echo "   3) phi3           (fast & lightweight - 2.2GB - less accurate)"
echo "   4) llama3.1:70b   (best quality - 40GB - slower)"
echo ""
read -p "Select model (1-4) [default: 1]: " MODEL_CHOICE

case $MODEL_CHOICE in
    2|"2")
        MODEL="llama3.1:8b"
        ;;
    3|"3")
        MODEL="phi3"
        ;;
    4|"4")
        MODEL="llama3.1:70b"
        ;;
    *)
        MODEL="llama3.1"
        ;;
esac

echo ""
echo "⬇️  Downloading $MODEL (this may take a few minutes)..."
echo ""

ollama pull "$MODEL"

echo ""
echo "✅ Model downloaded: $MODEL"
echo ""

# Step 4: Update configuration
echo "⚙️  Updating configuration..."
CONFIG_FILE="config/config.yaml"

if [ -f "$CONFIG_FILE" ]; then
    # Backup original config
    cp "$CONFIG_FILE" "$CONFIG_FILE.bak"

    # Change provider to local
    if [[ "${PLATFORM}" == "macOS" ]]; then
        sed -i '' 's/provider: "openai"/provider: "local"/' "$CONFIG_FILE"
    else
        sed -i 's/provider: "openai"/provider: "local"/' "$CONFIG_FILE"
    fi

    echo "✅ Configuration updated: provider set to 'local'"
    echo "   • Backup saved: $CONFIG_FILE.bak"
else
    echo "⚠️  Config file not found: $CONFIG_FILE"
fi

echo ""

# Step 5: Verify setup
echo "🧪 Verifying setup..."
echo ""

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama service is not responding"
    exit 1
fi

if ! ollama list | grep -q "$MODEL"; then
    echo "❌ Model '$MODEL' not found"
    exit 1
fi

echo "✅ Setup verification passed"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  Setup Complete! 🎉                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Configuration Summary:"
echo "   • Provider:      local (Ollama)"
echo "   • Model:         $MODEL"
echo "   • Base URL:      http://localhost:11434"
echo "   • Cost:          100% FREE"
echo ""
echo "🚀 Quick Start:"
echo ""
echo "   1. Make sure Ollama is running:"
echo "      ollama serve"
echo ""
echo "   2. Test summarization:"
echo "      python scripts/cli.py summarize transcript.txt --provider local"
echo ""
echo "   3. Or use with full pipeline:"
echo "      ./process.sh meeting.m4a --summarize"
echo ""
echo "📖 More info:"
echo "   • Check status:    ./scripts/check_ollama.sh"
echo "   • View models:     ollama list"
echo "   • Update model:    ollama pull $MODEL"
echo ""
