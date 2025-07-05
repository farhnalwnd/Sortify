import time
import threading
import os
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from picamera2 import Picamera2
import cv2
import RPi.GPIO as GPIO

# MQTT config
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC_SUB = "waste/raw"
MQTT_TOPIC_PUB = "waste/raw"

# Servo config
SERVO_PIN = 12
SERVO_FREQ = 50

SERVO_POSITIONS = {
    "plastic": 20,
    "paper": 95,
    "organic": 150
}

model = YOLO("models/best.pt")

IMAGES_DIR = "/home/admin/caps/aiCameraDetection/images"
os.makedirs(IMAGES_DIR, exist_ok=True)

running = False
process_command = None

GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo_pwm = GPIO.PWM(SERVO_PIN, SERVO_FREQ)
servo_pwm.start(0)

def angle_to_duty_cycle(angle):
    return 2 + (angle / 180) * 10

def move_servo(angle):
    try:
        duty = angle_to_duty_cycle(angle)
        servo_pwm.ChangeDutyCycle(duty)
        time.sleep(0.5)
        servo_pwm.ChangeDutyCycle(0)
        print(f"[SERVO] Moved to {angle}°")
    except Exception as e:
        print(f"[SERVO ERROR] {e}")

def get_servo_position(label):
    label = label.split('(')[0].strip().lower()
    if "plastic" in label or "plastik" in label:
        return SERVO_POSITIONS["plastic"]
    elif "paper" in label or "kertas" in label:
        return SERVO_POSITIONS["paper"]
    elif "organic" in label or "organik" in label:
        return SERVO_POSITIONS["organic"]
    return None

def classify_and_publish(picam2):
    print("[CAMERA] persiapan mengambil gambar")
    time.sleep(5)
    frame = picam2.capture_array()
    results = model(frame)

    timestamp = int(time.time())
    filepath = os.path.join(IMAGES_DIR, f"classified_{timestamp}.jpg")
    annotated = results[0].plot()
    cv2.imwrite(filepath, annotated)
    print(f"[CAMERA] saved: {filepath}")

    try:
        result = results[0]
        label_str = "no object detected"
        if result.boxes and result.boxes.cls is not None and len(result.boxes.cls) > 0:
            class_ids = result.boxes.cls.tolist()
            confidences = result.boxes.conf.tolist()
            best_idx = confidences.index(max(confidences))
            best_label = model.names[int(class_ids[best_idx])]
            best_conf = confidences[best_idx]
            label_str = f"{best_label} ({best_conf:.2f})"
        elif result.probs is not None:
            probs = result.probs.data.tolist()
            max_index = probs.index(max(probs))
            label_str = model.names[max_index]
    except Exception as e:
        print(f"[YOLO ERROR] {e}")
        label_str = "no object detected"

    print(f"[CLASSIFICATION] {label_str}")
    
    if label_str != "no object detected":
        angle = get_servo_position(label_str)
        if angle is not None:
            move_servo(angle)
        else:
            print("[SERVO] No matching class found.")
    client.publish(MQTT_TOPIC_PUB, label_str)

def camera_loop():
    global running, process_command
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 640)})
    picam2.configure(config)
    picam2.start()

    while True:
        if running and process_command:
            print(f"[CAMERA LOOP] Perintah: {process_command}")
            classify_and_publish(picam2)
            process_command = None
        time.sleep(0.5)

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Terhubung dengan kode {rc}")
    client.subscribe(MQTT_TOPIC_SUB)

def on_message(client, userdata, msg):
    global running, process_command
    message = msg.payload.decode().strip().lower()
    print(f"[MQTT] Pesan diterima: {message}")
    if message == "start":
        running = True
        process_command = "start"
    elif message == "insert again" and running:
        process_command = "insert again"
    elif message == "stop":
        running = False
        process_command = None

def cleanup():
    servo_pwm.stop()
    GPIO.cleanup()
    print("[CLEANUP] GPIO dibersihkan")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

camera_thread = threading.Thread(target=camera_loop)
camera_thread.daemon = True
camera_thread.start()

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("[EXIT] Program dihentikan oleh user")
finally:
    cleanup()
