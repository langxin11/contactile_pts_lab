# ============================================================
# PillarState.msg — 单个触点 (Pillar) 的状态消息
#
# PapillArray 传感器表面由多个弹性柱状体 (pillar) 组成，
# 每个 pillar 的形变和受力可被独立测量，用于感知局部接触状态。
# ============================================================

# 触点编号 (从 0 开始)
int64 id

# ---- 三维位移 (mm) ----
float32 dx    # X 方向位移
float32 dy    # Y 方向位移
float32 dz    # Z 方向位移 (法向)

# ---- 三维力 (N) ----
float32 fx    # X 方向力 (切向)
float32 fy    # Y 方向力 (切向)
float32 fz    # Z 方向力 (法向)

# ---- 接触与滑动状态 ----
bool in_contact    # 该触点当前是否与物体接触

# 滑动状态，取值定义于 PTSDKConstants.h:
#    0 = UNKNOWN          数据包未提供滑动状态
#   -2 = INELIGIBLE       滑动检测启动时该 pillar 未处于接触状态
#   -1 = LOST_CONTACT     接触后失去接触
#    1 = CONTACT_AT_START 滑动检测启动时处于接触状态
#    2 = TLOADING         正在承受切向载荷
#    3 = SLIPPED          已发生滑动
int64 slip_state
