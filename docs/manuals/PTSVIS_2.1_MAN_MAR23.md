# Contactile

# PapillArray Tactile Sensor Visualisation Software (v2.1)

Installation and Operation Manual

Document #: PTSVIS_2.1_MAN_MAR23

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

3.2 End user licence agreement licence.. . 6

3.3 Software installation .. . 6

4 Operation... 7

4.1 COM Port.. 7

4.2 Microsoft Windows display settings..

4.3 Starting the software .. 7

4.4 Start-up sequence.. 7

5 GUI overview ... . 8

6 Display options . . 9

6.1 Visual representation of pillar displacement .. . 9

6.2 Rotating a sensor... .. 10

6.3 Internal temperature display.. .. 10

6.4 Slip detection and friction display ... . 10

6.5 Display controls.. . 10

7 GUI controls... .. 13

7.1 Changing the COM port .. . 13

7.2 Biasing the sensor data.. . 13

7.3 Start/stop slip detection.. .. 13

7.4 Log file controls.. . 14

7.5 Keyboard shortcuts .. . 14

8 Log file ... .. 15

8.1 Overview... . 15

8.2 Log file location .. . 15

8.3 Log file name . . 15

8.4 Log file format .. . 15

# 1 Introduction

The PapillArray Tactile Sensor Development Kit (v2.0) is a system of (up to) two PapillArray Tactile Sensor arrays and a Controller. Each PapillArray Tactile Sensor array can measure 3D displacement, 3D force, and vibration on each sensing element, as well as global 3D force, global 3D torque, the onset of slip, and friction. The Controller supplies power for (up to) two sensors and coordinates the simultaneous data acquisition from up to two PapillArray Tactile Sensors; i.e., coordinates sampling of the 9 pillars if one sensor is connected to the Controller, 18 pillars if two sensors are connected to the Controller. The Development Kit is shipped with visualisation software and (optional) C++ libraries for Windows and Linux environments and a ROS node for developing software control algorithms using the sensor signals.

The main components of the PapillArray Tactile Sensor Development Kit (v2.0) are shown in Figure 1.1, connected to a laptop running the visualisation software.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/eb01fc416f853274ef42d6d710bd48383550ee72ba24e696e159e23b51d4113b.jpg)



Figure 1.1 – The PapillArray Tactile Sensor Development Kit (v2.0). Laptop not included.


This document contains an operation and installation manual for the Visualisation Software. Figure 1.2 shows a screenshot of the Visualisation Software.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/76375474808c16dfb71593ab72d727df791d77d9410c693bfd8c87303d2024c0.jpg)



Figure 1.2 – The PapillArray Tactile Sensor Visualisation Software (v2.1).


# 2 Safety

# 2.1 General

The customer should verify that the maximum loads and moments expected during operation fall within the sensing range of the sensor as outside this range, sensor reading accuracy is not guaranteed (refer to Document #PTS_2.0_SPEC_DEC21). Particular attention should be paid to dynamic loads caused by robot acceleration and deceleration if the sensors are mounted on robotic equipment. These forces can be many multiples of the value of static forces in high acceleration or deceleration situations.

# 2.2 Explanation of warnings

The warnings included here are specific to the product(s) covered by this manual. It is expected that the user heed all warnings from the manufacturers of other components used in the installation.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/abaf37fc06248b09b5b5845e4e56539782a833092da7916336d0242796cd5b5b.jpg)


Danger indicates that a situation could result in potentially serious injury or damage to equipment.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/9652aa82c27bbdd2aa4e2c2fbb67313cdf8dfb788977813579943e3a9f035f0a.jpg)


Caution indicates that a situation could result in damage to the product and/or the other system components.

# 2.3 Precautions

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/31524a42fc4f9e1b9cc6b532c8905187e227117b8549e43e9613ff84ce0885bc.jpg)


DANGER: Do not attempt to disassemble the sensor. This could damage the sensor and will invalidate the calibration.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/8121012a17e53321d3a8a0cd61b9b77c761224e2458001390d5c8c67ec670d3e.jpg)


