#!/usr/bin/env python3
"""Launch the Contactile PTS tactile GUI."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Create the visualizer launch description."""
    topic_arg = DeclareLaunchArgument(
        "topic",
        default_value="/hub_0/sensor_0",
        description="SensorState topic to visualize",
    )
    refresh_hz_arg = DeclareLaunchArgument(
        "refresh_hz",
        default_value="30",
        description="GUI refresh rate in Hz",
    )
    history_sec_arg = DeclareLaunchArgument(
        "history_sec",
        default_value="10",
        description="Global force history window in seconds",
    )
    view_arg = DeclareLaunchArgument(
        "view",
        default_value="global",
        description="Display view: displacement, force, or global",
    )
    display_arg = DeclareLaunchArgument(
        "display",
        default_value="curve",
        description="Display mode: text or curve",
    )
    pillar_id_arg = DeclareLaunchArgument(
        "pillar_id",
        default_value="0",
        description="Pillar id used by displacement and force views",
    )

    return LaunchDescription(
        [
            topic_arg,
            refresh_hz_arg,
            history_sec_arg,
            view_arg,
            display_arg,
            pillar_id_arg,
            Node(
                package="contactile_visualizer",
                executable="tactile_gui",
                name="contactile_tactile_gui",
                output="screen",
                arguments=[
                    "--topic",
                    LaunchConfiguration("topic"),
                    "--refresh-hz",
                    LaunchConfiguration("refresh_hz"),
                    "--history-sec",
                    LaunchConfiguration("history_sec"),
                    "--view",
                    LaunchConfiguration("view"),
                    "--display",
                    LaunchConfiguration("display"),
                    "--pillar-id",
                    LaunchConfiguration("pillar_id"),
                ],
            ),
        ]
    )
