#!/bin/bash

# Start Ollama server in background
ollama serve &

# Wait for Ollama to be ready
sleep 5

# Pull model if not exists
MODEL_NAME=${MODEL_NAME:-llama3.1:8b}
echo "Checking for model: $MODEL_NAME"
ollama list | grep -q "$MODEL_NAME" || ollama pull "$MODEL_NAME"

# Preload the model into memory with a warm-up request
echo "Preloading model into memory..."
ollama run "$MODEL_NAME" "Hello" --verbose > /dev/null 2>&1

echo "Model loaded and ready!"

# Start FastAPI wrapper
python3 /app/src/main.py
