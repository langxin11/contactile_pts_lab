cmake_minimum_required(VERSION 3.16)
project(contactile_pts_cpp)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 添加原厂 SDK 头文件路径
set(VENDOR_INCLUDE_DIR "${CMAKE_SOURCE_DIR}/../vendor/C++LIN/Include")
set(VENDOR_LIB_DIR "${CMAKE_SOURCE_DIR}/../vendor/C++LIN/Library")

include_directories(${VENDOR_INCLUDE_DIR})
link_directories(${VENDOR_LIB_DIR})

# 查找线程库（PTSDK 多线程示例需要）
find_package(Threads REQUIRED)

# 最简读取示例
add_executable(minimal_reader src/minimal_reader.cpp)
target_link_libraries(minimal_reader PTSDK Threads::Threads)
