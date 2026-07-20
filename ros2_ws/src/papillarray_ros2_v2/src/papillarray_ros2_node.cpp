// ============================================================
// papillarray_ros2_node.cpp — PapillArray ROS 2 驱动节点实现
//
// 节点生命周期:
//   1. 加载 launch 参数 (hub_id / n_sensors / com_port / …)
//   2. 创建 PTSDKSensor 实例并注册到 PTSDKListener
//   3. 通过串口连接传感器集线器
//   4. 设置采样频率，启动定时器
//   5. 定时回调 updateData() 采集并发布传感器数据
//   6. 析构时断开串口连接
// ============================================================

#include "papillarray_ros2_node.hpp"

#include <array>
#include <chrono>

// ============================================================
// 构造函数: 初始化节点、连接硬件、启动采样
// ============================================================
PapillArrayNode::PapillArrayNode([[maybe_unused]] const rclcpp::NodeOptions &options)
    : Node("papillarray_ros2_v2_node")   // 节点名称
    , listener_(true)                     // 启用 CSV 日志 (写入 ~/.ros/Logs)
{
    // ---------- 1. 加载参数 ----------
    RCLCPP_INFO(this->get_logger(), "Loading parameters...\n");

    // 集线器 ID: 用于构造 Topic 和 Service 名称
    hub_id_ = this->declare_parameter("hub_id", 0);
    RCLCPP_INFO(this->get_logger(), "Hub id: %d", hub_id_);

    // 传感器数量: 不能超过 MAX_NSENSOR (4)
    n_sensors_ = this->declare_parameter("n_sensors", 0);
    if (n_sensors_ > MAX_NSENSOR || n_sensors_ < 1) {
        RCLCPP_ERROR(this->get_logger(),
            "\033[91mInvalid number of sensors!  %d selected (must be no more than %d)\033[0m",
            n_sensors_, MAX_NSENSOR);
    } else {
        RCLCPP_INFO(this->get_logger(), "\033[92mUsing %d sensor/s\033[0m", n_sensors_);
    }

    // 串口设备路径
    port_ = this->declare_parameter("com_port", std::string(""));
    RCLCPP_INFO(this->get_logger(), "Reading from serial COM port: %s", port_.c_str());

    // 串口波特率
    baud_rate_ = this->declare_parameter("baud_rate", 0);
    RCLCPP_INFO(this->get_logger(), "Baud rate: %d Hz", baud_rate_);

    // 校验位: 0=无校验(PARITY_NONE), 1=奇校验(PARITY_ODD), 2=偶校验(PARITY_EVEN)
    parity_ = this->declare_parameter("parity", 0);
    RCLCPP_INFO(this->get_logger(),
        "Parity set to: %d (0=PARITY_NONE, 1=PARITY_ODD, 2=PARITY_EVEN)", parity_);

    // 数据位宽
    byte_size_ = this->declare_parameter("byte_size", 0);
    RCLCPP_INFO(this->get_logger(), "Byte size: %d bits", byte_size_);

    // 缓冲区溢出时是否执行 Flush 清空硬件输入缓冲
    is_flush_ = this->declare_parameter("is_flush", false);
    RCLCPP_INFO(this->get_logger(), "Is Flush: %d", is_flush_);

    // 采样频率 (Hz)
    sampling_rate_ = this->declare_parameter("sampling_rate", 0);
    RCLCPP_INFO(this->get_logger(), "Sampling rate: %d Hz", sampling_rate_);

    RCLCPP_INFO(this->get_logger(), "Loaded parameters.\n");

    // ---------- 2. 创建传感器实例 ----------
    sensors_.resize(n_sensors_);

    RCLCPP_INFO(this->get_logger(), "Creating sensors...\n");
    for (size_t sensor_id = 0; sensor_id < static_cast<size_t>(n_sensors_); sensor_id++) {
        RCLCPP_INFO(this->get_logger(), "Creating sensor %zu...", sensor_id);

        // 创建 PTSDKSensor 对象 (来自 SDK)
        auto sensor = std::make_unique<PTSDKSensor>();

        // 将传感器注册到监听器，监听器负责从串口数据流中解析该传感器的数据
        RCLCPP_INFO(this->get_logger(), "Adding sensor %zu to listener...", sensor_id);
        listener_.addSensor(sensor.get());
        RCLCPP_INFO(this->get_logger(), "Added sensor %zu to listener!\n", sensor_id);

        sensors_[sensor_id] = std::move(sensor);

        // 为每个传感器创建独立的 Publisher
        // 话题名: /hub_<hub_id>/sensor_<sensor_id>
        // QoS: SensorDataQoS (可靠+低延迟，适合传感器数据流)
        std::string topic = "/hub_" + std::to_string(hub_id_) + "/sensor_" + std::to_string(sensor_id);
        sensor_pubs_.push_back(
            this->create_publisher<papillarray_interfaces::msg::SensorState>(
                topic, rclcpp::SensorDataQoS()));
    }

    // ---------- 3. 创建服务 ----------
    RCLCPP_INFO(this->get_logger(), "Starting services...");

    // 启动滑动检测服务
    std::string service_name = "/hub_" + std::to_string(hub_id_) + "/start_slip_detection";
    start_sd_srv_ = this->create_service<papillarray_interfaces::srv::StartSlipDetection>(
        service_name,
        [this]([[maybe_unused]] const std::shared_ptr<papillarray_interfaces::srv::StartSlipDetection::Request> request,
               std::shared_ptr<papillarray_interfaces::srv::StartSlipDetection::Response> response) {
            return startSlipDetectionSrvCallback(request, response);
        });
    RCLCPP_INFO(this->get_logger(), "Started %s service", service_name.c_str());

    // 停止滑动检测服务
    service_name = "/hub_" + std::to_string(hub_id_) + "/stop_slip_detection";
    stop_sd_srv_ = this->create_service<papillarray_interfaces::srv::StopSlipDetection>(
        service_name,
        [this]([[maybe_unused]] const std::shared_ptr<papillarray_interfaces::srv::StopSlipDetection::Request> request,
               std::shared_ptr<papillarray_interfaces::srv::StopSlipDetection::Response> response) {
            return stopSlipDetectionSrvCallback(request, response);
        });
    RCLCPP_INFO(this->get_logger(), "Started %s service", service_name.c_str());

    // 偏置校准服务
    service_name = "/hub_" + std::to_string(hub_id_) + "/send_bias_request";
    send_bias_request_srv_ = this->create_service<papillarray_interfaces::srv::BiasRequest>(
        service_name,
        [this]([[maybe_unused]] const std::shared_ptr<papillarray_interfaces::srv::BiasRequest::Request> request,
               std::shared_ptr<papillarray_interfaces::srv::BiasRequest::Response> response) {
            return sendBiasRequestSrvCallback(request, response);
        });
    RCLCPP_INFO(this->get_logger(), "Started %s service", service_name.c_str());

    // ---------- 4. 连接串口并启动监听 ----------
    RCLCPP_INFO(this->get_logger(), "Connecting to %s port...", port_.c_str());
    if (listener_.connectAndStartListening(port_.c_str(), baud_rate_, parity_, char(byte_size_), is_flush_)) {
        // 连接失败 (返回 true 表示出错)
        RCLCPP_FATAL(this->get_logger(), "\033[91mFailed to connect to port: %s\033[0m", port_.c_str());
        rclcpp::shutdown();
    } else {
        RCLCPP_INFO(this->get_logger(), "\033[92mConnected to port: %s\033[0m", port_.c_str());
    }

    // ---------- 5. 设置采样频率并启动定时器 ----------
    RCLCPP_INFO(this->get_logger(), "Setting sampling rate to %u...", sampling_rate_);
    if (!listener_.setSamplingRate(sampling_rate_)) {
        RCLCPP_WARN(this->get_logger(), "\033[91mFailed to set sampling rate to: %u\033[0m", sampling_rate_);
    } else {
        RCLCPP_INFO(this->get_logger(), "\033[92mSampling rate set to %u\033[0m", sampling_rate_);
    }

    // 根据采样频率计算定时器周期 (period = 1 / frequency)
    if (sampling_rate_ > 0) {
        auto period = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::duration<double>(1.0 / sampling_rate_));
        // 创建 WallTimer，按固定周期触发 updateData()
        update_timer_ = this->create_wall_timer(period, [this]() {
            updateData();
        });
    } else {
        RCLCPP_ERROR(this->get_logger(), "\033[91mInvalid sampling rate: %d\033[0m", sampling_rate_);
    }
}

