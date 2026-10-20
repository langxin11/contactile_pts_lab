# USB 插入到数据流的连接建立耗时实测

> 2026-10-20 在 Ubuntu 24.04 x86_64 上对 PTS 控制器（枚举为 Teensy `16c0:0483`）的实测记录。
> 结论：控制器上电后即持续输出数据流，等待主要来自固件启动与原厂 SDK 首次连接握手。

---

## 1. 测量方法

- USB/节点出现时刻：100 ms 轮询 `lsusb` 与 `/dev/ttyACM*`，配合 `udevadm monitor` 事件时间戳。
- 打开串口到首帧：`quick_read_sdk.py` 输出逐行打 `date +%H:%M:%S.%3N` 时间戳，
  取"已连接"与"收到首帧"两行之差。

## 2. 实测时间线

| 阶段 | 耗时 | 说明 |
|------|------|------|
| 物理插入 → USB 枚举 → `/dev/ttyACM0` 出现 | 约 1~2 s | 大头是 Teensy 上电启动固件；枚举到节点生成仅 2 ms，udev 规则处理 7 ms |
| 首次 SDK `connectAndStartListening` → 首帧 | **2.85 s** | 仅发生在插上后的第一次打开 |
| 第二次 SDK 打开 → 首帧 | 9 ms | 不拔线重开很快 |
| 纯 pyserial 打开 → 首帧 | 7 ms | `quick_read_serial.py`，不走 SDK |

## 3. 关键证据与结论

1. **控制器不因开串口复位**：两次 SDK 运行的首帧控制器时间戳（46.96 s / 69.04 s）
   反推出同一个固件启动时刻（差 < 0.1 s），说明打开 `/dev/ttyACM0` 不会重启固件。
2. **控制器上电后持续流式输出**：纯 pyserial 打开后 7 ms 即解析出有效帧。
3. **2.85 s 延迟是原厂 SDK 首次连接的内部握手**，不是控制器或系统行为；
   纯协议链路（`quick_read_serial.py` / `pts_protocol.py`）没有这段延迟。
4. 系统若启用 ModemManager（Ubuntu 桌面版默认启用），插入后头几秒开串口可能被
   探测抢占；`udev/99-contactile-pts.rules` 已加 `ENV{ID_MM_DEVICE_IGNORE}="1"` 规避。

## 4. 实用建议

- 入口脚本 `quick_read_sdk.py` / `quick_read_serial.py` 已内置设备节点等待
  （`--wait`，默认 5 s，由 `serial_utils.wait_for_serial_device` 提供），
  插上 USB 后直接运行即可，不再因枚举未完成而立即失败。
- 走 SDK 链路时，首帧等待超时给足 **≥ 5 s**（`quick_read_sdk.py` 默认 5 s 即为此留的余量）。
- 对首帧延迟敏感的实验（如高速触发采集）优先用纯协议链路。
- 纯协议链路重开串口时，`quick_read_serial.py` 已在打开后**先静默 0.1 s 再
  `reset_input_buffer()`**：旧帧滞留在设备端缓冲（实测可达 40 s 前的数据），打开后
  约几 ms 才涌入内核，立即 flush 扑空、静默后 flush 才能清干净（实测二次打开首帧
  时间戳与上次尾帧间隔恢复为真实墙钟间隔）。其他直接使用 `serial.Serial` 的脚本
  （如 `pts_protocol_compare.py`）如依赖时间戳，需自行做同样处理。

## 5. udev 修复后的复测（同日）

安装新规则（Teensy VID/PID + `ID_MM_DEVICE_IGNORE`）后重新插拔复测：

- `/dev/contactile_pts` 软链接正常创建（udev 属性显示设备自报
  `ID_USB_MODEL=Contactile_Controller_v2.0`、序列号 `15954100`、固件版本 `0279`）。
- `ID_MM_DEVICE_IGNORE=1` 生效：节点出现后 **107 ms** 即打开串口成功，
  未被 ModemManager 抢占（该时间窗口正是修复前的风险区）。
- SDK 首连握手复现：连接 → 首帧 **3.07 s**（与首轮 2.85 s 一致，确认为 SDK 稳定行为）；
  第二次打开 → 首帧 10 ms。
