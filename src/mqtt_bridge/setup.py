from setuptools import setup
import os
from glob import glob

package_name = 'mqtt_bridge'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools', 'paho-mqtt'],
    zip_safe=True,
    maintainer='NFAZ10',
    maintainer_email='nick.fazio@gmail.com',
    description='MQTT Bridge for ROS Mower',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mqtt_bridge_node = mqtt_bridge.mqtt_bridge_node:main',
        ],
    },
)
