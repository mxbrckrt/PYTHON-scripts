==========================================================================================================
              x-IMU3 to Max/MSP Multi-Sensor Bridge
              Author Max Bruckert
==========================================================================================================.

Project Context
This project was developed as a high-performance alternative to native Max/MSP UDP processing (such as the SADAM library). It was specifically engineered to handle the rigorous data demands of the production **"Eternal Dawn" by Alexander Schubert (2025)**.

The Problem
Processing high-density data from **15+ X-IO x-imu3 sensors** within Max/MSP presents significant challenges:
    - Thread 0 Congestion:** Objects like `atoi` and `sprintf` create high overhead on the main message thread.
    - Buffer Overflow:** High-rate UDP packets can lead to "unemptied buffers," causing lag or system instability.
    - Single-threaded Limits:** Max's scheduler struggles to scale when every sensor streams 9-axis data, Euler angles, and metadata simultaneously.

The Solution
This Python-based bridge offloads the decoding and routing to a dedicated multi-threaded environment:
    - Parallel Processing:** Utilizes Python's threading to listen to 15 sensors independently.
    - Efficient Decoding:** Decodes raw sensor packets and formats them into structured OSC messages.
    - Human-Readable OSC:** Streams data back to Max/MSP via local UDP (e.g., `/sensor-01/accel`, `/sensor-05/gyro`).
    - Universal Analytics:** Includes a standalone engine for dynamic scaling, smoothing, and statistical analysis (Min, Max, Avg, StDev, Magnitude).

CONCEPT:
This setup uses a separate Python scripts to keep Max/MSP running smoothly.
    - Like "Hand-Gluing" 15 sensors to your computer it starts with a handshake with every available sensor to link it to your machine.
    - It catches 15 raw UDP streams simultaneously, cleans the data, and hands it to Max/MSP as labeled OSC messages.


SOFTWARE REQUIREMENTS
    - Python 3.9 or higher.
    - Library: python-osc
  -> Install via terminal: pip3 install python-osc


NETWORK CONFIGURATION
Ensure your x-IMU3 sensors are configured to the correct IP range (defaulting to 192.168.0.41 - 55) and are sending data to the corresponding ports (8001 - 8015). This can be done in with the x-IMU3 GUI app (https://x-io.co.uk/x-imu3/#downloads)
    - Computer IP: 192.168.0.10 (Manual/Static)
    - Subnet Mask: 255.255.255.0
    - Sensor IPs: 192.168.0.41 through 192.168.0.55

DATA MAP (OSC) : From Bridge to Max (Port 9999)
| Address | Arguments | Description |
| :--- | :--- | :--- |
| `/sensor-XX/gyro` | `float x, y, z` | Angular velocity |
| `/sensor-XX/accel` | `float x, y, z` | Linear acceleration |
| `/sensor-XX/euler` | `float p, r, y` | Pitch, Roll, Yaw (Orientation) |
| `/sensor-XX/mag` | `float x, y, z` | Magnetic field data |

Note: Battery levels are monitored and printed in the terminal every 60s but are not sent over OSC to preserve network bandwidth for motion data.*


Usage :
You can run the scripts directly from the terminal:
python3 multi_sensor_bridge.py
