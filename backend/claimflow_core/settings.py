import os
from pathlib import Path
from datetime import timedelta
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps directory to sys.path
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'apps'))

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-claimflow-super-secret-key-production-ready-2026!#$*'
)

DEBUG = os.environ.get('DJANGO_DEBUG', os.environ.get('DEBUG', 'True')).lower() in ('true', '1', 'yes')

# Domains & Hosts configuration
CLAIMFLOW_DOMAINS = [
    'api.claimflowx.com',
    'claimflowx.com',
    'www.claimflowx.com',
    '.claimflowx.com',
    'localhost',
    '127.0.0.1',
    'web',
]
raw_allowed_hosts = os.environ.get('ALLOWED_HOSTS', '')
if raw_allowed_hosts and raw_allowed_hosts != '*':
    ALLOWED_HOSTS = [h.strip() for h in raw_allowed_hosts.split(',') if h.strip()]
    for host in CLAIMFLOW_DOMAINS:
        if host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)
else:
    ALLOWED_HOSTS = ['*'] if DEBUG else CLAIMFLOW_DOMAINS

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party packages
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',

    # Local apps
    'apps.authentication',
    'apps.policies',
    'apps.claims',
    'apps.blockchain',
    'apps.payouts',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'claimflow_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'claimflow_core.wsgi.application'
ASGI_APPLICATION = 'claimflow_core.asgi.application'

# Database
# Supports both POSTGRES_* and DB_* environment variables for Dokploy / local Docker
DB_NAME = os.environ.get('POSTGRES_DB', os.environ.get('DB_NAME', 'claimflow_db'))
DB_USER = os.environ.get('POSTGRES_USER', os.environ.get('DB_USER', 'claimflow_user'))
DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD', os.environ.get('DB_PASSWORD', 'claimflow_password'))
DB_HOST = os.environ.get('POSTGRES_HOST', os.environ.get('DB_HOST', ''))
DB_PORT = os.environ.get('POSTGRES_PORT', os.environ.get('DB_PORT', '5432'))

if DB_HOST:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'authentication.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS & CSRF configuration
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    'https://claimflowx.com',
    'https://www.claimflowx.com',
    'https://api.claimflowx.com',
    'http://localhost:3000',
    'http://localhost:5173',
    'http://127.0.0.1:3000',
]
extra_cors = os.environ.get('CORS_ALLOWED_ORIGINS', '')
if extra_cors:
    CORS_ALLOWED_ORIGINS.extend([origin.strip() for origin in extra_cors.split(',') if origin.strip()])

CSRF_TRUSTED_ORIGINS = [
    'https://claimflowx.com',
    'https://www.claimflowx.com',
    'https://api.claimflowx.com',
    'http://localhost:8000',
    'http://localhost:3000',
    'http://127.0.0.1:8000',
]
extra_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if extra_csrf:
    CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in extra_csrf.split(',') if origin.strip()])

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# SimpleJWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# drf-spectacular (OpenAPI / Swagger) Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'ClaimFlow Insurance & Soroban Settlement API',
    'DESCRIPTION': (
        'Enterprise Insurance Claims Management Platform powered by Stellar Soroban smart contracts. '
        'Enables claim submission, role-based review workflow, on-chain state verification, '
        'payout authorization, and testnet transaction monitoring.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    # Pin to a stable version without the import.meta bundle bug:
    'REDOC_DIST': 'https://cdn.jsdelivr.net/npm/redoc@2.1.5',
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
}

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Stellar Soroban Configuration
STELLAR_NETWORK = os.environ.get('STELLAR_NETWORK', 'TESTNET')
SOROBAN_RPC_URL = os.environ.get('SOROBAN_RPC_URL', 'https://soroban-testnet.stellar.org')
STELLAR_NETWORK_PASSPHRASE = os.environ.get(
    'STELLAR_NETWORK_PASSPHRASE', 'Test SDF Network ; September 2015'
)
SOROBAN_CONTRACT_ID = os.environ.get(
    'SOROBAN_CONTRACT_ID',
    'CCLAIMFLOWCONTRACTTESTNET00000000000000000000000000000000000000'
)
STELLAR_ADMIN_PUBLIC_KEY = os.environ.get(
    'STELLAR_ADMIN_PUBLIC_KEY',
    'GBU2DCSH5QSKUGW7USN4QL7I72O5ZPGX7Z44FUX3F47V4K633F2G245C'
)
STELLAR_ADMIN_SECRET_KEY = os.environ.get('STELLAR_ADMIN_SECRET_KEY', '')
SIMULATED_BLOCKCHAIN = os.environ.get('SIMULATED_BLOCKCHAIN', 'True').lower() in ('true', '1', 'yes')

