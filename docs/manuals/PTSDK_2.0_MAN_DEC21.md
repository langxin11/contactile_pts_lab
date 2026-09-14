# Contactile

# PapillArray Tactile Sensor Development Kit (v2.0)

Installation and Operation Manual

Document #: PTSDK_2.0_MAN_DEC21

December, 2021

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

3.1 Introduction . . 6

3.2 Unpacking.. . 6

3.3 Development Kit Components.. . 6

3.3.1 PapillArray Tactile Sensor (v2.0)..... 6

3.3.2 PapillArray Tactile Sensor Controller (v2.0) . . 6

3.3.3 Sensor Cable (v2.0)..

3.3.4 USB Cable (v2.0)... 7

3.3.5 Contactile USB Flash Drive . 8

4 Installation . . 9

4.1 Precautions.. 9

4.2 Mounting the sensor . 9

4.3 Mounting the Controller... 9

4.4 Connecting the sensor(s) and Controller.. 9

4.5 Powering up the Controller and sensors... . 10

4.6 Interfacing the Controller to a PC . . 10

5 Software and algorithms .. . 11

5.1 Visualisation software . . 11

5.2 C++ WIN and C++ LIN (optional) .. 11

5.3 ROS (optional) . 11

5.4 Communications protocol.. 11

6 Maintenance ... .. 12

6.1 General.. . 12

6.2 Cleaning.. . 12

6.3 Silicone integrity.. . 12

6.4 Cabling and connectors . . 12

6.5 Periodic calibration.. . 12

# 1 Introduction

The PapillArray Tactile Sensor Development Kit (v2.0) is a system of (up to) two PapillArray Tactile Sensor arrays and a Controller. Each PapillArray Tactile Sensor array can measure 3D displacement, 3D force, and vibration on each sensing element, as well as global 3D force, global 3D torque, the onset of slip, and friction. The Controller supplies power for (up to) two sensors and coordinates the simultaneous data acquisition from up to two PapillArray Tactile Sensors; i.e., coordinates sampling of the 9 pillars if one sensor is connected to the Controller, 18 pillars if two sensors are connected to the Controller. The Development Kit is shipped with visualisation software and (optional) C++ libraries for Windows and Linux environments and a ROS node for developing software control algorithms using the sensor signals.

The main components of the PapillArray Tactile Sensor Development Kit (v2.0) are shown in Figure 1.1, connected to a laptop running the visualisation software.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/d092dac657bf2912c4218680bb66930b814d7e1c31822f7275d1a1552fd88772.jpg)



Figure 1.1 – The PapillArray Tactile Sensor Development Kit (v2.0). Laptop not included.


This document contains the installation and operation manual for the PapillArray Tactile Sensor Development Kit (v2.0).

# 2 Safety

# 2.1 General

The customer should verify that the maximum loads and moments expected during operation fall within the sensing range of the sensor as outside this range, sensor reading accuracy is not guaranteed (refer to Document #PTS_2.0_SPEC_DEC21). Particular attention should be paid to dynamic loads caused by robot acceleration and deceleration if the sensors are mounted on robotic equipment. These forces can be many multiples of the value of static forces in high acceleration or deceleration situations.

# 2.2 Explanation of warnings

The warnings included here are specific to the product(s) covered by this manual. It is expected that the user heed all warnings from the manufacturers of other components used in the installation.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/31524d8bc277f36f59b01202cf72282230d17bb0208455b689e371a2cd75cd70.jpg)


Danger indicates that a situation could result in potentially serious injury or damage to equipment.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/8472f8675254388b95403f48004911ac528952ac563e62bfccee8dd71a15583a.jpg)


Caution indicates that a situation could result in damage to the product and/or the other system components.

# 2.3 Precautions

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/ae5b2bf026424f03f236f2027bdfec0c09c3d4cde0181ccb8963eab917ec707e.jpg)


