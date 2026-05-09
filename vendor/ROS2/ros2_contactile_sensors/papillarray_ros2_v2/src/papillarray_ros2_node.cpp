#include "papillarray_ros2_node.hpp"

PapillArrayNode::PapillArrayNode([[maybe_unused]] const rclcpp::NodeOptions &options) : Node("papillarray_ros2_v2_node"), listener_(true) {
	// listener_ argument: isLogging to .csv file; Log file written to /home/.ros/Logs

	RCLCPP_INFO(this->get_logger(), "Loading parameters...\n");
    hub_id_ = this->declare_parameter("hub_id", 0);
    RCLCPP_INFO(this->get_logger(), "Hub id: %d", hub_id_);

    n_sensors_ = this->declare_parameter("n_sensors", 0);
    if (n_sensors_ > MAX_NSENSOR || n_sensors_ < 1) {
        RCLCPP_ERROR(this->get_logger(), "\033[91mInvalid number of sensors!  %d selected (must be no more than %d)\033[0m", n_sensors_, MAX_NSENSOR);
    } else {
        RCLCPP_INFO(this->get_logger(), "\033[92mUsing %d sensor/s\033[0m", n_sensors_);
    }

    port_ = this->declare_parameter("com_port", std::string(""));
    RCLCPP_INFO(this->get_logger(), "Reading from serial COM port: %s", port_.c_str());

    baud_rate_ = this->declare_parameter("baud_rate", 0);
    RCLCPP_INFO(this->get_logger(), "Baud rate: %d Hz", baud_rate_);

    parity_ = this->declare_parameter("parity", 0);
    RCLCPP_INFO(this->get_logger(), "Parity set to: %d (0=PARITY_NONE, 1=PARITY_ODD, 2=PARITY_EVEN)", parity_);

    byte_size_ = this->declare_parameter("byte_size", 0);
    RCLCPP_INFO(this->get_logger(), "Byte size: %d bits", byte_size_);

    is_flush_ = this->declare_parameter("is_flush", false);
    RCLCPP_INFO(this->get_logger(), "Is Flush: %d", is_flush_);

    sampling_rate_ = this->declare_parameter("sampling_rate", 0);
    RCLCPP_INFO(this->get_logger(), "Sampling rate: %d Hz", sampling_rate_);

    RCLCPP_INFO(this->get_logger(), "Loaded parameters.\n");

	// Resize sensors_ to the required size
    sensors_.resize(n_sensors_);

    // Create sensors and add to listener
    RCLCPP_INFO(this->get_logger(), "Creating sensors...\n");

    for (size_t sensor_id = 0; sensor_id < static_cast<size_t>(n_sensors_); sensor_id++) {
        RCLCPP_INFO(this->get_logger(), "Creating sensor %zu...", sensor_id);
        auto sensor = std::make_unique<PTSDKSensor>();
        RCLCPP_INFO(this->get_logger(), "Adding sensor %zu to listener...", sensor_id);
        listener_.addSensor(sensor.get());
        RCLCPP_INFO(this->get_logger(), "Added sensor %zu to listener!\n", sensor_id);
        sensors_[sensor_id] = std::move(sensor);

        // Setup publisher for sensor
        std::string topic = "/hub_" + std::to_string(hub_id_) + "/sensor_" + std::to_string(sensor_id);
        sensor_pubs_.push_back(this->create_publisher<sensor_interfaces::msg::SensorState>(topic, sampling_rate_));
    }

	// Start services
	RCLCPP_INFO(this->get_logger(), "Starting services...");
	std::string service_name = "/hub_" + std::to_string(hub_id_) + "/start_slip_detection";
	start_sd_srv_ = this->create_service<sensor_interfaces::srv::StartSlipDetection>(service_name, 
		[this]([[maybe_unused]] const std::shared_ptr<sensor_interfaces::srv::StartSlipDetection::Request> request, 
			std::shared_ptr<sensor_interfaces::srv::StartSlipDetection::Response> response) {
			return startSlipDetectionSrvCallback(request, response);
		});
	RCLCPP_INFO(this->get_logger(), "Started %s service", service_name.c_str());

	service_name = "/hub_" + std::to_string(hub_id_) + "/stop_slip_detection";
	stop_sd_srv_ = this->create_service<sensor_interfaces::srv::StopSlipDetection>(service_name, 
		[this]([[maybe_unused]] const std::shared_ptr<sensor_interfaces::srv::StopSlipDetection::Request> request, 
			std::shared_ptr<sensor_interfaces::srv::StopSlipDetection::Response> response) {
			return stopSlipDetectionSrvCallback(request, response);
		});
	RCLCPP_INFO(this->get_logger(), "Started %s service", service_name.c_str());

	service_name = "/hub_" + std::to_string(hub_id_) + "/send_bias_request";
	send_bias_request_srv_ = this->create_service<sensor_interfaces::srv::BiasRequest>(service_name, 
		[this]([[maybe_unused]] const std::shared_ptr<sensor_interfaces::srv::BiasRequest::Request> request, 
			std::shared_ptr<sensor_interfaces::srv::BiasRequest::Response> response) {
			return sendBiasRequestSrvCallback(request, response);
		});
	RCLCPP_INFO(this->get_logger(), "Started %s service", service_name.c_str());

	// Start listener
	RCLCPP_INFO(this->get_logger(), "Connecting to %s port...", port_.c_str());
	if (listener_.connectAndStartListening(port_.c_str(), baud_rate_, parity_, char(byte_size_), is_flush_)) {
		RCLCPP_FATAL(this->get_logger(), "\033[91mFailed to connect to port: %s\033[0m", port_.c_str());
		rclcpp::shutdown();
	} else {
		RCLCPP_INFO(this->get_logger(), "\033[92mConnected to port: %s\033[0m", port_.c_str());
	}

	// Set sampling rate
	RCLCPP_INFO(this->get_logger(), "Setting sampling rate to %u...", sampling_rate_);
	if (!listener_.setSamplingRate(sampling_rate_)) {
		RCLCPP_WARN(this->get_logger(), "\033[91mFailed to set sampling rate to: %u\033[0m", sampling_rate_);
	} else {
		RCLCPP_INFO(this->get_logger(), "\033[92mSampling rate set to %u\033[0m", sampling_rate_);
	}
}


