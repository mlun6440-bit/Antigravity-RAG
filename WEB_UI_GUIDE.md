# Web UI Guide - Asset Register ISO 55000 Specialist

## Overview

This guide documents the web-based user interface pattern for the Asset Register ISO 55000 Specialist system. The web UI replaces the command-line interface with a professional, user-friendly chat interface.

## Architecture

### Technology Stack

- **Backend Framework**: Flask 3.1.2
- **Frontend**: Vanilla JavaScript + HTML5 + CSS3
- **Communication**: REST API with JSON responses
- **CORS**: Enabled via flask-cors for cross-origin requests

### File Structure

```
Asset/
├── web_app.py              # Flask application (backend)
├── templates/
│   └── index.html          # Main UI template (frontend)
├── static/                 # Static assets directory
├── start_web.bat           # Windows launcher script
└── tools/                  # Backend modules
    ├── gemini_query_engine.py
    ├── command_parser.py
    ├── asset_updater.py
    └── question_suggester.py
```

## Components

### 1. Backend (web_app.py)

**Purpose**: Flask application that serves the UI and provides REST API endpoints

**Key Features**:
- Loads environment variables from `.env`
- Initializes all components (query engine, parser, updater, suggester)
- Graceful degradation if components fail to initialize
- No Unicode characters in print statements (Windows compatibility)

**API Endpoints**:

#### GET `/`
Returns the main HTML interface

#### POST `/api/query`
Handle user queries and commands

**Request**:
```json
{
  "question": "What is ISO 55000?"
}
```

**Response (Regular Query)**:
```json
{
  "answer": "ISO 55000 is...",
  "model": "gemini-1.5-flash",
  "context_size": 1500,
  "citation_count": 3
}
```

**Response (CRUD Detection)**:
```json
{
  "intent": "UPDATE",
  "params": {
    "type": "single",
    "asset_id": "A-001",
    "field": "Condition",
    "value": "Poor"
  },
  "requires_confirmation": true,
  "message": "This will perform a UPDATE operation. Please confirm."
}
```

#### GET `/api/suggestions?num=5&difficulty=all`
Get question suggestions

**Response**:
```json
{
  "suggestions": [
    {
      "question": "What is ISO 55000?",
      "category": "ISO Standards",
      "difficulty": "beginner"
    }
  ]
}
```

#### GET `/api/status`
Get system status and statistics

**Response**:
```json
{
  "asset_index": true,
  "iso_kb": true,
  "components": {
    "query_engine": true,
    "command_parser": true,
    "asset_updater": true,
    "question_suggester": true
  },
  "stats": {
    "total_assets": 150,
    "total_fields": 450,
    "source_files": 9
  },
  "iso_stats": {
    "total_standards": 3,
    "total_chunks": 60
  }
}
```

#### POST `/api/crud`
Execute CRUD operations after confirmation

**Request**:
```json
{
  "operation": "UPDATE",
  "params": {
    "type": "single",
    "asset_id": "A-001",
    "field": "Condition",
    "value": "Poor"
  },
  "confirmed": true
}
```

**Response**:
```json
{
  "success": true,
  "message": "Update completed",
  "result": {}
}
```

### 2. Frontend (templates/index.html)

**Purpose**: Single-page application with chat interface

**Key Features**:
- Gradient purple/blue theme
- Real-time chat interface
- Citation highlighting
- CRUD confirmation dialogs
- Question suggestion chips
- System status indicator
- Loading animations
- Responsive design

**UI Sections**:

1. **Header**: Title and description with gradient background
2. **Status Bar**: Real-time system status and statistics
3. **Chat Area**: Scrollable message history with user/AI avatars
4. **Suggestions**: Clickable question chips
5. **Input Area**: Text input + send button

**JavaScript Functions**:

- `loadSystemStatus()`: Polls `/api/status` on page load
- `loadSuggestions()`: Fetches question suggestions
- `sendMessage()`: Sends user query to `/api/query`
- `addMessage(role, content)`: Adds message to chat
- `addCrudConfirmation()`: Shows CRUD confirmation dialog
- `confirmCrud()`: Executes CRUD operation via `/api/crud`
- `cancelCrud()`: Cancels pending CRUD operation
- `formatAnswer()`: Converts markdown-style text to HTML

## Usage

### Starting the Web UI

**Option 1: Using Batch Script** (Recommended)
```batch
start_web.bat
```

**Option 2: Manual**
```batch
cd "c:\Users\eralu\OneDrive\Desktop\Asset managment\N8N NAT\Asset"
py web_app.py
```

The server will start on:
- Local: http://127.0.0.1:5000
- Network: http://192.168.0.107:5000

### User Interactions

#### 1. Asking Questions
Type a question in the input field and press Enter or click Send.

