# app/admin/routes.py
import csv
from io import StringIO
from flask import Blueprint, render_template, make_response
from app.models import UploadLog
from sqlalchemy import desc

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')

@admin_bp.route('/dashboard')
def dashboard():
    logs = UploadLog.query.order_by(desc(UploadLog.timestamp)).all()
    return render_template('dashboard.html', logs=logs)

@admin_bp.route('/export_logs')
def export_logs():
    logs = UploadLog.query.all()
    si = StringIO()
    cw = csv.writer(si)
    
    # Write header
    cw.writerow(['ID', 'Filename', 'Timestamp (UTC)', 'Status', 'Language', 'Pages Processed'])
    # Write data
    for log in logs:
        cw.writerow([log.id, log.filename, log.timestamp, log.status, log.language, log.pages_processed])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=upload_logs.csv"
    output.headers["Content-type"] = "text/csv"
    return output

