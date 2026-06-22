from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'office_bot_model'


def package_files(directory):
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            full_path = os.path.join(path, filename)
            install_path = os.path.join('share', package_name, path)
            paths.append((install_path, [full_path]))
    return paths


data_files = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ('share/' + package_name + '/config', glob('config/*.rviz') + glob('config/*.xml')),
    ('share/' + package_name + '/controllers', glob('controllers/*.yaml')),
]
data_files.extend(package_files('models'))


setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=data_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='thedevmanek',
    maintainer_email='thedevmanek@gmail.com',
    description='OpenHRI office robot simulation model, world, launch, and Nav2 configuration',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [],
    },
)