DANGER: Do not attempt to disassemble the sensor. This could damage the sensor and will invalidate the calibration.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/7cf1fbf6a20d6abe1bac67c1378b9780f16e8fb6dbe1fb0752fb3a80b704c75e.jpg)


DANGER: Do not attempt to drill, tap, machine, or otherwise modify the sensor casing. This could damage the sensor and will void any warranty.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/e68140dcb699249bd2352d1f8593e17eb82afff81887ba7c99db92174cf3c80c.jpg)


DANGER: Do not use the sensor on abrasive surfaces or surfaces with sharp points/edges. This could damage the silicone surface of the sensor.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/89473cde34001152890fe85ece0374d5f483560797c066c0b59b993f758f28f8.jpg)


CAUTION: Sensors may exhibit a small offset in readings when exposed to intense light sources.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/840d7c75cdc0300800a4746a322a43af7c9b2bb50b59acfdcce3675e51982a93.jpg)


CAUTION: Exceptionally strong and changing electromagnetic fields, such as those produced by magnetic resonance imaging (MRI) machines, constitute a possible source of interference with the operation of the sensor and Controller.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/fdd47e26c02e68e3329ed0d7dc0fb32734ef8834c13fc53d65509dad4f0a47d9.jpg)


CAUTION: Temperature variations can cause drift in sensor readings. Some temperature compensation is included in Development Kit version of the PapillArray. However, bias removal in software prior to operation is necessary, and it is recommended that biasing is performed each time the sensor is known to be unloaded.

# 3 Getting started

# 3.1 Introduction

This section describes the contents of the PapillArray Tactile Sensor Development Kit (v2.0). Installation is covered in Section 4.

# 3.2 Unpacking

Check the shipping box and components for damage during shipping. Any damage should be reported to Contactile Pty Ltd.

Standard components of the Development Kit are:

• 2x PapillArray Tactile Sensor (v2.0)

• 1x PapillArray Tactile Sensor Controller (v2.0)

• 2x Sensor Cable – 600 mm length

• 1x USB cable – 1 m length

• Contactile USB flash drive

# 3.3 Development Kit Components

# 3.3.1 PapillArray Tactile Sensor (v2.0)

The PapillArray Tactile Sensor (v2.0) is a sensor array that can measure 3D displacement, 3D force and vibration on each sensing element, as well as global 3D force, global 3D torque, the onset of slip and friction. Figure 3.1 shows the PapillArray Tactile Sensor (v2.0).

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/2b670b2d6d6debd2a49c2c0e3a4d1eb57c31023639ac12cf6f5b37062b2b01d3.jpg)



Figure 3.1 – The PapillArray Tactile Sensor (v2.0)


Unless otherwise specified, a sensor has no special IP protection. In this case, the sensor may be used only in benign environments with no dust or debris and no liquids or spray.

For detailed specifications of the sensor, refer to PapillArray Tactile Sensor (v2.0) Specification (Document # PTS_2.0_SPEC_DEC21).

# 3.3.2 PapillArray Tactile Sensor Controller (v2.0)

The PapillArray Tactile Sensor Controller (v2.0) coordinates the simultaneous data acquisition from up to two PapillArray Tactile Sensors (v2.0); i.e., coordinates sampling of 18 pillars across two independent sensors. The Controller also supplies power to up to two PapillArray Tactile Sensors (v2.0) over the same single USB cable used for communications. Figure 3.2 shows the PapillArray Tactile Sensor Controller (v2.0).

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/770d76da2c1dfde104250382fa00edcbaf2e282e6582df67759d2b9702b5f483.jpg)



Figure 3.2 – The PapillArray Tactile Sensor Controller (v2.0)


Before proceeding to installation, please read the PapillArray Tactile Sensor Controller (v2.0) Specification (Document # PTSCTR_2.0_SPEC_DEC21).

# 3.3.3 Sensor Cable (v2.0)

The sensor cable connects a PapillArray Tactile Sensor (v2.0) to the PapillArray Tactile Sensor Controller (v2.0). The sensor cable is a Molex PicoBlade 10 pin female-to-female cable assembly. The sensor cable is shown in Figure 3.3.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/0182fd0dab276b51b17fde3c2ebca3d61944d0535e97a9ab37f5ea5c67e51ac7.jpg)



