import os.path
from datetime import timedelta
from pathlib import Path
import environ
from celery.schedules import crontab

from django.urls import reverse_lazy


env = environ.Env(
    DEBUG=(bool, True)
)

BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG')

ALLOWED_HOSTS = ['testserver', '127.0.0.1']

INTERNAL_IPS = [
    "127.0.0.1"
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'debug_toolbar',
    'rest_framework',
    'rest_framework_simplejwt',
    'dj_rest_auth',
    'rest_framework.authtoken',
    'drf_psq',
    'phonenumber_field',
    'rest_framework_swagger',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'dj_rest_auth.registration',

    # apps
    'flats.apps.FlatsConfig',
    'users.apps.UsersConfig',

    'drf_spectacular',
    'django_celery_beat',
    'django_filters'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'api_swipe.urls'

AUTH_USER_MODEL = 'users.User'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
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

SITE_ID = 1

LOGIN_REDIRECT_URL = '/additions'

ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True

ACCOUNT_USER_MODEL_USERNAME_FIELD = 'email'

ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = 'confirmation_congratulations'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = 'confirmation_congratulations'

ACCOUNT_EMAIL_SUBJECT_PREFIX = 'APISwipe. '

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=90),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,

    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
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
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1)
}


WSGI_APPLICATION = 'api_swipe.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT')
    }
}

REST_AUTH = {
    'SESSION_LOGIN': False,
    'LOGIN_SERIALIZER': 'users.serializers.AuthLoginSerializer',
    'REGISTER_SERIALIZER': 'users.serializers.AuthRegistrationSerializer',
    'PASSWORD_CHANGE_SERIALIZER': 'users.serializers.AuthPasswordChangeSerializer',
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'access_token',
    'JWT_AUTH_HTTPONLY': False,
    'JWT_AUTH_REFRESH_COOKIE': 'refresh_token',
}


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'APISwipe',
    'DESCRIPTION': 'API endpoints for APISwipe',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

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


LANGUAGE_CODE = 'uk'

TIME_ZONE = 'Europe/Kyiv'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DEFAULT_FROM_EMAIL = env('EMAIL_HOST_USER')
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')

CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/1'
CELERY_TIMEZONE = 'Europe/Kyiv'

CELERY_BEAT_SCHEDULE = {
    'every-day-carrying-on-subscription': {
        'task': 'users.tasks.carry_on_activation',
        'schedule': crontab(minute=2, hour=0)
    },
    'every-day-deactivating-subscription': {
        'task': 'users.tasks.deactivate_subscription',
        'schedule': crontab(minute=3, hour=0)
    }
}

SECRET_PASSWORD_KEY = env('SECRET_PASSWORD_KEY')
