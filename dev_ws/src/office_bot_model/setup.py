from setuptools import find_packages, setup
from glob import glob
package_name = 'office_bot_model'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
          ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/models', glob('models/officebot/*')),
        ('share/' + package_name + '/models', glob('models/worlds/*.sdf')),
        ('share/' + package_name + '/config', glob('config/*.rviz')),
        ('share/' + package_name + '/controllers', glob('controllers/*.yaml')),


    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='thedevmanek',
    maintainer_email='thedevmanek@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },

)
