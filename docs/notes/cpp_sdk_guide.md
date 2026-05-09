# C++ Linux SDK 使用笔记

> 基于原厂手册 PTSC++LIN_2.0_MAN_MAR23 的中文总结。

---

## 1. SDK 文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| `PTSDKConstants.h` | `vendor/C++LIN/Include/` | 常量定义 |
| `PTSDKListener.h` | `vendor/C++LIN/Include/` | 监听器类 |
| `PTSDKParser.h` | `vendor/C++LIN/Include/` | 数据解析器类 |
| `PTSDKSensor.h` | `vendor/C++LIN/Include/` | 传感器类 |
| `PTSDKPillar.h` | `vendor/C++LIN/Include/` | 柱体类 |
| `libPTSDK.a` | `vendor/C++LIN/Library/` | 静态库（x86_64） |
| `example.cpp` | `vendor/C++LIN/Example/` | 原厂完整示例 |
| `makefile` | `vendor/C++LIN/Example/` | 原厂 Makefile |

---

## 2. 核心常量 (PTSDKConstants.h)

| 常量名 | 值 | 说明 |
|--------|-----|------|
| `NDIM` | 3 | 空间维度数 (X, Y, Z) |
| `MAX_NSENSOR` | 4 | 最大传感器数量 |
| `MAX_NPILLAR` | 100 | 最大柱体数 |
| `CONTACT_THRESH` | 0.5 N | 接触判定阈值（法向力） |
| `SAMP_RATE_100` | 100 | 100 Hz |
| `SAMP_RATE_250` | 250 | 250 Hz |
| `SAMP_RATE_500` | 500 | 500 Hz |
| `SAMP_RATE_1000` | 1000 | 1000 Hz（上电默认） |

**滑动状态常量**

| 常量名 | 值 | 说明 |
|--------|-----|------|
| `INELIGIBLE` | -2 | 滑动检测开始时未接触 |
| `CONTACT_AT_START` | 1 | 滑动检测开始时已接触 |
| `LOST_CONTACT` | -1 | 滑动检测开始后失去接触 |
| `TLOADING` | 2 | 正在被切向加载 |
| `SLIPPED` | 3 | 已发生滑动 |
| `NOFRICTIONEST` | -1 | 无摩擦估计值 |

**索引常量**

| 常量名 | 值 |
|--------|-----|
| `X_IND` | 0 |
| `Y_IND` | 1 |
| `Z_IND` | 2 |

---

## 3. 核心类

### PTSDKListener — 串口监听器

负责与 Controller 的串口通信、数据接收与解析。

| 方法 | 说明 |
|------|------|
| `PTSDKListener(bool isLog)` | 构造。`isLog=true` 会记录 CSV 日志 |
| `addSensor(PTSDKSensor* pSensor)` | 向监听器添加传感器对象 |
| `connect(port, rate, parity, byteSize)` | 连接串口（单线程模式） |
| `connectAndStartListening(port, rate, parity, byteSize, isFlush)` | 连接并启动监听线程（多线程模式） |
| `disconnect()` | 断开串口（单线程模式） |
| `stopListeningAndDisconnect()` | 停止监听并断开（多线程模式） |
| `readNextSample()` | 读取并解析下一帧（单线程模式） |
| `sendBiasRequest()` | 发送 Bias 请求 |
| `setSamplingRate(int rate)` | 设置采样率 |
| `startSlipDetection()` | 启动滑动检测 |
| `stopSlipDetection()` | 停止滑动检测 |

### PTSDKSensor — 传感器数据容器

存储单个传感器的所有测量数据，提供数据访问接口。

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `getNPillar()` | int | 传感器柱体数量 |
| `getGlobalForce(double result[NDIM])` | void | 全局 3D 力 (N) |
| `getGlobalTorque(double result[NDIM])` | void | 全局 3D 力矩 (N·mm)，参考点为 P4 顶端 |
| `getAllDisplacements(...)` | void | 所有柱的 3D 位移 (mm) |
| `getAllForces(...)` | void | 所有柱的 3D 力 (N) |
| `getPillarDisplacements(pillarInd, result)` | bool | 单柱 3D 位移 |
| `getPillarForces(pillarInd, result)` | bool | 单柱 3D 力 |
| `getPillarForceAbs(pillarInd, result)` | bool | 单柱力绝对值 |
| `getPillarForceN(pillarInd, result)` | bool | 单柱法向 (Z) 力 |
| `getPillarForceT(pillarInd, result)` | bool | 单柱切向 (XY) 力 |
| `getAllSlipStatus(...)` | void | 所有柱的滑动状态 |
| `getFrictionEstimate()` | double | 摩擦估计值 |
| `isSensorInContact()` | bool | 是否有柱处于接触状态 |
| `getTimestamp_us()` | uint32_t | 当前样本时间戳 (µs) |

---

## 4. 典型使用流程

### 4.1 单线程模式

```cpp
PTSDKSensor sen0;
PTSDKListener listener(false);  // 不记录日志
listener.addSensor(&sen0);

// 1. 连接
listener.connect("/dev/ttyACM0", 9600, 0, 8);

// 2. Bias（必须无负载）
listener.sendBiasRequest();

// 3. 设置采样率
listener.setSamplingRate(SAMP_RATE_500);

// 4. 循环读取
while (true) {
    listener.readNextSample(true);  // true = 必要时 flush 缓冲区
    double force[NDIM];
    sen0.getGlobalForce(force);
    // 处理数据...
}

// 5. 断开
listener.disconnect();
```

### 4.2 多线程模式（推荐）

```cpp
PTSDKSensor sen0;
PTSDKListener listener(false);
listener.addSensor(&sen0);

// 1. 连接并启动监听线程
listener.connectAndStartListening("/dev/ttyACM0", 9600, 0, 8, false);

// 2. Bias
listener.sendBiasRequest();
listener.setSamplingRate(SAMP_RATE_500);

// 3. 主线程直接读取已解析的数据
while (true) {
    double force[NDIM];
    sen0.getGlobalForce(force);
    // 处理数据...
}

// 4. 停止监听并断开
listener.stopListeningAndDisconnect();
```

---

## 5. 关键注意事项

| 项目 | 说明 |
|------|------|
| **波特率** | C++ 默认 **9600**，与 Python 的 115200 不同 |
| **串口权限** | 用户必须在 `dialout` 组：`sudo usermod -aG dialout $USER` |
| **Bias 条件** | 必须无负载，耗时最长 2 秒 |
| **串口释放** | 异常退出时必须调用 `disconnect()` 或 `stopListeningAndDisconnect()`，否则串口锁死 |
| **byteSize** | C++ 中用 `char` 类型传递，值为 `8` |
| **日志文件** | `isLog=true` 时，在应用同级目录的 `Logs/` 下生成 CSV，命名格式 `LOG_YYYY_MM_DD_hh_mm_ss.csv` |
| **默认采样率** | 控制器上电默认为 **1000 Hz**，可通过 `setSamplingRate()` 修改 |