**Examples**:
- "What is ISO 55000?"
- "How many assets do we have?"
- "According to ISO 55001, how should I manage assets?"

The system will respond with an answer including citations if available.

#### 2. Using Suggestions
Click any suggestion chip to automatically populate the input field and send the query.

#### 3. CRUD Operations

**Update Single Asset**:
```
update asset A-001 condition to Poor
```

**Bulk Update**:
```
change all Fair to Poor
```

When a CRUD operation is detected:
1. System shows confirmation dialog with operation details
2. Click "Confirm" to execute or "Cancel" to abort
3. Success/error message displayed after execution

#### 4. Viewing Citations
Citations appear as blue numbered tags like [1], [2], [3] within the answer text. The full reference list appears at the bottom of the answer.

## Design Patterns

### 1. Chat Interface Pattern

**Structure**:
```html
<div class="message user">
  <div class="message-avatar">U</div>
  <div class="message-content">User's question</div>
</div>

<div class="message assistant">
  <div class="message-avatar">AI</div>
  <div class="message-content">AI's answer</div>
</div>
```

**Styling**:
- User messages: Right-aligned, purple background
- AI messages: Left-aligned, white background
- Avatars: Circular, colored by role
- Max width: 70% of chat area

### 2. Confirmation Dialog Pattern

**Use Case**: Before executing destructive operations (UPDATE/DELETE)

**Implementation**:
```javascript
let pendingCrudOperation = null;

function addCrudConfirmation(operation, params, message) {
  // Store operation details
  pendingCrudOperation = { operation, params };

  // Show dialog with operation details
  contentDiv.innerHTML = `
    <div class="confirmation-dialog">
      <strong>${message}</strong>
      <ul>${paramsList}</ul>
      <div class="buttons">
        <button onclick="confirmCrud()">Confirm</button>
        <button onclick="cancelCrud()">Cancel</button>
      </div>
    </div>
  `;
}
```

### 3. Status Indicator Pattern

**Visual States**:
- Green pulsing dot = System online
- Red solid dot = System offline
- Text description next to dot

**Implementation**:
```javascript
async function loadSystemStatus() {
  const response = await fetch('/api/status');
  const data = await response.json();

  if (data.asset_index && data.iso_kb) {
    statusDot.className = 'status-dot active';  // Green
    statusText.textContent = 'Online';
  } else {
    statusDot.className = 'status-dot inactive'; // Red
    statusText.textContent = 'Offline';
  }
}
```

### 4. Loading Animation Pattern

**Purpose**: Show activity during API calls

**Implementation**:
```javascript
function showLoading() {
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'loading active';
  loadingDiv.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';
  chatArea.appendChild(loadingDiv);
}

function hideLoading() {
  document.getElementById('loading-indicator')?.remove();
}
```

**CSS Animation**:
```css
@keyframes loading {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
```

### 5. Citation Formatting Pattern

**Backend** (citation_formatter.py):
```python
def add_iso_citation(self, iso_standard, section, page_range):
    self.citation_counter += 1
    self.citations.append({
        'number': self.citation_counter,
        'type': 'iso_standard',
        'iso_standard': iso_standard,
        'section_number': section,
        'page_range': page_range
    })
    return self.citation_counter
```

**Frontend** (JavaScript):
```javascript
function formatAnswer(answer) {
  // Convert [1], [2] to clickable citations
  let formatted = answer.replace(/\[(\d+)\]/g,
    '<span class="citation">[$1]</span>');

  // Convert horizontal lines
  formatted = formatted.replace(/━{70}/g,
    '<hr style="margin: 15px 0;">');

  return formatted;
}
```

## Customization

### Theme Colors

Edit the CSS variables in `templates/index.html`:

```css
/* Primary gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* User message */
.message.user .message-content {
  background: #667eea;
  color: white;
}

/* Citation color */
.citation {
  color: #667eea;
}
```

### Adding New API Endpoints

