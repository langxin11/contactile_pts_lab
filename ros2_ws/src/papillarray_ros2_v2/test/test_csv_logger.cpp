#include <gtest/gtest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

#include "csv_logger.hpp"

namespace {

class TemporaryDirectory {
public:
  TemporaryDirectory() {
    const auto suffix =
        std::chrono::steady_clock::now().time_since_epoch().count();
    path_ = std::filesystem::temp_directory_path() /
            ("papillarray_csv_logger_test_" + std::to_string(suffix));
  }

  ~TemporaryDirectory() {
    std::error_code cleanup_error;
    std::filesystem::remove_all(path_, cleanup_error);
  }

  const std::filesystem::path &path() const { return path_; }

private:
  std::filesystem::path path_;
};

TEST(CsvLoggerTest, WritesReadableSlipTimeSeries) {
  TemporaryDirectory temporary_directory;
  CsvLogger logger;
  std::string error_message;

  ASSERT_TRUE(
      logger.open(temporary_directory.path(), 2, 3, false, &error_message))
      << error_message;

  papillarray_interfaces::msg::SensorState message;
  message.header.stamp.sec = 12;
  message.header.stamp.nanosec = 345;
  message.tus = 456789;
  message.gfx = 1.25F;
  message.gfy = -2.5F;
  message.gfz = 3.75F;
  message.is_sd_active = true;
  message.is_ref_loaded = true;
  message.is_contact = true;

  papillarray_interfaces::msg::PillarState first_pillar;
  first_pillar.id = 0;
  first_pillar.in_contact = true;
  first_pillar.slip_state = 3;
  message.pillars.push_back(first_pillar);

  ASSERT_TRUE(logger.write(1, message, &error_message)) << error_message;
  const auto log_path = logger.filePath();
  logger.close();

  const auto permissions = std::filesystem::status(log_path).permissions();
  EXPECT_NE(permissions & std::filesystem::perms::owner_read,
            std::filesystem::perms::none);
  EXPECT_NE(permissions & std::filesystem::perms::owner_write,
            std::filesystem::perms::none);

  std::ifstream log_file(log_path);
  ASSERT_TRUE(log_file.is_open());
  std::ostringstream contents;
  contents << log_file.rdbuf();
  const std::string csv = contents.str();

  EXPECT_NE(csv.find("t_us,ros_time_ns,sensor_id"), std::string::npos);
  EXPECT_NE(csv.find("p0_in_contact,p0_slip_state"), std::string::npos);
  EXPECT_EQ(csv.find("p0_dx_mm"), std::string::npos);
  EXPECT_NE(csv.find("456789,12000000345,1,1.25,-2.5,3.75"), std::string::npos);
  EXPECT_NE(csv.find(",1,3,0,0,0,0\n"), std::string::npos);
}

TEST(CsvLoggerTest, AddsPillarDetailOnlyWhenRequested) {
  TemporaryDirectory temporary_directory;
  CsvLogger logger;
  std::string error_message;

  ASSERT_TRUE(
      logger.open(temporary_directory.path(), 0, 1, true, &error_message))
      << error_message;

  papillarray_interfaces::msg::SensorState message;
  papillarray_interfaces::msg::PillarState pillar;
  pillar.dx = 0.1F;
  pillar.dy = 0.2F;
  pillar.dz = 0.3F;
  pillar.fx = 1.0F;
  pillar.fy = 2.0F;
  pillar.fz = 3.0F;
  message.pillars.push_back(pillar);

  ASSERT_TRUE(logger.write(0, message, &error_message)) << error_message;
  const auto log_path = logger.filePath();
  logger.close();

  std::ifstream log_file(log_path);
  ASSERT_TRUE(log_file.is_open());
  std::ostringstream contents;
  contents << log_file.rdbuf();

  EXPECT_NE(contents.str().find("p0_dx_mm,p0_dy_mm,p0_dz_mm"),
            std::string::npos);
  EXPECT_NE(contents.str().find(",0.100000001,0.200000003,0.300000012,1,2,3\n"),
            std::string::npos);
}

} // namespace