void PapillArrayNode::updateData() {
	if (n_sensors_ == 0) {
		return;
	}

	for (size_t sensor_id = 0; sensor_id < sensors_.size(); sensor_id++) {
		auto ss_msg = std::make_shared<sensor_interfaces::msg::SensorState>();

		// RCLCPP_INFO(this->get_logger(), "N pillars: %d", sensors_[sensor_id]->getNPillar());
		auto h = std_msgs::msg::Header();
		auto time = this->now();
		h.stamp.sec = time.seconds();
		h.stamp.nanosec = time.nanoseconds();
		// ss_msg->header = h;

		long timestamp_us = sensors_[sensor_id]->getTimestamp_us();
		ss_msg->tus = timestamp_us;

		double globalForce[NDIM];
		double globalTorque[NDIM];

		// Read global forces
		sensors_[sensor_id]->getGlobalForce(globalForce);
		ss_msg->gfx = static_cast<float>(globalForce[X_IND]);
		ss_msg->gfy = static_cast<float>(globalForce[Y_IND]);
		ss_msg->gfz = static_cast<float>(globalForce[Z_IND]);
		// Read global torques
		sensors_[sensor_id]->getGlobalTorque(globalTorque);
		ss_msg->gtx = static_cast<float>(globalTorque[X_IND]);
		ss_msg->gty = static_cast<float>(globalTorque[Y_IND]);
		ss_msg->gtz = static_cast<float>(globalTorque[Z_IND]);

		// Friction estimate
		ss_msg->friction_est = static_cast<float>(sensors_[sensor_id]->getFrictionEstimate());

		// Target grip force (-1 if no friction estimate)
		ss_msg->target_grip_force = static_cast<float>(sensors_[sensor_id]->getTargetGripForce());

		int n_pillar = sensors_[sensor_id]->getNPillar();

		bool is_sd_active;
		bool is_ref_loaded;
		bool contact_states[n_pillar];
		int slip_states[n_pillar];

		sensors_[sensor_id]->getAllSlipStatus(&is_sd_active,
								&is_ref_loaded,
								contact_states,
								slip_states);

		ss_msg->is_sd_active = is_sd_active;
		ss_msg->is_ref_loaded = is_ref_loaded;
		ss_msg->is_contact = false;

		// Get PillarState data for all pillars in sensor array
		for (int pillar_id = 0; pillar_id < n_pillar; pillar_id++) {
			auto ps_msg = sensor_interfaces::msg::PillarState();

			ps_msg.id = pillar_id;
			ps_msg.slip_state = slip_states[pillar_id];
			ps_msg.in_contact = contact_states[pillar_id];

			ss_msg->is_contact = ss_msg->is_contact | ps_msg.in_contact;

			double pillar_d[NDIM];
			sensors_[sensor_id]->getPillarDisplacements(pillar_id, pillar_d);
			ps_msg.dx = static_cast<float>(pillar_d[X_IND]);
			ps_msg.dy = static_cast<float>(pillar_d[Y_IND]);
			ps_msg.dz = static_cast<float>(pillar_d[Z_IND]);

			double pillar_f[NDIM];
			sensors_[sensor_id]->getPillarForces(pillar_id, pillar_f);
			ps_msg.fx = static_cast<float>(pillar_f[X_IND]);
			ps_msg.fy = static_cast<float>(pillar_f[Y_IND]);
			ps_msg.fz = static_cast<float>(pillar_f[Z_IND]);

			ss_msg->pillars.push_back(ps_msg);

			if(pillar_id == 0){
				// RCLCPP_INFO(this->get_logger(), "From C++API: %.2f; From ROS: %.2f\n",pillar_f[2], ps_msg.fZ);
			}
		}

		// Publish SensorState message
		sensor_pubs_[sensor_id]->publish(*ss_msg);
	}
}

