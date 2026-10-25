"""
Django settings for Arslan's Software — Pharmacy ERP (stocktime project).

Phase 1 commercial foundation:
- Pakistan timezone (Asia/Karachi)
- PKR-ready configuration
- SECRET_KEY and DEBUG from environment
- i18n ready for Urdu + English
"""

from pathlib import Path
import os
from decimal import Decimal

# Optional: load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Security — NEVER hardcode production secrets
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-only-change-me-in-production-@efq6_55qub20@c_vq*'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
    if h.strip()
]

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'inventory.apps.InventoryConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # for future Urdu/English switching
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'stocktime.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'inventory.context_processors.app_ui',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'stocktime.wsgi.application'

# ---------------------------------------------------------------------------
# Database (SQLite for local single-PC deployment)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 30,  # help concurrent access a little
        },
    }
}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internationalization — Pakistan first, bilingual ready
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en'  # default; 'ur' can be activated later
LANGUAGES = [
    ('en', 'English'),
    ('ur', 'اردو'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']

TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True

LOGIN_URL = 'login'

# ---------------------------------------------------------------------------
# Static & Media
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')] if (BASE_DIR / 'static').exists() else []
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Arslan's Software — Pharmacy ERP constants
# ---------------------------------------------------------------------------
CURRENCY_CODE = 'PKR'
CURRENCY_SYMBOL = 'Rs.'
CURRENCY_DECIMAL_PLACES = 2

# Helper used by views/templates for consistent money
def quantize_money(value):
    """Return a Decimal quantized to 2 places (PKR paisa)."""
    if value is None:
        return Decimal('0.00')
    return Decimal(str(value)).quantize(Decimal('0.01'))

# Custom error handlers (views must define these)
HANDLER404 = 'inventory.views.custom_404'
HANDLER500 = 'inventory.views.custom_500'


# --- SMS / WhatsApp gateway (configure via environment) ---
# SMS_PROVIDER: console | http | twilio
SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'console')
SMS_API_URL = os.environ.get('SMS_API_URL', '')  # generic HTTP POST endpoint
SMS_API_KEY = os.environ.get('SMS_API_KEY', '')
SMS_SENDER_ID = os.environ.get('SMS_SENDER_ID', 'ARSALAN')
# WhatsApp: console | http | twilio
WHATSAPP_PROVIDER = os.environ.get('WHATSAPP_PROVIDER', 'console')
WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL', '')
WHATSAPP_API_KEY = os.environ.get('WHATSAPP_API_KEY', '')
WHATSAPP_FROM = os.environ.get('WHATSAPP_FROM', '')  # e.g. whatsapp:+92...
# Twilio (optional)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_SMS_FROM = os.environ.get('TWILIO_SMS_FROM', '')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', '')
MESSAGING_ENABLED = os.environ.get('MESSAGING_ENABLED', '0') == '1'
