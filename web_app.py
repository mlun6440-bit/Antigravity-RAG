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
from flask import Flask, render_template, request, jsonify, session, send_file
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
from consultant_analyzer import ConsultantAnalyzer

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
query_engine = None
command_parser = None
asset_updater = None
question_suggester = None
consultant_analyzer = None

try:
    query_engine = GeminiQueryEngine()
    print(f"[OK] Query engine initialized: {query_engine}")
    print(f"[DEBUG] query_engine is None: {query_engine is None}")
except Exception as e:
    print(f"[ERROR] Query engine initialization failed: {e}")
    query_engine = None

try:
    command_parser = CommandParser()
    print("[OK] Command parser initialized")
except Exception as e:
    print(f"[ERROR] Command parser initialization failed: {e}")

try:
    asset_updater = AssetUpdater()
    print("[OK] Asset updater initialized (Google Sheets sync enabled)")
except Exception as e:
    print(f"[WARNING] Asset updater initialization failed: {e}")
    print("[INFO] Google Sheets sync disabled - queries will still work")
    asset_updater = None

try:
    question_suggester = QuestionSuggester()
    print("[OK] Question suggester initialized")
except Exception as e:
    print(f"[WARNING] Question suggester initialization failed: {e}")

try:
    consultant_analyzer = ConsultantAnalyzer()
    print("[OK] Consultant analyzer initialized")
