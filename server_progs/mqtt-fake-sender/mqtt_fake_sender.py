import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime, timezone
import os

BROKER_HOST = os.getenv("BROKER_HOST", "mosquitto")
BROKER_PORT = int(os.getenv("BROKER_PORT", "1883"))
TOPIC = os.getenv("TOPIC", "/events")
METEO_UUID = os.getenv("METEO_UUID", "2cf7f1c043900193")
SENSOR_UUID = os.getenv("SENSOR_UUID", "2cf7f1c043900193_measurement8")

def make_payload():
    return {
        "meteo_UUID": METEO_UUID,
        "sensor_UUID": SENSOR_UUID,
        "value": random.randint(0, 100),
        "time": datetime.now(timezone.utc).isoformat()
    }

def main():
    client = mqtt.Client()
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    print("Connected to MQTT broker.")
    while True:
        payload = make_payload()
        msg = json.dumps(payload)
        print(f"Publishing: {msg}")
        client.publish(TOPIC, msg)
        time.sleep(60)

if __name__ == "__main__":
    main()