# PapillArray 自研串口 ROS 2 驱动

本包通过 `pyserial` 和 PTS v2.0 协议直接读取 Controller，不依赖原厂 PTSDK 动态库。
它与 `papillarray_ros2_v2` 使用相同的消息、Topic 和 Service，因此两者应二选一运行。

## 启动

```bash
ros2 launch papillarray_serial_driver papillarray_serial.launch.py
```

常用参数：

```bash
ros2 launch papillarray_serial_driver papillarray_serial.launch.py \
  com_port:=/dev/ttyACM0 baud_rate:=115200 n_sensors:=2 sampling_rate:=500
```

节点发布 `/hub_<hub_id>/sensor_<sensor_id>`，并提供以下服务：

- `/hub_<hub_id>/send_bias_request`
- `/hub_<hub_id>/start_slip_detection`
- `/hub_<hub_id>/stop_slip_detection`

调用 Bias 服务前必须确保传感器完全无负载，并在约 2 s 内保持无负载。节点不会自动执行
Bias。串口断开后节点停止发布，并以最长 10 s 的退避间隔自动重连。
