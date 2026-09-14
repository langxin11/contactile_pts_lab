# Contactile

# PapillArray Tactile Sensor Controller (v2.0)

Specifications

Document #: PTSCTR_2.0_SPEC_DEC21

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

2.2 Explanation of warnings . . 5

2.3 Precautions.. . 5

3 Physical specifications . . 6

3.1 Sensor ports . 6

3.2 Micro-USB port .. .. 6

3.3 Indicator panel .

3.4 Casing .

3.5 Environmental conditions .

3.6 Mechanical drawings.. .. 8

4 Installation . . 9

4.1 Mounting the Controller.. 9

4.2 Interfacing ... 9

4.3 Powering up.. . 9

4.4 Normal operation start-up sequence . . 9

5 Status indicators .. .. 10

5.1 HUB LED . . 10

5.2 SEN0 LED and SEN1 LED.. . 10

# 1 Introduction

The PapillArray Tactile Sensor Development Kit (v2.0) is a system of (up to) two PapillArray Tactile Sensor arrays and a Controller. Each PapillArray Tactile Sensor array can measure 3D displacement, 3D force, and vibration on each sensing element, as well as global 3D force, global 3D torque, the onset of slip, and friction. The Controller supplies power for (up to) two sensors and coordinates the simultaneous data acquisition from up to two PapillArray Tactile Sensors; i.e., coordinates sampling of the 9 pillars if one sensor is connected to the Controller, 18 pillars if two sensors are connected to the Controller. The Development Kit is shipped with visualisation software and (optional) C++ libraries for Windows and Linux environments and a ROS node for developing software control algorithms using the sensor signals.

The main components of the PapillArray Tactile Sensor Development Kit (v2.0) are shown in Figure 1.1, connected to a laptop running the visualisation software.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/b6718f57b55da2a16df2b464bd27dcf0ec157f226d1be51f0764850142a3fe4e.jpg)



Figure 1.1 – The PapillArray Tactile Sensor Development Kit (v2.0). Laptop not included.


This document contains the specifications for the PapillArray Tactile Sensor (v2.0). Error! R eference source not found. shows the PapillArray Tactile Sensor (v2.0).

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/38712eb4bde064342953363ebd34735ae772e391001d3ed182f63baa063e5db5.jpg)



Figure 1.2 – The PapillArray Tactile Sensor Controller (v2.0).


# 2 Safety

# 2.1 General

The customer should verify that the maximum loads and moments expected during operation fall within the sensing range of the sensor as outside this range, sensor reading accuracy is not guaranteed (refer to Document #PTS_2.0_SPEC_DEC21). Particular attention should be paid to dynamic loads caused by robot acceleration and deceleration if the sensors are mounted on robotic equipment. These forces can be many multiples of the value of static forces in high acceleration or deceleration situations.

# 2.2 Explanation of warnings

The warnings included here are specific to the product(s) covered by this manual. It is expected that the user heed all warnings from the manufacturers of other components used in the installation.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/985cc01e97ad44478021204e8e2717fe66a039f35b5d70427ec061a78f20739a.jpg)


Danger indicates that a situation could result in potentially serious injury or damage to equipment.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/f80dcffa15238cc144be1f42aa1deeb9a7af9a8fa1bb48832c8b64c512905c7b.jpg)


Caution indicates that a situation could result in damage to the product and/or the other system components.

# 2.3 Precautions

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/38f000ec4783ef49f9910532c49dc0ae5b4c096ee8d5e2c0bcf69566e3ca952a.jpg)


DANGER: Do not attempt to disassemble the sensor. This could damage the sensor and will invalidate the calibration.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/0599e70a0d28460d5c8a5d14c290d8f9897266812ccfafaa1054be89bed9affe.jpg)


DANGER: Do not attempt to drill, tap, machine, or otherwise modify the sensor casing. This could damage the sensor and will void any warranty.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/cd1a531defce43c0242258ae00ac7e9c50f12de47b4568cbada564c1cb5c67e0.jpg)


