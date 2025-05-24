import time
import threading
import os
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from picamera2 import Picamera2
import cv2

# MQTT config
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC_SUB = "waste/raw"
MQTT_TOPIC_PUB = "waste/raw"

# Load YOLO model
model = YOLO("models/best.pt")

# Pastikan folder images/ ada
IMAGES_DIR = "/home/admin/caps/aiCameraDetection/images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# Status flag
running = False
process_command = None  # Bisa "start", "insert again", atau None

def classify_and_publish(picam2):
    print("Delay 5 detik sebelum klasifikasi...")
    time.sleep(5)

    frame = picam2.capture_array()
    results = model(frame)

    timestamp = int(time.time())
    filename = f"classified_{timestamp}.jpg"
    filepath = os.path.join(IMAGES_DIR, filename)
    annotated = results[0].plot()
    cv2.imwrite(filepath, annotated)
    print(f"Gambar disimpan: {filepath}")

    try:
        result = results[0]
        label_str = "no object detected"

        if result.boxes and result.boxes.cls is not None and len(result.boxes.cls) > 0:
            class_ids = result.boxes.cls.tolist()
            confidences = result.boxes.conf.tolist()
            max_index = confidences.index(max(confidences))
            best_class = int(class_ids[max_index])
            best_label = model.names[best_class]
            best_conf = confidences[max_index]
            label_str = f"{best_label} ({best_conf:.2f})"

        elif result.probs is not None:
            probs = result.probs.data.tolist()
            max_index = probs.index(max(probs))
            best_label = model.names[max_index]
            best_conf = probs[max_index]
            label_str = best_label

    except Exception as e:
        print(f"Error saat klasifikasi: {e}")
        label_str = "no object detected"

    print(f"Hasil klasifikasi: {label_str}")
    client.publish(MQTT_TOPIC_PUB, label_str)

def camera_loop():
    global running, process_command

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (512, 384)})
    picam2.configure(config)
    picam2.start()

    while True:
        if running and process_command:
            print(f"Menangani perintah: {process_command}")
            classify_and_publish(picam2)
            process_command = None  # Reset agar menunggu perintah baru
        time.sleep(0.5)

    picam2.close()
    cv2.destroyAllWindows()

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Terhubung ke MQTT broker dengan kode: {rc}")
    client.subscribe(MQTT_TOPIC_SUB)

def on_message(client, userdata, msg):
    global running, process_command
    message = msg.payload.decode().strip().lower()
    print(f"Pesan diterima: {message}")

    if message == "start":
        running = True
        process_command = "start"
        print("Perintah 'start' diterima. Menyiapkan klasifikasi.")
    elif message == "insert again":
        if running:
            process_command = "insert again"
            print("Perintah 'insert again' diterima. Menyiapkan klasifikasi ulang.")
    elif message == "stop":
        running = False
        process_command = None
        print("Proses klasifikasi dihentikan.")

# Setup MQTT
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Jalankan kamera di thread terpisah
camera_thread = threading.Thread(target=camera_loop)
camera_thread.daemon = True
camera_thread.start()

# Loop MQTT
client.loop_forever()