bool PapillArrayNode::startSlipDetectionSrvCallback([[maybe_unused]] const std::shared_ptr<sensor_interfaces::srv::StartSlipDetection::Request> req,
                        std::shared_ptr<sensor_interfaces::srv::StartSlipDetection::Response> resp) {
	RCLCPP_INFO(this->get_logger(), "startSlipDetection callback");
	resp->result = listener_.startSlipDetection();
	std::this_thread::sleep_for(std::chrono::milliseconds(100)); // wait
	return resp->result;
}


bool PapillArrayNode::stopSlipDetectionSrvCallback([[maybe_unused]] const std::shared_ptr<sensor_interfaces::srv::StopSlipDetection::Request> req,
                       std::shared_ptr<sensor_interfaces::srv::StopSlipDetection::Response> resp) {
	RCLCPP_INFO(this->get_logger(), "stopSlipDetection callback");
	resp->result = listener_.stopSlipDetection();
	std::this_thread::sleep_for(std::chrono::milliseconds(100)); // wait
	return resp->result;
}

bool PapillArrayNode::sendBiasRequestSrvCallback([[maybe_unused]] const std::shared_ptr<sensor_interfaces::srv::BiasRequest::Request> req,
                     std::shared_ptr<sensor_interfaces::srv::BiasRequest::Response> resp) {
	RCLCPP_INFO(this->get_logger(), "sendBiasRequest callback");
	resp->result = listener_.sendBiasRequest();
	std::this_thread::sleep_for(std::chrono::milliseconds(100)); // wait
	return resp->result;
}


int main(int argc, char *argv[]) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<PapillArrayNode>(rclcpp::NodeOptions());

    rclcpp::Rate loop_rate(node->getSamplingRate());

    while (rclcpp::ok()) {
        rclcpp::spin_some(node);
        loop_rate.sleep();
        node->updateData(); // Update sensor data and publish
    }

    rclcpp::shutdown();

    return 0;
}