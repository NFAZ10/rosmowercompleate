#!/usr/bin/env python3
"""
Simple MQTT subscriber to test the bridge
"""

import paho.mqtt.client as mqtt
import json
import sys


def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code: {rc}")
    # Subscribe to all rosmower topics
    client.subscribe("rosmower/#")
    print("Subscribed to rosmower/#")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"\n[{msg.topic}]")
        print(json.dumps(payload, indent=2))
    except:
        print(f"\n[{msg.topic}] {msg.payload.decode()}")


def main():
    broker = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"Connecting to MQTT broker at {broker}:1883...")
    client.connect(broker, 1883, 60)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nDisconnecting...")
        client.disconnect()


if __name__ == "__main__":
    main()
