# Contactile

# PapillArray Tactile Sensor (v2.1)

Specifications

Document #: PTS_2.1_SPEC_JAN25

January, 2025

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

1 Introduction ..... 4

2 Safety .. 5

2.1 General . 5

2.2 Explanation of warnings. 5

2.3 Precautions .. 5

3 Physical specifications . . 6

3.1 Sensing pillars.. 6

3.2 Casing . 6

3.3 Environmental conditions.. 6

3.4 Transduction mechanism overview ... 6

3.5 Mechanical drawings . 7

4 Sensing characteristics . . 8

4.1 Displacement sensing.. 8

4.2 Force sensing.. 8

4.3 Temperature effects on accuracy.. 8

5 Electrical specifications ... 9

5.1 Anti-alias filtering .. 9

5.2 Sampling rate ... 9

6 Installation .. . 10

6.1 Mounting the sensor... . 10

6.2 Interfacing . . 10

6.3 Power . . 10

# 1 Introduction

The PapillArray Tactile Sensor Development Kit (v2.1) is a system of (up to) two PapillArray Tactile Sensor arrays and a Controller. Each PapillArray Tactile Sensor array can measure 3D displacement, 3D force, and vibration on each sensing element, as well as global 3D force, global 3D torque, the onset of slip, and friction. The Controller supplies power for (up to) two sensors and coordinates the simultaneous data acquisition from up to two PapillArray Tactile Sensors; i.e., coordinates sampling of the 9 pillars if one sensor is connected to the Controller, 18 pillars if two sensors are connected to the Controller. The Development Kit is shipped with visualisation software and (optional) C++ libraries for Windows and Linux environments and a ROS node for developing software control algorithms using the sensor signals.

The main components of the PapillArray Tactile Sensor Development Kit (v2.0) are shown in Figure 1.1, connected to a laptop running the visualisation software.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/13ff620deb4698eaf9a8ae5c63bbac13822e061b81667d14eacd76af1b91fb0e.jpg)



Figure 1.1 – The PapillArray Tactile Sensor Development Kit (v2.0). Laptop not included.


This document contains the specifications for the PapillArray Tactile Sensor (v2.1). Figure 1.2 shows the PapillArray Tactile Sensor (v2.1).

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/7de261ebcb8ac0c71075b8da8573c2f16e29ee29616f8e9d1d781914578a581c.jpg)



Figure 1.2 – The PapillArray Tactile Sensor (v2.1).


# 2 Safety

# 2.1 General

The customer should verify that the maximum loads and moments expected during operation fall within the sensing range of the sensor as outside this range, sensor reading accuracy is not guaranteed (refer to Document #PTS_2.1_SPEC_JAN25). Particular attention should be paid to dynamic loads caused by robot acceleration and deceleration if the sensors are mounted on robotic equipment. These forces can be many multiples of the value of static forces in high acceleration or deceleration situations.

# 2.2 Explanation of warnings

The warnings included here are specific to the product(s) covered by this manual. It is expected that the user heed all warnings from the manufacturers of other components used in the installation.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/caece67dd6b4c9ccbeb6780c28a9f341e426a39c25e47811145e1c63a9750f24.jpg)


Danger indicates that a situation could result in potentially serious injury or damage to equipment.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/1bd32d88c26c48f9884bdfd8e0dc8de84a8daa10ec0952392c58293606458d15.jpg)


Caution indicates that a situation could result in damage to the product and/or the other system components.

# 2.3 Precautions

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/58c2d138d7d8cbdc770ca1126ccd0217c4543d82f239be2bb4ba18bd51d077c1.jpg)


DANGER: Do not attempt to disassemble the sensor. This could damage the sensor and will invalidate the calibration.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/b93c77d31875347e5ba3d5604816e8ff22dd63b0857d24ea2d822508a5d00523.jpg)


DANGER: Do not attempt to drill, tap, machine, or otherwise modify the sensor casing. This could damage the sensor and will void any warranty.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/32a9ba4d64a77379e48b0a930a03767133fd6b8031dac44ba0fb5acdc119619e.jpg)


