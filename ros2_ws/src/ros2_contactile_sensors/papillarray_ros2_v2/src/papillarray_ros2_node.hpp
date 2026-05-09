#ifndef PAPILLARRAY_ROS2_V2_NODE_H_
#define PAPILLARRAY_ROS2_V2_NODE_H_

#include <stdio.h>
#include <memory>
#include <vector>
#include <string>
#include <chrono>


#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/header.hpp"

// Messages
#include "sensor_interfaces/msg/pillar_state.hpp"
#include "sensor_interfaces/msg/sensor_state.hpp"

// Services
#include "sensor_interfaces/srv/bias_request.hpp"
#include "sensor_interfaces/srv/start_slip_detection.hpp"
#include "sensor_interfaces/srv/stop_slip_detection.hpp"

// Workaround for GCC 13 + C++17: std::byte conflicts with BYTE macro
// PTSDKParser.h and PTSDKListener.h now use #define BYTE unsigned char
// Removed: typedef unsigned char byte;

#ifndef PTSDKCONSTANTS_H
#include <PTSDKConstants.h>
#endif
#ifndef PTSDKLISTENER_H
#include <PTSDKListener.h>
#endif
#ifndef PTSDKSENSOR_H
#include <PTSDKSensor.h>
#endif

class PapillArrayNode : public rclcpp::Node {
public:
    // Constructor
    PapillArrayNode(const rclcpp::NodeOptions & options);

    // Destructor
    ~PapillArrayNode() {
        // Stop listening for and processing data and disconnect from the COM port
        listener_.stopListeningAndDisconnect();
    }

    // Update sensor data and publish
    void updateData();

    // Get the sampling rate
    int getSamplingRate(){ return sampling_rate_; };

private:
    int hub_id_;

    int n_sensors_;

    std::string port_;
    int baud_rate_;
    int parity_;
    int byte_size_;
    bool is_flush_;
    int sampling_rate_;

    PTSDKListener listener_;
    std::vector<std::unique_ptr<PTSDKSensor> > sensors_;

    // Sensor publishers
    std::vector<rclcpp::Publisher<sensor_interfaces::msg::SensorState>::SharedPtr> sensor_pubs_;

    // Services
    rclcpp::Service<sensor_interfaces::srv::StartSlipDetection>::SharedPtr start_sd_srv_;
    rclcpp::Service<sensor_interfaces::srv::StopSlipDetection>::SharedPtr stop_sd_srv_;
    rclcpp::Service<sensor_interfaces::srv::BiasRequest>::SharedPtr send_bias_request_srv_;

    // Service callback functions
    bool startSlipDetectionSrvCallback([[maybe_unused]] const std::shared_ptr<sensor_interfaces::srv::StartSlipDetection::Request> request,
                    std::shared_ptr<sensor_interfaces::srv::StartSlipDetection::Response> response);
    bool stopSlipDetectionSrvCallback([[maybe_unused]] const std::shared_ptr<sensor_interfaces::srv::StopSlipDetection::Request> request,
                    std::shared_ptr<sensor_interfaces::srv::StopSlipDetection::Response> response);
    bool sendBiasRequestSrvCallback([[maybe_unused]] const std::shared_ptr<sensor_interfaces::srv::BiasRequest::Request> request,
                    std::shared_ptr<sensor_interfaces::srv::BiasRequest::Response> response);

    // Load parameters from launch file
    void loadParams(const rclcpp::NodeOptions & options);
};

#endif // PAPILLARRAY_ROS2_V2_NODE_H_
