#!/usr/bin/env python3
"""
AI Chatbot Server - Ollama Integration
A simple Flask server that connects to Ollama API for AI chat functionality.
"""

import os
import json
import requests
import time
import re
import sqlite3
import secrets
import string
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template_string, redirect, url_for, session, flash
from flask_cors import CORS
from auth import auth_manager, login_required, get_current_user
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Generate a secure secret key if not provided
def generate_secret_key():
    """Generate a secure random secret key"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(32))

app.secret_key = os.getenv('SECRET_KEY', generate_secret_key())
CORS(app)  # Enable CORS for all routes

# Security configuration
MAX_MESSAGE_LENGTH = 1000
ALLOWED_MODELS = ['phi3:latest', 'deepseek-r1:1.5b', 'llama3:latest']

# Rate limiting
from collections import defaultdict
import threading
request_counts = defaultdict(int)
request_times = defaultdict(list)
rate_limit_lock = threading.Lock()

def check_rate_limit(ip, max_requests=10, window_seconds=60):
    """Simple rate limiting"""
    with rate_limit_lock:
        current_time = time.time()
        
        # Clean old requests
        request_times[ip] = [t for t in request_times[ip] if current_time - t < window_seconds]
        
        # Check if limit exceeded
        if len(request_times[ip]) >= max_requests:
            return False
        
        # Add current request
        request_times[ip].append(current_time)
        return True

def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    return response

@app.after_request
def after_request(response):
    """Add security headers to all responses"""
    return add_security_headers(response)

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "phi3:latest")
DATABASE_PATH = os.getenv("DATABASE_PATH", "chatbot.db")

def validate_input(data, max_length=MAX_MESSAGE_LENGTH):
    """Validate and sanitize user input"""
    if not data or not isinstance(data, str):
        return None
    
    # Remove any null bytes and excessive whitespace
    data = data.strip().replace('\x00', '')
    
    # Check length
    if len(data) > max_length:
        return None
    
    # Basic content validation (prevent script injection)
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'data:text/html',
        r'on\w+\s*=',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, data, re.IGNORECASE):
            return None
    
    return data

def validate_model(model):
    """Validate model name"""
    return model in ALLOWED_MODELS

def validate_conversation_id(conversation_id):
    """Validate conversation ID format"""
    if not conversation_id or not isinstance(conversation_id, str):
        return False
    
    # Only allow alphanumeric, underscore, and hyphen
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', conversation_id))

class DatabaseManager:
    """Manages SQLite database operations for chat history"""
    
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT UNIQUE NOT NULL,
                        username TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create conversations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        conversation_id TEXT NOT NULL,
                        title TEXT,
                        model TEXT DEFAULT 'phi3',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Create messages table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        model TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def get_or_create_user(self, user_id, username=None):
        """Get existing user or create new one"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user = cursor.fetchone()
                
                if user:
                    # Update last_active
                    cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
                    conn.commit()
                    return user[1]  # Return user_id
                else:
                    # Create new user
                    cursor.execute('''
                        INSERT INTO users (user_id, username) 
                        VALUES (?, ?)
                    ''', (user_id, username or f"User_{user_id[:8]}"))
                    conn.commit()
                    return user_id
                    
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            return user_id
    
    def create_conversation(self, user_id, conversation_id, model=DEFAULT_MODEL):
        """Create a new conversation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO conversations (user_id, conversation_id, model)
                    VALUES (?, ?, ?)
                ''', (user_id, conversation_id, model))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return False
    
    def add_message(self, conversation_id, role, content, model=None):
        """Add a message to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO messages (conversation_id, role, content, model)
                    VALUES (?, ?, ?, ?)
                ''', (conversation_id, role, content, model))
                
                # Update conversation timestamp
                cursor.execute('''
                    UPDATE conversations 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE conversation_id = ?
                ''', (conversation_id,))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False
    
    def get_conversation_messages(self, conversation_id, limit=50):
        """Get messages for a conversation (optimized for speed)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Optimized query with DESC order and LIMIT for faster retrieval
                cursor.execute('''
                    SELECT role, content, model, timestamp
                    FROM messages 
                    WHERE conversation_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (conversation_id, limit))
                
                messages = []
                for row in cursor.fetchall():
                    messages.append({
                        'role': row[0],
                        'content': row[1],
                        'model': row[2],
                        'timestamp': row[3]
                    })
                # Reverse to get correct chronological order
                return list(reversed(messages))
        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            return []
    
    def get_user_conversations(self, user_id):
        """Get all conversations for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT conversation_id, title, model, created_at, updated_at
                    FROM conversations 
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                ''', (user_id,))
                
                conversations = []
                for row in cursor.fetchall():
                    conversations.append({
                        'conversation_id': row[0],
                        'title': row[1],
                        'model': row[2],
                        'created_at': row[3],
                        'updated_at': row[4]
                    })
                return conversations
        except Exception as e:
            logger.error(f"Error getting user conversations: {e}")
            return []
    
    def delete_conversation(self, conversation_id):
        """Delete a conversation and all its messages"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Delete messages first (foreign key constraint)
                cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
                # Delete conversation
                cursor.execute('DELETE FROM conversations WHERE conversation_id = ?', (conversation_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False
    
    def clear_user_conversations(self, user_id):
        """Clear all conversations for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Get all conversation IDs for the user
                cursor.execute('SELECT conversation_id FROM conversations WHERE user_id = ?', (user_id,))
                conversation_ids = [row[0] for row in cursor.fetchall()]
                
                # Delete messages for all conversations
                for conv_id in conversation_ids:
                    cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conv_id,))
                
                # Delete conversations
                cursor.execute('DELETE FROM conversations WHERE user_id = ?', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error clearing user conversations: {e}")
            return False
    
    def conversation_belongs_to_user(self, conversation_id, user_id):
        """Check if a conversation belongs to a specific user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM conversations 
                    WHERE conversation_id = ? AND user_id = ?
                ''', (conversation_id, user_id))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"Error checking conversation ownership: {e}")
            return False

# Initialize database manager
db_manager = DatabaseManager()

class OllamaClient:
    """Client for communicating with Ollama API"""
    
    def __init__(self, base_url=OLLAMA_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
    
    def check_connection(self):
        """Check if Ollama server is running"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False
    
    def get_available_models(self):
        """Get list of available models"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get models: {e}")
            return []
    
    def generate_response(self, message, model=DEFAULT_MODEL, system_prompt=None):
        """Generate response using Ollama API with streaming for faster responses"""
        try:
            payload = {
                "model": model,
                "prompt": message,
                "stream": True,  # Enable streaming for faster responses
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_predict": 256,  # Reduced for faster responses
                    "stop": ["User:", "Human:", "Assistant:", "AI:"]
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60,  # Reduced timeout
                stream=True  # Enable streaming
            )
            
            if response.status_code == 200:
                # Collect streaming response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if 'response' in data:
                                full_response += data['response']
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
                
                return full_response.strip()
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return f"Error: Ollama API returned status {response.status_code}. Try using a smaller model like 'llama2' or 'phi3'."
                
        except requests.exceptions.Timeout:
            logger.error("Ollama API timeout")
            return "Error: Request timed out. The model is taking too long to respond. Try using a smaller model like 'llama2' or 'phi3'."
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed: {e}")
            return f"Error: Failed to connect to Ollama. Make sure Ollama is running and the model is available."
    
    def stream_response(self, message, model=DEFAULT_MODEL, system_prompt=None):
        """Stream response from Ollama API"""
        try:
            payload = {
                "model": model,
                "prompt": message,
                "stream": True,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_predict": 256,
                    "stop": ["User:", "Human:", "Assistant:", "AI:"]
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60,
                stream=True
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if 'response' in data:
                                yield data['response']
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                yield f"Error: Ollama API returned status {response.status_code}."
                
        except requests.exceptions.Timeout:
            logger.error("Ollama API timeout")
            yield "Error: Request timed out. The model is taking too long to respond."
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed: {e}")
            yield f"Error: Failed to connect to Ollama. Make sure Ollama is running and the model is available."

# Initialize Ollama client
ollama_client = OllamaClient()

def format_code_blocks(text):
    """Format code blocks in the text with proper HTML structure"""
    # Pattern to match code blocks: ```language code ```
    pattern = r'```(\w+)?\n(.*?)```'
    
    def replace_code_block(match):
        language = match.group(1) or 'text'
        code = match.group(2).strip()
        
        # Escape HTML characters in the code
        code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Format as HTML code block without inline syntax highlighting
        escaped_code = code.replace("`", "\\`")
        return f'<div class="code-block"><div class="code-header"><span class="language">{language}</span><button class="copy-btn" onclick="navigator.clipboard.writeText(`{escaped_code}`)">Copy</button></div><pre><code class="language-{language.lower()}">{code}</code></pre></div>'
    
    # Replace code blocks
    formatted_text = re.sub(pattern, replace_code_block, text, flags=re.DOTALL)
    
    # Also format inline code
    inline_pattern = r'`([^`]+)`'
    def replace_inline_code(match):
        code = match.group(1)
        code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<code>{code}</code>'
    
    formatted_text = re.sub(inline_pattern, replace_inline_code, formatted_text)
    
    # Handle cases where AI might not format code properly
    # Look for code-like patterns that weren't caught by the above patterns
    if '```' in text and '```' not in formatted_text:
        # If there are backticks but they weren't processed, try to fix them
        lines = text.split('\n')
        in_code_block = False
        code_lines = []
        language = 'text'
        
        for line in lines:
            if line.strip().startswith('```'):
                if not in_code_block:
                    # Start of code block
                    in_code_block = True
                    lang_match = re.match(r'```(\w+)', line.strip())
                    if lang_match:
                        language = lang_match.group(1)
                    code_lines = []
                else:
                    # End of code block
                    in_code_block = False
                    if code_lines:
                        code = '\n'.join(code_lines)
                        code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        escaped_code = code.replace("`", "\\`")
                        code_block_html = f'<div class="code-block"><div class="code-header"><span class="language">{language}</span><button class="copy-btn" onclick="navigator.clipboard.writeText(`{escaped_code}`)">Copy</button></div><pre><code class="language-{language.lower()}">{code}</code></pre></div>'
                        formatted_text = formatted_text.replace(f'```{language}\n{code}\n```', code_block_html)
            elif in_code_block:
                code_lines.append(line)
    
    return formatted_text

def get_user_id():
    """Get authenticated user ID or create anonymous user ID"""
    if 'user_id' in session:
        user_id = session['user_id']
        
        # Check if this is an authenticated user (starts with auth_user_)
        if isinstance(user_id, str) and user_id.startswith('auth_user_'):
            return user_id  # Return the prefixed version for template compatibility
        elif isinstance(user_id, int):
            # Legacy case: convert integer user ID to prefixed string
            session['user_id'] = f"auth_user_{user_id}"
            return f"auth_user_{user_id}"
        else:
            # This is an anonymous user ID, but we don't want to show logout
            # Clear the session for anonymous users
            session.pop('user_id', None)
    
    # For anonymous users, don't create a session
    # This will make the template show Login/Register buttons
    user_id = f"anon_user_{int(time.time())}_{os.getpid()}"
    # Don't store in session for anonymous users
    # session['user_id'] = user_id  # Comment this out
    # Create user in database
    db_manager.get_or_create_user(user_id)
    return user_id

@app.route('/')
def index():
    """Serve the main HTML page with conversation history"""
    user_id = get_user_id()
    conversation_id = request.args.get('conversation_id', 'default')
    selected_model = request.args.get('model', DEFAULT_MODEL)
    
    # Validate inputs
    if not validate_conversation_id(conversation_id):
        conversation_id = 'default'
    
    if not validate_model(selected_model):
        selected_model = DEFAULT_MODEL
    
    # Check if we need to generate AI response
    generate_response = request.args.get('generate_response', '0')
    user_message = validate_input(request.args.get('user_message', ''))
    
    if generate_response == '1' and user_message:
        # Generate AI response immediately
        try:
            # Get recent conversation context (last 2 messages for faster processing)
            recent_messages = db_manager.get_conversation_messages(conversation_id, 2)
            context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
            
            # Generate response with general conversational prompt
            system_prompt = """You are a friendly and helpful AI assistant. Respond naturally to any question or topic. Be conversational, helpful, and engaging. You can discuss anything from casual conversation to technical topics."""
            
            # Include minimal conversation context in the prompt
            full_prompt = f"{context}\n\nUser: {user_message}\nAssistant:"
            
            response = ollama_client.generate_response(full_prompt, selected_model, system_prompt)
            
            # Format the response with code blocks
            formatted_response = format_code_blocks(response)
            
            # Add assistant response to database
            db_manager.add_message(conversation_id, 'assistant', formatted_response, selected_model)
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
        
        # Redirect to show the complete conversation
        return redirect(f'/?conversation_id={conversation_id}&model={selected_model}#bottom')
    
    # Get available models
    available_models = ollama_client.get_available_models()
    if not available_models:
        available_models = ['phi3:latest', 'deepseek-r1:1.5b', 'llama3:latest']
    
    # Get conversation history from database (filtered by user)
    messages = []
    if conversation_id != 'default':
        # Verify this conversation belongs to the current user
        if db_manager.conversation_belongs_to_user(conversation_id, user_id):
            messages = db_manager.get_conversation_messages(conversation_id)
        else:
            # If conversation doesn't belong to user, redirect to default
            return redirect('/?conversation_id=default&model=' + selected_model)
    else:
        # For default conversation, get the most recent conversation for this user
        user_conversations = db_manager.get_user_conversations(user_id)
        if user_conversations:
            # Use the most recent conversation
            conversation_id = user_conversations[0]['conversation_id']
            messages = db_manager.get_conversation_messages(conversation_id)
    
    # Read the HTML template
    with open('index.html', 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # Render the template with data
    return render_template_string(template_content,
                                conversation_id=conversation_id,
                                selected_model=selected_model,
                                available_models=available_models,
                                messages=messages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        username = validate_input(request.form.get('username', ''), max_length=50)
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return redirect(url_for('login'))
        
        success, user_id, username = auth_manager.login_user(username, password)
        
        if success:
            # Store the prefixed user ID in session for template compatibility
            session['user_id'] = f"auth_user_{user_id}"
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
    
    # GET request - show login form
    with open('login.html', 'r', encoding='utf-8') as f:
        template_content = f.read()
    return render_template_string(template_content)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if request.method == 'POST':
        username = validate_input(request.form.get('username', ''), max_length=50)
        email = validate_input(request.form.get('email', ''), max_length=100)
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not username or not email or not password:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return redirect(url_for('register'))
        
        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('register'))
        
        success, message = auth_manager.register_user(username, email, password)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
            return redirect(url_for('register'))
    
    # GET request - show registration form
    with open('register.html', 'r', encoding='utf-8') as f:
        template_content = f.read()
    return render_template_string(template_content)

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    """Show user profile"""
    current_user = get_current_user()
    if not current_user:
        flash('User not found', 'error')
        return redirect(url_for('index'))
    
    with open('profile.html', 'r', encoding='utf-8') as f:
        template_content = f.read()
    return render_template_string(template_content, user=current_user)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    is_connected = ollama_client.check_connection()
    return jsonify({
        'status': 'healthy',
        'ollama_connected': is_connected,
        'available_models': ollama_client.get_available_models() if is_connected else []
    })

@app.route('/api/models')
def get_models():
    """Get available models"""
    models = ollama_client.get_available_models()
    return jsonify({'models': models})

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get all conversation IDs for current user"""
    user_id = get_user_id()
    conversations = db_manager.get_user_conversations(user_id)
    return jsonify({'conversations': conversations})

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get conversation history"""
    messages = db_manager.get_conversation_messages(conversation_id)
    if messages:
        return jsonify({'messages': messages})
    return jsonify({'error': 'Conversation not found'}), 404

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation"""
    if db_manager.delete_conversation(conversation_id):
        return jsonify({'message': 'Conversation deleted'})
    return jsonify({'error': 'Conversation not found'}), 404

@app.route('/api/conversations', methods=['DELETE'])
def clear_all_conversations():
    """Clear all conversations for current user"""
    user_id = get_user_id()
    if db_manager.clear_user_conversations(user_id):
        return jsonify({'message': 'All conversations cleared'})
    return jsonify({'error': 'Failed to clear conversations'}), 500

@app.route('/new_chat')
def new_chat():
    """Start a new conversation"""
    user_id = get_user_id()
    conversation_id = 'chat_' + str(int(time.time()))
    db_manager.create_conversation(user_id, conversation_id)
    return redirect(f'/?conversation_id={conversation_id}')

@app.route('/clear_history')
def clear_history():
    """Clear all conversation history for current user"""
    user_id = get_user_id()
    db_manager.clear_user_conversations(user_id)
    return redirect('/')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests via form submission"""
    # Rate limiting
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip, max_requests=5, window_seconds=60):
        return redirect(f'/?conversation_id=default&model={DEFAULT_MODEL}&error=rate_limit_exceeded')
    
    try:
        user_id = get_user_id()
        
        # Get and validate form data
        message = validate_input(request.form.get('message', ''))
        model = request.form.get('model', DEFAULT_MODEL)
        conversation_id = request.form.get('conversation_id', 'default')
        
        # Validate inputs
        if not message:
            return redirect(f'/?conversation_id={conversation_id}&model={model}&error=invalid_message')
        
        if not validate_model(model):
            model = DEFAULT_MODEL
        
        if not validate_conversation_id(conversation_id):
            conversation_id = 'default'
        
        # Check if Ollama is running
        if not ollama_client.check_connection():
            return redirect(f'/?conversation_id={conversation_id}&model={model}&error=ollama_not_running')
        
        # Create conversation if it doesn't exist
        if conversation_id == 'default':
            conversation_id = 'chat_' + str(int(time.time()))
            db_manager.create_conversation(user_id, conversation_id, model)
        
        # Add user message to database immediately
        db_manager.add_message(conversation_id, 'user', message)
        
        # Redirect to show user message immediately, then generate AI response
        return redirect(f'/?conversation_id={conversation_id}&model={model}&generate_response=1&user_message={message}#bottom')
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return redirect(f'/?conversation_id=default&model={DEFAULT_MODEL}&error=server_error#bottom')



@app.route('/api/status')
def status():
    """Get server and Ollama status"""
    is_connected = ollama_client.check_connection()
    models = ollama_client.get_available_models() if is_connected else []
    
    return jsonify({
        'server_status': 'running',
        'ollama_connected': is_connected,
        'available_models': models,
        'default_model': DEFAULT_MODEL
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def main():
    """Main function to run the server"""
    print("🤖 AI Chatbot Server Starting...")
    print("=" * 50)
    
    # Initialize database
    print("🗄️  Initializing database...")
    try:
        db_manager.init_database()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return
    
    # Check Ollama connection
    if ollama_client.check_connection():
        print("✅ Ollama server is running")
        models = ollama_client.get_available_models()
        if models:
            print(f"📦 Available models: {', '.join(models)}")
        else:
            print("⚠️  No models found. You may need to pull a model first.")
    else:
        print("❌ Ollama server is not running")
        print("   Please start Ollama first:")
        print("   - Download from: https://ollama.ai/")
        print("   - Run: ollama serve")
        print("   - Pull a model: ollama pull llama2")
    
    print("=" * 50)
    print("🌐 Server will be available at: http://localhost:5000")
    print("📝 API endpoints:")
    print("   - GET  /api/health     - Health check")
    print("   - GET  /api/models     - List available models")
    print("   - POST /chat           - Send chat message")
    print("   - GET  /api/status     - Server status")
    print("   - GET  /api/conversations - List conversations")
    print("   - GET  /api/conversations/<id> - Get conversation")
    print("   - DELETE /api/conversations/<id> - Delete conversation")
    print("   - DELETE /api/conversations - Clear all conversations")
    print("=" * 50)
    
    # Run the server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )

if __name__ == '__main__':
    main() 