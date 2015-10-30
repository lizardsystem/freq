import os

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # # Enable 'old' /media directories in addition to /static.
    # 'django.contrib.staticfiles.finders.LegacyAppDirectoriesFinder',
    # # Enable support for django-compressor.
    # 'compressor.finders.CompressorFinder',
    )

# Production, so DEBUG is False. developmentsettings.py sets it to True.
DEBUG = False
# Show template debug information for faulty templates.  Only used when DEBUG
# is set to True.
TEMPLATE_DEBUG = True

# SETTINGS_DIR allows media paths and so to be relative to this settings file
# instead of hardcoded to c:\only\on\my\computer.
SETTINGS_DIR = os.path.dirname(os.path.realpath(__file__))

# BUILDOUT_DIR is for access to the "surrounding" buildout, for instance for
# BUILDOUT_DIR/var/static files to give django-staticfiles a proper place
# to place all collected static files.
BUILDOUT_DIR = os.path.abspath(os.path.join(SETTINGS_DIR, '..'))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(name)s %(levelname)s\n    %(message)s',
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'logfile': {
            'level': 'WARN',
            'class': 'logging.FileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(BUILDOUT_DIR, 'var', 'log', 'django.log'),
        },
    },
    'loggers': {
        '': {
            'handlers': ['console',],
            'propagate': True,
            'level': 'DEBUG',
        },
        'django.db.backends': {
            'handlers': ['null'],  # Quiet by default!
            'propagate': False,
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['console',],
            'propagate': False,
            'level': 'WARN',  # WARN=404, ERROR=500
        },
    }
}

# ADMINS get internal error mails, MANAGERS get 404 mails.
ADMINS = (
    ('Roel van den Berg', 'roel.vandenberg@nelen-schuurmans.nl'),
)
MANAGERS = ADMINS


# TODO: Switch this to the real production database.
# ^^^ 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
# In case of geodatabase, prepend with: django.contrib.gis.db.backends.(postgis)
DATABASES = {
    'default': {
        'NAME': 'freq',
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'USER': 'freq',
        'PASSWORD': '^rrrl#-+19',
        'HOST': '',
        'PORT': '5432',
        }
    }

# Almost always set to 1.  Django allows multiple sites in one database.
SITE_ID = 1


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name although not all
# choices may be available on all operating systems.  If running in a Windows
# environment this must be set to the same as your system time zone.
TIME_ZONE = 'Europe/Amsterdam'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'nl-NL'

# For at-runtime language switching.  Note: they're shown in reverse order in
# the interface!
LANGUAGES = (
#    ('en', 'English'),
    ('nl', 'Nederlands'),
)

# If you set this to False, Django will make some optimizations so as not to
# load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds user-uploaded media.
MEDIA_ROOT = os.path.join(BUILDOUT_DIR, 'var', 'media')
# Absolute path to the directory where django-staticfiles'
# "bin/django build_static" places all collected static files from all
# applications' /media directory.
STATIC_ROOT = os.path.join(BUILDOUT_DIR, 'var', 'static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
MEDIA_URL = '/media/'
# URL for the per-application /media static files collected by
# django-staticfiles.  Use it in templates like
# "{{ MEDIA_URL }}mypackage/my.css".
STATIC_URL = '/static_media/'

# STATICFILES_DIRS = [
#     os.path.join(BUILDOUT_DIR, 'bower_components'),
#     # ^^^ bower-managed files.
# ]


ROOT_URLCONF = 'freq.urls'

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# SSO *can* be disabled for development with local accounts.
SSO_ENABLED = True

from freq.secrets import SSO_KEY, SSO_SECRET, SECRET_KEY

# URL used to redirect the user to the SSO server.
# Note: needs a trailing slash
SSO_SERVER_PUBLIC_URL = 'https://sso.lizard.net/'
# URL used for server-to-server communication
# Note: needs a trailing slash
SSO_SERVER_PRIVATE_URL = 'http://110-sso-c1.external-nens.local:9874/'

# SSO_CLIENT_STAFF_ROLES = ['user', 'superman']


INSTALLED_APPS = [
    'freq',
    'django_nose',
    'django_extensions',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.gis',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'lizard_auth_client',
    ]

ROOT_URLCONF = 'freq.urls'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'lizard_auth_client.middleware.LoginRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    )

# Add your production name here. Django 1.6+
ALLOWED_HOSTS = ['freq.lizard.net', 'localhost:8078']


TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# Used for django-staticfiles (and for media files
STATIC_URL = '/static_media/'
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.join(BUILDOUT_DIR, 'var', 'static')
MEDIA_ROOT = os.path.join(BUILDOUT_DIR, 'var', 'media')
# STATICFILES_DIRS = [
#     os.path.join(BUILDOUT_DIR, 'bower_components'),
#     # ^^^ bower-managed files.
# ]


try:
    # Import local settings that aren't stored in svn/git.
    from freq.localproductionsettings import *
except ImportError:
    pass