DANGER: Do not use the sensor on abrasive surfaces or surfaces with sharp points/edges. This could damage the silicone surface of the sensor.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/107364540c5110280aff1c7343f8aa4fbb32999ba4515a81cb0320c38a3665c1.jpg)


CAUTION: Sensors may exhibit a small offset in readings when exposed to intense light sources.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/f8a8f01df241caf693f73404fd76dd1515482f55a746ebe5adfaf4806c93a1e7.jpg)


CAUTION: Exceptionally strong and changing electromagnetic fields, such as those produced by magnetic resonance imaging (MRI) machines, constitute a possible source of interference with the operation of the sensor and Controller.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/bdbed032e0721e08b559d31763fa8ada9640ae169876b3306ceba853e40478e5.jpg)


CAUTION: Temperature variations can cause drift in sensor readings. Some temperature compensation is included in Development Kit version of the PapillArray. However, bias removal in software prior to operation is necessary, and it is recommended that biasing is performed each time the sensor is known to be unloaded.

# 3 Physical specifications

# 3.1 Sensor ports

The Controller has two sensor ports, labelled SEN0 and SEN1. The sensor ports are shown in Figure 3.1.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/cf0a0648690d5eecc76f8bf7ae4d0179451d25fb0eca4db32d38b97681a8a740.jpg)



Figure 3.1 – Sensor ports of the PapillArray Tactile Sensor Controller (v2.0)


# 3.2 Micro-USB port

The Controller has one micro-USB port as shown in Figure 3.2.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/7267d6a9b26737030451b0969831df0b0117b12e0f0115f9070473d043ae3c18.jpg)



Figure 3.2 – Micro-USB port of the PapillArray Tactile Sensor Controller (v2.0)


The micro-USB port supplies power to the Controller from the PC and transmits data to the PC from up to two sensors at a rate of 1000 Hz. The Visualisation Software, the C++ Library and/or the ROS Node can be used to read the data – see the respective manual for further instructions.

# 3.3 Indicator panel

On the top face of the Controller, there are three indicator LEDs labelled HUB, SEN0 and SEN1. The indicator panel is shown in Figure 3.3. The LEDs indicate the status of the system:

• HUB – indicates the Controller status

• SEN0 – indicates the status of sensor connected to the SEN0 port

• SEN1 – indicates the status of sensor connected to the SEN1 port

In general, a solid white LED indicates that the status is functional, a flashing white LED indicates waiting for some event, and a solid red LED indicates an error. For more information on the different states of the LEDs, see section 5 Status indicator.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/d0e871e2e3976739e28976eb2bfae432fdc9de8c5738e5e66510383b156dd884.jpg)



Figure 3.3 – Indicator LEDs of the PapillArray Tactile Sensor Controller (v2.0)


# 3.4 Casing

The physical characteristics of the casing of the Controller are summarised in Table 3.1.


Table 3.1 – Physical characteristics of plastic casing.


<table><tr><td>Dimensions(W x L x H mm)</td><td>46 × 36 × 16</td></tr><tr><td>Material</td><td>Anodised Aluminium</td></tr><tr><td>Mounting</td><td>4x M3 threaded holes on bottom-side – see Figure 3.4</td></tr></table>

# 3.5 Environmental conditions

The Controller is designed to be used in standard laboratory or light-manufacturing conditions and does not yet have ingress protection to withstand dusty environments, or fresh- or salt-water immersion to any depth. The Controller may be used in environments with up to 95% relative humidity, non-condensing.

# 3.6 Mechanical drawings

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/913924248844e2a6c7a5f26c379e7ba178c996bf58ab1175821b63de1767db55.jpg)



BOTTOM



TOP


![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/200ba99e8ef505e782f98d0622233f1169b42eae29ee4a360251c15766452509.jpg)



SIDE (USB CONNECTOR)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/5fe09d73628bbfbf3bf9f6ebd92e681e8bdd5bb91a354a5361e59718a187320a.jpg)



FRONT (SENSOR CONNECTORS)



Figure 3.4 – Mechanical drawing of PapillArray Tactile Sensor Controller (v2.0). All dimensions are in mm. Customer mounting interface is shown as orange circles ( )


# 4 Installation

