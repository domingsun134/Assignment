# AI Chatbot with Ollama

A beautiful, modern AI chatbot built with Flask and HTML/CSS that connects to Ollama for local AI model inference. Features user authentication, conversation history, and model selection.

## Features

- 🎨 **Modern UI**: Beautiful gradient design with smooth animations
- 🤖 **AI Powered**: Connects to Ollama for local AI model inference
- 📱 **Responsive**: Works perfectly on desktop and mobile devices
- 🎯 **Model Selection**: Choose from different Ollama models
- 🚀 **Zero JavaScript**: Pure HTML/CSS only
- 🔒 **Local**: All processing happens on your machine via Ollama
- 👤 **User Authentication**: Register, login, and manage user profiles
- 💾 **Conversation History**: Persistent chat history with database storage
- 🐳 **Docker Support**: Easy deployment with Docker Compose
- 🔐 **Security**: Bcrypt password hashing, input validation, rate limiting

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   Flask Server  │    │   Ollama API    │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   HTML/CSS  │◄┼────┼►│   Flask     │◄┼────┼►│   Ollama    │ │
│ │   Interface │ │    │ │   App       │ │    │ │   Server    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│                 │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│                 │    │ │  Auth       │ │    │ │  AI Models  │ │
│                 │    │ │  System     │ │    │ │  (phi3,     │ │
│                 │    │ └─────────────┘ │    │ │  deepseek)  │ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   SQLite DB     │
                       │                 │
                       │ ┌─────────────┐ │
                       │ │   Users     │ │
                       │ │   Tables    │ │
                       │ └─────────────┘ │
                       │ ┌─────────────┐ │
                       │ │Conversations│ │
                       │ │   Tables    │ │
                       │ └─────────────┘ │
                       └─────────────────┘
```

### Data Flow

1. **User Interface**: Pure HTML/CSS frontend with zero JavaScript
2. **Flask Backend**: Handles HTTP requests, authentication, and database operations
3. **Ollama Integration**: Connects to local Ollama server for AI model inference
4. **Database**: SQLite stores user accounts, conversations, and messages
5. **Authentication**: Secure user registration, login, and session management

## Technology Choices

### Frontend
- **HTML5/CSS3**: Pure markup and styling for maximum compatibility
- **Zero JavaScript**: No JavaScript at all - pure HTML/CSS implementation
- **Responsive Design**: CSS Grid and Flexbox for mobile-first approach
- **Modern UI**: Gradient backgrounds, glass-morphism effects, and smooth animations

### Backend
- **Flask**: Lightweight Python web framework for rapid development
- **SQLite**: File-based database for simplicity and portability
- **Flask-CORS**: Cross-origin resource sharing for API access
- **Session Management**: Secure user sessions with Flask

### AI Integration
- **Ollama**: Local AI model inference server
- **Multiple Models**: Support for phi3, deepseek-r1:1.5b
- **Model Selection**: User can choose and maintain their preferred model

### Security
- **Bcrypt Password Hashing**: Secure password storage with salt
- **Session Management**: Secure user sessions with Flask
- **Input Validation**: Server-side validation for all user inputs
- **SQL Injection Protection**: Parameterized queries with SQLite
- **Rate Limiting**: IP-based rate limiting to prevent abuse
- **Security Headers**: XSS protection, content type options, frame options

### Deployment
- **Docker**: Containerized deployment for consistency
- **Docker Compose**: Multi-service orchestration (Flask + Ollama)
- **Environment Variables**: Configurable settings for different environments
- **Health Checks**: Built-in health monitoring for containers
- **Security Options**: No-new-privileges, read-only filesystem where possible

### Why These Choices?

1. **Simplicity**: HTML/CSS frontend with zero JavaScript
2. **Performance**: Local AI inference with Ollama
3. **Portability**: SQLite database and Docker containers
4. **Security**: Built-in authentication and session management
5. **Scalability**: Modular architecture for easy feature additions
6. **User Experience**: Modern UI with responsive design
7. **Developer Experience**: Clear separation of concerns and well-documented code

## Prerequisites

Before running this chatbot, you need to:

1. **Install Ollama**: Download and install Ollama from [https://ollama.ai/](https://ollama.ai/)
2. **Install Python**: Make sure you have Python 3.7+ installed
3. **Pull a Model**: Download at least one AI model (auto pull phi3 and deepseek)

## Quick Start

### Option 1: Docker (Recommended)

The easiest way to run the chatbot with automatic model setup:

```bash
# Build and start with Docker Compose
docker-compose up --build

# Access at: http://localhost:5000
```

The Docker setup automatically:
- Starts Ollama server
- Pulls Phi-3 and DeepSeek models
- Starts the chatbot server
- Handles all dependencies

### Option 2: Manual Setup

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Start Ollama

```bash
# Start the Ollama server
ollama serve
```

#### 3. Pull Models (if you haven't already)

```bash
# Pull Phi-3 (recommended)
ollama pull phi3

# Pull DeepSeek-R1:1.5b (coding focused)
ollama pull deepseek-r1:1.5b

