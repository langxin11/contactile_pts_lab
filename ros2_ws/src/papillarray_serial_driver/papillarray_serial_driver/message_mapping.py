"""将协议数据包映射为 PapillArray ROS 2 消息。"""

from __future__ import annotations

from builtin_interfaces.msg import Time
from papillarray_interfaces.msg import PillarState, SensorState

from .protocol import ParsedPacket

UNKNOWN_SLIP_STATE = 0
NO_ESTIMATE = -1.0


def packet_to_messages(
    packet: ParsedPacket,
    stamp: Time,
    hub_id: int,
    expected_sensors: int,
    contact_threshold_n: float,
) -> list[SensorState]:
    """将一个多传感器数据包映射为 ROS 消息。

    Args:
        packet: 已校验并解析的数据包；力单位 N，位移单位 mm，力矩单位 N·mm。
        stamp: 主机收到数据包时的 ROS 时间。
        hub_id: Controller 标识符。
        expected_sensors: 参数声明的传感器数量。
        contact_threshold_n: sensor frame 中 pillar 法向力接触阈值，单位 N。

    Returns:
        每个传感器一条 ``SensorState``，顺序与数据包 sensor 索引一致。

    Raises:
        ValueError: 数据包中的传感器数或字段 shape 不一致。
    """
    _validate_packet_shape(packet, expected_sensors)
    messages: list[SensorState] = []
    has_pillar_slip = bool(packet.pillar_slip_states)
    has_sensor_slip = bool(packet.slip_detection_active)

    for sensor_index in range(expected_sensors):
        message = SensorState()
        message.header.stamp = stamp
        message.header.frame_id = f"hub_{hub_id}/sensor_{sensor_index}"
        message.tus = packet.timestamp_us

        global_force = packet.global_forces[sensor_index]
        global_torque = packet.global_torques[sensor_index]
        message.gfx, message.gfy, message.gfz = (float(value) for value in global_force)
        message.gtx, message.gty, message.gtz = (
            float(value) for value in global_torque
        )

        if has_sensor_slip:
            message.is_sd_active = packet.slip_detection_active[sensor_index]
            message.is_ref_loaded = packet.reference_pillar_loaded[sensor_index]
            message.friction_est = packet.sensor_friction_estimates[sensor_index]
            message.target_grip_force = packet.target_grip_forces[sensor_index]
        else:
            message.is_sd_active = False
            message.is_ref_loaded = False
            message.friction_est = NO_ESTIMATE
            message.target_grip_force = NO_ESTIMATE

        forces = packet.pillar_forces[sensor_index]
        displacements = packet.pillar_displacements[sensor_index]
        slip_states = (
            packet.pillar_slip_states[sensor_index] if has_pillar_slip else None
        )
        for pillar_index in range(forces.shape[0]):
            pillar = PillarState()
            pillar.id = pillar_index
            pillar.fx, pillar.fy, pillar.fz = (
                float(value) for value in forces[pillar_index]
            )
            pillar.dx, pillar.dy, pillar.dz = (
                float(value) for value in displacements[pillar_index]
            )
            pillar.in_contact = pillar.fz > contact_threshold_n
            pillar.slip_state = (
                int(slip_states[pillar_index])
                if slip_states is not None
                else UNKNOWN_SLIP_STATE
            )
            message.pillars.append(pillar)

        message.is_contact = any(pillar.in_contact for pillar in message.pillars)
        messages.append(message)

    return messages


def _validate_packet_shape(packet: ParsedPacket, expected_sensors: int) -> None:
    if packet.n_sensors != expected_sensors:
        raise ValueError(
            f"数据包包含 {packet.n_sensors} 个传感器，参数 n_sensors={expected_sensors}"
        )
    required_fields = {
        "pillar_displacements": packet.pillar_displacements,
        "global_forces": packet.global_forces,
        "global_torques": packet.global_torques,
    }
    for field_name, values in required_fields.items():
        if len(values) != expected_sensors:
            raise ValueError(f"{field_name} 的传感器数量不一致")

    for sensor_index, (forces, displacements) in enumerate(
        zip(packet.pillar_forces, packet.pillar_displacements, strict=True)
    ):
        if forces.ndim != 2 or forces.shape[1] != 3:
            raise ValueError(f"sensor {sensor_index} pillar_forces shape 应为 (Np, 3)")
        if displacements.shape != forces.shape:
            raise ValueError(f"sensor {sensor_index} 的力与位移 shape 不一致")
        if packet.global_forces[sensor_index].shape != (3,):
            raise ValueError(f"sensor {sensor_index} global_forces shape 应为 (3,)")
        if packet.global_torques[sensor_index].shape != (3,):
            raise ValueError(f"sensor {sensor_index} global_torques shape 应为 (3,)")

    if packet.pillar_slip_states:
        if len(packet.pillar_slip_states) != expected_sensors:
            raise ValueError("pillar_slip_states 的传感器数量不一致")
        if len(packet.pillar_friction_estimates) != expected_sensors:
            raise ValueError("pillar_friction_estimates 的传感器数量不一致")
        for sensor_index, states in enumerate(packet.pillar_slip_states):
            if states.shape != (packet.pillar_forces[sensor_index].shape[0],):
                raise ValueError(f"sensor {sensor_index} 的 pillar slip shape 不一致")
            if packet.pillar_friction_estimates[sensor_index].shape != states.shape:
                raise ValueError(
                    f"sensor {sensor_index} 的 pillar friction shape 不一致"
                )
    elif packet.pillar_friction_estimates:
        raise ValueError("pillar friction 存在但 slip state 缺失")

    sensor_slip_fields = (
        packet.slip_detection_active,
        packet.reference_pillar_loaded,
        packet.sensor_friction_estimates,
        packet.target_grip_forces,
    )
    populated = [bool(values) for values in sensor_slip_fields]
    if any(populated) and not all(populated):
        raise ValueError("Type 6 滑移字段不完整")
    if all(populated) and any(
        len(values) != expected_sensors for values in sensor_slip_fields
    ):
        raise ValueError("Type 6 滑移字段的传感器数量不一致")