DANGER: Do not attempt to drill, tap, machine, or otherwise modify the sensor casing. This could damage the sensor and will void any warranty.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/fd5527e04b0711399a1c095d1cfea3f64ac4e47aed2794ac88749c8c7c1145a8.jpg)


DANGER: Do not use the sensor on abrasive surfaces or surfaces with sharp points/edges. This could damage the silicone surface of the sensor.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/17139535034acb7532e15b0021309cad49370441b6d388f68fd63f3dcde87719.jpg)


CAUTION: Sensors may exhibit a small offset in readings when exposed to intense light sources.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/9875040143d129e20ebb4fda2658f77335e0a5f51e8c32be37015efe1403da97.jpg)


CAUTION: Exceptionally strong and changing electromagnetic fields, such as those produced by magnetic resonance imaging (MRI) machines, constitute a possible source of interference with the operation of the sensor and Controller.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/800fe2b24a7443d71cffa201228dd3f6589f32808fc7b257245762f0203c2f6c.jpg)


CAUTION: Temperature variations can cause drift in sensor readings. Some temperature compensation is included in Development Kit version of the PapillArray. However, bias removal in software prior to operation is necessary, and it is recommended that biasing is performed each time the sensor is known to be unloaded.

# 3 Getting started

This section contains instructions for setting up and using PapillArray Tactile Sensor Visualisation Software (v2.1). It is recommended that first time users first read the preceding Safety section, then read through this section to get more familiar with the system.

# 3.1 Hardware installation

The visualisation software is used with the PapillArray Tactile Sensor Development Kit (v2.0). The Controller should first be connected to the sensors and then to a PC via the micro-USB port on the Controller before you can use the visualisation software. For more information about connecting the sensors and powering on the Controller, refer to Document #PTSDK_2.0_MAN_DEC21.

The micro-USB port is shown in Figure 3.1.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/fc8f0504abb59c6145399ac9d56d358643c5afb22b2a7fbd6039a86c6533e7a0.jpg)



Figure 3.1 – Micro-USB port of the PapillArray Tactile Sensor Controller (v2.0)


# 3.2 End user licence agreement licence

Contactile's end user license agreement applies to all software and algorithms included with the products sold by Contactile. The end user license agreement that applies is provided on the USB flash drive shipped with the product in the folder ‘LEGAL’ in the root directory.

# 3.3 Software installation

The visualisation software is provided on the Contactile USB flash drive that was shipped with the development kit. Copy the entire contents of the Contactile USB flash drive to a location on the PC running Microsoft Windows.

# 4 Operation

# 4.1 COM Port

The data transmission protocol between the Controller device and the PC is a serial connection emulated on the USB connection, visible as a COM port on the PC. After connecting the Controller to the PC, use the PCs device manager to determine the COM port number of the connection.

# 4.2 Microsoft Windows display settings

Before starting the software, for the GUI to display in full screen, it is recommended to change the Windows display settings.

# In Windows 7:

1. Type “Display” in the windows search bar

2. Open “Display”

3. In the section “Make it easier to read what’s on your screen”, select “Smaller – 100%”

# In Windows 10:

1. Type “Display Settings” in the windows search bar

2. Open the “Display Settings”

3. In the section “Scale and layout”, change the “size of text, apps and other items” to “100%”

# 4.3 Starting the software

Run the executable file “PTSVIS_2.1.exe”.

# 4.4 Start-up sequence

Once the software is launched, the GUI will appear. A serial connection will need to be made before the software begins sampling and displaying the data. To select a COM port and make a serial connections, see 7.1 Changing the COM port).

# 5 GUI overview

The top left area of the GUI window is a visual representation of the sensor connected to the SEN0 port of the Controller, and the top right is a visual representation of the sensor connected to the SEN1 port. Directly below each sensor visual representation is an area which can be toggled between plots or a text-based representation of 3D force or 3D displacement for each pillar or global 3D force and global 3D torque of each of each sensor. There are also numerous controls for connecting to the Controller, logging data, biasing the sensors, starting/stopping slip detection and changing the display options - these are highlighted in Figure 5.1.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/6f13e44741c656877367e1dad1839cf052fe0a9dd4d0f2a6bb709c44025f6d42.jpg)



