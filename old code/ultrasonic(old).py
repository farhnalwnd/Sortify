# ultrasonic.py
import time
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

# MQTT config
[cite_start]MQTT_BROKER = "broker.emqx.io" # [cite: 1]
[cite_start]MQTT_PORT = 1883 # [cite: 1]
[cite_start]MQTT_TOPIC_CAPACITY = "waste/bin_status" # [cite: 1]

# Ultrasonic sensor pin config
[cite_start]TRIG_PIN = 18 # [cite: 1]
[cite_start]ECHO_PIN = 24 # [cite: 1]

# Setup GPIO
[cite_start]GPIO.setmode(GPIO.BCM) # [cite: 1]
[cite_start]GPIO.setup(TRIG_PIN, GPIO.OUT) # [cite: 1]
[cite_start]GPIO.setup(ECHO_PIN, GPIO.IN) # [cite: 1]

# MQTT setup
[cite_start]client = mqtt.Client() # [cite: 1]
[cite_start]client.connect(MQTT_BROKER, MQTT_PORT, 60) # [cite: 1]

def read_distance():
    [cite_start]GPIO.output(TRIG_PIN, False) # [cite: 1]
    time.sleep(0.05)

    [cite_start]GPIO.output(TRIG_PIN, True) # [cite: 1]
    [cite_start]time.sleep(0.00001) # [cite: 1]
    [cite_start]GPIO.output(TRIG_PIN, False) # [cite: 1]

    [cite_start]pulse_start = time.time() # [cite: 1]
    [cite_start]pulse_end = time.time() # [cite: 1]

    [cite_start]while GPIO.input(ECHO_PIN) == 0: # [cite: 1]
        [cite_start]pulse_start = time.time() # [cite: 1]

    [cite_start]while GPIO.input(ECHO_PIN) == 1: # [cite: 1]
        [cite_start]pulse_end = time.time() # [cite: 1]

    [cite_start]pulse_duration = pulse_end - pulse_start # [cite: 1]
    [cite_start]distance = pulse_duration * 17150  # cm [cite: 1]
    [cite_start]return round(distance, 2) # [cite: 1]

def calculate_bin_capacity(distance_cm):
    [cite_start]max_distance = 50.0  # 40 cm bin + 10 cm gap [cite: 1]
    [cite_start]filled_percent = max(0, min(100, (1 - (distance_cm / max_distance)) * 100)) # [cite: 1]
    [cite_start]return round(filled_percent, 2) # [cite: 1]

try:
    while True:
        [cite_start]distance = read_distance() # [cite: 1]
        [cite_start]capacity = calculate_bin_capacity(distance) # [cite: 1]
        print(f"[ULTRASONIC] Jarak: {distance} cm, Kapasitas: {capacity}%")
        [cite_start]client.publish(MQTT_TOPIC_CAPACITY, f"{capacity}%") # [cite: 1]
        [cite_start]time.sleep(10) # [cite: 1]
except KeyboardInterrupt:
    [cite_start]print("Dihentikan oleh user") # [cite: 1]
finally:
    [cite_start]GPIO.cleanup() # [cite: 1]