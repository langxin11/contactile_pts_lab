#ifndef PAPILLARRAY_ROS2_V2_CSV_LOGGER_HPP_
#define PAPILLARRAY_ROS2_V2_CSV_LOGGER_HPP_

#include <cstddef>
#include <filesystem>
#include <fstream>
#include <string>

#include "papillarray_interfaces/msg/sensor_state.hpp"

class CsvLogger {
public:
  CsvLogger() = default;
  ~CsvLogger();

  CsvLogger(const CsvLogger &) = delete;
  CsvLogger &operator=(const CsvLogger &) = delete;

  bool open(const std::filesystem::path &log_dir, int hub_id,
            std::size_t max_pillars, bool include_pillar_detail,
            std::string *error_message);
  bool write(std::size_t sensor_id,
             const papillarray_interfaces::msg::SensorState &message,
             std::string *error_message);
  void close();

  bool isOpen() const;
  const std::filesystem::path &filePath() const;

private:
  void writeHeader();

  static constexpr std::size_t FLUSH_INTERVAL_ROWS = 500;

  std::ofstream file_;
  std::filesystem::path file_path_;
  std::size_t max_pillars_ = 0;
  std::size_t rows_since_flush_ = 0;
  bool include_pillar_detail_ = false;
};

#endif // PAPILLARRAY_ROS2_V2_CSV_LOGGER_HPP_
