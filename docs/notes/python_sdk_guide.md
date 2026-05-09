# Python SDK 使用笔记

> 基于原厂手册 PTSPython_1.0_MAN_MAR25 的中文总结。

---

## 1. 环境准备

### Python 版本问题

原厂 wheel 包名：`ptsdk_cxx_pybind-1.0.2-cp310-cp310-linux_x86_64.whl`

- `cp310` = **Python 3.10**
- Ubuntu 24.04 默认 Python 3.12，**直接安装会失败**

**解决方案（使用 uv）**：

```bash
cd python_ws
uv venv --python 3.10 .venv
source .venv/bin/activate
uv pip install ../vendor/PythonLIN/ptsdk_cxx_pybind-1.0.2-cp310-cp310-linux_x86_64.whl
```

### 导入库

```python
import PTSDK_CXX_Pybind
```

---

## 2. SDK 文件清单

| 文件 | 说明 |
|------|------|
| `ptsdk_cxx_pybind-1.0.2-cp310-cp310-linux_x86_64.whl` | Python wheel 包（C++ pybind） |
| `ptsdk_pybind_example.py` | 原厂完整示例 |

---

## 3. 核心常量 (PTSDKConstants)

与 C++ SDK 完全一致，通过 `PTSDK_CXX_Pybind.PTSDKConstants` 访问：

| 常量名 | 值 | 说明 |
|--------|-----|------|
| `NDIM` | 3 | 维度数 |
| `MAX_NSENSOR` | 4 | 最大传感器数 |
| `MAX_NPILLAR` | 100 | 最大柱体数 |
| `CONTACT_THRESH` | 0.5 | 接触阈值 (N) |
| `SAMP_RATE_100` | 100 | 100 Hz |
| `SAMP_RATE_250` | 250 | 250 Hz |
| `SAMP_RATE_500` | 500 | 500 Hz |
| `SAMP_RATE_1000` | 1000 | 1000 Hz |
| `INELIGIBLE` | -2 | 滑动状态 |
| `CONTACT_AT_START` | 1 | 滑动状态 |
| `LOST_CONTACT` | -1 | 滑动状态 |
| `TLOADING` | 2 | 滑动状态 |
| `SLIPPED` | 3 | 滑动状态 |
| `NOFRICTIONEST` | -1 | 无摩擦估计 |

---

## 4. 核心类

### PTSDKListener

| 方法 | 说明 |
|------|------|
| `__init__(isLog: bool)` | 构造。`isLog=True` 记录 CSV |
| `addSensor(pSensor: PTSDKSensor)` | 添加传感器 |
| `connect(port, rate, parity, byteSize)` | 连接串口（单线程） |
| `connectAndStartListening(port, rate, parity, byteSize, isFlush)` | 连接并启动监听线程（多线程） |
| `disconnect()` | 断开（单线程） |
| `stopListeningAndDisconnect()` | 停止监听并断开（多线程） |
| `readNextSample()` | 读取下一帧（单线程） |
| `sendBiasRequest()` | Bias |
| `setSamplingRate(samplingRate)` | 设置采样率 |
| `startSlipDetection()` | 启动滑动检测 |
| `stopSlipDetection()` | 停止滑动检测 |
| `getTargetGripForce()` | 获取目标夹持力 |

### PTSDKSensor

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `getNPillar()` | int | 柱体数 |
| `getGlobalForce()` | list[NDIM] | 全局 3D 力 (N) |
| `getGlobalTorque()` | list[NDIM] | 全局 3D 力矩 (N·mm) |
| `getAllDisplacements()` | list[NDIM][NPILLAR] | 所有柱位移 (mm) |
| `getAllForces()` | list[NDIM][NPILLAR] | 所有柱力 (N) |
| `getPillarDisplacements(pillarInd)` | list[NDIM] | 单柱位移 |
| `getPillarForces(pillarInd)` | list[NDIM] | 单柱力 |
| `getPillarForceAbs(pillarInd)` | float | 单柱力绝对值 |
| `getPillarForceN(pillarInd)` | float | 单柱法向力 |
| `getPillarForceT(pillarInd)` | float | 单柱切向力 |
| `getAllSlipStatus()` | tuple | 滑动状态元组 |
| `getFrictionEstimate()` | float | 摩擦估计 |
| `getTargetGripForce()` | float | 目标夹持力 |
| `getTimestamp_us()` | int | 时间戳 (µs) |
| `isSensorInContact()` | bool | 是否接触 |

---

## 5. 典型使用流程

### 多线程模式（推荐）

```python
import PTSDK_CXX_Pybind

# 初始化
sen0 = PTSDK_CXX_Pybind.PTSDKSensor()
listener = PTSDK_CXX_Pybind.PTSDKListener(isLogging=False)
listener.addSensor(sen0)

# 连接并启动监听
port = "/dev/ttyACM0"
rate = 115200       # Python 默认 115200！
parity = 0
byte_size = "\u0008"  # Unicode 字符！不是整数 8
is_flush = True

res = listener.connectAndStartListening(port, rate, parity, byte_size, is_flush)
if res != 0:
    raise RuntimeError("连接失败")

# Bias（必须无负载）
listener.sendBiasRequest()

# 设置采样率
listener.setSamplingRate(PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_500)

# 读取数据
for i in range(100):
    force = sen0.getGlobalForce()  # [fx, fy, fz]
    print(f"Force: {force[0]:.3f}, {force[1]:.3f}, {force[2]:.3f}")

# 断开
listener.stopListeningAndDisconnect()
```

---

## 6. 关键注意事项

| 项目 | 说明 |
|------|------|
| **波特率** | Python 默认 **115200**，与 C++ 的 9600 不同！ |
| **byte_size** | 必须传递 **Unicode 字符** `"\u0008"`，不是整数 `8` |
| **Ctrl+C** | pybind 的 C++ 阻塞 I/O 持有 GIL，可能导致 Ctrl+C 无法中断。建议预检查设备存在性 |
| **串口权限** | 用户必须在 `dialout` 组 |
| **Bias** | 必须无负载，耗时最长 2 秒 |
| **串口释放** | 异常退出时必须调用 `stopListeningAndDisconnect()`，否则串口锁死 |
| **日志** | `isLogging=True` 时，在应用同级目录的 `Logs/` 下生成 CSV，命名 `LOG_YYYY_MM_DD_hh_mm_ss.csv` |
| **无效索引** | 若传入无效 pillarInd，部分函数返回 `[-1000, -1000, -1000]` 或 `-1000` |
