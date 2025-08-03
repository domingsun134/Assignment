#!/bin/bash

echo "🚀 Starting AI Chatbot with Multiple Models"
echo "=========================================="

# Wait for Ollama to be ready and pull Phi-3 model
echo "📦 Setting up Phi-3 model..."
python pull_phi3.py

if [ $? -eq 0 ]; then
    echo "✅ Phi-3 model setup complete!"
    
    # Pull DeepSeek-R1:1.5b model
    echo "📦 Setting up DeepSeek-R1:1.5b model..."
    python pull_deepseek.py
    
    if [ $? -eq 0 ]; then
        echo "✅ DeepSeek-R1:1.5b model setup complete!"
    else
        echo "⚠️  DeepSeek-R1:1.5b model setup failed, but continuing with Phi-3..."
    fi
    
    echo "🌐 Starting chatbot server..."
    python server.py
else
    echo "❌ Failed to setup models. Exiting."
    exit 1
fi 