1. **Define route in web_app.py**:
```python
@app.route('/api/myendpoint', methods=['POST'])
def api_myendpoint():
    try:
        data = request.get_json()
        # Process data
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

2. **Call from frontend**:
```javascript
async function callMyEndpoint(data) {
  const response = await fetch('/api/myendpoint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return await response.json();
}
```

### Adding New Message Types

1. **Create CSS class**:
```css
.message.system {
  justify-content: center;
}

.message.system .message-content {
  background: #ffc107;
  color: #333;
  max-width: 90%;
}
```

2. **Add to JavaScript**:
```javascript
function addSystemMessage(content) {
  addMessage('system', content);
}
```

## Troubleshooting

### Issue: Unicode Characters Not Displaying

**Symptom**: `UnicodeEncodeError: 'charmap' codec can't encode character`

**Solution**: Use ASCII-safe characters in Python print statements
```python
# BAD
print("✓ Success")

# GOOD
print("[OK] Success")
```

**Launcher Script** (start_web.bat):
```batch
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
```

### Issue: API Key Not Found

**Symptom**: "Gemini API key not found" warning on startup

**Solution**: Ensure `.env` file exists with:
```
GEMINI_API_KEY=your_api_key_here
```

**Note**: The web UI will still load, but queries will fail without API key.

### Issue: CORS Errors

**Symptom**: Browser console shows CORS policy errors

**Solution**: Ensure CORS is enabled in web_app.py:
```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
```

### Issue: Port Already in Use

**Symptom**: `Address already in use` error

**Solution**: Change port in web_app.py:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Use different port
```

## Security Considerations

### Development vs Production

**Current Setup**: Development server (Flask built-in)
- Good for: Testing, local use, development
- NOT for: Production deployment, public access

**For Production**: Use a WSGI server
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 web_app:app
```

### CSRF Protection

For write operations, consider adding CSRF tokens:

```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

@app.route('/api/crud', methods=['POST'])
@csrf.exempt  # Or use CSRF token
def api_crud():
    # ...
```

### Input Validation

Always validate user input on the backend:

```python
@app.route('/api/query', methods=['POST'])
def api_query():
    data = request.get_json()
    question = data.get('question', '').strip()

    # Validate
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    if len(question) > 1000:
        return jsonify({'error': 'Question too long'}), 400

    # Process...
```

### Authentication

For multi-user deployments, add authentication:

```python
from flask_login import LoginManager, login_required

@app.route('/api/query', methods=['POST'])
@login_required
def api_query():
    # Only authenticated users can query
```

## Performance Optimization

### 1. Static File Caching

Add cache headers for static files:
```python
@app.after_request
def add_header(response):
    if 'static' in request.path:
        response.cache_control.max_age = 3600  # 1 hour
    return response
```

### 2. API Response Compression

Enable gzip compression:
```python
from flask_compress import Compress
Compress(app)
```

### 3. Async Processing

For long-running queries, use background tasks:
```python
from flask import Flask
import threading

def process_query_async(question):
    # Long running task
    result = query_engine.query(question, ...)
    # Store result in session or database

@app.route('/api/query', methods=['POST'])
def api_query():
    threading.Thread(target=process_query_async, args=(question,)).start()
    return jsonify({'status': 'processing', 'job_id': job_id})
```

## Future Enhancements

### Potential Features

1. **User Authentication**: Login system with user-specific history
2. **Conversation History**: Save and restore previous chat sessions
3. **Export Functionality**: Download answers as PDF or Word
4. **Advanced Search**: Filter assets with complex criteria
5. **Visualization**: Charts and graphs for asset statistics
6. **File Upload**: Import new asset data via web UI
7. **Real-time Collaboration**: Multiple users chatting simultaneously
8. **Voice Input**: Speech-to-text for queries
9. **Dark Mode Toggle**: User preference for theme
10. **Mobile App**: Native iOS/Android wrapper

### Code Organization

For larger applications, consider:

1. **Blueprints**: Organize routes into modules
```python
from flask import Blueprint
api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/query', methods=['POST'])
def query():
    # ...
```

2. **Template Inheritance**: Reusable layouts
```html
<!-- base.html -->
<!DOCTYPE html>
<html>
  <head>{% block head %}{% endblock %}</head>
  <body>{% block content %}{% endblock %}</body>
</html>

<!-- index.html -->
{% extends "base.html" %}
{% block content %}
  <div class="container">...</div>
{% endblock %}
```

3. **Config Classes**: Environment-specific settings
```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = False

class DevelopmentConfig(Config):
    DEBUG = True

app.config.from_object(DevelopmentConfig)
```

## Conclusion

This web UI pattern provides a professional, user-friendly interface for the Asset Register ISO 55000 Specialist system. It demonstrates:

- Clean separation of frontend/backend
- RESTful API design
- Responsive, modern UI
- Real-time interactions
- Safe CRUD operations with confirmations
- Citation transparency
- Graceful error handling

The pattern is reusable for any LLM-powered chat application requiring asset management, knowledge base queries, and data modification capabilities.

## Quick Reference

**Start Server**: `start_web.bat` or `py web_app.py`

**URLs**:
- Main UI: http://localhost:5000
- API: http://localhost:5000/api/*

**Key Files**:
- Backend: `web_app.py`
- Frontend: `templates/index.html`
- Launcher: `start_web.bat`

**Dependencies**:
- Flask 3.1.2
- flask-cors 6.0.2
- python-dotenv 1.0.0

**Browser Requirements**:
- Modern browser with JavaScript enabled
- Tested on: Chrome, Firefox, Edge