Figure 5.1 – GUI components of the visualisation software.


# 6 Display options

# 6.1 Visual representation of pillar displacement

The visual representation of the sensor takes a top view of the sensor pillars. Each pillar of the sensor is represented as a 2-D grey (when unloaded) or white (when loaded) shape with a cross hair representing the tip of the pillar. The representation of an unloaded sensor is shown alongside the physical sensor is shown in Figure 5.1.


Visual representation of sensor


![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/a7eaefe0c1321a58d36ea97208857a59e33f1c7dfa5dc5bb3b0390fb4e74b670.jpg)



Top view of real sensor


![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/b234a430f68600b34118b4eb8380a5d5446a38443fe86932e2527f4143e0d1ce.jpg)



Figure 6.1 – Visual representation of sensor in GUI, including the X and Y axis orientation and internal temperature measurement; and corresponding physical sensor.


The cross hair moves left and right, and up and down to indicate positive and negative displacement of the pillar, in the X- and Y-axis depending upon the orientation of the visual representation (see Section 6.2 Rotating a sensor). The shape of the pillar representation deforms as a result of displacement in the X- and Y- axis. Additionally, Z displacement of the pillar is represented by a grey circle centred at the cross-hair – larger positive $\dot { Z }$ displacement results in a larger grey circle. Contact is represented by a change in the colour of the pillar – when the pillar is not in contact, it is grey, and when contact is made, the pillar becomes white. For visual purposes, the default threshold for a pillar to be considered in contact is 0.2 N in any one axis. Figure 6.2 shows an unloaded pillar, a pillar that is compressed to 1.5 N in the Z-axis, a pillar compressed to 5 N in the Z-axis, and a pillar compressed to 6 N in the Z-axis and displaced in the positive X-axis.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/dfc772865622e2e74848798270b770015e028b757373483b4f10207292d4cbcd.jpg)



Figure 6.2 – Visual representation of a pillar when uncompressed, compressed to different zforces, and displaced in X-axis.


# 6.2 Rotating a sensor

To rotate the orientation of a sensor by 90° in a clockwise direction, click on the Rotate button in the visual representation of the sensor (see Figure 6.3). This will rotate the sensor visualisation as well as the per pillar plots and text values.

# Rotate

Figure 6.3 – Rotating a sensor

# 6.3 Internal temperature display

The internal temperature of the sensor is displayed as text in the bottom left corner of the visual representation of the sensor (see Figure 6.1).

# 6.4 Slip detection and friction display

If slip detection is started (see Section 7.3 Start/stop slip detection) the slip status legend will appear between the two sensor visual representations. The slip status of each pillar is represented by a coloured ring surrounding the pillar in the visual representation. The current friction estimate is shown next to each sensor opposite the internal temperature display.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/c20247e1069fcd115319114005ba809bfa3c5e9732f37cb77bf9134adc4d7e3d.jpg)



Figure 6.4 – Slip status (coloured ring surrounding each pillar in the visual representation), the slip status legend and current friction estimate of each sensor.


# 6.5 Display controls

The display controls enable the user to configure the text or plot displays as required. The per pillar 3D displacement, per pillar 3D force and global 3D force and global 3D torque can be displayed as either text or plots. Each combination of options is described in the sections below.

# 6.5.1 Per pillar 3D displacement or 3D force values

For each pillar, the calibrated displacement or force values (in the X-, Y- and Z-axis) are displayed can be displayed as text. The relative locations of a block of values for one pillar corresponds to the pillar location in the sensor visualisation. The X-, Y- and Z-axis displacements or forces are arranged in separate rows. Figure 6.5 shows the displacement and force values displayed as text.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/ba199cbc3722cf84623bd69097c8ae1fecbcfc1c1f994f660b5c6d76151d4e69.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/77ba29a4f51c9569b3548fab705125878ac7b3550239a33e7a0f198185d43faa.jpg)



Figure 6.5 – Left: Pillar displacements arranged vertically as DX, DY, DZ for each pillar in a sensor. Right: Pillar forces arranged vertically as FX, FY, FZ.


