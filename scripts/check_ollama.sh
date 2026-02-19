#!/bin/bash
# Check Ollama installation and service status

echo "🔍 Checking Ollama..."
echo ""

# 1. Check if ollama command exists
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama not installed"
    echo ""
    echo "📦 Installation options:"
    echo "   • macOS (Homebrew):  brew install ollama"
    echo "   • Or download:       https://ollama.ai/download"
    echo ""
    echo "💡 Quick setup: Run ./scripts/setup_ollama.sh"
    exit 1
fi

echo "✅ Ollama installed: $(ollama --version)"
echo ""

# 2. Check if service is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama service not running"
    echo ""
    echo "🚀 Start the service:"
    echo "   ollama serve"
    echo ""
    echo "💡 Or run in background:"
    echo "   nohup ollama serve > /tmp/ollama.log 2>&1 &"
    exit 1
fi

echo "✅ Ollama service running on http://localhost:11434"
echo ""

# 3. Check if model is available
MODEL=${1:-llama3.1}
if ! ollama list | grep -q "$MODEL"; then
    echo "⚠️  Model '$MODEL' not found"
    echo ""
    echo "📥 Download the model:"
    echo "   ollama pull $MODEL"
    echo ""
    echo "💡 Other model options:"
    echo "   • llama3.1       (recommended - 4.7GB)"
    echo "   • llama3.1:8b    (smaller - 4.7GB)"
    echo "   • phi3           (faster - 2.2GB)"
    echo "   • llama3.1:70b   (better quality - 40GB)"
    exit 1
fi

echo "✅ Model '$MODEL' available"
echo ""

# 4. Test API connection
echo "🧪 Testing API connection..."
if curl -s http://localhost:11434/api/generate -d '{"model":"'$MODEL'","prompt":"test","stream":false}' | grep -q "response"; then
    echo "✅ API responding correctly"
else
    echo "⚠️  API test failed"
    exit 1
fi

echo ""
echo "🎉 Ollama is ready!"
echo ""
echo "📝 Configuration:"
echo "   • Provider: local"
echo "   • Model: $MODEL"
echo "   • Base URL: http://localhost:11434"
echo ""
echo "✨ You can now use free AI summarization!"
echo ""
echo "Test with:"
echo "   python scripts/cli.py summarize transcript.txt --provider local"