Figure 3.3 – The Sensor Cable (v2.0)


NOTE: The sensor cable comprises part of the calibrated sensor. Changing the length or type of the cable can affect the calibration. Check with Contactile when making cabling changes to ensure your system’s calibration will not be affected.

# 3.3.4 USB Cable (v2.0)

The Development Kit comes with a standard 1 m long USB 2.0 cable for connecting the Controller to a PC (for power and communications). The USB cable is shown in Figure 3.4.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/5ee87b2e1460af6e44203fd17a1099e79f154ffb36c95b42e474cdc98229cbf2.jpg)



Figure 3.4 – The USB cable


# 3.3.5 Contactile USB Flash Drive

The Development Kit comes with a Contactile USB flash drive containing manuals, software, and legal documents. The USB flash drive is shown in Figure 3.5.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/9ee9669aef192d2fa07b9bec8ba8b86995aa8629fce270561eb9ebd99e075831.jpg)



Figure 3.5 – The Contactile USB Flash Drive


A summary of the contents of the USB flash drive are described in

Table 3.1. For a full folder and file list of the contents of the USB flash drive, see Document # PTSDK_2.0_USBCONTENTS_DEC21 in the root folder of the USB flash drive.


Table 3.1 – Contents of Contactile USB flash drive


<table><tr><td>Folder Name</td><td>Description of Contents</td><td>More Information</td></tr><tr><td rowspan="7">MANUALS</td><td>PTSDK_2.0_MAN_DEC21</td><td>Development kit manual (this document)</td></tr><tr><td>PTS_2.0_SPEC_DEC21</td><td>PapillArray Tactile Sensor (v2.0) specification</td></tr><tr><td>PTSCTR_2.0_SPEC_DEC21</td><td>PapillArray Tactile Sensor Controller (v2.0) specification</td></tr><tr><td>PTSVIS_2.0_MAN_DEC21</td><td>Manual for Visualisation Software (v2.0)</td></tr><tr><td>PTSC++WIN_2.0_MAN_DEC21</td><td>Manual for C++ Library for Windows (v2.0)</td></tr><tr><td>PTSC++LIN_2.0_MAN_DEC21</td><td>Manual for C++ Library for Linux (v2.0)</td></tr><tr><td>PTSROS_2.0_MAN_DEC21</td><td>Manual for ROS node (v2.0)</td></tr><tr><td>LEGAL</td><td>CONDITIONSOFSALE _20211028</td><td>The conditions of sale</td></tr><tr><td></td><td>ENDUSERLICENCEAGREEMENT _20211028</td><td>The end user licence agreement</td></tr><tr><td>SOFTWARE</td><td>PTSCOM_2.0_SPEC_DEC21</td><td>Describes the communications protocol for the serial communications over USB</td></tr><tr><td>SOFTWARE/VIS</td><td>Java GUI for real-time visualisation and data logging</td><td>See Document PTSVIS_2.0_MAN_DEC21</td></tr><tr><td>SOFTWARE/C++WIN</td><td>C++ Library for Windows (optional)</td><td>See Document PTSC++WIN_2.0_MAN_DEC21</td></tr><tr><td>SOFTWARE/C++LIN</td><td>C++ Library for Linux (optional)</td><td>See Document PTSC++LIN_2.0_MAN_DEC21</td></tr><tr><td>SOFTWARE/ROS</td><td>ROS node (optional)</td><td>See Document PTSROS_2.0_MAN_DEC21</td></tr></table>

# 4 Installation

# 4.1 Precautions

Before attempting to mount or connect the PapillArray Tactile Sensor or the Controller, the user must ensure they have read the following documents:

