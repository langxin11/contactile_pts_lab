# 质量—法向压力准确性与标定实验

本实验评估 Contactile PTS（PapillArray）触觉传感器在标准质量（砝码）垂直加压下的法向力输出准确度，并作为**自研协议与原厂 SDK 同源精度比对**的关键实验。

---

## 1. 实验原理与同源比对设计

通常情况下，对比两种实现往往需要分别运行两次物理实验。然而，触觉传感器的接触力极易受砝码放置位置偏差、静态温漂及弹性迟滞影响。

为了消除物理条件偏差，本系统采用了**硬件单流中继（Twin Relay）设计**：
1. `force_accuracy_measure.py` 打开物理串口读取原始字节。
2. 原始串口字节被实时中继至原厂 SDK，由官方算法计算第一组力输出。
3. 原始字节原样落盘为 `capture_raw.bin`。
4. 测量完成后，自研串口解析器基于相同的控制器硬件微秒时间戳窗口（$T_{us}$）离线计算第二组结果。
5. 最终生成的 `measurements.csv` 记录的是**同一次物理放置、同一批原始采样点**下的两套实现数值及其差值。

---

## 2. 实验步骤

### 2.1 依赖与准备
- 确保传感器水平平放且表面悬空无负载。
- 准备好标准精密电子秤及若干标准砝码（如 5g, 10g, 20g, 50g, 100g, 200g 等）。
- 配置文件见 `config/force_accuracy.yaml`。

### 2.2 启动数据采集

在 `python_ws` 目录下运行：

```bash
# 自动完成测量并调用绘图钩子
uv run --extra experiment python force_accuracy_measure.py \
  --config ../config/force_accuracy.yaml
```

若只需记录 CSV 数据暂不自动画图（或用于无图形化界面的工控机）：
```bash
uv run --extra measurement python force_accuracy_measure.py \
  --config ../config/force_accuracy.yaml
```

### 2.3 终端交互与记录控制

实验启动后，程序会引导用户依次放置指定质量并进行采样：
- **放置确认**：将砝码平稳轻放在传感器 3×3 柱阵列中心后，按回车开始稳定采样。
- **记录撤销 (`u`)**：若发现砝码放置位置偏移或手抖干扰，在下一次输入时键入 `u` 并回车，即可撤销最近一条有效记录。
- **指定排除 (`d <ID>`)**：键入 `d 3` 可逻辑排除第 3 条记录。CSV 会保留原始数值并将 `included` 标记设为 `false`，绘图时自动过滤。
- **动态补点 (`--interactive`)**：默认测量序列由 YAML 中的 `measurement.target_masses_g` 预设；如需临时组合加码，可加 `--interactive` 参数逐项手动输入砝码质量。
- **保存退出 (`q`)**：键入 `q` 退出测量，脚本会原子更新 CSV、安全释放串口，并触发绘图子进程。

---

## 3. 数据重绘与独立分析

每次测量均会在 `data/force_accuracy/<时间戳>/` 目录下生成独立的会话数据包：
- `measurements.csv`：汇总各质量点的测量数据、官方 SDK 结果、自研协议结果与两者差值。
- `capture_raw.bin`：完整原始串口二进制流。

如需调整图表样式或单独重绘已有数据：

```bash
uv run --extra plot python force_accuracy_plot.py \
  ../data/force_accuracy/<YYYYMMDD_HHMMSS>/measurements.csv \
  --config ../config/force_accuracy.yaml
```

生成的图表基于 IEEE 单栏科研论文规范排版（SciencePlots 风格）：
- **实心圆点**：Official SDK 输出。
- **空心方块**：Serial protocol 自研协议输出。
- **虚线参考线**：标准理论重力 $F = m \cdot g$（$g = 9.80665 \text{ m/s}^2$）。
