# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
from freq.settings import *

DEBUG = True

LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'verbose': {
                'format': '%(asctime)s %(name)s %(levelname)s\n%(message)s',
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
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple'
                },
            'logfile': {
                'level': 'WARN',
                'class': 'logging.FileHandler',
                'formatter': 'verbose',
                'filename': os.path.join(BUILDOUT_DIR,
                                         'var', 'log', 'django.log'),
                }
        },
        'loggers': {
            '': {
                'handlers': [],
                'propagate': True,
                'level': 'DEBUG',
                },
            'django.db.backends': {
                'handlers': ['null'],  # Quiet by default!
                'propagate': False,
                'level': 'DEBUG',
                },
            },
        }

# ENGINE: 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
# In case of geodatabase, prepend with:
# django.contrib.gis.db.backends.(postgis)
DATABASES = {
    # If you want to use another database, consider putting the database
    # settings in localsettings.py. Otherwise, if you change the settings in
    # the current file and commit them to the repository, other developers will
    # also use these settings whether they have that database or not.
    # One of those other developers is Jenkins, our continuous integration
    # solution. Jenkins can only run the tests of the current application when
    # the specified database exists. When the tests cannot run, Jenkins sees
    # that as an error.
    'default': {
        'NAME': 'freq',
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'USER': 'buildout',
        'PASSWORD': 'buildout',
        'HOST': '',  # empty string for localhost.
        'PORT': '',  # empty string for default.
        }
    }


try:
    from freq.localsettings import *
    # For local dev overrides.
except ImportError:
    pass