#!/usr/bin/env python3
"""Contactile PTS 最简 Python 读取示例.

运行前请确保已激活虚拟环境:
    source python_ws/.venv/bin/activate
    python quick_read.py

或直接使用脚本:
    bash scripts/run_python.sh quick_read
"""

import sys
import time

import PTSDK_CXX_Pybind


def main() -> int:
    # 串口参数（Python SDK 默认 115200）
    port = "/dev/ttyACM0"
    baud_rate = 115200
    parity = 0
    byte_size = "\u0008"  # 原厂示例中的写法
    is_flush = True

    # C++ pybind 阻塞 I/O 时持有 GIL，Ctrl+C 可能失效，预检查设备
    import os

    if not os.path.exists(port):
        print(f"错误: 设备 {port} 不存在，请检查连接和权限", file=sys.stderr)
        return 1

    # 初始化传感器和监听器
    sen0 = PTSDK_CXX_Pybind.PTSDKSensor()
    listener = PTSDK_CXX_Pybind.PTSDKListener(logFlag=False)
    listener.addSensor(sen0)

    # 连接并启动监听
    res = listener.connectAndStartListening(port, baud_rate, parity, byte_size, is_flush)
    if res != 0:
        print("错误: 无法连接串口", file=sys.stderr)
        return 1
    print(f"已连接到 {port}")

    # Bias（确保传感器无负载）
    res = listener.sendBiasRequest()
    if not res:
        print("错误: Bias 请求失败", file=sys.stderr)
        listener.stopListeningAndDisconnect()
        return 1
    print("Bias 完成")

    # 设置采样率 500 Hz
    listener.setSamplingRate(PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_500)

    # 读取数据
    print(f"{'Sample':<8} {'Fx (N)':<12} {'Fy (N)':<12} {'Fz (N)':<12}")
    try:
        for i in range(100):
            time.sleep(0.002)
            force = sen0.getGlobalForce()  # shape=(3,)
            print(f"{i + 1:<8} {force[0]:<12.4f} {force[1]:<12.4f} {force[2]:<12.4f}")
    except KeyboardInterrupt:
        print("\n收到中断信号")
    finally:
        # 异常退出时必须释放串口，否则 /dev/ttyACM0 锁死
        listener.stopListeningAndDisconnect()
        print("已断开连接")

    return 0


if __name__ == "__main__":
    sys.exit(main())