• PapillArray Tactile Sensor (v2.0) Specification (Document # PTS_2.0_SPEC_DEC21)

• PapillArray Tactile Sensor Controller (v2.0) Specification (Document # PTSCTR_2.0_SPEC_DEC21).

These documents contain details of specifications as well as safety information to prevent damage to the sensors and Controller.

# 4.2 Mounting the sensor

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/feaa0bef739278ead43f2afac31ba2eeef309b17bbc7536f4c7d47a3c9c3f88c.jpg)


DANGER: Do not attempt to drill, tap, machine, or otherwise modify or disassemble the sensor. This could damage the sensor and will void any warranty.

Mount the sensor(s) to a structure with sufficient mechanical strength. Not doing so can lead to suboptimal performance. The sensor can be mounted using the bolt pattern provided – See Document # PTS_2.0_SPEC_DEC21.

# 4.3 Mounting the Controller

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/6942e05641348f9e528b90cccb881ec2dea18e2c2ff869030fb342097045015a.jpg)


DANGER: Do not attempt to drill, tap, machine, or otherwise modify or disassemble the Controller. This could damage the Controller and will void any warranty.

The Controller can be mounted if desired. Mount the Controller to a structure with sufficient mechanical strength that is moving together with the sensors to avoid mechanically loading/cycling the sensor cables. Not doing so can lead to suboptimal performance. The Controller can be mounted using the bolt pattern provided – See Document # PTSCTR_2.0_SPEC_DEC21.

# 4.4 Connecting the sensor(s) and Controller

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/78003b1486ce59c841bc57472cbf5914b1cc943bb993f107705c3d4707a5be2f.jpg)


CAUTION: Do not stress or over bend the sensor cable, especially where it is attached to the sensor. Sharp bends must be avoided as they can damage the cable and sensor and will void the warranty.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/15dfb29893f2b44b80557648c27445a7945f225d1adc452057f443ec841dd6fd.jpg)


CAUTION: Be careful not to crush the sensor cable by over-tightening tie wraps or walking on the cable, since this may damage the cable.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/f9e39b4377ae17bf9f44dad2d225ad77a354e1cc28271aa917a4fac5b6c88f12.jpg)


CAUTION: Do not attempt to disconnect sensor cables by pulling on the cable itself; this can damage your system.

Each sensor is connected to the Controller via a sensor cable. The sensor cable is connected to the Controller into one of the sensor ports (labelled SEN0 and SEN1). The sensor cable must be routed so that it is not stressed, pulled, kinked, cut, or otherwise damaged throughout the full range of motion.

# 4.5 Powering up the Controller and sensors

