#include "csv_logger.hpp"

#include <chrono>
#include <cstdint>
#include <ctime>
#include <iomanip>
#include <limits>
#include <sstream>
#include <system_error>

namespace {

constexpr std::int64_t NANOSECONDS_PER_SECOND = 1000000000LL;

std::string makeLogFileName(int hub_id) {
  const auto now = std::chrono::system_clock::now();
  const auto now_time = std::chrono::system_clock::to_time_t(now);
  const auto milliseconds =
      std::chrono::duration_cast<std::chrono::milliseconds>(
          now.time_since_epoch()) %
      1000;

  std::tm local_time{};
  localtime_r(&now_time, &local_time);

  std::ostringstream name;
  name << "LOG_hub" << hub_id << '_'
       << std::put_time(&local_time, "%Y%m%d_%H%M%S") << '_' << std::setw(3)
       << std::setfill('0') << milliseconds.count() << ".csv";
  return name.str();
}

void setError(std::string *error_message, const std::string &message) {
  if (error_message != nullptr) {
    *error_message = message;
  }
}

} // namespace

CsvLogger::~CsvLogger() { close(); }

bool CsvLogger::open(const std::filesystem::path &log_dir, int hub_id,
                     std::size_t max_pillars, bool include_pillar_detail,
                     std::string *error_message) {
  close();

  if (log_dir.empty()) {
    setError(error_message, "CSV 日志目录不能为空");
    return false;
  }

  std::error_code filesystem_error;
  std::filesystem::create_directories(log_dir, filesystem_error);
  if (filesystem_error) {
    setError(error_message, "无法创建 CSV 日志目录: " + log_dir.string() +
                                ": " + filesystem_error.message());
    return false;
  }

  file_path_ = log_dir / makeLogFileName(hub_id);
  file_.open(file_path_, std::ios::out | std::ios::trunc);
  if (!file_.is_open()) {
    setError(error_message, "无法打开 CSV 日志文件: " + file_path_.string());
    return false;
  }

  // SDK 会生成权限为 000 的日志；这里显式保证当前用户始终能够读写采集结果。
  std::filesystem::permissions(
      file_path_,
      std::filesystem::perms::owner_read | std::filesystem::perms::owner_write,
      std::filesystem::perm_options::replace, filesystem_error);
  if (filesystem_error) {
    setError(error_message, "无法设置 CSV 日志权限: " + file_path_.string() +
                                ": " + filesystem_error.message());
    close();
    return false;
  }

  max_pillars_ = max_pillars;
  include_pillar_detail_ = include_pillar_detail;
  rows_since_flush_ = 0;
  writeHeader();
  if (!file_) {
    setError(error_message, "无法写入 CSV 日志表头: " + file_path_.string());
    close();
    return false;
  }

  return true;
}

bool CsvLogger::write(std::size_t sensor_id,
                      const papillarray_interfaces::msg::SensorState &message,
                      std::string *error_message) {
  if (!file_.is_open()) {
    setError(error_message, "CSV 日志文件未打开");
    return false;
  }

  const std::int64_t ros_time_ns =
      static_cast<std::int64_t>(message.header.stamp.sec) *
          NANOSECONDS_PER_SECOND +
      static_cast<std::int64_t>(message.header.stamp.nanosec);

  file_ << std::setprecision(std::numeric_limits<float>::max_digits10)
        << message.tus << ',' << ros_time_ns << ',' << sensor_id << ','
        << message.gfx << ',' << message.gfy << ',' << message.gfz << ','
        << message.gtx << ',' << message.gty << ',' << message.gtz << ','
        << message.friction_est << ',' << message.target_grip_force << ','
        << message.is_sd_active << ',' << message.is_ref_loaded << ','
        << message.is_contact;

  for (std::size_t pillar_id = 0; pillar_id < max_pillars_; ++pillar_id) {
    if (pillar_id < message.pillars.size()) {
      const auto &pillar = message.pillars[pillar_id];
      file_ << ',' << pillar.in_contact << ',' << pillar.slip_state;
    } else {
      // 不存在的 pillar 使用 UNKNOWN=0，避免与 SDK 的 INELIGIBLE=-2 混淆。
      file_ << ",0,0";
    }
  }

  if (include_pillar_detail_) {
    for (std::size_t pillar_id = 0; pillar_id < max_pillars_; ++pillar_id) {
      if (pillar_id < message.pillars.size()) {
        const auto &pillar = message.pillars[pillar_id];
        file_ << ',' << pillar.dx << ',' << pillar.dy << ',' << pillar.dz << ','
              << pillar.fx << ',' << pillar.fy << ',' << pillar.fz;
      } else {
        file_ << ",,,,,,";
      }
    }
  }

  file_ << '\n';
  ++rows_since_flush_;
  if (rows_since_flush_ >= FLUSH_INTERVAL_ROWS) {
    file_.flush();
    rows_since_flush_ = 0;
  }

  if (!file_) {
    setError(error_message, "写入 CSV 日志失败: " + file_path_.string());
    return false;
  }
  return true;
}

void CsvLogger::close() {
  if (file_.is_open()) {
    file_.flush();
    file_.close();
  }
  rows_since_flush_ = 0;
}

bool CsvLogger::isOpen() const { return file_.is_open(); }

const std::filesystem::path &CsvLogger::filePath() const { return file_path_; }

void CsvLogger::writeHeader() {
  file_ << "t_us,ros_time_ns,sensor_id,gfx_N,gfy_N,gfz_N,gtx_N_mm,gty_N_mm,gtz_"
           "N_mm,"
           "friction_est,target_grip_force_N,is_sd_active,is_ref_loaded,is_"
           "contact";

  for (std::size_t pillar_id = 0; pillar_id < max_pillars_; ++pillar_id) {
    file_ << ",p" << pillar_id << "_in_contact,p" << pillar_id << "_slip_state";
  }

  if (include_pillar_detail_) {
    for (std::size_t pillar_id = 0; pillar_id < max_pillars_; ++pillar_id) {
      file_ << ",p" << pillar_id << "_dx_mm,p" << pillar_id << "_dy_mm,p"
            << pillar_id << "_dz_mm,p" << pillar_id << "_fx_N,p" << pillar_id
            << "_fy_N,p" << pillar_id << "_fz_N";
    }
  }

  file_ << '\n';
}
