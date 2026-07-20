# ============================================================
# papillarray.launch.py — PapillArray 传感器驱动节点启动文件
#
# 声明所有可配置参数并启动 papillarray_ros2_node。
# 启动后可动态查看传感器数据和调用服务。
#
# 用法:
#   ros2 launch papillarray_ros2_v2 papillarray.launch.py
#   ros2 launch papillarray_ros2_v2 papillarray.launch.py com_port:=/dev/ttyACM1 sampling_rate:=1000
# ============================================================

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """生成启动描述: 声明参数 + 启动节点"""

    # ---- 集线器 ID ----
    hub_id_arg = DeclareLaunchArgument(
        'hub_id',
        default_value='0',
        description='集线器 ID (用于构造 Topic 和 Service 名称)'
    )

    # ---- 传感器数量 ----
    n_sensors_arg = DeclareLaunchArgument(
        'n_sensors',
        default_value='2',
        description='传感器数量，可设为 1 或 2'
    )

    # ---- 串口设备路径 ----
    com_port_arg = DeclareLaunchArgument(
        'com_port',
        default_value='/dev/ttyACM0',
        description='串口设备路径'
    )

    # ---- 串口波特率 ----
    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate',
        default_value='9600',
        description='串口波特率'
    )

    # ---- 校验位 ----
    parity_arg = DeclareLaunchArgument(
        'parity',
        default_value='0',
        description='校验位: 0=无校验(PARITY_NONE), 1=奇校验(PARITY_ODD), 2=偶校验(PARITY_EVEN)'
    )

    # ---- 数据位宽 ----
    byte_size_arg = DeclareLaunchArgument(
        'byte_size',
        default_value='8',
        description='数据位宽 (默认 8 位)'
    )

    # ---- Flush 标志 ----
    is_flush_arg = DeclareLaunchArgument(
        'is_flush',
        default_value='true',
        description='缓冲区溢出时是否清空硬件输入缓冲'
    )

    # ---- 采样频率 ----
    sampling_rate_arg = DeclareLaunchArgument(
        'sampling_rate',
        default_value='500',
        description='采样频率 (Hz): 100, 250, 500 或 1000'
    )

    # 返回 LaunchDescription，包含参数声明和节点定义
    return LaunchDescription([
        # 声明所有可配置参数
        hub_id_arg,
        n_sensors_arg,
        com_port_arg,
        baud_rate_arg,
        parity_arg,
        byte_size_arg,
        is_flush_arg,
        sampling_rate_arg,

        # 启动驱动节点
        Node(
            package='papillarray_ros2_v2',
            executable='papillarray_ros2_node',
            name='papillarray_ros2_node',
            output='screen',   # 日志输出到终端
            parameters=[{
                'hub_id': LaunchConfiguration('hub_id'),
                'n_sensors': LaunchConfiguration('n_sensors'),
                'com_port': LaunchConfiguration('com_port'),
                'baud_rate': LaunchConfiguration('baud_rate'),
                'parity': LaunchConfiguration('parity'),
                'byte_size': LaunchConfiguration('byte_size'),
                'is_flush': LaunchConfiguration('is_flush'),
                'sampling_rate': LaunchConfiguration('sampling_rate'),
            }]
        )
    ])