DANGER: Do not use the sensor on abrasive surfaces or surfaces with sharp points/edges. This could damage the silicone surface of the sensor.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/df72c1c1f80fc9510c04d937471a3aeb30a898c33526ece472934e869a224dd7.jpg)


CAUTION: Sensors may exhibit a small offset in readings when exposed to intense light sources.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/386e5161c0f9e41f0409e3b2c95b8ea797a4aa411ee0728148f34426b1d2732f.jpg)


CAUTION: Exceptionally strong and changing electromagnetic fields, such as those produced by magnetic resonance imaging (MRI) machines, constitute a possible source of interference with the operation of the sensor and Controller.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/2a6220e1b55bb75e8d7485ff60c543e84f5d74e5ac504a4d8596d7ed5d5b365d.jpg)


CAUTION: Temperature variations can cause drift in sensor readings. Some temperature compensation is included in Development Kit version of the PapillArray. However, bias removal in software prior to operation is necessary, and it is recommended that biasing is performed each time the sensor is known to be unloaded.

# 3 Physical specifications

# 3.1 Sensing pillars

The physical characteristics of the sensing pillars are shown in Table 3.1.


Table 3.1 – Physical characteristics of sensing pillars.


<table><tr><td>Pillar height</td><td>4.2 mm max. Centre pillar tallest, corner pillars shortest</td></tr><tr><td>Pillar diameter</td><td>6 mm</td></tr><tr><td>Pillar spacing</td><td>7 mm (centre-to-centre) on square grid</td></tr><tr><td>Material</td><td>Silicone</td></tr><tr><td>Shore hardness</td><td>A40</td></tr></table>


Note: Pillar size, shape, spacing, and hardness can be customised - height and hardness most easily.


# 3.2 Casing

The physical characteristics of the casing of the PapillArray Tactile Sensor are summarised in Table 3.2.


Table 3.2 – Physical characteristics of casing.


<table><tr><td>Dimensions(W x L x H mm)</td><td>24.0 × 30.6 × 8.6</td></tr><tr><td>Material</td><td>Anodised Aluminium</td></tr><tr><td>Mounting</td><td>4x M3 threaded holes on bottom side</td></tr></table>

# 3.3 Environmental conditions

The PapillArray Tactile Sensor (v2.1) is designed to be used in standard laboratory or lightmanufacturing conditions and does not yet have ingress protection to withstand dusty environments, or fresh- or salt-water immersion to any depth. The PapillArray Tactile Sensor (v2.1) may be used in environments with up to 95% relative humidity, non-condensing.

# 3.4 Transduction mechanism overview

Each of the nine silicone pillars in the 3x3 array uses an optical transduction mechanism to measure the 3D displacement of the tip of the outer hemispherical tip of the pillar; from this displacement measurement, 3D force on the pillar is estimated via a factory calibration which is performed before shipping and applied in software in real-time.

Details on the performance of this sensing approach for a larger pillar design can be found here:

[1] Khamis, Xia, Redmond, Sensor and Actuators A: Physical, 2019.

https://www.sciencedirect.com/science/article/pii/S0924424718319794

# 3.5 Mechanical drawings

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/80a8ec583e7020dff6418b0677b7eff9139e35712afd266d61405da0b03ab47b.jpg)


# SIDE

Figure 3.1 – Mechanical drawing of PapillArray Tactile Sensor (v2.1). All dimensions are in mm. X-, Y- and Z-axis orientations are labelled with red arrows ( ). Origin of measurement frame of reference is labelled with a green target ( ). Pillar numbers are labelled in magenta (P0 – P8). Customer mounting interface is shown as orange circles ( ).

# 4 Sensing characteristics

# 4.1 Displacement sensing

Pillars can be deformed to the point of mechanical failure without damaging any of the sensing electronics, but the indicated sensor reading is only valid within the ranges listed in Table 4.1.


Table 4.1 – Displacement sensing range for valid reading and associated measurement resolution (standard deviation of sensing error).


