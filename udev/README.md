# udev 规则安装说明

## 什么是 udev 规则？

`udev` 是 Linux 系统中负责**管理硬件热插拔**的子系统。当你插入 U 盘、鼠标、串口等设备时，udev 会自动检测到它们，并决定：

- 设备文件叫什么名字（如 `/dev/ttyACM0`）
- 谁有权限读写它
- 是否创建固定的软链接（别名）

**udev 规则就是一条条“如果检测到某个硬件，就自动执行某些操作”的指令。**

### 为什么要安装？

| 场景 | 没有 udev 规则 | 有 udev 规则 |
|------|---------------|-------------|
| 设备名 | 每次插拔可能变（`ttyACM0` → `ttyACM1`） | 可创建固定软链接，代码里写死名字 |
| 权限 | 可能需要 `sudo` 才能访问串口 | 自动归属 `dialout` 组，普通用户直接用 |
| 多设备 | 分不清哪个串口对应哪个传感器 | 可按端口/序列号分配固定名称 |

> **一句话：udev 规则让传感器每次插上都有固定的名字和正确的权限，不用手动改。**

---

## 安装步骤

```bash
# 1. 复制规则文件到系统目录
sudo cp udev/99-contactile-pts.rules /etc/udev/rules.d/

# 2. 重新加载 udev 规则
sudo udevadm control --reload-rules
sudo udevadm trigger

# 3. 确认用户已在 dialout 组
sudo usermod -aG dialout $USER

# 4. 注销并重新登录（或重启）使权限生效
```

## 验证

插入设备后执行：

```bash
ls -la /dev/ttyACM*
# 期望输出: crw-rw---- 1 root dialout ... /dev/ttyACM0
```

如果看到 `dialout` 组且有读写权限，说明规则生效。
