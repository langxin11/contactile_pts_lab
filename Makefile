.DEFAULT_GOAL := help

# ==============================================================================
# Contactile PTS Lab 统一任务流水线
# 任务主线：传感器 SDK 使用 -> 基本数据分析 -> 自研协议确保准确性
# ==============================================================================

.PHONY: help check setup docs clean test
.PHONY: read-sdk read-serial read-cpp run-ros2 vis noise-psd measure-force compare-relay

help: ## 显示所有可用指令与研究主线说明
	@echo "======================================================================"
	@echo "Contactile PTS Lab - 触觉传感器实验环境"
	@echo "任务主线: [阶段一] SDK 使用  ->  [阶段二] 信号分析  ->  [阶段三] 协议验证"
	@echo "======================================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ------------------------------------------------------------------------------
# 环境与设备检查
# ------------------------------------------------------------------------------
check: ## [设备] 检查 USB 连接与串口读写权限
	@bash scripts/check_usb.sh

setup: ## [环境] 一键拉取子模块、编译 C++、初始化 Python 虚拟环境
	@bash scripts/setup.sh

# ------------------------------------------------------------------------------
# 阶段一：传感器 SDK 使用与基准确立
# ------------------------------------------------------------------------------
read-sdk: ## [阶段一] Python: 运行官方 SDK 读取基准 (依赖 cp310 wheel)
	@bash scripts/run_python.sh quick_read_sdk

read-cpp: ## [阶段一] C++: 运行 minimal_reader 官方 C++ 极简读取器
	@bash scripts/run_cpp.sh

run-ros2: ## [阶段一] ROS2: 启动 ROS 2 触觉节点发布话题
	@bash scripts/run_ros2.sh --real

# ------------------------------------------------------------------------------
# 阶段二：传感器物理特性与基本数据分析
# ------------------------------------------------------------------------------
vis: ## [阶段二] 启动 DearPyGui 3D 触觉力与形变实时可视化
	@bash scripts/run_python.sh pts_vis

noise-psd: ## [阶段二] 运行空载本底噪声 PSD 功率谱密度分析 (需 CSV=路径)
	@if [ -z "$(CSV)" ]; then \
		echo "用法: make noise-psd CSV=data/protocol_compare/<会话>/protocol.csv"; \
		exit 1; \
	fi
	@cd python_ws && uv run --extra plot python noise_psd_analysis.py $(CSV)

measure-force: ## [阶段二] 启动质量—法向力标定与阶梯加载测量
	@cd python_ws && uv run --extra experiment python force_accuracy_measure.py --config ../config/force_accuracy.yaml

# ------------------------------------------------------------------------------
# 阶段三：自研协议开发与准确性闭环
# ------------------------------------------------------------------------------
read-serial: ## [阶段三] Python: 运行自研纯串口协议实时读取 (无需 wheel/全平台通用)
	@bash scripts/run_python.sh quick_read_serial

compare-relay: ## [阶段三] 启动同源单流硬件中继比对 (官方 SDK 与自研协议同源双跑)
	@cd python_ws && uv run --extra experiment python pts_protocol_compare.py --relay

test: ## [质量] 运行 Python 工作区完整单元测试与协议校验
	@cd python_ws && uv run pytest

docs: ## [文档] 编译 Sphinx HTML 手册并输出本地链接
	@bash scripts/build_docs.sh

clean: ## [清理] 清除临时编译缓存与文档产物
	@rm -rf cpp_ws/build docs/_build
