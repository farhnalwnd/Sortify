# ultrasonic_sensor.py

import time
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

# MQTT config
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC_CAPACITY = "waste/bin_status"

# Ultrasonic sensor pin config
TRIG_PIN = 18
ECHO_PIN = 24

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

# MQTT setup
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)

def read_distance():
    GPIO.output(TRIG_PIN, False)
    time.sleep(0.05)

    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.time()

    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150  # cm
    return round(distance, 2)

def calculate_bin_capacity(distance_cm):
    max_distance = 50.0  # 40 cm bin + 10 cm gap
    filled_percent = max(0, min(100, (1 - (distance_cm / max_distance)) * 100))
    return round(filled_percent, 2)

try:
    while True:
        distance = read_distance()
        capacity = calculate_bin_capacity(distance)
        print(f"[ULTRASONIC] Jarak: {distance} cm, Kapasitas: {capacity}%")
        client.publish(MQTT_TOPIC_CAPACITY, f"{capacity}%")
        time.sleep(10)  # Kirim setiap 10 detik
except KeyboardInterrupt:
    print("Dihentikan oleh user")
finally:
    GPIO.cleanup()