# 6.5.2 Per pillar 3D displacement or 3D force plots

For each pillar, the calibrated X-, Y- and Z-axis forces vs. time can be displayed in a single plot. The relative locations of the force vs. time plots correspond to the pillar location in the sensor visualisation. The X-axis force is displayed as a yellow trace, the Y-axis force is displayed as a green trace, and the Z-axis force is displayed as a blue trace. Figure 6.6 shows a displacement vs. time and force vs. time plot for a single pillar.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/9f61749443b8fbd62be22957b2d2c3863cb195c4a09b718afd03f03db4c19312.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/e281f6e6f4fa339881d1c4c848539256bb922f86b369b3c9bd14746508afbd47.jpg)



Figure 6.6 – Left: 3D Displacement vs. time plot of pillar 8. Right: 3D Force vs. time plot of pillar 8. The X-axis data, Y-axis data and Z-axis data are displayed in yellow, green and blue, respectively.


# 6.5.3 Global force and torque

The global 3D force and global 3D torque of each sensor can be displayed. The torque reference point is the current tip position of the centre pillar (P4). The X-axis force is displayed as a yellow trace, the Y-axis force is displayed as a green trace, and the Z-axis force is displayed as a blue trace.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/017f4a4366329bd092558328b5d5f8527d272a4d5906450f87f7a348a72e2e5d.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/955f5aee13fc4c72a684bf7c50e7413c3de53c0ded88adfbcbed0c3f8c0e3219.jpg)



Figure 6.7 – Left: Global 3D force and global 3D torque text values for a sensor. Right: Global 3D force vs. time plot and global 3D torque vs time for a sensor. The X-axis data, Y-axis data and Zaxis data are displayed in yellow, green and blue, respectively.


# 6.5.4 Change graph Y-axis limits

To increase the y-axis resolution of the per pillar displacement, per pillar force or global force and global torque (i.e., reduce the limits of y-axis) vs. time plots, click on the Toggle Graph Y-Range button. Each time the Toggle Graph Y-Range button is pressed, the graph y-axis limits will reduce, until a minimum value. If the graph y-axis limits are at the minimum value and the Toggle Graph Y-Range button is pressed, then the y-axis limits will reset to the maximum limit.

# Toggle Graph Y-Range

Figure 6.8 – Toggling graph y-range

# 7 GUI controls

# 7.1 Changing the COM port

The GUI controls related to the serial connection are shown in Figure 7.1. To change the COM port number of the serial connection to the Controller:

1. If the GUI is already connected to a COM port, click the Disconnect button.

2. Select the appropriate COM port number from the COM Port drop down list.

3. Click on the Connect button.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/52671f135bf08b8e9f1562da6312d217b094dc24252c93ce71a6373f01ebc1cc.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/a64cd3d0db2686eff7eeccf05bc809c432d099d7744103c111112864b2a14443.jpg)



Figure 7.1 – Changing the COM port in the GUI and connecting


# 7.2 Biasing the sensor data

To bias the data (i.e., remove any offset in the calibrated displacement and force data), ensure that the sensor is unloaded and the signals are in a steady state, click on the Bias Sensors button (Figure 7.2). The bias operation takes approximately 2 s. Ensure that the sensor remains unloaded throughout this time. The sensor calibrated displacement and force signals should become zero after this point.

# Bias Sensors

Figure 7.2 – Biasing the sensors

If a bias is initiated in one instance of the visualisation software (connected to the MAIN), it will be processed in all running instances of the visualisation software as well as any program using the C++ library that is also reading from the same Controller (and vice versa).

It is recommended that the sensors are biased each time the sensors are know to be unloaded – particularly during the first 20 minutes of operation when the sensors are warming up to a steadystate temperature.

# 7.3 Start/stop slip detection

Slip detection can be activated by clicking the Start Slip Detection button. This will activate the slip detection algorithms on the controller, the slip status legend will appear between the two sensor visual representations and more (see Section 6.4 Slip detection and friction display). To stop slip detection, select the Stop Slip Detection button.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/217e6a1ab3a65c377fcf3621b0ca9b4c3801bc75ddbcbb288d413959813495e9.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/4181801cca30fb298ccc48f6499ba144d94d5cda62290d51d5b6976bf76a3c4d.jpg)



