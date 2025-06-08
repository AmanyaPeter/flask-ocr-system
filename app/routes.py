import os
import json
import uuid
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for,
    current_app, session, send_file, make_response
)
from werkzeug.utils import secure_filename
from app.utils import process_file, create_downloadable_file
from app.models import UploadLog
from app import db

main_bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/')
def index():
    return render_template('main/index.html')

@main_bp.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    
    files = request.files.getlist('files[]')
    language = request.form.get('language', 'eng')
    
    if not files or files[0].filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)

    job_id = str(uuid.uuid4())
    job_folder = os.path.join(current_app.config['PROCESSED_FOLDER'], job_id)
    os.makedirs(job_folder, exist_ok=True)
    
    all_results = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)
            
            log = UploadLog(filename=filename, status='Processing', language=language)
            db.session.add(log)
            db.session.commit()
            
            try:
                # Process the file
                result_data = process_file(upload_path, lang=language)
                result_data['original_filename'] = filename # Keep track for download
                all_results.append(result_data)
                
                # Update log
                log.status = 'Complete'
                log.pages_processed = result_data.get('page_count', 0)
                db.session.commit()

            except Exception as e:
                log.status = f'Error: {str(e)}'
                db.session.commit()
                flash(f'An error occurred while processing {filename}: {e}', 'danger')
        else:
            flash(f'File type not allowed for {file.filename}', 'warning')

    # Save results to a JSON file in the job folder
    results_path = os.path.join(job_folder, 'results.json')
    with open(results_path, 'w') as f:
        json.dump(all_results, f)
        
    session['job_id'] = job_id
    return redirect(url_for('main.show_results'))

@main_bp.route('/results')
def show_results():
    job_id = session.get('job_id')
    if not job_id:
        return redirect(url_for('main.index'))
    
    results_path = os.path.join(current_app.config['PROCESSED_FOLDER'], job_id, 'results.json')
    try:
        with open(results_path, 'r') as f:
            results = json.load(f)
    except FileNotFoundError:
        flash('Results not found. Please try uploading again.', 'danger')
        return redirect(url_for('main.index'))
        
    return render_template('main/results.html', results=results, job_id=job_id)

@main_bp.route('/download/<job_id>/<int:file_index>/<file_format>')
def download_file(job_id, file_index, file_format):
    results_path = os.path.join(current_app.config['PROCESSED_FOLDER'], job_id, 'results.json')
    try:
        with open(results_path, 'r') as f:
            results_data = json.load(f)
        
        file_result = results_data[file_index]
        content, mimetype = create_downloadable_file(file_result, file_format)
        
        if content is None:
            flash('Invalid download format.', 'danger')
            return redirect(url_for('main.show_results'))
            
        filename = file_result['original_filename'].rsplit('.', 1)[0]
        download_filename = f"{filename}.{file_format}"
        
        response = make_response(content)
        response.headers.set('Content-Type', mimetype)
        response.headers.set('Content-Disposition', 'attachment', filename=download_filename)
        return response

    except (FileNotFoundError, IndexError):
        flash('Could not find the file to download.', 'danger')
        return redirect(url_for('main.show_results'))
