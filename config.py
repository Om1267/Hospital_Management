import os
import logging
from logging.handlers import RotatingFileHandler

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuration class for the Hospital Management System."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hospital-mgmt-secret-key-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Security Settings
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Logging
    LOG_DIR = os.path.join(basedir, 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'application.log')

