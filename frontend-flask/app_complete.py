#!/usr/bin/env python3
"""
Complete Flask Web GUI pro Virtual Fitting Room
All features: DB, webcam, URL, background removal, rating, variants, timing, print
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
import os
import requests
from werkzeug.utils import secure_filename
import logging
import time
import uuid
from datetime import datetime
from io import BytesIO
import base64
from PIL import Image
import database as db

# Initialize database
db.init_db()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'virtual-fitting-room-complete-2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'static/results'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# Backend API URL
BACKEND_API = 'http://localhost:8000'

# Create folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main page with complete GUI"""
    variants = db.get_available_variants()
    generations = db.get_all_generations()
    return render_template('index_complete.html',
                         active_page='home',
                         variants=variants,
                         generations=generations)

# ============================================================================
# UPLOAD & GENERATION
# ============================================================================

@app.route('/upload', methods=['POST'])
def upload():
    """Upload and process virtual try-on with full tracking"""
    try:
        # Get form data
        person_name = request.form.get('person_name', 'Unnamed Person')
        garment_name = request.form.get('garment_name', 'Unnamed Garment')
        generation_type = request.form.get('generation_type', 'local')

        # Get variant info
        variants = db.get_available_variants()
        variant = next((v for v in variants if v['name'] == generation_type), None)

        if not variant:
            return jsonify({'success': False, 'error': 'Neplatný typ generování'}), 400

        # Handle person image (file, webcam, or existing)
        person_image_data = None
        person_path = None

        if 'person_image' in request.files and request.files['person_image'].filename:
            person_file = request.files['person_image']
            person_filename = f"{uuid.uuid4()}_{secure_filename(person_file.filename)}"
            person_path = os.path.join(app.config['UPLOAD_FOLDER'], person_filename)
            person_file.save(person_path)
        elif 'person_webcam' in request.form and request.form['person_webcam']:
            # Webcam capture (base64 data)
            person_image_data = request.form['person_webcam']
            person_filename = f"{uuid.uuid4()}_webcam.jpg"
            person_path = os.path.join(app.config['UPLOAD_FOLDER'], person_filename)
            save_base64_image(person_image_data, person_path)
        else:
            return jsonify({'success': False, 'error': 'Chybí fotka osoby'}), 400

        # Handle garment image (file, webcam, URL)
        garment_path = None

        if 'garment_image' in request.files and request.files['garment_image'].filename:
            garment_file = request.files['garment_image']
            garment_filename = f"{uuid.uuid4()}_{secure_filename(garment_file.filename)}"
            garment_path = os.path.join(app.config['UPLOAD_FOLDER'], garment_filename)
            garment_file.save(garment_path)
        elif 'garment_webcam' in request.form and request.form['garment_webcam']:
            garment_image_data = request.form['garment_webcam']
            garment_filename = f"{uuid.uuid4()}_webcam.jpg"
            garment_path = os.path.join(app.config['UPLOAD_FOLDER'], garment_filename)
            save_base64_image(garment_image_data, garment_path)
        elif 'garment_url' in request.form and request.form['garment_url']:
            garment_url = request.form['garment_url']
            garment_filename = f"{uuid.uuid4()}_url.jpg"
            garment_path = os.path.join(app.config['UPLOAD_FOLDER'], garment_filename)
            download_image_from_url(garment_url, garment_path)
        else:
            cleanup_files([person_path])
            return jsonify({'success': False, 'error': 'Chybí fotka oblečení'}), 400

        # Remove background if requested
        if request.form.get('remove_background', 'false') == 'true':
            garment_path = remove_background(garment_path)

        # Save to database
        gen_id = db.save_generation(
            person_name=person_name,
            person_path=person_path,
            garment_name=garment_name,
            garment_path=garment_path,
            generation_type=generation_type
        )

        # Start timing
        start_time = time.time()

        # Call backend API
        try:
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

            generation_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()

                # Save result image
                result_url = result.get('result_url', '')
                result_filename = result_url.split('/')[-1]
                result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)

                # Download result from backend
                result_response = requests.get(f'{BACKEND_API}{result_url}', timeout=30)
                with open(result_path, 'wb') as f:
                    f.write(result_response.content)

                # Update database
                db.update_generation(
                    gen_id=gen_id,
                    result_path=result_path,
                    generation_time=generation_time,
                    status='completed',
                    cost=variant['cost_per_generation']
                )

                # Update variant timing
                db.update_variant_time(generation_type, generation_time)

                return jsonify({
                    'success': True,
                    'message': f'✅ Virtual try-on dokončen za {generation_time:.1f}s!',
                    'generation_id': gen_id,
                    'generation_time': generation_time,
                    'cost': variant['cost_per_generation'],
                    'result': {
                        'result_url': f'/static/results/{result_filename}',
                        'person_path': person_path,
                        'garment_path': garment_path
                    }
                })
            else:
                error_msg = f'Backend error: {response.text}'
                db.update_generation(
                    gen_id=gen_id,
                    status='failed',
                    error_message=error_msg,
                    generation_time=time.time() - start_time
                )
                return jsonify({'success': False, 'error': error_msg}), response.status_code

        except Exception as e:
            generation_time = time.time() - start_time
            error_msg = str(e)
            db.update_generation(
                gen_id=gen_id,
                status='failed',
                error_message=error_msg,
                generation_time=generation_time
            )
            raise e

    except Exception as e:
        logger.error(f"Error during upload: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# DATABASE API
# ============================================================================

@app.route('/api/generations')
def get_generations():
    """Get all generations from database"""
    generations = db.get_all_generations()
    return jsonify(generations)

@app.route('/api/generation/<int:gen_id>')
def get_generation(gen_id):
    """Get specific generation"""
    generation = db.get_generation(gen_id)
    if generation:
        return jsonify(generation)
    return jsonify({'error': 'Generation not found'}), 404

@app.route('/api/generation/<int:gen_id>/rating', methods=['POST'])
def update_rating(gen_id):
    """Update generation rating"""
    try:
        data = request.json
        rating = data.get('rating', 0)

        if not 0 <= rating <= 5:
            return jsonify({'error': 'Rating must be 0-5'}), 400

        db.update_rating(gen_id, rating)
        return jsonify({'success': True, 'message': 'Rating updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generation/<int:gen_id>', methods=['DELETE'])
def delete_generation(gen_id):
    """Delete generation"""
    try:
        generation = db.get_generation(gen_id)
        if not generation:
            return jsonify({'error': 'Generation not found'}), 404

        # Delete files
        for path in [generation['person_image_path'],
                     generation['garment_image_path'],
                     generation['result_image_path']]:
            if path and os.path.exists(path):
                os.remove(path)

        db.delete_generation(gen_id)
        return jsonify({'success': True, 'message': 'Generation deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/variants')
def get_variants():
    """Get available generation variants"""
    variants = db.get_available_variants()
    return jsonify(variants)

# ============================================================================
# UTILITY ROUTES
# ============================================================================

@app.route('/api/remove-background', methods=['POST'])
def api_remove_background():
    """Remove background from image"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400

        image_file = request.files['image']
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{uuid.uuid4()}.jpg')
        image_file.save(temp_path)

        result_path = remove_background(temp_path)

        with open(result_path, 'rb') as f:
            image_data = f.read()

        os.remove(temp_path)
        if result_path != temp_path:
            os.remove(result_path)

        return send_file(
            BytesIO(image_data),
            mimetype='image/png',
            as_attachment=False
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/print/<int:gen_id>')
def print_generation(gen_id):
    """Print generation page"""
    generation = db.get_generation(gen_id)
    if not generation:
        return "Generation not found", 404

    return render_template('print.html', generation=generation)

@app.route('/health')
def health():
    """Health check"""
    try:
        response = requests.get(f'{BACKEND_API}/health', timeout=5)
        backend_status = 'OK' if response.status_code == 200 else 'ERROR'
    except:
        backend_status = 'OFFLINE'

    return jsonify({
        'status': 'OK',
        'backend': backend_status,
        'database': 'OK'
    })

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def save_base64_image(base64_data, output_path):
    """Save base64 encoded image to file"""
    # Remove data:image/jpeg;base64, prefix
    if ',' in base64_data:
        base64_data = base64_data.split(',')[1]

    image_data = base64.b64decode(base64_data)
    with open(output_path, 'wb') as f:
        f.write(image_data)

def download_image_from_url(url, output_path):
    """Download image from URL"""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    with open(output_path, 'wb') as f:
        f.write(response.content)

def remove_background(image_path):
    """Remove background from image using rembg"""
    try:
        from rembg import remove
        from PIL import Image

        # Read input
        with open(image_path, 'rb') as f:
            input_data = f.read()

        # Remove background
        output_data = remove(input_data)

        # Save with transparency
        output_path = image_path.replace('.jpg', '_nobg.png').replace('.jpeg', '_nobg.png')
        with open(output_path, 'wb') as f:
            f.write(output_data)

        return output_path
    except Exception as e:
        logger.error(f"Background removal error: {e}")
        return image_path

def cleanup_files(file_paths):
    """Cleanup temporary files"""
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║   Virtual Fitting Room - Complete Web GUI           ║
    ║   🎨 AI-Powered Virtual Try-On                       ║
    ║   ✨ Features: DB, Webcam, URL, Rating, Print        ║
    ╚══════════════════════════════════════════════════════╝

    🌐 Web GUI: http://localhost:5001
    🔧 Backend API: http://localhost:8000
    📚 API Docs: http://localhost:8000/docs
    💾 Database: virtual_fitting_room.db
    """)

    app.run(host='0.0.0.0', port=5001, debug=True)
