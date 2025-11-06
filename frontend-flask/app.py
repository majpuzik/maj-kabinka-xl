#!/usr/bin/env python3
"""
Flask Web GUI pro Virtual Fitting Room
Inspirováno maj-kabinka designem
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import requests
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'virtual-fitting-room-2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# Backend API URL
BACKEND_API = 'http://localhost:8000'

# Vytvoření složek
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/results', exist_ok=True)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Hlavní stránka s upload formulářem"""
    return render_template('index.html', active_page='home')

@app.route('/upload', methods=['POST'])
def upload():
    """Upload a process virtual try-on"""
    try:
        # Kontrola souborů
        if 'person_image' not in request.files or 'garment_image' not in request.files:
            return jsonify({'success': False, 'error': 'Chybí soubory'}), 400

        person_file = request.files['person_image']
        garment_file = request.files['garment_image']

        if person_file.filename == '' or garment_file.filename == '':
            return jsonify({'success': False, 'error': 'Nevybrány soubory'}), 400

        # Uložení dočasných souborů
        person_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(person_file.filename))
        garment_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(garment_file.filename))

        person_file.save(person_path)
        garment_file.save(garment_path)

        # Volání backend API
        with open(person_path, 'rb') as pf, open(garment_path, 'rb') as gf:
            files = {
                'person_image': pf,
                'garment_image': gf
            }

            use_ollama = request.form.get('use_ollama', 'true').lower() == 'true'
            response = requests.post(
                f'{BACKEND_API}/api/tryon',
                files=files,
                params={'use_ollama': use_ollama},
                timeout=300
            )

        # Cleanup
        os.remove(person_path)
        os.remove(garment_path)

        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'message': '✅ Virtual try-on dokončen!',
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Backend chyba: {response.text}'
            }), response.status_code

    except Exception as e:
        logger.error(f"Error during upload: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        response = requests.get(f'{BACKEND_API}/health', timeout=5)
        backend_status = 'OK' if response.status_code == 200 else 'ERROR'
    except:
        backend_status = 'OFFLINE'

    return jsonify({
        'status': 'OK',
        'backend': backend_status
    })

@app.route('/api/status')
def api_status():
    """Get backend API status"""
    try:
        response = requests.get(f'{BACKEND_API}/', timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 503

if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════╗
    ║   Virtual Fitting Room - Web GUI             ║
    ║   🎨 AI-Powered Virtual Try-On                ║
    ╚═══════════════════════════════════════════════╝

    🌐 Web GUI: http://localhost:5000
    🔧 Backend API: http://localhost:8000
    📚 API Docs: http://localhost:8000/docs
    """)

    app.run(host='0.0.0.0', port=5001, debug=True)
