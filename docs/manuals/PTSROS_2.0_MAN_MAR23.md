# Contactile

# PapillArray Tactile Sensor ROS (v2.0)

# Installation and Operation Manual

Document #: PTSROS_2.0_MAN_MAR23

March, 2023

# Foreword

Information contained in this document is the property of Contactile Pty Ltd. and shall not be reproduced in whole or in part without prior written approval of Contactile Pty Ltd. The information herein is subject to change without notice and should not be construed as a commitment on Contactile Pty Ltd. This manual is periodically revised to reflect and incorporate changes made to the PapillArray Tactile Sensor Development Kit.

Contactile Pty Ltd assumes no responsibility for any errors or omissions in this document. Users' critical evaluation is welcome to assist in the preparation of future documentation.

Copyright © by Contactile Pty Ltd, Sydney, Australia. All Rights Reserved.

Published in Australia.

All trademarks belong to their respective owners.

# Conditions of Sale

Contactile's conditions of sale apply to all products sold by Contactile to the Distributor under this Agreement. The conditions of sale that apply are provided on the USB flash drive shipped with the product in the folder ‘LEGAL’ in the root directory.

# End User Licence Agreement

Contactile's end user license agreement applies to all software and algorithms included with the products sold by Contactile. The end user license agreement that applies is provided on the USB flash drive shipped with the product in the folder ‘LEGAL’ in the root directory.

# Compliance

The devices are sold as is.

The devices are specifically designed solely for the purposes of research and development only made available on a business-to-business basis.

The devices are not for resale.

# Table of Contents

1 Introduction.. 4

2 Safety .. . 5

2.1 General.. 5

2.2 Explanation of warnings .. 5

2.3 Precautions.. 5

3 Getting started . . 6

3.1 Hardware installation.. . 6

3.2 Minimum requirements.. . 6

3.3 End user licence agreement licence.. . 6

3.4 ROS node location..

4 Package summary . . 8

5 Installing the package . . 8

6 Starting the node . . 8

7 papillarray_ros_node . . 9

7.1 Parameters . 9

7.2 Subscribed topics.. 9

7.3 Messages . 9

7.4 Services.. . 10

7.5 Log file .. . 11

# 1 Introduction

The PapillArray Tactile Sensor Development Kit (v2.0) is a system of (up to) two PapillArray Tactile Sensor arrays and a Controller. Each PapillArray Tactile Sensor array can measure 3D displacement, 3D force, and vibration on each sensing element, as well as global 3D force, global 3D torque, the onset of slip, and friction. The Controller supplies power for (up to) two sensors and coordinates the simultaneous data acquisition from up to two PapillArray Tactile Sensors; i.e., coordinates sampling of the 9 pillars if one sensor is connected to the Controller, 18 pillars if two sensors are connected to the Controller. The Development Kit is shipped with visualisation software and (optional) C++ libraries for Windows and Linux environments and a ROS node for developing software control algorithms using the sensor signals.

The main components of the PapillArray Tactile Sensor Development Kit (v2.0) are shown in Figure 1.1, connected to a laptop running the visualisation software.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/f976ac3a-9f08-46fb-9eda-07c19b054da0/13f7a8205c8c2714a81ccc692c27f61e0f99bff787ed4bd90cc9a668f4f967e2.jpg)



Figure 1.1 – The PapillArray Tactile Sensor Development Kit (v2.0). Laptop not included.


This document is an installation and operation manual for the ROS Node which was provided on the Contactile USB flash drive that was shipped with the Development Kit.

# 2 Safety

# 2.1 General

The customer should verify that the maximum loads and moments expected during operation fall within the sensing range of the sensor as outside this range, sensor reading accuracy is not guaranteed (refer to Document #PTS_2.0_SPEC_DEC21). Particular attention should be paid to dynamic loads caused by robot acceleration and deceleration if the sensors are mounted on robotic equipment. These forces can be many multiples of the value of static forces in high acceleration or deceleration situations.

# 2.2 Explanation of warnings

The warnings included here are specific to the product(s) covered by this manual. It is expected that the user heed all warnings from the manufacturers of other components used in the installation.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/f976ac3a-9f08-46fb-9eda-07c19b054da0/4791d24832a10b2fbff5cba88cc6906ae48f14a769a0ca427be284b59cdb7ecb.jpg)


