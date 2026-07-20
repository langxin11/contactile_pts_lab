# ============================================================
# SensorState.msg — 传感器完整状态消息
#
# 包含单个 PapillArray 传感器在某一时刻的全部数据：
#   时间戳、所有 pillar 的局部状态、全局合力/力矩、摩擦估计等。
# 驱动节点以固定频率（默认 500 Hz）发布此消息。
# ============================================================

# 标准 ROS 消息头 (含时间戳与坐标系 frame_id)
std_msgs/Header header

# 传感器内部时间戳 (微秒)
int64 tus

# 所有触点的状态数组 (每个 pillar 一个 PillarState)
PillarState[] pillars

# ---- 全局合力 (N)，所有 pillar 受力的矢量和 ----
float32 gfx   # X 方向合力
float32 gfy   # Y 方向合力
float32 gfz   # Z 方向合力 (法向合力)

# ---- 全局合力矩 (N·mm) ----
float32 gtx   # X 方向力矩
float32 gty   # Y 方向力矩
float32 gtz   # Z 方向力矩

# ---- 摩擦与抓取 ----
float32 friction_est       # 摩擦系数估计值 (当前无合理估计时为 -1)
float32 target_grip_force  # 目标抓取力 (当前无合理值时也为 -1)

# ---- 滑动检测状态 ----
bool is_sd_active   # 滑动检测功能是否已激活
bool is_ref_loaded  # 参考载荷是否已加载 (滑动检测以此为基准)
bool is_contact     # 传感器整体是否与物体接触 (任一 pillar 接触即为 true)