except Exception as e:
    print(f"[WARNING] Consultant analyzer initialization failed: {e}")


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
            citations = result.get('citations', [])
            logger.info(f"[CITATIONS DEBUG] Returning {len(citations)} citations")
            for i, cit in enumerate(citations):
                logger.info(f"[CITATION {i+1}] Type: {cit.get('type')}, Source: {cit.get('source', 'N/A')[:50]}")

            return jsonify({
                'answer': result['answer'],
                'citations': citations,  # Structured citations for popups
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


@app.route('/api/consultant-analysis', methods=['POST'])
@limiter.limit("5 per minute")  # Lower limit for expensive analysis
def api_consultant_analysis():
    """Provide consultant-level analysis of query results."""
    try:
        # Check if consultant analyzer is initialized
        if consultant_analyzer is None:
            logger.error("Consultant analyzer not initialized")
            return jsonify({
                'error': 'Consultant analyzer not initialized',
                'setup_required': True
            }), 500

        data = request.get_json()
        question = data.get('question', '').strip()
        answer = data.get('answer', '').strip()
        citations = data.get('citations', [])
        asset_summary = data.get('asset_summary', {})

        if not question or not answer:
            return jsonify({'error': 'Question and answer required'}), 400

        # Log analysis request
        logger.info(f"Consultant analysis requested from {request.remote_addr}")

        # Perform consultant analysis
        result = consultant_analyzer.analyze(
            question=question,
            answer=answer,
            citations=citations,
            asset_summary=asset_summary
        )

        if result['status'] == 'success':
            return jsonify({
                'analysis': result['analysis'],
                'analysis_type': result['analysis_type'],
                'frameworks_applied': result['frameworks_applied'],
                'citations': result.get('citations', [])
            })
        else:
            return jsonify({'error': result.get('error', 'Analysis failed')}), 500

    except Exception as e:
        logger.error(f"Consultant analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/<filename>')
def serve_pdf(filename):
    """Serve ISO PDF files."""
    try:
        # Sanitize filename to prevent directory traversal
        safe_filename = os.path.basename(filename)

        # Only allow specific PDF files
        allowed_pdfs = [
            'ASISO55000-20241.pdf',
            'ASISO55001-20241.pdf',
            'ASISO55002-20241.pdf'
        ]

        if safe_filename not in allowed_pdfs:
            logger.warning(f"Attempted access to unauthorized PDF: {safe_filename}")
            return jsonify({'error': 'PDF not found'}), 404

        pdf_path = os.path.join('data', '.tmp', safe_filename)

        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return jsonify({'error': 'PDF file not found'}), 404

        logger.info(f"Serving PDF: {safe_filename}")
        return send_file(pdf_path, mimetype='application/pdf')

    except Exception as e:
        logger.error(f"Error serving PDF: {str(e)}")
        return jsonify({'error': 'Error serving PDF'}), 500


# =============================================================================
# Work Order (WO) Endpoints
# =============================================================================

@app.route('/api/wo/ingest', methods=['POST'])
def wo_ingest():
    """Trigger WO ingestion from WOs.xlsx into the work_orders table."""
    try:
        import subprocess
        script = os.path.join(os.path.dirname(__file__), 'tools', 'ingest_wos.py')
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0:
            logger.error(f"WO ingest failed: {result.stderr}")
            return jsonify({'error': result.stderr}), 500

        # Parse summary from stdout
        lines = result.stdout + result.stderr
        stats = {}
        for key in ['rows_inserted', 'rm_count', 'pm_count', 'open_count', 'completed_count']:
            import re as _re
            m = _re.search(rf'{key.replace("_", ".*")}.*?(\d[\d,]*)', lines, _re.IGNORECASE)
            if m:
                stats[key] = int(m.group(1).replace(',', ''))

        logger.info(f"WO ingest complete: {stats}")
        return jsonify({'status': 'ok', **stats})
    except Exception as e:
        logger.error(f"WO ingest error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/wo/match', methods=['POST'])
@limiter.limit("10 per hour")
def wo_match():
    """Run NLP matching for unmatched WOs. Optional body: {"site_id": "54500293", "limit": 1000}"""
    try:
        from tools.wo_asset_matcher import create_matcher
        data = request.get_json(silent=True) or {}
        site_id = data.get('site_id')
        limit = data.get('limit')

        matcher = create_matcher()
        result = matcher.match_all_unmatched(site_id=site_id, limit=limit)
        logger.info(f"WO match complete: {result}")
        return jsonify({'status': 'ok', **result})
    except Exception as e:
        logger.error(f"WO match error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/wo/site/<site_id>', methods=['GET'])
def wo_by_site(site_id):
    """Get WOs and matched assets for a specific site."""
    try:
        from tools.database_manager import DatabaseManager
        db = DatabaseManager()
        wo_type = request.args.get('wo_type')  # RM or PM
        wos = db.get_wo_by_site(site_id=site_id, wo_type=wo_type, exclude_status='Completed')

        # Enrich with matched asset details
        asset_ids = list({w['matched_asset_id'] for w in wos if w.get('matched_asset_id')})
        asset_map = {}
        if asset_ids:
            placeholders = ','.join(['?'] * len(asset_ids))
            with db.get_connection() as conn:
                rows = conn.execute(
                    f"SELECT asset_id, asset_name, asset_type, condition, criticality, location FROM assets WHERE asset_id IN ({placeholders})",
                    asset_ids
                ).fetchall()
                asset_map = {r['asset_id']: dict(r) for r in rows}

        for w in wos:
            aid = w.get('matched_asset_id')
            w['matched_asset'] = asset_map.get(aid) if aid else None

        return jsonify({'site_id': site_id, 'count': len(wos), 'wos': wos})
    except Exception as e:
        logger.error(f"WO by site error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/wo/summary', methods=['GET'])
def wo_summary():
    """Site-level WO backlog summary (open RMs, open PMs per site)."""
    try:
        from tools.database_manager import DatabaseManager
        db = DatabaseManager()
        sites = db.get_wo_summary_by_site()
        total_open_rm = sum(s.get('open_rm', 0) for s in sites)
        total_open_pm = sum(s.get('open_pm', 0) for s in sites)
        return jsonify({
            'total_open_rm': total_open_rm,
            'total_open_pm': total_open_pm,
            'sites': sites
        })
    except Exception as e:
        logger.error(f"WO summary error: {e}")
        return jsonify({'error': str(e), 'sites': []}), 500


# =============================================================================
# Dashboard Endpoint
# =============================================================================

@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    """Return all dashboard widget data for the 📊 Dashboard view."""
    try:
        from tools.database_manager import DatabaseManager
        db = DatabaseManager()

        summary = db.get_asset_summary()
        condition_breakdown = db.get_condition_breakdown()
        asset_types = db.get_asset_types()[:10]  # Top 10
        wo_sites = db.get_wo_summary_by_site()

        total_open_rm = sum(s.get('open_rm', 0) for s in wo_sites)
        total_open_pm = sum(s.get('open_pm', 0) for s in wo_sites)

        widgets = [
            {
                'type': 'stat_card',
                'title': 'Total Assets',
                'value': f"{summary.get('total_assets', 0):,}",
                'subtitle': f"{summary.get('locations', 0)} sites · {summary.get('buildings', 0)} buildings",
                'status': 'good'
            },
            {
                'type': 'stat_card',
                'title': 'Open Reactive WOs',
                'value': str(total_open_rm),
                'subtitle': 'Requires immediate attention',
                'status': 'critical' if total_open_rm > 0 else 'good'
            },
            {
                'type': 'stat_card',
                'title': 'Open Planned WOs',
                'value': str(total_open_pm),
                'subtitle': 'Scheduled maintenance',
                'status': 'warning' if total_open_pm > 0 else 'good'
            },
            {
                'type': 'stat_card',
                'title': 'Avg Condition Score',
                'value': f"{summary.get('avg_condition_score', 0):.1f}/5",
                'subtitle': 'Across all assets',
                'status': 'good' if summary.get('avg_condition_score', 0) >= 3 else 'warning'
            },
            {
                'type': 'pie_chart',
                'title': 'Asset Condition Breakdown',
                'segments': [
                    {'label': cond, 'value': count}
                    for cond, count in condition_breakdown.items()
                ]
            },
            {
                'type': 'bar_chart',
                'title': 'Top Asset Types',
                'labels': [t[0] for t in asset_types],
                'values': [t[1] for t in asset_types]
            },
        ]

        # Add WO backlog chart if data exists
        if wo_sites:
            widgets.append({
                'type': 'bar_chart',
                'title': 'Open Reactive WOs by Site (Top 10)',
                'labels': [s.get('site_name', 'Unknown')[:30] for s in wo_sites[:10]],
                'values': [s.get('open_rm', 0) for s in wo_sites[:10]]
            })
            widgets.append({
                'type': 'bar_chart',
                'title': 'RM vs PM by Site',
                'labels': [s.get('site_name', 'Unknown')[:30] for s in wo_sites[:10]],
                'values': [s.get('open_rm', 0) for s in wo_sites[:10]],
                'values2': [s.get('open_pm', 0) for s in wo_sites[:10]],
                'label1': 'Open RM',
                'label2': 'Open PM'
            })

        return jsonify({'widgets': widgets})
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'error': str(e), 'widgets': []}), 500


# =============================================================================
# CSV Export Endpoint
# =============================================================================

@app.route('/api/export/csv', methods=['GET'])
@limiter.limit("5 per hour")
def export_csv():
    """Export assets as CSV, with optional WO enrichment and filters."""
    try:
        import csv
        import io

        from tools.database_manager import DatabaseManager
        db = DatabaseManager()

        # Build filters from query params
        filters = {}
        condition = request.args.get('condition')
        site = request.args.get('site')
        asset_type_filter = request.args.get('asset_type')
        include_wos = request.args.get('include_wos', 'false').lower() == 'true'

        if condition:
            filters['condition'] = sanitize_input(condition)
        if site:
            filters['location__like'] = f"%{sanitize_input(site)}%"
        if asset_type_filter:
            filters['asset_type__like'] = f"%{sanitize_input(asset_type_filter)}%"

        assets, total = db.query_assets(filters=filters, limit=50000)
        if not assets:
            return jsonify({'error': 'No assets found for the given filters'}), 404

        # Optional WO enrichment
        if include_wos:
            try:
                with db.get_connection() as conn:
                    rows = conn.execute("""
                        SELECT matched_asset_id,
                               SUM(CASE WHEN wo_type='RM' AND status!='Completed' THEN 1 ELSE 0 END) AS open_rm,
                               SUM(CASE WHEN wo_type='PM' AND status!='Completed' THEN 1 ELSE 0 END) AS open_pm,
                               MAX(CASE WHEN status!='Completed' THEN description END) AS last_open_wo,
                               MAX(matched_at) AS last_wo_date
                        FROM work_orders
                        WHERE matched_asset_id IS NOT NULL
                        GROUP BY matched_asset_id
                    """).fetchall()
                    wo_map = {r['matched_asset_id']: dict(r) for r in rows}
                for asset in assets:
                    aid = asset.get('asset_id')
                    wo = wo_map.get(aid, {})
                    asset['open_rm_count'] = wo.get('open_rm', 0)
                    asset['open_pm_count'] = wo.get('open_pm', 0)
                    asset['last_open_wo'] = wo.get('last_open_wo', '')
                    asset['last_wo_date'] = wo.get('last_wo_date', '')
            except Exception as wo_err:
                logger.warning(f"WO enrichment skipped (table may not exist): {wo_err}")

        # Stream CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(assets[0].keys()))
        writer.writeheader()
        writer.writerows(assets)
        output.seek(0)

        filename = f"assets_{datetime.now().strftime('%Y-%m-%d')}.csv"
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"CSV export error: {e}")
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
