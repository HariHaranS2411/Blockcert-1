import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / '.env')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'blockcert-default-dev-key-change-in-production')
    
    # Database configuration
    # Default to sqlite:///blockcert.db if DATABASE_URL is not set or empty
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{BASE_DIR / 'blockcert.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload and QR Code Folders
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR / 'app' / 'static' / 'uploads' / 'certificates'))
    QR_FOLDER = os.environ.get('QR_FOLDER', str(BASE_DIR / 'app' / 'static' / 'uploads' / 'qrcodes'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH') or 16 * 1024 * 1024)
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

    # Blockchain (Ganache / Web3)
    GANACHE_RPC_URL = os.environ.get('GANACHE_RPC_URL', 'http://127.0.0.1:8545')
    CONTRACT_ADDRESS = os.environ.get('CONTRACT_ADDRESS', '')
    ISSUER_PRIVATE_KEY = os.environ.get('ISSUER_PRIVATE_KEY', '')
    ISSUER_ADDRESS = os.environ.get('ISSUER_ADDRESS', '')
    CONTRACT_ARTIFACT_PATH = str(BASE_DIR / 'contracts' / 'Certificate.json')

    # WTForms CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = str(BASE_DIR / 'tests' / 'test_uploads')
    QR_FOLDER = str(BASE_DIR / 'tests' / 'test_qr')


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
