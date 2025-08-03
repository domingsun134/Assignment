#!/usr/bin/env python3
"""
Pull DeepSeek-R1:1.5b model from Ollama
This script waits for Ollama to be ready and pulls the DeepSeek-R1:1.5b model
"""

import os
import time
import requests
import subprocess
import sys

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = "deepseek-r1:1.5b"
MAX_RETRIES = 30
RETRY_DELAY = 2

def check_ollama_connection():
    """Check if Ollama is running and accessible"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def check_model_exists():
    """Check if DeepSeek-R1:1.5b model is already available"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            for model in models:
                if MODEL_NAME in model.get("name", ""):
                    return True
        return False
    except requests.exceptions.RequestException:
        return False

def pull_model():
    """Pull the DeepSeek-R1:1.5b model using Ollama API"""
    try:
        print(f"📥 Pulling {MODEL_NAME} model...")
        
        # Use the Ollama API to pull the model
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": MODEL_NAME},
            timeout=600,  # 10 minutes timeout
            stream=True
        )
        
        if response.status_code == 200:
            print(f"✅ {MODEL_NAME} model pulled successfully!")
            return True
        else:
            print(f"❌ Failed to pull {MODEL_NAME} model: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏰ Timeout while pulling {MODEL_NAME} model")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error pulling {MODEL_NAME} model: {e}")
        return False
    except Exception as e:
        print(f"❌ Error pulling {MODEL_NAME} model: {e}")
        return False

def main():
    """Main function to pull DeepSeek-R1:1.5b model"""
    print(f"🤖 Setting up {MODEL_NAME} model for AI Chatbot")
    print("=" * 50)
    
    # Check if model already exists
    print(f"🔍 Checking if {MODEL_NAME} model is already available...")
    if check_model_exists():
        print(f"✅ {MODEL_NAME} model is already available!")
        return True
    
    # Wait for Ollama to be ready
    print("⏳ Waiting for Ollama to be ready...")
    retries = 0
    
    while retries < MAX_RETRIES:
        if check_ollama_connection():
            print("✅ Ollama is ready!")
            break
        else:
            retries += 1
            print(f"⏳ Waiting for Ollama... (attempt {retries}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
    
    if retries >= MAX_RETRIES:
        print("❌ Ollama is not responding. Please check if Ollama is running.")
        return False
    
    # Pull the model
    success = pull_model()
    
    if success:
        print(f"🎉 {MODEL_NAME} model setup complete!")
        print(f"📊 Model info:")
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                for model in models:
                    if MODEL_NAME in model.get("name", ""):
                        size_mb = model.get("size", 0) / (1024 * 1024)
                        print(f"   - Name: {model.get('name', 'N/A')}")
                        print(f"   - Size: {size_mb:.1f} MB")
                        print(f"   - Modified: {model.get('modified_at', 'N/A')}")
                        break
        except:
            print("   - Model info unavailable")
    else:
        print(f"❌ Failed to setup {MODEL_NAME} model")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 