// ============================================================
// updateData() — 定时采样回调
//
// 每个采样周期执行一次:
//   1. 遍历所有传感器
//   2. 从 PTSDKSensor 读取: 全局力/力矩、各 pillar 的位移/力、接触/滑动状态
//   3. 填充 SensorState 消息并发布到对应 Topic
// ============================================================
void PapillArrayNode::updateData() {
    if (n_sensors_ == 0) {
        return;
    }

    for (size_t sensor_id = 0; sensor_id < sensors_.size(); sensor_id++) {
        // 创建 SensorState 消息 (用 shared_ptr 管理，发布时零拷贝)
        auto ss_msg = std::make_shared<papillarray_interfaces::msg::SensorState>();

        // ---- 消息头 ----
        ss_msg->header.stamp = this->now();  // ROS 时间戳
        ss_msg->header.frame_id = "hub_" + std::to_string(hub_id_)
            + "/sensor_" + std::to_string(sensor_id);  // 坐标系标识

        // 传感器内部时间戳 (微秒)
        long timestamp_us = sensors_[sensor_id]->getTimestamp_us();
        ss_msg->tus = timestamp_us;

        // ---- 全局力 (所有 pillar 的合力) ----
        double globalForce[NDIM];
        sensors_[sensor_id]->getGlobalForce(globalForce);
        ss_msg->gfx = static_cast<float>(globalForce[X_IND]);
        ss_msg->gfy = static_cast<float>(globalForce[Y_IND]);
        ss_msg->gfz = static_cast<float>(globalForce[Z_IND]);

        // ---- 全局力矩 ----
        double globalTorque[NDIM];
        sensors_[sensor_id]->getGlobalTorque(globalTorque);
        ss_msg->gtx = static_cast<float>(globalTorque[X_IND]);
        ss_msg->gty = static_cast<float>(globalTorque[Y_IND]);
        ss_msg->gtz = static_cast<float>(globalTorque[Z_IND]);

        // ---- 摩擦与抓取 ----
        ss_msg->friction_est = static_cast<float>(sensors_[sensor_id]->getFrictionEstimate());
        ss_msg->target_grip_force = static_cast<float>(sensors_[sensor_id]->getTargetGripForce());

        // ---- 各 pillar 的状态 ----
        int n_pillar = sensors_[sensor_id]->getNPillar();  // 该传感器实际的 pillar 数量

        bool is_sd_active;    // 滑动检测是否激活
        bool is_ref_loaded;   // 参考载荷是否已加载
        std::array<bool, MAX_NPILLAR> contact_states{};    // 各 pillar 的接触状态
        std::array<int, MAX_NPILLAR> slip_states{};        // 各 pillar 的滑动状态

        // 一次性获取所有 pillar 的接触和滑动状态
        sensors_[sensor_id]->getAllSlipStatus(
            &is_sd_active,
            &is_ref_loaded,
            contact_states.data(),
            slip_states.data());

        ss_msg->is_sd_active = is_sd_active;
        ss_msg->is_ref_loaded = is_ref_loaded;
        ss_msg->is_contact = false;  // 初始化为 false，下面任一 pillar 接触则置 true

        // 遍历每个 pillar，填充 PillarState
        for (int pillar_id = 0; pillar_id < n_pillar; pillar_id++) {
            auto ps_msg = papillarray_interfaces::msg::PillarState();

            ps_msg.id = pillar_id;

            // 滑动与接触状态 (来自 getAllSlipStatus 批量获取的结果)
            ps_msg.slip_state = slip_states[pillar_id];
            ps_msg.in_contact = contact_states[pillar_id];

            // 任一 pillar 接触，则传感器整体标记为接触中
            ss_msg->is_contact = ss_msg->is_contact | ps_msg.in_contact;

            // 读取该 pillar 的三维位移 (mm)
            double pillar_d[NDIM];
            sensors_[sensor_id]->getPillarDisplacements(pillar_id, pillar_d);
            ps_msg.dx = static_cast<float>(pillar_d[X_IND]);
            ps_msg.dy = static_cast<float>(pillar_d[Y_IND]);
            ps_msg.dz = static_cast<float>(pillar_d[Z_IND]);

            // 读取该 pillar 的三维力 (N)
            double pillar_f[NDIM];
            sensors_[sensor_id]->getPillarForces(pillar_id, pillar_f);
            ps_msg.fx = static_cast<float>(pillar_f[X_IND]);
            ps_msg.fy = static_cast<float>(pillar_f[Y_IND]);
            ps_msg.fz = static_cast<float>(pillar_f[Z_IND]);

            // 将 pillar 状态添加到消息的 pillars 数组
            ss_msg->pillars.push_back(ps_msg);
        }

        // 发布 SensorState 消息
        sensor_pubs_[sensor_id]->publish(*ss_msg);
    }
}

