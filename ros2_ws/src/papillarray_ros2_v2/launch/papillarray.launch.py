from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    hub_id_arg = DeclareLaunchArgument(
        'hub_id',
        default_value='0',
        description='ID of the hub'
    )
    n_sensors_arg = DeclareLaunchArgument(
        'n_sensors',
        default_value='2',
        description='Number of sensors being used. Value can be 1 or 2'
    )
    com_port_arg = DeclareLaunchArgument(
        'com_port',
        default_value='/dev/ttyACM0',
        description='Name of COM port to connect with'
    )
    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate',
        default_value='9600',
        description='Rate of serial connection'
    )
    parity_arg = DeclareLaunchArgument(
        'parity',
        default_value='0',
        description='Parity: 0=PARITY_NONE, 1=PARITY_ODD, 2=PARITY_EVEN'
    )
    byte_size_arg = DeclareLaunchArgument(
        'byte_size',
        default_value='8',
        description='Number of bits in byte. Default 8'
    )
    is_flush_arg = DeclareLaunchArgument(
        'is_flush',
        default_value='true',
        description='Flushing flag: flush hardware input buffer when it contains too many bytes'
    )
    sampling_rate_arg = DeclareLaunchArgument(
        'sampling_rate',
        default_value='500',
        description='Rate (Hz): 100, 250, 500, or 1000'
    )

    return LaunchDescription([
        hub_id_arg,
        n_sensors_arg,
        com_port_arg,
        baud_rate_arg,
        parity_arg,
        byte_size_arg,
        is_flush_arg,
        sampling_rate_arg,

        Node(
            package='papillarray_ros2_v2',
            executable='papillarray_ros2_node',
            name='papillarray_ros2_node',
            output='screen',
            parameters=[
                {'hub_id': LaunchConfiguration('hub_id')},
                {'n_sensors': LaunchConfiguration('n_sensors')},
                {'com_port': LaunchConfiguration('com_port')},
                {'baud_rate': LaunchConfiguration('baud_rate')},
                {'parity': LaunchConfiguration('parity')},
                {'byte_size': LaunchConfiguration('byte_size')},
                {'is_flush': LaunchConfiguration('is_flush')},
                {'sampling_rate': LaunchConfiguration('sampling_rate')}
            ]
        )
    ])
