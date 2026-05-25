from glob import glob

from setuptools import find_packages, setup

package_name = 'object_detector'
resource_files = glob('resource/coco.names') + glob('resource/*.pth')

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/resource', resource_files),
        ('share/' + package_name + '/web', glob('web/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='thedevmanek',
    maintainer_email='thedevmanek@gmail.com',
    description='OpenHRI object detection, localization, tracking, and navigation UI',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'detect = object_detector.object_detect:main',
        ],
    },
)
