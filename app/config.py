import os
from dotenv import load_dotenv

load_dotenv()

def get_db_uri(env_var):
    url = os.environ.get(env_var)
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        
        # Ensure SSL mode for Supabase/Cloud DBs
        if "sslmode=" not in url:
            separator = "&" if "?" in url else "?"
            url += f"{separator}sslmode=require"
    return url

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-string'
    UPLOAD_FOLDER = '/tmp/uploads' if os.environ.get('VERCEL') else os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024 # 5MB limit

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = get_db_uri('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(os.getcwd(), 'dev.db')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = get_db_uri('TEST_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(os.getcwd(), 'test.db')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = get_db_uri('DATABASE_URL')
    
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
