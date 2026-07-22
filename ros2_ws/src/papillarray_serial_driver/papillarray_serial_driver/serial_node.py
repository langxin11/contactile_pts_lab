#!/usr/bin/env python3
"""使用自研串口协议发布 PapillArray ROS 2 传感器消息。"""

from __future__ import annotations

import rclpy
from papillarray_interfaces.msg import SensorState
from papillarray_interfaces.srv import (
    BiasRequest,
    StartSlipDetection,
    StopSlipDetection,
)
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from .message_mapping import packet_to_messages
from .protocol import ParsedPacket
from .serial_worker import (
    BIAS_COMMAND,
    START_SLIP_COMMAND,
    STOP_SLIP_COMMAND,
    SerialWorker,
    SerialWorkerConfig,
)

DEFAULT_HUB_ID = 0
DEFAULT_SENSOR_COUNT = 2
DEFAULT_PORT = "/dev/ttyACM0"
DEFAULT_BAUD_RATE = 115200
DEFAULT_SAMPLING_RATE_HZ = 500
DEFAULT_SERIAL_TIMEOUT_SEC = 1.0
DEFAULT_MAX_PACKET_BYTES = 8192
DEFAULT_CONTACT_THRESHOLD_N = 0.5
DEFAULT_RECONNECT_INITIAL_DELAY_SEC = 1.0
DEFAULT_RECONNECT_MAX_DELAY_SEC = 10.0
MAX_SENSOR_COUNT = 4


class PapillArraySerialNode(Node):
    """通过 pyserial 读取 PTS 数据并提供与原厂驱动兼容的 ROS 接口。"""

    def __init__(self) -> None:
        super().__init__("papillarray_serial_node")
        self._hub_id = int(self.declare_parameter("hub_id", DEFAULT_HUB_ID).value)
        self._n_sensors = int(
            self.declare_parameter("n_sensors", DEFAULT_SENSOR_COUNT).value
        )
        self._contact_threshold_n = float(
            self.declare_parameter(
                "contact_threshold_n", DEFAULT_CONTACT_THRESHOLD_N
            ).value
        )
        if not 1 <= self._n_sensors <= MAX_SENSOR_COUNT:
            raise ValueError(f"n_sensors 必须在 1~{MAX_SENSOR_COUNT} 之间")
        if self._contact_threshold_n < 0:
            raise ValueError("contact_threshold_n 不能小于 0")

        config = SerialWorkerConfig(
            port=str(self.declare_parameter("com_port", DEFAULT_PORT).value),
            baud_rate=int(self.declare_parameter("baud_rate", DEFAULT_BAUD_RATE).value),
            sampling_rate=int(
                self.declare_parameter("sampling_rate", DEFAULT_SAMPLING_RATE_HZ).value
            ),
            timeout_sec=float(
                self.declare_parameter(
                    "serial_timeout_sec", DEFAULT_SERIAL_TIMEOUT_SEC
                ).value
            ),
            max_packet_bytes=int(
                self.declare_parameter(
                    "max_packet_bytes", DEFAULT_MAX_PACKET_BYTES
                ).value
            ),
            reconnect_initial_delay_sec=float(
                self.declare_parameter(
                    "reconnect_initial_delay_sec",
                    DEFAULT_RECONNECT_INITIAL_DELAY_SEC,
                ).value
            ),
            reconnect_max_delay_sec=float(
                self.declare_parameter(
                    "reconnect_max_delay_sec", DEFAULT_RECONNECT_MAX_DELAY_SEC
                ).value
            ),
        )

        self._publishers = [
            self.create_publisher(
                SensorState,
                f"/hub_{self._hub_id}/sensor_{sensor_index}",
                qos_profile_sensor_data,
            )
            for sensor_index in range(self._n_sensors)
        ]
        service_prefix = f"/hub_{self._hub_id}"
        self._bias_service = self.create_service(
            BiasRequest,
            f"{service_prefix}/send_bias_request",
            self._handle_bias_request,
        )
        self._start_slip_service = self.create_service(
            StartSlipDetection,
            f"{service_prefix}/start_slip_detection",
            self._handle_start_slip,
        )
        self._stop_slip_service = self.create_service(
            StopSlipDetection,
            f"{service_prefix}/stop_slip_detection",
            self._handle_stop_slip,
        )

        self._worker = SerialWorker(
            config=config,
            on_packet=self._publish_packet,
            on_info=self.get_logger().info,
            on_warning=self.get_logger().warning,
            on_error=self.get_logger().error,
        )
        self._worker.start()

    def destroy_node(self) -> None:
        """停止串口线程后销毁节点，确保字符设备被释放。"""
        if hasattr(self, "_worker"):
            self._worker.stop()
        super().destroy_node()

    def _publish_packet(self, packet: ParsedPacket) -> None:
        try:
            messages = packet_to_messages(
                packet=packet,
                stamp=self.get_clock().now().to_msg(),
                hub_id=self._hub_id,
                expected_sensors=self._n_sensors,
                contact_threshold_n=self._contact_threshold_n,
            )
        except ValueError as exc:
            # 参数与实际硬件拓扑不一致时不能发布错位的 sensor topic。
            self.get_logger().error(f"已丢弃字段不一致的数据包: {exc}")
            return

        for publisher, message in zip(self._publishers, messages, strict=True):
            publisher.publish(message)

    def _handle_bias_request(
        self,
        _request: BiasRequest.Request,
        response: BiasRequest.Response,
    ) -> BiasRequest.Response:
        # 服务无法判断机械负载，调用者必须把服务调用本身视为无负载确认。
        self.get_logger().warning("发送 Bias 前必须确认传感器无负载，并保持约 2 s")
        response.result = self._worker.send_command(BIAS_COMMAND)
        return response

    def _handle_start_slip(
        self,
        _request: StartSlipDetection.Request,
        response: StartSlipDetection.Response,
    ) -> StartSlipDetection.Response:
        response.result = self._worker.send_command(START_SLIP_COMMAND)
        return response

    def _handle_stop_slip(
        self,
        _request: StopSlipDetection.Request,
        response: StopSlipDetection.Response,
    ) -> StopSlipDetection.Response:
        response.result = self._worker.send_command(STOP_SLIP_COMMAND)
        return response


def main(args: list[str] | None = None) -> None:
    """启动 ROS 2 节点。

    Args:
        args: 传递给 ``rclpy.init`` 的 ROS 参数。
    """
    rclpy.init(args=args)
    node: PapillArraySerialNode | None = None
    try:
        node = PapillArraySerialNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Ctrl+C 由 finally 统一关闭串口，避免设备锁残留。
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
