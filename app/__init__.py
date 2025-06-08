# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Configuration
    app.config['SECRET_KEY'] = 'a_very_secret_key_change_this'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['PROCESSED_FOLDER'] = 'processed'
    app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB limit

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Ensure upload and processed folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    with app.app_context():
        # Import blueprints
        from .main.routes import main_bp
        from .admin.routes import admin_bp
        
        # Register blueprints
        app.register_blueprint(main_bp)
        app.register_blueprint(admin_bp, url_prefix='/admin')

        # Create database tables for our models
        db.create_all()

    return app