<table><tr><td colspan="3">Single sensing element</td></tr><tr><td></td><td>X, Y</td><td>Z</td></tr><tr><td>Sensing range (mm)</td><td>±1</td><td>+2.5</td></tr><tr><td>Resolution (mm)</td><td>&lt; ±0.01</td><td>&lt; ±0.01</td></tr></table>


Note: Sensing range can be traded for sensing resolution in customised designs.


# 4.2 Force sensing

Force readings are subsequently estimated from 3D pillar displacements. The force and torque sensing ranges and measurement resolutions are listed in Table 4.2.


Table 4.2 – Force and torque sensing ranges for valid reading, and associated measurement resolution (standard deviation of sensing error).


<table><tr><td colspan="3">Single sensing element</td></tr><tr><td></td><td>Fx, Fy</td><td>Fz</td></tr><tr><td>Sensing range (N)</td><td>±4</td><td>15</td></tr><tr><td>Resolution (N)</td><td>&lt; ±0.05</td><td>&lt; ±0.05</td></tr></table>


Note: Sensing range can be traded for sensing resolution in customised designs.


# 4.3 Temperature effects on accuracy

Temperature variations can cause drift in sensor readings; this is due to variation in LED output and due to thermal expansion/contraction of the pillar silicone. Some temperature compensation is included in this version of the PapillArray. However, bias removal in software prior to operation is necessary and it is recommended that biasing is performed each time the sensor is known to be unloaded. Bias removal is a standard procedure for many commercial force/torque sensors.

# 5 Electrical specifications

# 5.1 Anti-alias filtering

A hardware anti-alias low-pass filter with a cut-off frequency of 338.8 Hz for 1000 Hz sampling frequency is applied to each of the four photodiode signals coming from each sensing pillar. The frequency response of the anti-alias filter is shown in Figure 5.1.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/78d4ba28dc72f3fbbe608dd834cd5de32a0629cdba99e4f0579a1581f033886e.jpg)



Figure 5.1 – Input filter frequency response (-3dB @ 235Hz)


# 5.2 Sampling rate

Each pillar can be sampled at 1000 Hz at full 16-bit resolution. This is coordinated by the Controller. For more specifications of the Controller, see Document #PTSCTR_2.0_SPEC_DEC21.

# 6 Installation

# 6.1 Mounting the sensor

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/a12895d4eec2d3291d8285be02df60b26a17da7b5ee4e5682fd06c53f6774874.jpg)


DANGER: Do not attempt to drill, tap, machine, or otherwise modify the sensor casing. This could damage the sensor or invalidate the calibration.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/934e913e-b0d8-4330-8e11-f604bbb4999d/c0fa9a3bf3a9e718968fcbfd78c07d44303d1f533949ecfc192c681f772d7b74.jpg)


DANGER: Do not exceed the mounting interface depth. This could damage the sensor.

The sensor can be mounted using the bolt pattern provided on the bottom of the sensor. See section 3.5 Mechanical drawings.

# 6.2 Interfacing

A separate Controller device coordinates the simultaneous data acquisition from up to two PapillArray Tactile Sensors (v2.1); i.e., coordinates sampling of 18 pillars across two independent sensors.

Data transmission between the Controller device and the host computer (i.e., laptop, PC) is via a serial connection emulated on the USB connection, visible as a COM port on the host computer. The Controller also decodes the raw photodiode readings into calibrated 3D displacement and 3D force values and performs torque calculations, slip detection and friction estimation.

For more specifications of the Controller, refer to Document #PTSCTR_2.0_SPEC_DEC21. For more information about installation and operation of the Development Kit, refer to Document #PTSDK_2.0_MAN_DEC21.

# 6.3 Power

Power for the Controller and up to two PapillArray Tactile Sensors (v2.1) is supplied over the same single micro-USB to USB cable used to communicate with the Controller. A standard USB 2.0 5 V / 500 mA port is sufficient. USB 3.0, 3.1, or 3.2 are also compatible.

For more specifications of the Controller, refer to Document #PTSCTR_2.0_SPEC_DEC21. For more information about installation and operation of the Development Kit, refer to Document #PTSDK_2.0_MAN_DEC21.