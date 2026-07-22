#!/usr/bin/env python3
"""协议包到 ROS 消息的离线映射测试。"""

import numpy as np
import pytest
from builtin_interfaces.msg import Time

from papillarray_serial_driver.message_mapping import (
    NO_ESTIMATE,
    UNKNOWN_SLIP_STATE,
    packet_to_messages,
)
from papillarray_serial_driver.protocol import ParsedPacket


def _packet(with_slip: bool = True) -> ParsedPacket:
    pillar_states = [np.array([3, -2], dtype=np.int8)] if with_slip else []
    return ParsedPacket(
        packet_counter=7,
        timestamp_us=123456,
        pillar_forces=[np.array([[1.0, 2.0, 0.5], [4.0, 5.0, 0.5001]])],
        pillar_displacements=[np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])],
        global_forces=[np.array([5.0, 7.0, 1.0001])],
        global_torques=[np.array([0.7, 0.8, 0.9])],
        pillar_slip_states=pillar_states,
        pillar_friction_estimates=[np.array([0.6, 0.7])] if with_slip else [],
        slip_detection_active=[True] if with_slip else [],
        reference_pillar_loaded=[True] if with_slip else [],
        sensor_friction_estimates=[0.65] if with_slip else [],
        target_grip_forces=[12.5] if with_slip else [],
    )


def test_maps_packet_fields_and_strict_contact_threshold() -> None:
    messages = packet_to_messages(_packet(), Time(sec=1, nanosec=2), 3, 1, 0.5)

    message = messages[0]
    assert message.header.frame_id == "hub_3/sensor_0"
    assert message.header.stamp == Time(sec=1, nanosec=2)
    assert message.tus == 123456
    assert (message.gfx, message.gfy, message.gfz) == pytest.approx((5.0, 7.0, 1.0001))
    assert (message.gtx, message.gty, message.gtz) == pytest.approx((0.7, 0.8, 0.9))
    assert message.pillars[0].in_contact is False
    assert message.pillars[1].in_contact is True
    assert message.pillars[0].slip_state == 3
    assert message.is_contact is True
    assert message.is_sd_active is True
    assert message.is_ref_loaded is True
    assert message.friction_est == pytest.approx(0.65)
    assert message.target_grip_force == pytest.approx(12.5)


def test_uses_documented_defaults_when_slip_blocks_are_absent() -> None:
    message = packet_to_messages(_packet(with_slip=False), Time(), 0, 1, 0.5)[0]

    assert all(pillar.slip_state == UNKNOWN_SLIP_STATE for pillar in message.pillars)
    assert message.is_sd_active is False
    assert message.is_ref_loaded is False
    assert message.friction_est == NO_ESTIMATE
    assert message.target_grip_force == NO_ESTIMATE


def test_rejects_sensor_count_mismatch() -> None:
    with pytest.raises(ValueError, match="n_sensors=2"):
        packet_to_messages(_packet(), Time(), 0, 2, 0.5)
