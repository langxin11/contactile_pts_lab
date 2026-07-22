// ============================================================
// papillarray_ros2_node.hpp — PapillArray ROS 2 驱动节点头文件
//
// 定义 PapillArrayNode 类，继承自 rclcpp::Node。
// 负责管理传感器连接、数据采集、消息发布和服务响应。
// ============================================================

#ifndef PAPILLARRAY_ROS2_V2_NODE_H_
#define PAPILLARRAY_ROS2_V2_NODE_H_

#include <stdio.h>
#include <chrono>
#include <memory>
#include <string>
#include <vector>

// ROS 2 核心头文件
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/header.hpp"

#include "csv_logger.hpp"

// ---- 自定义消息 ----
#include "papillarray_interfaces/msg/pillar_state.hpp"
#include "papillarray_interfaces/msg/sensor_state.hpp"

// ---- 自定义服务 ----
#include "papillarray_interfaces/srv/bias_request.hpp"
#include "papillarray_interfaces/srv/start_slip_detection.hpp"
#include "papillarray_interfaces/srv/stop_slip_detection.hpp"

// ---- PTSDK 传感器 SDK ----
// Workaround for GCC 13 + C++17: std::byte conflicts with BYTE macro
// PTSDKParser.h and PTSDKListener.h now use #define BYTE unsigned char
// Removed: typedef unsigned char byte;
//
// 注意: GCC 13 + C++17 下 std::byte 与 PTSDK 的 BYTE 宏存在冲突，
// 当前 SDK 头文件中已使用 #define BYTE unsigned char 绕过

#ifndef PTSDKCONSTANTS_H
#include <PTSDKConstants.h>   // 常量定义 (维度索引、滑动状态枚举等)
#endif
#ifndef PTSDKLISTENER_H
#include <PTSDKListener.h>    // 串口监听器，管理连接与数据接收
#endif
#ifndef PTSDKSENSOR_H
#include <PTSDKSensor.h>      // 传感器对象，封装单个传感器的数据读取接口
#endif

// ============================================================
// PapillArrayNode — PapillArray 传感器 ROS 2 驱动节点
//
// 生命周期:
//   1. 构造 - 加载参数 → 创建传感器对象 → 连接串口 → 启动定时采样
//   2. 运行 - 定时回调 updateData() 发布 SensorState 消息
//   3. 析构 - 停止监听并断开串口连接
// ============================================================
class PapillArrayNode : public rclcpp::Node {
public:
    // 构造函数: 声明参数、创建传感器、连接串口、启动定时器
    explicit PapillArrayNode(const rclcpp::NodeOptions & options);

    // 析构函数: 停止数据监听并断开与 COM 口的连接
    ~PapillArrayNode() {
        csv_logger_.close();
        listener_.stopListeningAndDisconnect();
    }

    // 定时采样回调: 从各传感器读取最新数据并发布到对应 Topic
    void updateData();

private:
    // ======== 配置参数 ========
    int hub_id_;           // 集线器 ID，用于命名话题和服务
    int n_sensors_;        // 传感器数量 (1~4)
    std::string port_;     // 串口设备路径，如 /dev/ttyACM0
    int baud_rate_;        // 串口波特率，如 9600
    int parity_;           // 校验位: 0=无, 1=奇, 2=偶
    int byte_size_;        // 数据位宽，默认 8 位
    bool is_flush_;        // 缓冲区溢出时是否清空硬件输入缓冲
    int sampling_rate_;    // 采样频率 (Hz): 100/250/500/1000
    std::string log_dir_;  // CSV 日志目录；空字符串表示关闭日志
    bool csv_pillar_detail_;  // 是否在 CSV 中记录逐 pillar 位移与力

    // ======== 传感器管理 ========
    PTSDKListener listener_;                         // 串口监听器，管理底层数据流
    std::vector<std::unique_ptr<PTSDKSensor> > sensors_;  // 传感器对象容器
    CsvLogger csv_logger_;                           // 可控权限的时间序列 CSV 写入器

    // ======== ROS 2 通信接口 ========
    // 每个传感器对应一个 Publisher，发布到 /hub_{id}/sensor_{n} 话题
    std::vector<rclcpp::Publisher<papillarray_interfaces::msg::SensorState>::SharedPtr> sensor_pubs_;

    // 定时器: 按 sampling_rate 周期触发 updateData()
    rclcpp::TimerBase::SharedPtr update_timer_;

    // ---- 服务端 ----
    rclcpp::Service<papillarray_interfaces::srv::StartSlipDetection>::SharedPtr start_sd_srv_;
    rclcpp::Service<papillarray_interfaces::srv::StopSlipDetection>::SharedPtr stop_sd_srv_;
    rclcpp::Service<papillarray_interfaces::srv::BiasRequest>::SharedPtr send_bias_request_srv_;

    // ---- 服务回调函数 ----
    bool startSlipDetectionSrvCallback(
        [[maybe_unused]] const std::shared_ptr<papillarray_interfaces::srv::StartSlipDetection::Request> request,
        std::shared_ptr<papillarray_interfaces::srv::StartSlipDetection::Response> response);

    bool stopSlipDetectionSrvCallback(
        [[maybe_unused]] const std::shared_ptr<papillarray_interfaces::srv::StopSlipDetection::Request> request,
        std::shared_ptr<papillarray_interfaces::srv::StopSlipDetection::Response> response);

    bool sendBiasRequestSrvCallback(
        [[maybe_unused]] const std::shared_ptr<papillarray_interfaces::srv::BiasRequest::Request> request,
        std::shared_ptr<papillarray_interfaces::srv::BiasRequest::Response> response);
};

#endif // PAPILLARRAY_ROS2_V2_NODE_H_
