from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'openmower_mission'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'behavior_trees'), glob('behavior_trees/*.xml')),
    ],
    install_requires=['setuptools', 'shapely'],
    zip_safe=True,
    maintainer='RosMower Developer',
    maintainer_email='you@example.com',
    description='Autonomous mowing mission execution package inspired by OpenMowerNext.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'coverage_path_generator = openmower_mission.coverage_path_generator:main',
            'mission_executor = openmower_mission.mission_executor:main',
            'dock_manager = openmower_mission.dock_manager:main',
            'zone_costmap_publisher = openmower_mission.zone_costmap_publisher:main',
        ],
    },
)