# Or try other models
ollama pull llama2
ollama pull codellama
```

#### 4. Run the Chatbot Server

```bash
python server.py
```

#### 5. Open in Browser

Navigate to: http://localhost:5000

## Usage

1. **Register/Login**: Create an account or login to save your conversations
2. **Select a Model**: Choose from the dropdown menu (Phi-3, DeepSeek-R1:1.5b, Llama 2, Code Llama, etc.)
3. **Type Your Message**: Enter your question or prompt in the input field
4. **Send**: Click "Send" or press Enter to get an AI response
5. **Chat**: Continue the conversation naturally - your model selection will be maintained

## Available Models

The chatbot supports any model available in Ollama. Popular options include:

- **phi3**: Fast and efficient model (default)
- **deepseek-r1:1.5b**: Specialized for code generation

To see all available models:
```bash
ollama list
```

To pull a new model:
```bash
ollama pull <model-name>
```

## Authentication Features

The chatbot includes a complete authentication system:

- **User Registration**: Create new accounts with email verification
- **User Login**: Secure login with password hashing
- **User Profiles**: Manage your profile and preferences
- **Session Management**: Persistent login sessions
- **Conversation Privacy**: Each user's conversations are private

## API Endpoints

The server provides several API endpoints:

- `GET /api/health` - Health check and Ollama connection status
- `GET /api/models` - List available Ollama models
- `POST /chat` - Send a chat message and get AI response
- `GET /api/status` - Server and Ollama status
- `GET /api/conversations` - Get user's conversation history
- `POST /login` - User authentication
- `POST /register` - User registration

## File Structure

```
ai-chatbot/
├── server.py              # Main Flask server application
├── index.html             # Main chat interface
├── login.html             # Login page
├── register.html          # Registration page
├── profile.html           # User profile page
├── auth.py                # Authentication system
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker orchestration
├── Dockerfile             # Docker container definition
├── .dockerignore          # Docker ignore rules
├── startup.sh             # Startup script for Docker
├── pull_phi3.py          # Phi-3 model setup script
├── pull_deepseek.py      # DeepSeek model setup script
├── db_utils.py           # Database utilities (optional)
└── README.md             # This file
```

## Troubleshooting

### Ollama Not Running
If you see "Ollama server is not running":
1. Make sure Ollama is installed
2. Run `ollama serve` in a terminal
3. Check that Ollama is accessible at http://localhost:11434

### No Models Available
If no models are found:
1. Pull a model: `ollama pull llama2`
2. Check available models: `ollama list`
3. Restart the server

### Connection Errors
If the chatbot can't connect to the server:
1. Make sure the Python server is running: `python server.py`
2. Check the URL: http://localhost:5000
3. Verify no firewall is blocking the connection

### Model Auto-Switching Issue (Fixed)
The model selection now properly maintains your choice throughout the conversation. The previous issue where models would auto-switch back to phi3 has been resolved.

### DeepSeek Model Not Pulling (Fixed)
The DeepSeek model pull script has been updated to match the working Phi-3 pattern. Both models should now pull successfully during startup.

### Authentication Issues (Fixed)
- **Login/Register Display**: Fixed to show correct buttons for anonymous vs authenticated users
- **Password Hashing**: Upgraded to bcrypt for secure password storage
- **Session Management**: Improved session handling for better user experience

### Slow Responses
- Try a smaller model (e.g., `llama2:7b` instead of `llama2:13b`)
- Close other applications to free up RAM
- Consider using a more powerful machine

### Docker Issues
If you encounter Docker-related issues:
1. **Line ending errors**: The Dockerfile now includes `dos2unix` to fix Windows/Unix line ending issues
2. **Permission errors**: The startup script is properly made executable
3. **Model pull failures**: Both model pull scripts have been standardized for reliability

## Customization

### Changing the Default Model
Edit `server.py` and change the `DEFAULT_MODEL` variable:
```python
DEFAULT_MODEL = "phi3"  # Change to your preferred model
```

### Modifying the UI
The entire UI is in the HTML files. You can customize:
- Colors and gradients in the CSS
- Layout and spacing
- Animations and transitions
- Message styling

### Adding System Prompts
Modify the system prompt in `server.py`:
```python
system_prompt = """Your custom system prompt here."""
```

## Development

### Running in Development Mode
```bash
# Enable debug mode
export FLASK_ENV=development
python server.py
```

### Adding New Features
1. Modify HTML files for UI changes
2. Update `server.py` for backend functionality
3. Test with different Ollama models

## Security Notes

- The server runs on `0.0.0.0:5000` by default
- For production use, consider:
  - Using a reverse proxy (nginx)
  - Adding HTTPS
  - Running behind a firewall
  - Limiting access to localhost only
  - Changing the default secret key

## Performance Tips

1. **Use Smaller Models**: 7B models are faster than 13B models
2. **Close Unused Applications**: Free up RAM for AI inference
3. **SSD Storage**: Faster model loading with SSD
4. **GPU Acceleration**: Install CUDA for GPU acceleration (if supported)

## Contributing

Feel free to contribute by:
- Reporting bugs
- Suggesting new features
- Improving the UI/UX
- Adding new model support
- Optimizing performance

## License

This project is open source and available under the MIT License.

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify Ollama is running: `ollama list`
3. Check server logs for error messages
4. Ensure you have sufficient RAM for the selected model

---

**Happy Chatting! 🤖✨**
