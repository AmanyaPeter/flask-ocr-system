from . import db
from datetime import datetime

class UploadLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)
    language = db.Column(db.String(10), nullable=False)
    pages_processed = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<UploadLog {self.filename}>'
