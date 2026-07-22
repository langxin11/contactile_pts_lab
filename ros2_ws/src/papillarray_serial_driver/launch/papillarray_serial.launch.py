#!/usr/bin/env python3
"""启动 PapillArray 自研串口驱动。"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """声明串口驱动参数并创建节点。"""
    arguments = [
        DeclareLaunchArgument(
            "hub_id", default_value="0", description="Controller 标识符"
        ),
        DeclareLaunchArgument(
            "n_sensors", default_value="2", description="预期传感器数量"
        ),
        DeclareLaunchArgument(
            "com_port", default_value="/dev/ttyACM0", description="串口设备路径"
        ),
        DeclareLaunchArgument(
            "baud_rate", default_value="115200", description="串口波特率"
        ),
        DeclareLaunchArgument(
            "sampling_rate", default_value="500", description="控制器采样频率，单位 Hz"
        ),
        DeclareLaunchArgument(
            "serial_timeout_sec",
            default_value="1.0",
            description="串口读取超时，单位 s",
        ),
        DeclareLaunchArgument(
            "max_packet_bytes", default_value="8192", description="单个协议帧字节上限"
        ),
        DeclareLaunchArgument(
            "contact_threshold_n",
            default_value="0.5",
            description="pillar 法向接触阈值，单位 N",
        ),
        DeclareLaunchArgument(
            "reconnect_initial_delay_sec",
            default_value="1.0",
            description="初始重连间隔，单位 s",
        ),
        DeclareLaunchArgument(
            "reconnect_max_delay_sec",
            default_value="10.0",
            description="最大重连间隔，单位 s",
        ),
    ]
    node = Node(
        package="papillarray_serial_driver",
        executable="papillarray_serial_node",
        name="papillarray_serial_node",
        output="screen",
        parameters=[
            {
                "hub_id": LaunchConfiguration("hub_id"),
                "n_sensors": LaunchConfiguration("n_sensors"),
                "com_port": LaunchConfiguration("com_port"),
                "baud_rate": LaunchConfiguration("baud_rate"),
                "sampling_rate": LaunchConfiguration("sampling_rate"),
                "serial_timeout_sec": LaunchConfiguration("serial_timeout_sec"),
                "max_packet_bytes": LaunchConfiguration("max_packet_bytes"),
                "contact_threshold_n": LaunchConfiguration("contact_threshold_n"),
                "reconnect_initial_delay_sec": LaunchConfiguration(
                    "reconnect_initial_delay_sec"
                ),
                "reconnect_max_delay_sec": LaunchConfiguration(
                    "reconnect_max_delay_sec"
                ),
            }
        ],
    )
    return LaunchDescription([*arguments, node])