# 4.1 Mounting the Controller

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/fcfee2fe-5e84-404d-8d59-bab3558e14ae/cff88d93a88c55a6b31103783fedb2cd7f1570f318b44c6e8679c72dfd715a0e.jpg)


DANGER: Do not attempt to drill, tap, machine, or otherwise modify or disassemble the Controller. This could damage the Controller and will void any warranty.

The Controller can be mounted if desired. Mount the Controller to a structure with sufficient mechanical strength that is moving together with the sensors to avoid mechanically loading/cycling the sensor cables. Not doing so can lead to suboptimal performance and may cause premature damage to the sensor cables. The Controller can be mounted using the bolt pattern provided – See 3.6 Mechanical drawings.

# 4.2 Interfacing

The Controller device coordinates the simultaneous data acquisition from up to two PapillArray Tactile Sensors (v2.0); i.e., coordinates sampling of 18 pillars across two independent sensors.

Data transmission between the Controller device and the host computer (i.e., laptop, PC) is via a serial connection emulated on the USB connection, visible as a COM port on the host computer.

Raw photodiode readings are read on the host computer through a closed application programming interface (API) provided. The calibrated values are also calculated through this API (See section Error! Reference source not found. Error! Reference source not found.).

# 4.3 Powering up

Power for the Controller and up to two PapillArray Tactile Sensors (v2.0) is supplied over the same single micro-USB to USB cable used to communicate with the Controller. A standard USB 2.0 5 V / 500 mA port is sufficient. USB 3.0, 3.1, or 3.2 are also compatible.

For more information about installation and operation of the Development Kit, refer to Document #PTSDK_2.0_MAN_DEC21.

# 4.4 Normal operation start-up sequence

Under normal operation when a PapillArray Tactile Sensor is connected to each of the sensor ports, SEN0 and SEN1, as soon as the Controller is connected to a laptop/PC via a micro-USB to USB cable, the HUB LED will then start flashing white as the Controller waits for a serial connection to be established with the laptop/PC. When a serial connection is established, the HUB LED will turn solid white, and if a sensor was connected to the SEN0 sensor port, then the SEN0 LED will turn solid white, and if a sensor was connected to the SEN1 sensor, then the SEN1 LED will turn solid white.

# 5 Status indicators

# 5.1 HUB LED

Once the Controller is powered, the HUB LED indicates the status of the Controller. The HUB LED can be in one of four states which are described in Table 5.1.


Table 5.1 – States of the HUB LED


<table><tr><td>State</td><td>Description</td></tr><tr><td>Off</td><td>There is no power to the Controller</td></tr><tr><td>Flashing white</td><td>The Controller is waiting for a serial connection to be established</td></tr><tr><td>Solid white</td><td>The Controller is functioning normally and sampling data</td></tr><tr><td>Solid red</td><td>The Controller has experienced an error</td></tr></table>

# 5.1.1 HUB LED error state

When the HUB LED is solid red, the Controller is experiencing an error. An error could be due to failure to initialise or a low voltage supply being delivered to the connected sensors.

# 5.2 SEN0 LED and SEN1 LED

Once the Controller is powered, the SEN0 LED and SEN1 LED indicate the status of a sensor that is connected to the SEN0 sensor port and the SEN1 sensor port, respectively. The SEN0 LED and SEN1 LED can each be in one of four states which are described in Table 5.2.


Table 5.2 – States of the SEN0 LED and SEN1 LED


<table><tr><td>State</td><td>Description</td></tr><tr><td>Off</td><td>If the PWR LED is also off, there is no power to the Controller;If the PWR LED is solid white, then there is no sensor connected to the SEN0/SEN1 sensor port</td></tr><tr><td>Solid white</td><td>The Controller is sampling data from the sensor connected to the SEN0/SEN1 sensor port</td></tr><tr><td>Solid red</td><td>The Controller has experienced an error related to the sensor connected to the SEN0/SEN1 sensor port</td></tr></table>

# 5.2.1 SEN0 LED and SEN1 error states

When the SEN0 LED or SEN1 LED is solid red, the corresponding sensor has invalid or missing data. This could be due to the sensor being disconnected.