// ============================================================
// startSlipDetectionSrvCallback — 启动滑动检测服务回调
//
// 调用 listener_.startSlipDetection() 激活传感器内置滑动检测算法。
// 激活后各 pillar 的 slip_state 将动态更新:
//   CONTACT_AT_START → TLOADING (切向加载) → SLIPPED (滑动发生)
// ============================================================
bool PapillArrayNode::startSlipDetectionSrvCallback(
    [[maybe_unused]] const std::shared_ptr<papillarray_interfaces::srv::StartSlipDetection::Request> req,
    std::shared_ptr<papillarray_interfaces::srv::StartSlipDetection::Response> resp) {
    RCLCPP_INFO(this->get_logger(), "startSlipDetection callback");
    resp->result = listener_.startSlipDetection();
    return resp->result;
}

// ============================================================
// stopSlipDetectionSrvCallback — 停止滑动检测服务回调
//
// 调用 listener_.stopSlipDetection() 关闭滑动检测算法。
// 停止后摩擦系数估计和目标抓取力也停止更新。
// ============================================================
bool PapillArrayNode::stopSlipDetectionSrvCallback(
    [[maybe_unused]] const std::shared_ptr<papillarray_interfaces::srv::StopSlipDetection::Request> req,
    std::shared_ptr<papillarray_interfaces::srv::StopSlipDetection::Response> resp) {
    RCLCPP_INFO(this->get_logger(), "stopSlipDetection callback");
    resp->result = listener_.stopSlipDetection();
    return resp->result;
}

