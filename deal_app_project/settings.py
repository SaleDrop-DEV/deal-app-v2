from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = False
ALLOWED_HOSTS = ['saledrop.app', 'www.saledrop.app']

CURRENT_URL = 'https://saledrop.app'
INSTA_URL = 'https://www.instagram.com/saledrop.app/'

# VARIABLES (PASSWORDS)#
from decouple import config

SECRET_KEY = config('SECRET_KEY')

PROXY_CAKE_USERNAME = config('PROXY_CAKE_USERNAME')
PROXY_CAKE_PASSWORD = config('PROXY_CAKE_PASSWORD')
PROXY_CAKE_IP = config('PROXY_CAKE_IP')
PROXY_CAKE_PORT = config('PROXY_CAKE_PORT')

GEMINI_API_KEY_GENERAL = config('GEMINI_API_KEY_GENERAL')
GEMINI_API_KEY_WOMEN = config('GEMINI_API_KEY_WOMEN')

EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')


DATABASE_PASSWORD = config('DATABASE_PASSWORD')

# Application definition




INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'pages',
    'deals',
    'api',
    'business',

    'accounts',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    'django.contrib.sitemaps',
]



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'deal_app_project.urls'

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

WSGI_APPLICATION = 'deal_app_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES_old = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

#pip install mysqlclient
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # MariaDB gebruikt de MySQL backend
        'NAME': 'saledropdb',
        'USER': 'django_user',
        'PASSWORD': 'PatronHein1913!#79',
        'HOST': '148.230.125.181',  # IP-adres of domeinnaam van je VPS
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        }
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
LOGIN_URL = '/accounts/log-in/'
LANGUAGE_CODE = 'nl'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
TEMPLATES[0]['DIRS'] = [os.path.join(BASE_DIR, 'templates')]
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    # e.g., 'your_app/static',
]
# STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_ROOT = Path('/var/www/deal_app_project/staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = Path('/var/www/media_uploads')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

AUTH_USER_MODEL = 'accounts.CustomUser'
ACCOUNT_FORMS = {
    'signup': 'accounts.forms.CustomUserCreationForm',
}

SITE_ID = 1

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_USERNAME_REQUIRED = False
LOGIN_REDIRECT_URL = '/'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'webmaster@localhost'


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.strato.de'
EMAIL_PORT = 465
EMAIL_USE_SSL = True

EMAIL_HOST_USER = "support@saledrop.app"
DEFAULT_FROM_EMAIL = "SaleDrop <support@saledrop.app>"
ACCOUNT_EMAIL_SUBJECT_PREFIX = 'SaleDrop | '





REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),     # Short-lived for security
    "REFRESH_TOKEN_LIFETIME": timedelta(days=180),     # Lasts 6 months (adjust as needed)
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,

    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY, # Use your existing Django SECRET_KEY
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",

    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",

    "JTI_CLAIM": "jti",

    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}





# Celery Configuration
# This tells Celery to use Redis as the message broker.
# Make sure your Redis server is running.
CELERY_BROKER_URL = 'redis://localhost:6379/0' # Or your Redis URL
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0' # Where task results are stored (optional)

# This tells Celery to accept JSON for task serialization.
# It's generally a good default and widely compatible.
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# This is important for tasks that might take longer than the default.
# Adjust as needed based on your email fetching and analysis time.
CELERY_TASK_TIME_LIMIT = 300 # 5 minutes (adjust if fetching many emails)

# Optional: If you want to limit the number of concurrent tasks a worker handles
CELERY_WORKER_CONCURRENCY = 15 # Adjust based on your server resources


# Celery Beat Schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'disperse-sales-every-minute': {
        'task': 'business.tasks.disperse_ready_sale_messages',
        'schedule': crontab(minute='*'),  # Runs every minute
        'args': (),
    },
    'moderate-sale-messages-very-hour': {
        'task': 'business.tasks.moderate_sale_messages',
        'schedule': crontab(minute=0, hour='*'),  # Runs every hour
        'args': (),
    },
}



LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
    },
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "/root/deal_app_project/deal_app_project.log",
            "formatter": "verbose",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}


# VARIABLES #
THRESHOLD_DEAL_PROBABILITY = 0.89
