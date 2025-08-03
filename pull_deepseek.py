#!/usr/bin/env python3
"""
Script to pull the DeepSeek-R1:1.5b model in the Ollama container
"""

import requests
import time
import os
import sys

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = "deepseek-r1:1.5b"

def wait_for_ollama():
    """Wait for Ollama to be ready"""
    print("⏳ Waiting for Ollama to be ready...")
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                print("✅ Ollama is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        attempt += 1
        print(f"   Attempt {attempt}/{max_attempts}...")
        time.sleep(2)
    
    print("❌ Ollama failed to start within expected time")
    return False

def check_model_exists():
    """Check if DeepSeek-R1:1.5b model already exists"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code == 200:
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            return MODEL_NAME in models
    except:
        pass
    return False

def pull_model():
    """Pull the DeepSeek-R1:1.5b model"""
    print(f"📦 Pulling {MODEL_NAME} model...")
    
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": MODEL_NAME},
            timeout=600  # 10 minutes timeout for larger model
        )
        
        if response.status_code == 200:
            print(f"✅ Successfully pulled {MODEL_NAME} model!")
            return True
        else:
            print(f"❌ Failed to pull model: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Timeout while pulling model")
        return False
    except Exception as e:
        print(f"❌ Error pulling model: {e}")
        return False

def main():
    """Main function"""
    print("🤖 DeepSeek-R1:1.5b Model Setup Script")
    print("=" * 50)
    
    # Wait for Ollama to be ready
    if not wait_for_ollama():
        sys.exit(1)
    
    # Check if model already exists
    if check_model_exists():
        print(f"✅ {MODEL_NAME} model already exists!")
        return
    
    # Pull the model
    if pull_model():
        print("🎉 Setup complete! The DeepSeek model is ready to use.")
    else:
        print("❌ Failed to pull the model. Please check the logs.")
        sys.exit(1)

if __name__ == "__main__":
    main() 