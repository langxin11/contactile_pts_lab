// ptsdk_compat.h
// 修复原厂 PTSDK Linux 头文件在 GCC 13 + C++14 下的兼容性问题
// 必须在所有 vendor 头文件之前包含

#ifndef PTSDK_COMPAT_H
#define PTSDK_COMPAT_H

// 原厂代码在 Linux 下使用 #define BYTE byte，但 C++14 没有裸 'byte' 类型
// 这里提供 typedef，使 'byte' 成为合法标识符
typedef unsigned char byte;

#endif // PTSDK_COMPAT_H