Danger indicates that a situation could result in potentially serious injury or damage to equipment.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/f976ac3a-9f08-46fb-9eda-07c19b054da0/a556b9c50a325cfcd2ab8bb555a328d9a0e93f6daa24619a902dd5302ceee82a.jpg)


Caution indicates that a situation could result in damage to the product and/or the other system components.

# 2.3 Precautions

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/f976ac3a-9f08-46fb-9eda-07c19b054da0/48bf45e60645cc1d73c17a2957bd3c3e60840a55a87645825fb499c49ddd02f9.jpg)


DANGER: Do not attempt to disassemble the sensor. This could damage the sensor and will invalidate the calibration.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/f976ac3a-9f08-46fb-9eda-07c19b054da0/02fb1fc9d97083111a6ccf7bcce17313eaaa85accda688dd4a31bd298fec6e37.jpg)


DANGER: Do not attempt to drill, tap, machine, or otherwise modify the sensor casing. This could damage the sensor and will void invalidated the calibration.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/f976ac3a-9f08-46fb-9eda-07c19b054da0/49311a8ef629cef27787dfb502c14f34d49d0b77f1d282c36378276718c63743.jpg)


DANGER: Do not use the sensor on abrasive surfaces or surfaces with sharp points/edges. This could damage the silicone surface of the sensor.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/f976ac3a-9f08-46fb-9eda-07c19b054da0/73316c7fa723eb46c1fbf5d3c5c69309c3afd7719564548dc4e98eec565cfae7.jpg)


CAUTION: Sensors may exhibit a small offset in readings when exposed to intense light sources.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/f976ac3a-9f08-46fb-9eda-07c19b054da0/7bf16ee753baac02fb620fba2c636c77be68a32314f293dc9b7bf11d781f311d.jpg)


CAUTION: Exceptionally strong and changing electromagnetic fields, such as those produced by magnetic resonance imaging (MRI) machines, constitute a possible source of interference with the operation of the sensor and Controller.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/f976ac3a-9f08-46fb-9eda-07c19b054da0/0b643bcddcfa0e3634458d3ebb224fc87042e4d09cd29c61d508a69f305cbc34.jpg)


CAUTION: Temperature variations can cause drift in sensor readings. Some temperature compensation is performed. However, bias removal in software prior to operation is necessary, and it is recommended that biasing is performed each time the sensor is known to be unloaded.

# 3 Getting started

This section contains instructions for setting up and using PapillArray Tactile Sensor Development Kit (v2.0) ROS node. It is recommended that first time users first read the preceding Safety section, then read through this section to get more familiar with the system.

# 3.1 Hardware installation

The ROS node is used with the PapillArray Tactile Sensor Development Kit (v2.0). The Controller should be connected to the PapillArray Tactile Sensors, then the Controller should be connected to a PC running LINUX via the micro USB port on the Controller before you can use the ROS node. For more information about connecting the sensors and powering on the Controller, refer to Document #PTSDK_2.0_MAN_DEC21.

# 3.2 Minimum requirements

The ROS node has been tested on a HP EliteBook with the following specifications

CPU: Intel Core i7 -4600U

▪ RAM: 16 GB RAM

Operating System: Ubuntu 20.04.2.0 LTS

▪ ROS installation: noetic

# 3.3 End user licence agreement licence

Contactile's end user license agreement applies to all software and algorithms included with the products sold by Contactile. The end user license agreement that applies is provided on the USB flash drive shipped with the product in the folder ‘LEGAL’ in the root directory.

# 3.4 ROS node location

The ROS node is provided on the Contactile USB flash drive that was shipped with the development kit in the folder named SOFTWARE/ROS. The ROS node is the papillarray_ros_v2 subfolder. The files in the ROS/papillarray_ros_v2 folder are summarised in Table 3.1.


Table 3.1 – Files in ROS/papillarray_ros_v2 folder


