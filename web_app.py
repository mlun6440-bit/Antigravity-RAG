#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asset Register ISO 55000 Specialist - Web UI
Flask-based web interface for user-friendly interactions.
"""

import os
import sys
import logging
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import secrets
from dotenv import load_dotenv

# Create logs directory before configuring logging
os.makedirs('logs', exist_ok=True)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from gemini_query_engine import GeminiQueryEngine
from command_parser import CommandParser
from asset_updater import AssetUpdater
from question_suggester import QuestionSuggester

# Initialize Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Restrict CORS to localhost only
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

# Initialize rate limiter (10 requests per minute per IP)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour", "10 per minute"],
    storage_uri="memory://"
)

# File paths
DATA_DIR = 'data/.tmp'
ASSET_INDEX_FILE = os.path.join(DATA_DIR, 'asset_index.json')
ISO_KB_FILE = os.path.join(DATA_DIR, 'iso_knowledge_base.json')

# Initialize components
try:
    query_engine = GeminiQueryEngine()
    command_parser = CommandParser()
    asset_updater = AssetUpdater()
    question_suggester = QuestionSuggester()
    print("[OK] All components initialized successfully")
except Exception as e:
    import traceback
    print(f"[WARNING] Component initialization warning:")
    print(f"Error: {str(e)}")
    traceback.print_exc()
    query_engine = None
    command_parser = None
    asset_updater = None
    question_suggester = None


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


def sanitize_input(text):
    """Sanitize user input to prevent injection attacks."""
    if not text:
        return ""

    # Remove potentially dangerous characters
    text = re.sub(r'[<>\"\'`]', '', text)

    # Limit length
    max_length = 1000
    if len(text) > max_length:
        text = text[:max_length]

    return text.strip()


@app.route('/api/query', methods=['POST'])
@limiter.limit("10 per minute")
def api_query():
    """Handle user queries."""
    try:
        # Check if components are initialized
        if query_engine is None:
            logger.error("Query engine not initialized")
            return jsonify({
                'error': 'Query engine not initialized. Please check your .env file and ensure GEMINI_API_KEY is set.',
                'setup_required': True
            }), 500

        data = request.get_json()
        question = data.get('question', '').strip()

        if not question:
            return jsonify({'error': 'No question provided'}), 400

        # Validate and sanitize input
        if len(question) > 1000:
            logger.warning(f"Question too long: {len(question)} characters")
            return jsonify({'error': 'Question too long (max 1000 characters)'}), 400

        question = sanitize_input(question)

        # Log query (without sensitive data)
        logger.info(f"Query received from {request.remote_addr}: {question[:50]}...")

        # Check if data exists
        if not os.path.exists(ASSET_INDEX_FILE):
            # Try querying ISO KB only
            if os.path.exists(ISO_KB_FILE):
                result = query_engine.query(
                    question=question,
                    asset_index_file=None,
                    iso_kb_file=ISO_KB_FILE
                )
            else:
                return jsonify({
                    'error': 'System not set up. Please run setup first.',
                    'setup_command': 'python run_asset_specialist.py --setup'
                }), 500
        else:
            # Detect command intent
            if command_parser is None:
                return jsonify({'error': 'Command parser not initialized'}), 500

            intent, params = command_parser.detect_intent(question)

            if intent in ['UPDATE', 'CREATE', 'DELETE']:
                # Handle CRUD operation
                return jsonify({
                    'intent': intent,
                    'params': params,
                    'requires_confirmation': True,
                    'message': f'This will perform a {intent} operation. Please confirm.'
                })
            else:
                # Regular query
                result = query_engine.query(
                    question=question,
                    asset_index_file=ASSET_INDEX_FILE,
                    iso_kb_file=ISO_KB_FILE if os.path.exists(ISO_KB_FILE) else None
                )

        if result['status'] == 'success':
            return jsonify({
                'answer': result['answer'],
                'citations': result.get('citations', []),  # Structured citations for popups
                'model': result.get('model', 'Unknown'),
                'context_size': result.get('context_size', 0),
                'citation_count': result.get('citation_count', 0)
            })
        else:
            return jsonify({'error': result.get('error', 'Unknown error')}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/suggestions', methods=['GET'])
def api_suggestions():
    """Get question suggestions."""
    try:
        num = int(request.args.get('num', 5))
        difficulty = request.args.get('difficulty', 'all')

        if not os.path.exists(ASSET_INDEX_FILE):
            # Return ISO-only suggestions
            suggestions = [
                {
                    'question': 'What is ISO 55000?',
                    'category': 'ISO Standards',
                    'difficulty': 'beginner'
                },
                {
                    'question': 'According to ISO 55001, how should I manage assets?',
                    'category': 'ISO Standards',
                    'difficulty': 'beginner'
                },
                {
                    'question': 'What does ISO 55002 say about condition assessment?',
                    'category': 'ISO Standards',
                    'difficulty': 'intermediate'
                },
                {
                    'question': 'How does ISO 55000 define asset management?',
                    'category': 'ISO Standards',
                    'difficulty': 'beginner'
                },
                {
                    'question': 'What are the key principles of ISO 55000?',
                    'category': 'ISO Standards',
                    'difficulty': 'beginner'
                }
            ]
        else:
            suggestions = question_suggester.suggest_questions(
                asset_index_file=ASSET_INDEX_FILE,
                num_suggestions=num,
                difficulty=difficulty
            )

        return jsonify({'suggestions': suggestions[:num]})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def api_status():
    """Get system status."""
    try:
        status = {
            'asset_index': os.path.exists(ASSET_INDEX_FILE),
            'iso_kb': os.path.exists(ISO_KB_FILE),
            'components': {
                'query_engine': query_engine is not None,
                'command_parser': command_parser is not None,
                'asset_updater': asset_updater is not None,
                'question_suggester': question_suggester is not None
            }
        }

        # Get stats if available
        if os.path.exists(ASSET_INDEX_FILE):
            import json
            with open(ASSET_INDEX_FILE, 'r', encoding='utf-8') as f:
                index = json.load(f)
                stats = index.get('statistics', {})
                status['stats'] = {
                    'total_assets': stats.get('total_assets', 0),
                    'total_fields': stats.get('total_fields', 0),
                    'source_files': len(stats.get('source_distribution', {}))
                }

        if os.path.exists(ISO_KB_FILE):
            import json
            with open(ISO_KB_FILE, 'r', encoding='utf-8') as f:
                kb = json.load(f)
                status['iso_stats'] = {
                    'total_standards': len(kb.get('standards', {})),
                    'total_chunks': len(kb.get('all_chunks', []))
                }

        return jsonify(status)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug-citations', methods=['GET'])
def api_debug_citations():
    """Debug endpoint to inspect citation data structure."""
    try:
        import json

        # Run a test query
        test_question = "What is risk management in ISO 55001?"

        if not os.path.exists(ISO_KB_FILE):
            return jsonify({
                'error': 'ISO knowledge base not found',
                'setup_required': True
            }), 500

        # Execute query
        result = query_engine.query(
            question=test_question,
            asset_index_file=None,
            iso_kb_file=ISO_KB_FILE
        )

        # Format output
        debug_info = {
            'test_question': test_question,
            'citations_count': len(result.get('citations', [])),
            'citations': result.get('citations', []),
            'sample_citation': result.get('citations', [])[0] if result.get('citations') else None,
            'field_check': {}
        }

        # Check each citation's fields
        if result.get('citations'):
            for i, cit in enumerate(result.get('citations', [])[:3], 1):
                debug_info['field_check'][f'citation_{i}'] = {
                    'has_number': 'number' in cit,
                    'has_type': 'type' in cit,
                    'has_standard': 'standard' in cit,
                    'has_section': 'section' in cit,
                    'has_title': 'title' in cit,
                    'has_pages': 'pages' in cit,
                    'has_quote': 'quote' in cit,
                    'all_fields': list(cit.keys())
                }

        return jsonify(debug_info), 200, {'Content-Type': 'application/json; charset=utf-8'}

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/crud', methods=['POST'])
def api_crud():
    """Handle CRUD operations."""
    try:
        data = request.get_json()
        operation = data.get('operation')
        params = data.get('params')
        confirmed = data.get('confirmed', False)

        if not confirmed:
            return jsonify({'error': 'Operation not confirmed'}), 400

        # Handle different CRUD operations
        if operation == 'UPDATE':
            if params.get('type') == 'single':
                result = asset_updater.update_asset(
                    asset_id=params['asset_id'],
                    field=params['field'],
                    new_value=params['value'],
                    confirm=False
                )
            elif params.get('type') == 'bulk':
                result = asset_updater.bulk_update_by_criteria(
                    filter_field=params['filter_field'],
                    filter_value=params['filter_value'],
                    update_field=params.get('update_field', params['filter_field']),
                    new_value=params['new_value'],
                    confirm=False
                )
            return jsonify({'success': True, 'message': 'Update completed', 'result': result})

        elif operation == 'CREATE':
            return jsonify({'success': True, 'message': 'Create operation (to be implemented)'})

        elif operation == 'DELETE':
            return jsonify({'success': True, 'message': 'Delete operation (to be implemented)'})

        else:
            return jsonify({'error': 'Unknown operation'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Get environment mode
    is_production = os.getenv('FLASK_ENV') == 'production'
    debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

    print("\n" + "="*70)
    print("=== Asset Register ISO 55000 Specialist - Web UI ===")
    print("="*70)
    print(f"\nEnvironment: {'Production' if is_production else 'Development'}")
    print(f"Debug Mode: {debug_mode}")
    print(f"Rate Limiting: 10 requests/minute, 100 requests/hour")
    print(f"CORS Restricted: localhost only")
    print("\nStarting web server...")
    print("Open your browser and go to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server")
    print("="*70 + "\n")

    logger.info("Web server starting")

    # Run with appropriate settings
    if is_production:
        # Production: Use Gunicorn or similar WSGI server
        logger.warning("Running in production mode with Flask dev server - use Gunicorn instead!")
        app.run(debug=False, host='127.0.0.1', port=5000)
    else:
        # Development: Allow debug mode
        app.run(debug=debug_mode, host='127.0.0.1', port=5000)
