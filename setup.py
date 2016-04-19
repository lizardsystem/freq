from setuptools import setup

version = '0.3.dev0'

long_description = '\n\n'.join([
    open('README.rst').read(),
    open('CREDITS.rst').read(),
    open('CHANGES.rst').read(),
    ])

install_requires = [
    'Django',
    'django-extensions',
    'django-nose',
    'djangorestframework',
    'lizard-auth-client',
    'numpy',
    'pandas',
    'pytz',
    'scipy',
    'statsmodels',
    ],

tests_require = [
    'nose',
    'coverage',
    'mock',
    ]

setup(name='freq',
      version=version,
      description="FREQ groundwater analysis app",
      long_description=long_description,
      # Get strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=['Programming Language :: Python',
                   'Framework :: Django',
                   ],
      keywords=[],
      author='Roel van den Berg',
      author_email='roel.vandenberg@nelen-schuurmans.nl',
      url='',
      license='GPL',
      packages=['freq'],
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      tests_require=tests_require,
      extras_require={'test': tests_require},
      entry_points={
          'console_scripts': [
          ]},
      )
