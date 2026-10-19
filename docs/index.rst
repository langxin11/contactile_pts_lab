Contactile PTS Lab 研究手册
====================================

Ubuntu 24.04 x86_64 环境下 Contactile PTS（PapillArray）触觉传感器的多语言实验环境。
本项目围绕三项核心任务演进推进：**传感器 SDK 使用 ➔ 基本数据分析 ➔ 自研协议确保准确性**。

.. toctree::
   :maxdepth: 2
   :caption: 阶段一：传感器 SDK 使用与基准建立

   notes/sensor_overview
   notes/cpp_sdk_guide
   notes/python_sdk_guide
   notes/ros2_integration
   notes/vis_software

.. toctree::
   :maxdepth: 2
   :caption: 阶段二：基本数据分析与物理特性

   notes/signal_filtering
   experiments/noise_psd
   experiments/force_accuracy

.. toctree::
   :maxdepth: 2
   :caption: 阶段三：自研协议开发与准确性闭环

   notes/communication_protocol