<table><tr><td>Sub Folder</td><td>File Name</td><td>File Description</td></tr><tr><td>.</td><td>CMakeLists.txt</td><td>Directives and instructions describing the project&#x27;s source files and targets</td></tr><tr><td>.</td><td>package.xml</td><td>The package manifest</td></tr><tr><td>.</td><td>README.md</td><td>Readme file</td></tr><tr><td>include</td><td>papillarray_ros_node.hpp</td><td>The header file for the node</td></tr><tr><td>launch</td><td>papillarray.launch</td><td>A launch file</td></tr><tr><td>lib</td><td>libPTSDK.aPTSDKListener.hPTSDKParser.hPTSDKSensor.hPTSDKPillar.hPTSDKConstants.h</td><td>The C++ library and associated header files</td></tr><tr><td>msg</td><td>PillarState.msgSensorState.msg</td><td>Message definitions of the PillarState and SensorState messages</td></tr><tr><td>src</td><td>papillarray_ros_node.cpp</td><td>The cpp file for the node</td></tr><tr><td>srv</td><td>BiasRequest.srvStartSlipDetection.srvStopSlipDetection.srv</td><td>Service definitions of the BiasRequest, StartSlipDetection and StopSlipDetection services</td></tr></table>

# 4 Package summary

This package implements a driver for the PapillArray Tactile Sensor Array Development Kit (v2.0).

Maintainer status: maintained

Maintainer: Heba Khamis (Contactile) <heba DOT khamis AT contractile DOT com>

Author: Heba Khamis

License: LGPLv3

The papilllarray_ros_v2 package provides a ROS interface that publishes data from two PapillArray Tactile Sensor arrays connected to a Controller that is connected over USB. The package allows the following:

1. Connecting to the controller, sampling the sensors at 100, 250, 500 or 1000 Hz and publishing the data

2. Biasing the sensors

3. Starting and stopping slip detection on the Controller

# 5 Installing the package

To use this package you should have ROS up and running. To install the package copy the papillarray_ros_v2 folder into the src folder of your catkin workspace.

# 6 Starting the node

The papillarray.launch launch file is provided to configure the COM port connection, get data from the sensors and publish the data.

# 7 papillarray_ros_node

ROS-Node for connecting to the controller and publishing sensor data.

# 7.1 Parameters


Table 7.1 – Parameters of the papillarray_ros $\underline { \underline { v } { 2 } }$ node


<table><tr><td>Name</td><td>Type</td><td>Description</td></tr><tr><td>hub_id</td><td>int</td><td>Identifier for the Controller</td></tr><tr><td>n_sensors</td><td>int</td><td>Number of sensors connected to the Controller. Should be 2.</td></tr><tr><td>com_port</td><td>string</td><td>Name of the COM port. Usually /dev/ttyACM0.</td></tr><tr><td>baud_rate</td><td>int</td><td>Baud rate for the serial connection to the Controller. Should be 9600.</td></tr><tr><td>parity</td><td>int</td><td>Parity of the serial connection to the Controller. Should be 0.</td></tr><tr><td>byte_size</td><td>int</td><td>Size of a byte. Should be 8.</td></tr><tr><td>is_flush</td><td>bool</td><td>Flag indicating if hardware input buffer is flushed if it has too many bytes</td></tr><tr><td>sampling_rate</td><td>int</td><td>Sampling rate of the Controller. Options: 100, 250, 500 or 1000 (Hz)</td></tr></table>

# 7.2 Subscribed topics

/hub_0/sensor_0 (See SensorState message)

Publish sensor data from Sensor 0 connected to the Controller /hub_0/sensor_1 (See SensorState message)

• Publish sensor data from Sensor 1 connected to the Controller

# 7.3 Messages

# 7.3.1 SensorState message


Table 7.2 – Variables in the SensorState message


