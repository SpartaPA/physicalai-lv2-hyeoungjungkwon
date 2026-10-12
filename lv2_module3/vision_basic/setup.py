from glob import glob

from setuptools import find_packages, setup

package_name = 'vision_basic'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    package_data={'': ['py.typed']},
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='JuneKunst',
    maintainer_email='hjkwon9401@gmail.com',
    description='HSV color detection node publishing raw, mask, overlay and detection topics',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'vision_node = vision_basic.nodes.vision_node:main',
            'image_file_publisher = vision_basic.tools.image_file_publisher:main',
            'topic_snapshot = vision_basic.tools.topic_snapshot:main',
        ],
    },
)