// ============================================================
// sendBiasRequestSrvCallback — 偏置校准服务回调
//
// 调用 listener_.sendBiasRequest() 向传感器发送零位校准指令。
// 应在传感器无负载状态下调用，以消除零点漂移。
// ============================================================
bool PapillArrayNode::sendBiasRequestSrvCallback(
    [[maybe_unused]] const std::shared_ptr<papillarray_interfaces::srv::BiasRequest::Request> req,
    std::shared_ptr<papillarray_interfaces::srv::BiasRequest::Response> resp) {
    RCLCPP_INFO(this->get_logger(), "sendBiasRequest callback");
    resp->result = listener_.sendBiasRequest();
    return resp->result;
}

// ============================================================
// main — 程序入口
//
// 创建 PapillArrayNode 实例并进入 ROS 2 事件循环 (spin)。
// 在 spin 过程中，定时器自动触发 updateData() 发布数据，
// 服务回调异步处理外部请求。
// ============================================================
int main(int argc, char *argv[]) {
    rclcpp::init(argc, argv);

    auto node = std::make_shared<PapillArrayNode>(rclcpp::NodeOptions());
    rclcpp::spin(node);   // 阻塞直到节点被关闭 (Ctrl+C 或 rclcpp::shutdown)

    rclcpp::shutdown();
    return 0;
}
