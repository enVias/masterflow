import os
import uuid
import matchering as mg
from flask import Flask, render_template, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename
import threading
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['PROCESSED_FOLDER'] = '/tmp/processed'

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

# Store job status
jobs = {}

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'aiff', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_audio(job_id, target_path, reference_path, output_path):
    """Process audio in background thread"""
    try:
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['progress'] = 'Analyzing tracks...'
        
        # Set up logging to capture progress
        def log_handler(msg):
            jobs[job_id]['progress'] = msg
        
        mg.log(log_handler)
        
        mg.process(
            target=target_path,
            reference=reference_path,
            results=[
                mg.pcm16(output_path.replace('.wav', '_16bit.wav')),
                mg.pcm24(output_path.replace('.wav', '_24bit.wav')),
            ]
        )
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['progress'] = 'Mastering complete!'
        jobs[job_id]['output_16bit'] = output_path.replace('.wav', '_16bit.wav')
        jobs[job_id]['output_24bit'] = output_path.replace('.wav', '_24bit.wav')
        
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)
    finally:
        # Cleanup uploaded files
        try:
            os.remove(target_path)
            os.remove(reference_path)
        except:
            pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'target' not in request.files or 'reference' not in request.files:
        return jsonify({'error': 'Both target and reference files are required'}), 400
    
    target = request.files['target']
    reference = request.files['reference']
    
    if target.filename == '' or reference.filename == '':
        return jsonify({'error': 'No files selected'}), 400
    
    if not allowed_file(target.filename) or not allowed_file(reference.filename):
        return jsonify({'error': 'Invalid file type. Allowed: WAV, MP3, FLAC, AIFF, OGG'}), 400
    
    job_id = str(uuid.uuid4())
    
    # Save uploaded files
    target_filename = secure_filename(f"{job_id}_target_{target.filename}")
    reference_filename = secure_filename(f"{job_id}_reference_{reference.filename}")
    output_filename = f"{job_id}_mastered.wav"
    
    target_path = os.path.join(app.config['UPLOAD_FOLDER'], target_filename)
    reference_path = os.path.join(app.config['UPLOAD_FOLDER'], reference_filename)
    output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
    
    target.save(target_path)
    reference.save(reference_path)
    
    # Initialize job
    jobs[job_id] = {
        'status': 'queued',
        'progress': 'Starting...',
        'created': time.time()
    }
    
    # Start processing in background
    thread = threading.Thread(
        target=process_audio,
        args=(job_id, target_path, reference_path, output_path)
    )
    thread.start()
    
    return jsonify({'job_id': job_id})

@app.route('/status/<job_id>')
def status(job_id):
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(jobs[job_id])

@app.route('/download/<job_id>/<bit_depth>')
def download(job_id, bit_depth):
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    
    if bit_depth == '16':
        file_path = job.get('output_16bit')
    elif bit_depth == '24':
        file_path = job.get('output_24bit')
    else:
        return jsonify({'error': 'Invalid bit depth'}), 400
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=f'mastered_{bit_depth}bit.wav'
    )

# Cleanup old jobs periodically
def cleanup_old_jobs():
    while True:
        time.sleep(3600)  # Run every hour
        current_time = time.time()
        jobs_to_remove = []
        for job_id, job in jobs.items():
            if current_time - job.get('created', 0) > 86400:  # 24 hours
                jobs_to_remove.append(job_id)
                # Remove output files
                for key in ['output_16bit', 'output_24bit']:
                    if key in job and os.path.exists(job[key]):
                        try:
                            os.remove(job[key])
                        except:
                            pass
        for job_id in jobs_to_remove:
            del jobs[job_id]

cleanup_thread = threading.Thread(target=cleanup_old_jobs, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
