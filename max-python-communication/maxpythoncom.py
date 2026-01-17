"""
================================================================================
UNIVERSAL ANALYTICS ENGINE (DYNAMIC SCALING + SMOOTHING + REMOTE CONTROL)
================================================================================
DESCRIPTION:
    A high-speed feature extractor for any 3-axis data (Sensors, Audio, MIDI).
    It automatically scales any input range to a 0.0 - 1.0 "Activity Index".

OSC INTERFACE:
    INPUTS:
        - /analyze/list [f, f, f...] : Data to process (triplets suggested)
        - /smoothing [0.0 - 1.0]     : Adjust filter fluidity (default: 0.5)
        - /reset                     : Clear peak history and recalibrate
    OUTPUTS:
        - /results [min, max, avg, stdev, smoothed_mag]
================================================================================
"""

from pythonosc import udp_client, dispatcher, osc_server, osc_bundle_builder, osc_message_builder
import math

# --- CONFIGURATION ---
MAX_IP = "127.0.0.1"
MAX_PORT_OUT = 9999    
PYTHON_PORT_IN = 8888  

# Global trackers
current_peak = 0.0001 
smoothed_mag = 0.0
smoothing_factor = 0.5 # Default

client = udp_client.SimpleUDPClient(MAX_IP, MAX_PORT_OUT)

def handle_smoothing(address, *args):
    global smoothing_factor
    if args:
        smoothing_factor = max(0.0, min(0.99, float(args[0])))
        print(f"[CONTROL] Smoothing updated to: {smoothing_factor:.2f}")

def handle_reset(address, *args):
    global current_peak, smoothed_mag
    current_peak = 0.0001
    smoothed_mag = 0.0
    print("[SYSTEM] Dynamic Range and Smoothing Reset.")

def handle_list(address, *args):
    global current_peak, smoothed_mag, smoothing_factor
    if not args or len(args) < 3: return
    
    data = list(args)
    n = len(data)
    
    # 1. Stats
    val_min, val_max = min(data), max(data)
    val_avg = sum(data) / n
    variance = sum((x - val_avg) ** 2 for x in data) / n
    val_stdev = math.sqrt(variance)
    
    # 2. Dynamic Normalization
    magnitudes = []
    for i in range(0, n - 2, 3):
        x, y, z = data[i], data[i+1], data[i+2]
        raw_mag = math.sqrt(x**2 + y**2 + z**2)
        if raw_mag > current_peak: current_peak = raw_mag
        magnitudes.append(raw_mag / current_peak)
    
    instant_mag = sum(magnitudes) / len(magnitudes) if magnitudes else 0
    
    # 3. Leaky Integrator (Smoothing)
    smoothed_mag = (instant_mag * (1.0 - smoothing_factor)) + (smoothed_mag * smoothing_factor)
    
    # 4. Build OSC Bundle
    bundle = osc_bundle_builder.OscBundleBuilder(osc_bundle_builder.IMMEDIATELY)
    msg = osc_message_builder.OscMessageBuilder(address="/results")
    for v in [val_min, val_max, val_avg, val_stdev, smoothed_mag]:
        msg.add_arg(float(v))
    bundle.add_content(msg.build())
    client.send(bundle.build())

# --- DOCUMENTATION PRINTER ---
def print_welcome():
    doc = f"""
{"="*60}
  UNIVERSAL ANALYTICS ENGINE v3
{"="*60}
  NETWORK SETUP:
  -> Listening on Port: {PYTHON_PORT_IN}
  -> Sending to Max on: {MAX_IP}:{MAX_PORT_OUT}

  OSC COMMANDS (Send from Max):
  1. /analyze/list [values] : Process list of data
  2. /smoothing [0.0-1.0]   : Set fluidity (Current: {smoothing_factor})
  3. /reset                 : Recalibrate Peak range

  DATA OUTPUT (OSC Bundle /results):
  [Min] [Max] [Average] [StDev] [Smoothed Magnitude]
{"="*60}
  READY AND LISTENING...
    """
    print(doc)

if __name__ == "__main__":
    disp = dispatcher.Dispatcher()
    disp.map("/analyze/list", handle_list)
    disp.map("/smoothing", handle_smoothing)
    disp.map("/reset", handle_reset)
    
    server = osc_server.OSCUDPServer(("127.0.0.1", PYTHON_PORT_IN), disp)
    print_welcome()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Engine closed safely.")