Figure 7.3 – Start and stop slip detection


# 7.4 Log file controls

The log file controls are shown in Figure 7.4.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-05-16/6be56f84-0c73-48f3-97c7-dc32f497b434/2a81448f458008ec5075979c6962ac5ee106499bd5bb0e0fc220c6370ea20e8d.jpg)



Figure 7.4 – Left: Log file controls before starting a log. Right: Log files control during logging


# 7.4.1 Changing the log file rate

To change the log file sampling rate, select the appropriate rate from the drop down list. The log file sampling rate can only be changed when the GUI is not logging data.

# 7.4.2 Start/stop logging

To start logging data, click on the Start Log button. If data logging had previously been started, the Start Log button will toggle to display Stop Log, and the status text under the Log area will display “Logging” followed by the number of samples logged so far. click on the Stop and Save button to stop logging and save the log file – see Section 8 Log file for more information about the log file.

# 7.5 Keyboard shortcuts

Keyboard shortcuts are displayed in square brackets next to each control button.

# 8 Log file

# 8.1 Overview


^ The torque reference point is the current tip position of the centre pillar (P4).


The visualisation software also generates a log file of the sensor data, including raw photodiode values, calibrated X-, Y- and Z-axis displacement values, calibrated X-, Y- and Z-axis force values, slip detection and friction estimates.

# 8.2 Log file location

The log file that is generated is stored in the Logs subfolder in the same location as the Visualisation Software executable file (PTSVIS_2.1.exe) which was run to launch the GUI.

# 8.3 Log file name

The name of the log file that is generated is LOG_YYMMDD_hhmmss.csv where YY is the two digit year, MM is the two digit month, DD is the two digit day, hh is the two digit hour, mm is the two digit minute and ss is the two digit second from the system clock at the time that the log file was created.

# 8.4 Log file format

The log file is saved as comma-separated values (CSV) in ASCII text format. The order of the values and a description is shown in Table 8.1


Table 8.1 – Data in log file


