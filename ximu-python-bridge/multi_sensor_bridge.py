"""
================================================================================
UDP TO OSC BRIDGE FOR X-IO X-IMU3
Author Max Bruckert
================================================================================
USER GUIDE:
    1. UDP_PORTS_IN: Set from 8001 to 8015.
    2. MAX_PORT: Your software's OSC port (Current: 9999).
    3. Handshake: Automatically sends JSON commands to initiate streaming.
    4. Battery: Printed in terminal only (not sent via OSC).
================================================================================
"""

import socket
import threading
import time
import json
from pythonosc import udp_client

# --- CONFIGURATION ---
SENSOR_IPS = [f"192.168.0.{i}" for i in range(41, 56)]
DATA_PORTS = list(range(8001, 8016))
CMD_PORTS  = list(range(9001, 9016))

MAX_IP = "127.0.0.1"     
MAX_PORT = 9999          
BATTERY_INTERVAL = 60 

last_battery_time = {port: 0 for port in DATA_PORTS}
sensor_online_status = {i+1: False for i in range(len(SENSOR_IPS))}
client = udp_client.SimpleUDPClient(MAX_IP, MAX_PORT)

def send_targeted_handshake():
    """ Sends strobe and enables Magnetometer messages """
    print("=========================================================================")
    print("[INIT] Starting Targeted Handshake Sequence...")
    
    cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 1. Strobe Handshake
    strobe_cmd = bytes([123, 34, 115, 116, 114, 111, 98, 101, 34, 58, 110, 117, 108, 108, 125, 10])
    
    # 2. Enable Magnetometer Message ({"magnetometer":true}\n)
    # This ensures the 'M' header is actually sent by the hardware
    mag_enable_cmd = '{"magnetometer":true}\n'.encode()
    
    for i, ip in enumerate(SENSOR_IPS):
        port = CMD_PORTS[i]
        try:
            cmd_sock.sendto(strobe_cmd, (ip, port))
            time.sleep(0.01) # Small gap between commands
            cmd_sock.sendto(mag_enable_cmd, (ip, port))
        except Exception as e:
            print(f" [!] Error reaching {ip}: {e}")
            
    cmd_sock.close()
    print("[INIT] Handshake and Magnetometer activation sent.")

def sensor_worker(data_port, sensor_index):
    sensor_num = sensor_index + 1
    sensor_id = f"{sensor_num:02d}"
    prefix = f"/sensor-{sensor_id}"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        sock.bind(("0.0.0.0", data_port))
    except: return

    while True:
        try:
            data, addr = sock.recvfrom(2048)
            sensor_online_status[sensor_num] = True
            raw = data.decode('ascii', errors='ignore').strip()
            
            if raw.startswith('{'):
                try:
                    msg = json.loads(raw)
                    if "battery" in msg:
                        val = msg["battery"]
                        if time.time() - last_battery_time[data_port] > BATTERY_INTERVAL:
                            print(f"[BATTERY] Sensor {sensor_id}: {val}%")
                            last_battery_time[data_port] = time.time()
                except: pass
                continue

            for line in raw.split('\n'):
                parts = line.split(',')
                if len(parts) < 2: continue
                header = parts[0].strip()
                try:
                    nums = [float(v) for v in parts[1:] if v.strip()]
                    if len(nums) < 2: continue
                    payload = nums[1:] 

                    # ROUTING LOGIC
                    if header == 'I' and len(payload) >= 6:
                        client.send_message(f"{prefix}/gyro", payload[0:3])
                        client.send_message(f"{prefix}/accel", payload[3:6])
                    elif header == 'A' and len(payload) >= 3:
                        client.send_message(f"{prefix}/euler", payload[0:3])
                    elif header == 'M' and len(payload) >= 3: # Magnetometer Header
                        client.send_message(f"{prefix}/mag", payload[0:3])
                    elif header == 'B' and len(payload) >= 1:
                        val = payload[0]
                        if time.time() - last_battery_time[data_port] > BATTERY_INTERVAL:
                            print(f"[BATTERY] Sensor {sensor_id}: {val}%")
                            last_battery_time[data_port] = time.time()
                except: continue
        except: break

# --- STARTUP ---
print("=========================================================================")
print("  X-IMU3 MULTI-BRIDGE INITIALIZING (IMU + EULER + MAG)")
print("=========================================================================")

for i, p in enumerate(DATA_PORTS):
    threading.Thread(target=sensor_worker, args=(p, i), daemon=True).start()

time.sleep(1)
send_targeted_handshake()

print("[SYSTEM] Monitoring for incoming streams (5s)...")
time.sleep(5)

print("=========================================================================")
print("  CONNECTION SUMMARY")
print("=========================================================================")
for i in range(1, 16):
    status = "ONLINE" if sensor_online_status[i] else "OFFLINE"
    print(f" Sensor {i:02d}: {status}")
print("=========================================================================")

try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    print("\n[SHUTDOWN] Closing bridge.")