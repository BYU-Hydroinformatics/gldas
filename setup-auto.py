import os
import sys
from setuptools import setup, find_packages
from tethys_apps.app_installation import find_resource_files

# -- Apps Definition -- #
app_package = 'gldas'
release_package = 'tethysapp-' + app_package
app_class = 'gldas.app:Gldas'
app_package_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tethysapp', app_package)

# -- Get Resource File -- #
resource_files = find_resource_files('tethysapp/' + app_package + '/templates')
resource_files += find_resource_files('tethysapp/' + app_package + '/public')

setup(
    name=release_package,
    version='2.7.2',
    description='Visualizes GLDAS data through maps and charts',
    long_description='Shows time-animated maps and timeseries plots of monthly average, 1/4 degree resolution, '
                     'GLDAS data sets from NASA LDAS and LIS.',
    keywords='GLDAS',
    author='Riley Hales',
    author_email='',
    url='',
    license='BSD 3-Clause',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    package_data={'': resource_files},
    namespace_packages=['tethysapp', 'tethysapp.' + app_package],
    include_package_data=True,
    zip_safe=False,
    install_requires=[]
)
