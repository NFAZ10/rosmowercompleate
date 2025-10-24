from setuptools import find_packages, setup

package_name = 'hailo_ros'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='NFAZ10',
    maintainer_email='nick.fazio@gmail.com',
    description='ROS 2 package for interfacing with Hailo-8 AI accelerator',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'hailo_node = hailo_ros.hailo_node:main'
        ],
    },
)