<table><tr><td>Parameter</td><td>Description</td></tr><tr><td>Header header</td><td></td></tr><tr><td>int64 tus</td><td>The time in μs on the Controller of this sample</td></tr><tr><td>PillarState[] pillars</td><td>Pillars of the sensor (see PillarState msg)</td></tr><tr><td>float32gfx</td><td>The global X-force (N) of the sensor</td></tr><tr><td>float32 gfy</td><td>The global Y-force (N) of the sensor</td></tr><tr><td>float32 gfz</td><td>The global Z-force (N) of the sensor</td></tr><tr><td>float32 gtx</td><td>The global X-torque (Nmm) of the sensor ^</td></tr><tr><td>float32 gty</td><td>The global Y-torque (Nmm) of the sensor ^</td></tr><tr><td>float32 gtz</td><td>The global Z-torque (Nmm) of the sensor ^</td></tr><tr><td>float32 friction_est</td><td>The friction estimate</td></tr><tr><td>float32 target_grip_force</td><td>The target grip force (N)</td></tr><tr><td>bool is_sd_active</td><td>Flag indicating if slip detection is active</td></tr><tr><td>bool is_ref_loaded</td><td>Flag indicating if reference pillar is tangentially loaded (slip detection)</td></tr></table>


^ The torque reference point is the current tip position of the centre pillar (P4).


# 7.3.2 PillarState message


Table 7.3 – Variables in the PillarState message


<table><tr><td>Parameter</td><td>Description</td></tr><tr><td>Header header</td><td></td></tr><tr><td>int32 id</td><td>The pillar ID</td></tr><tr><td>float32 dx</td><td>The X-displacement (mm) of the pillar</td></tr><tr><td>float32 dy</td><td>The Y-displacement (mm) of the pillar</td></tr><tr><td>float32 dz</td><td>The Z-displacement (mm) of the pillar</td></tr><tr><td>float32 fx</td><td>The X-force (N) of the pillar</td></tr><tr><td>float32 fy</td><td>The Y-force (N) of the pillar</td></tr><tr><td>float32 fz</td><td>The Z-force (N) of the pillar</td></tr><tr><td>bool in_contact</td><td>Flag indicating if the pillar is in contact</td></tr><tr><td>int32 slip_state</td><td>Flag indicating the slip state of the pillar (see include/PTSDKConstants.h)</td></tr></table>

# 7.4 Services


Table 7.4 – Services of the papillarray_ros $\_ { \tt V 2 }$ node


<table><tr><td>Name</td><td>Description</td></tr><tr><td>SendBiasRequest</td><td>■ Biasing refers to removing any offset in the pillar readings when the pillars are unloaded.■ It is recommended that the user performs a bias each time the sensors are known to be unloaded.■ Ensure that the sensor has been unloaded for at least one second before performing a bias to ensure that the bias calculation does not include hysteresis effects. A bias operation can take up to two seconds. Ensure that the sensor remains unloaded throughout this time.</td></tr><tr><td>StartSlipDetection</td><td>■ Start the slip detection algorithm on the Controller.■ Slip detection should only be started after a few pillars of each sensor are in contact and before a tangential load is applied.■ Slip detection algorithm is implemented for tangential slip only and is not intended for detecting slip in the presence of torsional loads.</td></tr><tr><td>StopSlipDetection</td><td>■ Stops the slip detection algorithm on the Controller</td></tr></table>

# 7.5 Log file

# 7.5.1 Overview

In the papillarray_ros_v2/src/papillarray_ros_node.cpp file (line 3) a PTSDKListener object (listener_) is initialised with a boolean argument that specifies whether to log data to a .csv file or not. The argument can be changed to true (to enable logging) or false (to disable logging), remembering that the node should be remade by a call to the catkin_make utility.

# 7.5.2 Log file location

If logging is enabled, then a .csv log file will be generated and saved in the location /home/.ros/Logs.

NB: The .ros folder is a hidden location – make sure that you can view hidden files.

# 7.5.3 Log file name

The name of the log file that is generated is LOG_YYYY_MM_DD_hh_mm_ss.csv where:

YYYY is the four digit year,

• MM is the two digit month,

DD is the two digit day,

hh is the two digit hour,

mm is the two digit minute and

• ss is the two digit second,

from the system clock at the time that the log file was created.

# 7.5.4 Log file format

The log file is saved as comma-separated values (CSV) in ASCII text format. See PTSC++LIN_2.0_MAN_MMMYY.pdf for information on the order of the values and a description.