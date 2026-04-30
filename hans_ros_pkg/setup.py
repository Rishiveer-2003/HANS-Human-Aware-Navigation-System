from setuptools import setup

package_name = 'hans_ros_pkg'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools',
        'rclpy',
        'geometry_msgs',
        'sensor_msgs',
        'std_msgs',
    ],
    zip_safe=True,
    author='Team HANS',
    author_email='rishi@example.com',
    maintainer='Team HANS',
    maintainer_email='rishi@example.com',
    description='HANS RL integration for ROS2',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'hans_rl_node = hans_ros_pkg.hans_rl_node:main',
        ],
    },
)
