#!/usr/bin/env python3
"""PapillArray 自研串口 ROS 2 包安装配置。"""

from glob import glob

from setuptools import find_packages, setup

PACKAGE_NAME = "papillarray_serial_driver"

setup(
    name=PACKAGE_NAME,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE_NAME}"]),
        (f"share/{PACKAGE_NAME}", ["package.xml", "README_zh.md"]),
        (f"share/{PACKAGE_NAME}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["numpy", "pyserial", "setuptools"],
    tests_require=["pytest"],
    zip_safe=True,
    maintainer="langxin11",
    maintainer_email="2658327508@qq.com",
    description="通过纯 Python PTS 串口协议发布 PapillArray ROS 2 消息",
    license="Proprietary",
    entry_points={
        "console_scripts": [
            "papillarray_serial_node = papillarray_serial_driver.serial_node:main",
        ],
    },
)
