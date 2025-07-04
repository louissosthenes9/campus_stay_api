"""
Django production settings for campus_stay project with Supabase and Cloudinary.
"""

from pathlib import Path
import os
import environ
from datetime import timedelta

# Cloudinary imports
import cloudinary
import cloudinary.api
import cloudinary.uploader

# Initialize environ
env = environ.Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # For GDAL/GIS functionality
    'django.contrib.sites',  # Required for django-allauth
    'rest_framework',
    'rest_framework_gis',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
    'leaflet',
    'allauth',  # Required for OAuth
    'allauth.account',  # Required for authentication flows
    'allauth.socialaccount',  # Required for social authentication
    'allauth.socialaccount.providers.google',  # Google provider
    'rest_auth',  # REST API endpoints for authentication
    'rest_auth.registration',  # REST API endpoints for registration
    'cloudinary',
    'cloudinary_storage',  # Cloudinary storage backend
    'users',
    'properties',
    'universities',
    'user_messages',
    'reviews',
    'favourites',
]

# Site ID required for django-allauth
SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',  
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'middleware.property_tracking.PropertyViewTrackingMiddleware',  # Custom middleware for property view tracking
]

ROOT_URLCONF = 'campus_stay.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'campus_stay.wsgi.application'

# Database
# Using Supabase PostgreSQL connection
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis' if env.bool('USE_GIS', default=True) else 'django.db.backends.postgresql',
        'NAME': env('SUPABASE_DB_NAME'),
        'USER': env('SUPABASE_DB_USER'),
        'PASSWORD': env('SUPABASE_DB_PASSWORD'),
        'HOST': env('SUPABASE_DB_HOST'),
        'PORT': env('SUPABASE_DB_PORT', default='5432'),
        'POOL_MODE': env('SUPABASE_DB_POOL_MODE', default='threaded'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

AUTH_USER_MODEL = 'users.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Cloudinary Configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': env('CLOUDINARY_API_KEY'),
    'API_SECRET': env('CLOUDINARY_API_SECRET'),
}

# Configure Cloudinary
cloudinary.config(
    cloud_name=env('CLOUDINARY_CLOUD_NAME'),
    api_key=env('CLOUDINARY_API_KEY'),
    api_secret=env('CLOUDINARY_API_SECRET'),
    secure=True
)

# File Storage Settings - Using Cloudinary
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Static files - You can use Cloudinary for static files too, or keep them local/CDN
# For static files with Cloudinary (uncomment if you want to use Cloudinary for static files):
# STATICFILES_STORAGE = 'cloudinary_storage.storage.StaticHashedCloudinaryStorage'
# STATIC_URL = '/static/'

# For local static files (recommended for CSS/JS):
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files URL - Cloudinary will handle the URLs automatically
MEDIA_URL = '/media/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# CORS settings
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_CREDENTIALS = True

FRONTEND_URL = env('FRONTEND_URL', default='https://campus-stay.vercel.app')

# Security settings
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Logging configuration - ALL LOGS TO CONSOLE
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.template': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'cloudinary': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='sandbox.smtp.mailtrap.io')
EMAIL_PORT = env.int('EMAIL_PORT', default=2525)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='7e2aacbc250784')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='e8f5e592bbe1b6')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='webmaster@localhost')

# Google OAuth Settings
GOOGLE_OAUTH2_CLIENT_ID = env('GOOGLE_OAUTH2_CLIENT_ID', default='')
GOOGLE_OAUTH2_CLIENT_SECRET = env('GOOGLE_OAUTH2_CLIENT_SECRET', default='')

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Django-allauth settings
ACCOUNT_EMAIL_VERIFICATION = 'none'  # Can be set to 'mandatory' in production

# Updated allauth settings (new syntax)
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_UNIQUE_EMAIL = True

# Social account settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': env('GOOGLE_OAUTH2_CLIENT_ID'),
            'secret': env('GOOGLE_OAUTH2_CLIENT_SECRET'),
            'key': '',
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}

SIMPLE_JWT = {
    "TOKEN_OBTAIN_SERIALIZER": "users.api.serializers.CustomTokenObtainPairSerializer",
    "ACCESS_TOKEN_LIFETIME": timedelta(days=40),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=40),
}

# REST Auth settings
REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'jwt-auth',
}