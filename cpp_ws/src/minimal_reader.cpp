// minimal_reader.cpp
// Contactile PTS 最简 C++ 读取示例
// 基于原厂 SDK，单传感器、单线程、打印 XYZ 全局力

// 兼容性修复头文件，必须在所有 vendor 头文件之前包含
#include "ptsdk_compat.h"

#include <PTSDKConstants.h>
#include <PTSDKListener.h>
// 注意：PTSDKListener.h 内部已包含 PTSDKSensor.h，且该头文件的 include guard 有 bug，
// 若再次显式包含会导致类重复定义。因此此处不再 #include <PTSDKSensor.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <thread>

int main(int argc, char* argv[]) {
    (void)argc;
    (void)argv;

    const char* port = "/dev/ttyACM0";
    const int baudRate = 9600;
    const int parity = 0;
    const char byteSize = 8;
    const bool isFlush = true;

    // 初始化传感器和监听器
    PTSDKSensor sen0;
    PTSDKListener listener(/* isLogging */ false);
    listener.addSensor(&sen0);  // 必须传指针

    // 连接串口并开始监听
    int res = listener.connectAndStartListening(port, baudRate, parity, byteSize, isFlush);
    if (res != 0) {
        fprintf(stderr, "错误: 无法连接到 %s，请检查硬件连接和权限\n", port);
        return 1;
    }
    printf("已连接到 %s\n", port);

    // 发送 Bias 请求（确保传感器无负载）
    res = listener.sendBiasRequest();
    if (!res) {
        fprintf(stderr, "错误: Bias 请求失败\n");
        listener.stopListeningAndDisconnect();
        return 1;
    }
    printf("Bias 完成，开始读取数据...\n");

    // 设置采样率 500 Hz
    listener.setSamplingRate(SAMP_RATE_500);

    // 读取 100 个样本后退出
    printf("%-8s %-12s %-12s %-12s\n", "Sample", "Fx (N)", "Fy (N)", "Fz (N)");
    double globalForce[NDIM];
    for (int i = 0; i < 100; ++i) {
        std::this_thread::sleep_for(std::chrono::milliseconds(2));

        // getGlobalForce 需要传入 double[NDIM] 数组，不会返回值
        sen0.getGlobalForce(globalForce);
        double fx = globalForce[X_IND];
        double fy = globalForce[Y_IND];
        double fz = globalForce[Z_IND];

        printf("%-8d %-12.4f %-12.4f %-12.4f\n", i + 1, fx, fy, fz);
    }

    // 断开连接
    listener.stopListeningAndDisconnect();
    printf("已断开连接\n");

    return 0;
}
