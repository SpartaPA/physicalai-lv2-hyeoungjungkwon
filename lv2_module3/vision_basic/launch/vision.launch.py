"""
vision_node와 입력(카메라 또는 고정 이미지)을 실행한다. bag 입력은 따로 `ros2 bag play` 한다.

  ros2 launch vision_basic vision.launch.py source:=camera
  ros2 launch vision_basic vision.launch.py source:=image image_path:=<png>
  ros2 launch vision_basic vision.launch.py source:=none params_file:=<yaml>   # bag 재생 시
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import LaunchConfigurationEquals
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('vision_basic')
    params_file = LaunchConfiguration('params_file')
    actions = [
        DeclareLaunchArgument('params_file',
                              default_value=os.path.join(share, 'config', 'vision.yaml')),
        DeclareLaunchArgument('source', default_value='none', choices=['none', 'camera', 'image']),
        DeclareLaunchArgument('image_path', default_value=''),
        DeclareLaunchArgument('rate_hz', default_value='5.0'),
        Node(package='vision_basic', executable='vision_node', name='vision_node',
             parameters=[params_file], output='screen'),
        Node(package='vision_basic', executable='image_file_publisher',
             name='image_file_publisher',
             condition=LaunchConfigurationEquals('source', 'image'), output='screen',
             parameters=[{'image_path': LaunchConfiguration('image_path'),
                          'rate_hz': LaunchConfiguration('rate_hz')}]),
    ]
    try:
        rs_launch = os.path.join(get_package_share_directory('realsense2_camera'),
                                 'launch', 'rs_launch.py')
        actions.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(rs_launch),
            condition=LaunchConfigurationEquals('source', 'camera'),
            launch_arguments={'enable_depth': 'false',
                              'rgb_camera.color_profile': '640x480x30'}.items()))
    except Exception:                      # realsense2_camera 미설치: source:=camera 만 쓸 수 없음
        pass
    return LaunchDescription(actions)
