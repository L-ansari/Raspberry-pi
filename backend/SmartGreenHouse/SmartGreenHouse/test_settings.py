"""Isolated SQLite tests for HTTP contracts; never loads Atlas credentials."""
from django.apps import AppConfig
import os


class SQLiteApiConfig(AppConfig):
    name = 'api'
    default_auto_field = 'django.db.models.BigAutoField'


SECRET_KEY = 'isolated-test-key-not-for-deployment-1234567890'
INSTALLED_APPS = [
    'django.contrib.auth', 'django.contrib.contenttypes', 'rest_framework',
    'corsheaders', 'SmartGreenHouse.test_settings.SQLiteApiConfig', 'llm',
]
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.getenv('GREENHOUSE_TEST_DB', ':memory:')}}
MIGRATION_MODULES = {'api': None, 'llm': None}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
ROOT_URLCONF = 'SmartGreenHouse.urls'
MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware', 'django.middleware.common.CommonMiddleware']
CORS_ALLOWED_ORIGINS = ['http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:5174']
USE_TZ = True
TIME_ZONE = 'UTC'
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication']}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
OLLAMA_MODEL = 'test-model'