<table><tr><td>Data Order</td><td>Data Name</td><td>Data Description</td><td></td></tr><tr><td>1</td><td>T_us</td><td>Timestamp in μs</td><td>Timestamps</td></tr><tr><td>2</td><td>S0_P0_DX</td><td>Sensor 0, pillar 0, X-axis displacement (mm)</td><td rowspan="3">Sensor 0, pillar 0, displacements</td></tr><tr><td>3</td><td>S0_P0_DY</td><td>Sensor 0, pillar 0, Y-axis displacement (mm)</td></tr><tr><td>4</td><td>S0_P0_DZ</td><td>Sensor 0, pillar 0, Z-axis displacement (mm)</td></tr><tr><td>5</td><td>S0_P0_FX</td><td>Sensor 0, pillar 0, X-axis force (N)</td><td rowspan="3">Sensor 0, pillar 0, forces</td></tr><tr><td>6</td><td>S0_P0_FY</td><td>Sensor 0, pillar 0, Y-axis force (N)</td></tr><tr><td>7</td><td>S0_P0_FZ</td><td>Sensor 0, pillar 0, Z-axis force (N)</td></tr><tr><td>8</td><td>S0_P1_DX</td><td>Sensor 0, pillar 1, X-axis displacement (mm)</td><td rowspan="3">Sensor 0, pillar 1, displacements</td></tr><tr><td>9</td><td>S0_P1_DY</td><td>Sensor 0, pillar 1, Y-axis displacement (mm)</td></tr><tr><td>10</td><td>S0_P1_DZ</td><td>Sensor 0, pillar 1, Z-axis displacement (mm)</td></tr><tr><td>11</td><td>S0_P1_FX</td><td>Sensor 0, pillar 1, X-axis force (N)</td><td rowspan="3">Sensor 0, pillar 1, forces</td></tr><tr><td>12</td><td>S0_P1_FY</td><td>Sensor 0, pillar 1, Y-axis force (N)</td></tr><tr><td>13</td><td>S0_P1_FZ</td><td>Sensor 0, pillar 1, Z-axis force (N)</td></tr><tr><td colspan="4">⋮</td></tr><tr><td>50</td><td>S0_P8_DX</td><td>Sensor 0, pillar 8, X-axis displacement (mm)</td><td rowspan="3">Sensor 0, pillar 8, displacements</td></tr><tr><td>51</td><td>S0_P8_DY</td><td>Sensor 0, pillar 8, Y-axis displacement (mm)</td></tr><tr><td>52</td><td>S0_P8_DZ</td><td>Sensor 0, pillar 8, Z-axis displacement (mm)</td></tr><tr><td>53</td><td>S0_P8_FX</td><td>Sensor 0, pillar 8, X-axis force (N)</td><td rowspan="3">Sensor 0, pillar 8, forces</td></tr><tr><td>54</td><td>S0_P8_FY</td><td>Sensor 0, pillar 8, Y-axis force (N)</td></tr><tr><td>55</td><td>S0_P8_FZ</td><td>Sensor 0, pillar 8, Z-axis force (N)</td></tr><tr><td>56</td><td>S0_GG_FX</td><td>Sensor 0, global X-axis force (N)</td><td rowspan="3">Sensor 0, global force</td></tr><tr><td>57</td><td>S0_GG_FY</td><td>Sensor 0, global Y-axis force (N)</td></tr><tr><td>58</td><td>S0_GG_FZ</td><td>Sensor 0, global Z-axis force (N)</td></tr><tr><td>59</td><td>S0_GG_TX</td><td>Sensor 0, global X-axis torque (Nmm)<eq>^</eq></td><td rowspan="3">Sensor 0, global torque<eq>^</eq></td></tr><tr><td>60</td><td>S0_GG_TY</td><td>Sensor 0, global Y-axis torque (Nmm)<eq>^</eq></td></tr><tr><td>61</td><td>S0_GG_TZ</td><td>Sensor 0, global Z-axis torque (Nmm)<eq>^</eq></td></tr><tr><td>62</td><td>S0_isSDActive</td><td>Sensor 0, is slip detection activated</td><td rowspan="10">Sensor 0 slip detection and friction estimate</td></tr><tr><td>63</td><td>S0_isRefLoad</td><td>Sensor 0, is the reference pillar tangentially loaded</td></tr><tr><td>64</td><td>S0_P0_isInContact</td><td>Sensor 0, pillar 0, is in contact</td></tr><tr><td>65</td><td>S0_P0_slipState</td><td>Sensor 0, pillar 0, slip state</td></tr><tr><td>66</td><td>S0_P1_isInContact</td><td>Sensor 0, pillar 1, is in contact</td></tr><tr><td>67</td><td>S0_P1_slipState</td><td>Sensor 0, pillar 1, slip state</td></tr><tr><td colspan="3">⋮</td></tr><tr><td>80</td><td>S0_P8_isInContact</td><td>Sensor 0, pillar 8, is in contact</td></tr><tr><td>81</td><td>S0_P8_slipState</td><td>Sensor 0, pillar 8, slip state</td></tr><tr><td>82</td><td>S0_FrictionEst</td><td>Sensor 0, friction estimate</td></tr><tr><td>83</td><td>S1_P0_DX</td><td>Sensor 1, pillar 0, X-axis displacement (mm)</td><td rowspan="3">Sensor 1, pillar 0, displacements</td></tr><tr><td>84</td><td>S1_P0_DY</td><td>Sensor 1, pillar 0, Y-axis displacement (mm)</td></tr><tr><td>85</td><td>S1_P0_DZ</td><td>Sensor 1, pillar 0, Z-axis displacement (mm)</td></tr><tr><td>86</td><td>S1_P0_FX</td><td>Sensor 1, pillar 0, X-axis force (N)</td><td rowspan="3">Sensor 1, pillar 0, forces</td></tr><tr><td>87</td><td>S1_P0_FY</td><td>Sensor 1, pillar 0, Y-axis force (N)</td></tr><tr><td>88</td><td>S1_P0_FZ</td><td>Sensor 1, pillar 0, Z-axis force (N)</td></tr><tr><td>89</td><td>S1_P1_DX</td><td>Sensor 1, pillar 1, X-axis displacement (mm)</td><td rowspan="3">Sensor 1, pillar 1, displacements</td></tr><tr><td>90</td><td>S1_P1_DY</td><td>Sensor 1, pillar 1, Y-axis displacement (mm)</td></tr><tr><td>91</td><td>S1_P1_DZ</td><td>Sensor 1, pillar 1, Z-axis displacement (mm)</td></tr><tr><td>92</td><td>S1_P1_FX</td><td>Sensor 1, pillar 1, X-axis force (N)</td><td rowspan="3">Sensor 1, pillar 1, forces</td></tr><tr><td>93</td><td>S1_P1_FY</td><td>Sensor 1, pillar 1, Y-axis force (N)</td></tr><tr><td>94</td><td>S1_P1_FZ</td><td>Sensor 1, pillar 1, Z-axis force (N)</td></tr><tr><td colspan="4">...</td></tr><tr><td>131</td><td>S1_P8_DX</td><td>Sensor 1, pillar 8, X-axis displacement (mm)</td><td rowspan="3">Sensor 1, pillar 8, displacements</td></tr><tr><td>132</td><td>S1_P8_DY</td><td>Sensor 1, pillar 8, Y-axis displacement (mm)</td></tr><tr><td>133</td><td>S1_P8_DZ</td><td>Sensor 1, pillar 8, Z-axis displacement (mm)</td></tr><tr><td>134</td><td>S1_P8_FX</td><td>Sensor 1, pillar 8, X-axis force (N)</td><td rowspan="3">Sensor 1, pillar 8, forces</td></tr><tr><td>135</td><td>S1_P8_FY</td><td>Sensor 1, pillar 8, Y-axis force (N)</td></tr><tr><td>136</td><td>S1_P8_FZ</td><td>Sensor 1, pillar 8, Z-axis force (N)</td></tr><tr><td>137</td><td>S1_GG_FX</td><td>Sensor 1, global X-axis force (N)</td><td rowspan="3">Sensor 1, global force</td></tr><tr><td>138</td><td>S1_GG_FY</td><td>Sensor 1, global y-axis force (N)</td></tr><tr><td>139</td><td>S1_GG_FZ</td><td>Sensor 1, global Z-axis force (N)</td></tr><tr><td>140</td><td>S1_GG_TX</td><td>Sensor 1, global X-axis torque (Nmm)<eq>^</eq></td><td rowspan="3">Sensor 1, global torque<eq>^</eq></td></tr><tr><td>141</td><td>S1_GG_TY</td><td>Sensor 1, global Y-axis torque (Nmm)<eq>^</eq></td></tr><tr><td>142</td><td>S1_GG_TZ</td><td>Sensor 1, global Z-axis torque (Nmm)<eq>^</eq></td></tr><tr><td>143</td><td>S0_isSDActive</td><td>Sensor 1, is slip detection activated</td><td rowspan="10">Sensor 1 slip detection and friction estimate</td></tr><tr><td>144</td><td>S0_isRefLoad</td><td>Sensor 1, is the reference pillar tangentially loaded</td></tr><tr><td>145</td><td>S0_P0_isInContact</td><td>Sensor 1, pillar 0, is in contact</td></tr><tr><td>146</td><td>S0_P0_slipState</td><td>Sensor 1, pillar 0, slip state</td></tr><tr><td>147</td><td>S0_P1_isInContact</td><td>Sensor 1, pillar 1, is in contact</td></tr><tr><td>148</td><td>S0_P1_slipState</td><td>Sensor 1, pillar 1, slip state</td></tr><tr><td colspan="3">⋮</td></tr><tr><td>161</td><td>S0_P8_isInContact</td><td>Sensor 1, pillar 8, is in contact</td></tr><tr><td>162</td><td>S0_P8_slipState</td><td>Sensor 1, pillar 8, slip state</td></tr><tr><td>163</td><td>S0_FrictionEst</td><td>Sensor 1, friction estimate</td></tr></table>