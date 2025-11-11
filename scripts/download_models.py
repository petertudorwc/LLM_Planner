"""
Download and prepare AI models for LLM Planner

This script downloads:
1. Llama 3.1 8B model via Ollama
2. Whisper base model
3. Sentence-transformers embedding model
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and print status"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True, capture_output=False)
    if result.returncode != 0:
        print(f"❌ Error: {description} failed")
        return False
    print(f"✅ {description} completed successfully")
    return True

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         LLM Planner - Model Download Script              ║
    ║                                                          ║
    ║  This will download ~8GB of AI models                   ║
    ║  Estimated time: 15-30 minutes                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Create model directories
    models_dir = Path(__file__).parent.parent / "models"
    models_dir.mkdir(exist_ok=True)
    (models_dir / "llm").mkdir(exist_ok=True)
    (models_dir / "whisper").mkdir(exist_ok=True)
    (models_dir / "embeddings").mkdir(exist_ok=True)
    
    print("\n📁 Model directories created")
    
    # Check if Ollama is installed
    print("\n🔍 Checking for Ollama installation...")
    try:
        result = subprocess.run(["C:\\Users\\Peter\\AppData\\Local\\Programs\\ollama\\ollama.exe", "--version"], capture_output=True, text=True)
        print(f"✅ Ollama found: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Ollama not found. Please install from: https://ollama.ai")
        print("   After installation, run this script again.")
        return False
    
    # Download Qwen3 8B
    if not run_command(
        "C:\\Users\\Peter\\AppData\\Local\\Programs\\ollama\\ollama.exe pull qwen3:8b",
        "Downloading Qwen3 8B model (~4.7GB)"
    ):
        return False
    
    # Download Python packages for other models
    print("\n📦 Installing Python dependencies...")
    
    packages = [
        "torch",
        "sentence-transformers",
        "openai-whisper",
    ]
    
    for package in packages:
        if not run_command(
            f"pip install {package}",
            f"Installing {package}"
        ):
            return False
    
    # Download embedding model
    print("\n🤖 Downloading sentence-transformers model...")
    download_embedding_code = """
import os
from sentence_transformers import SentenceTransformer

model_name = "sentence-transformers/all-mpnet-base-v2"
cache_dir = "./models/embeddings"

print(f"Downloading {model_name}...")
model = SentenceTransformer(model_name, cache_folder=cache_dir)
print("Embedding model downloaded successfully")
"""
    
    with open("temp_download_embedding.py", "w", encoding="utf-8") as f:
        f.write(download_embedding_code)
    
    if not run_command(
        "python temp_download_embedding.py",
        "Downloading embedding model (~420MB)"
    ):
        os.remove("temp_download_embedding.py")
        return False
    
    os.remove("temp_download_embedding.py")
    
    # Download Whisper model
    print("\n🎤 Downloading Whisper model...")
    download_whisper_code = """
import whisper

model_size = "base"
print(f"Downloading Whisper {model_size} model...")
model = whisper.load_model(model_size, download_root="./models/whisper")
print("Whisper model downloaded successfully")
"""
    
    with open("temp_download_whisper.py", "w", encoding="utf-8") as f:
        f.write(download_whisper_code)
    
    if not run_command(
        "python temp_download_whisper.py",
        "Downloading Whisper base model (~140MB)"
    ):
        os.remove("temp_download_whisper.py")
        return False
    
    os.remove("temp_download_whisper.py")
    
    print("""
    
    ╔══════════════════════════════════════════════════════════╗
    ║              ✅ All Models Downloaded!                   ║
    ║                                                          ║
    ║  Next steps:                                            ║
    ║  1. Download map tiles: python scripts/download_map_tiles.py  ║
    ║  2. Start the system: docker-compose up                 ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
