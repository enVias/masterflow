import os
import uuid
import traceback
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import threading
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
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
        jobs[job_id]['progress'] = 'Loading Matchering...'
        
        # Import matchering here to avoid loading on startup
        import matchering as mg
        
        jobs[job_id]['progress'] = 'Analyzing tracks...'
        
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
        
    except MemoryError:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = 'Out of memory. Please try shorter audio files.'
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        error_msg = str(e)
        # Provide user-friendly error messages
        if 'ffmpeg' in error_msg.lower():
            jobs[job_id]['error'] = 'Audio conversion error. Please try a different file format (WAV recommended).'
        elif 'sample rate' in error_msg.lower():
            jobs[job_id]['error'] = 'Sample rate mismatch. Please ensure both files have compatible sample rates.'
        elif 'mono' in error_msg.lower() or 'stereo' in error_msg.lower() or 'channel' in error_msg.lower():
            jobs[job_id]['error'] = 'Channel mismatch. Please use stereo audio files for both target and reference.'
        elif 'empty' in error_msg.lower() or 'silent' in error_msg.lower():
            jobs[job_id]['error'] = 'One of the audio files appears to be empty or silent.'
        else:
            jobs[job_id]['error'] = f'Mastering failed: {error_msg}'
        
        # Log full traceback for debugging
        print(f"Job {job_id} error: {traceback.format_exc()}")
    finally:
        # Cleanup uploaded files
        for path in [target_path, reference_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

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
        time.sleep(1800)  # Run every 30 minutes
        current_time = time.time()
        jobs_to_remove = []
        for job_id, job in list(jobs.items()):
            if current_time - job.get('created', 0) > 7200:  # 2 hours
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
