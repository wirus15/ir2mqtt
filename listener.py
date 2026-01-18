import broadlink
import json
import os
import paho.mqtt.client as mqtt
import time

DEVICE_HOST = os.getenv("DEVICE_HOST", "")
MQTT_HOST = os.getenv("MQTT_HOST", "homeassistant.local")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "broadlink/raw")
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

interval = 0.05

# Broadlink
print("Connecting to Broadlink device at {DEVICE_HOST}")
device = broadlink.hello(DEVICE_HOST)
device.auth()

# MQTT
print("Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}, topic: {MQTT_TOPIC}")
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
mqtt_client.loop_start()

print("Listening for IR commands...")

last_code = None

codes_map = {
    "111211211111111111111111111": "power",
    "111111122111111111111111111": "volume_up",
    "21111221111111111111111111": "volume_down",
    "221122112111111111111111": "red",
    "1211112211211111111111111": "green",
    "11111122112111111111111111": "yellow",
    "111111121111211111111111111": "blue",
    "1211111111222111111111111": "expo",
    "11111122111111111111111111": "hello",
}

def decode_command(code_hex):
    code_bytes = bytes.fromhex(code_hex)
    pulses = broadlink.remote.data_to_pulses(code_bytes)
    command = ''
    recording = False
    values_total = 0

    for p in pulses[::-1]:
        if (p > 50000):
            recording = True
            continue
        
        if not recording:
            continue
        
        value = round(p / 500)
        
        if values_total + value >= 30:
            break
        
        command += str(value)
        values_total += value
    
    return command

while True:
    device.enter_learning()
    listening_start_time = time.time()

    while True:
        # Timeout after 30 seconds without successful processing
        if time.time() - listening_start_time >= 30:
            # restart learning mode
            break 
        
        # read ir code, if any
        try:
            code = device.check_data()
        except Exception:
            time.sleep(interval)
            continue
    
        if code:
            hex_code = code.hex()
            if hex_code == last_code:
                time.sleep(interval)
                continue

        # send code via mqtt        
        last_code = hex_code
        command_code = decode_command(hex_code)
        command_name = codes_map.get(command_code, None)

        print("hex code", hex_code)
        print("command code", command_code)
        print("command name", command_name)

        if command_name is not None:
            payload = {
                "command_code": command_code,
                "command_name": command_name,
                "timestamp": time.time(),
                "device": DEVICE_HOST
            }

            mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=0)

        time.sleep(interval)
        break