After connecting the sensor/s and the Controller, connect the USB cable between the Controller and a PC. The LED labelled HUB on the Controller should flash white, and subsequently, should turn solid white when a serial connection is made with the Controller via the PC. For more information about the LED indicator panel on the communications hub, refer to the PapillArray Tactile Sensor Controller Specification (Document #PTSCTR_2.0_SPEC_DEC21).

The power of the development kit with 2x sensors is 5 V with up to 200 mA current draw via the USB connection.

# 4.6 Interfacing the Controller to a PC

After powering up the Controller through, the PC that is connected can be used to read the data being transmitted by the Controller, via the same USB connection.

The Controller device coordinates the simultaneous data acquisition from up to two PapillArray Tactile Sensors (v2.0); i.e., coordinates sampling of 18 pillars across two independent sensors. The Controller also decodes the raw photodiode readings into calibrated 3D displacement and 3D force values and performs torque calculations, slip detection and friction estimation.

Data transmission between the Controller device and the host computer (i.e., laptop, PC) is via a serial connection emulated on the USB connection, visible as a COM port on the host computer.

# 5 Software and algorithms

# 5.1 Visualisation software

A Java-based graphical user interface (GUI) is provided for basic post-installation testing and general demonstration of sensor operation.

This GUI can be found on the Contactile USB flash drive which was shipped with the Development Kit. The executable file is located in the folder ‘SOFTWARE/VIS’ in the root directory.

For further information, refer to the document PTSVIS_2.0_MAN_DEC21.

# 5.2 C++ WIN and C++ LIN (optional)

C++ libraries for the Windows and Linux environments are provided which read the calibrated 3D displacement and 3D force values for each of the sensing pillars, as well as global 3D force and 3D torque for the entire sensor array, slip status and friction estimates, for up to two sensors.

The C++ libraries can be found on the Contactile USB flash drive which was shipped with the Development Kit. The files are located in the folder ‘SOFTWARE/C++WIN’ and ‘SOFTWARE/C++LIN’ in the root directory.

For further information, refer to the document PTSC++WIN_2.0_MAN_DEC21 and PTSC++LIN_2.0_MAN_DEC21.

# 5.3 ROS (optional)

A ROS node is provided which reads the calibrated 3D displacement and 3D force values for each of the sensing pillars, as well as global 3D force and 3D torque for the entire sensor array, slip status and friction estimates, for up to two sensors.

The ROS node can be found on the Contactile USB flash drive which was shipped with the Development Kit. The files are located in the folder ‘SOFTWARE/ROS’ in the root directory.

For further information, refer to the document PTSROS_2.0_MAN_DEC21.

# 5.4 Communications protocol

The communications protocol refers to the data packet structure for sensor data being streamed by the Controller as well as commands accepted by the Controller for biasing the sensors, setting the sampling frequency and starting/stopping slip detection.

Users wishing to develop software for interfacing with the development kit that is independent of the software provided by Contactile can refer to the description of the communications protocol described in the document PTSCOM_2.0_SPEC_DEC21 in the ‘SOFTWARE’ folder on the root directory of the USB flash drive supplied.

# 6 Maintenance

# 6.1 General

For most applications, there are no parts that need to be replaced during normal operation.

# 6.2 Cleaning

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/fbead1669e12a7378550f6a29eadc5e086eb7bf7102d3d5bf435b26093b8d282.jpg)


CAUTION: The sensor and controller casing material is anodised aluminium. Do not clean with strong alkaline or acidic substances which can cause corrosion. Isopropanol is a suitable cleaning agent; however, care must be taken to avoid liquid ingress.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6eb34fe2-373a-42ef-96ec-6a4aaa2143e4/5abea23af731c335259dad5d6cb6d67155c977d326d09a6efd1a1510368153d3.jpg)


CAUTION: The sensor pillar material is silicone. Do not clean with strong alkaline or acidic substances which can cause corrosion. Isopropanol is a suitable cleaning agent; however, care must be taken to avoid liquid ingress.

Sensors and the Controller must be kept free of excessive dust, debris, and moisture. Debris and dust should be kept from accumulating on or in the sensor(s) and Controller.

# 6.3 Silicone integrity

Periodic inspection of the condition of the silicone of the sensor(s) is recommended. During normal use, the silicone surface finish may become dull - this is normal.

If the silicone appears worn or there are signs of damage, the silicone may need to be replaced and the sensor recalibrated. Contact Contactile for options on replacing the silicone and recalibration.

# 6.4 Cabling and connectors

In industrial-like applications that continuously or frequently move the system’s cabling, you should periodically check the cable jacket for signs of wear.

Damage to the outer jacketing of the sensor cable could enable moisture or water to enter an otherwise sealed sensor. Ensure the cable jacketing is in good condition to prevent sensor damage.

The sensor cables are not designed to be frequently connected and disconnected. To avoid damage to the sensor cables and sensor ports, avoid frequently connecting and disconnecting the sensor(s) from the Controller.

The sensor cables and connectors are not designed to be user serviceable. Contact Contactile for options on repairing or replacing cables and connectors.

# 6.5 Periodic calibration

Periodic calibration of the sensor and its electronics is required to maintain accuracy and resolution. We recommend annual recalibrations, especially for applications that frequently cycle the loads applied to the sensor. Contact Contactile for options on recalibration.