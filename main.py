# main.py (Versi Final dengan Kontrol LED Relay)
import time
import threading
import os
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from picamera2 import Picamera2
import cv2
import RPi.GPIO as GPIO # <-- Impor library GPIO

# --- Konfigurasi ---
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "waste/raw"

MODEL_PATH = "models/best.pt"
IMAGES_DIR = "/home/admin/caps/aiCameraDetection/images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# --- Konfigurasi Hardware ---
LED_RELAY_PIN = 26 # <-- Tentukan pin GPIO untuk relay LED strip

# Inisialisasi GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_RELAY_PIN, GPIO.OUT)
GPIO.output(LED_RELAY_PIN, GPIO.LOW) # Pastikan relay mati di awal

# Variabel Global untuk Kontrol Thread
running = False
process_command = None

# --- Inisialisasi Model ---
try:
    model = YOLO(MODEL_PATH)
except Exception as e:
    print(f"[ERROR] Gagal memuat model YOLO: {e}")
    exit()

# --- Fungsi Kontrol LED ---
def control_led_timed():
    """Menyalakan LED selama 4 detik tanpa memblokir thread utama."""
    try:
        print("[LED] Menyalakan lampu...")
        GPIO.output(LED_RELAY_PIN, GPIO.HIGH) # Nyalakan relay (LED ON)
        time.sleep(4)
    finally:
        GPIO.output(LED_RELAY_PIN, GPIO.LOW) # Matikan relay (LED OFF)
        print("[LED] Mematikan lampu.")

# --- Fungsi Utama ---
def classify_and_publish(picam2, mqtt_client):
    """
    Fungsi hybrid yang bisa menangani model deteksi (boxes) dan klasifikasi (probs).
    """
    print("[CAMERA] Persiapan mengambil gambar...")
    time.sleep(5) # Waktu tunggu ini mungkin bisa disesuaikan/dikurangi jika LED sudah menyala
    frame = picam2.capture_array()
    
    print("[YOLO] Memproses gambar...")
    results = model(frame)

    timestamp = int(time.time())
    filepath = os.path.join(IMAGES_DIR, f"classified_{timestamp}.jpg")
    try:
        annotated_frame = results[0].plot()
        cv2.imwrite(filepath, annotated_frame)
        print(f"[CAMERA] Gambar anotasi disimpan di: {filepath}")
    except Exception as plot_error:
        print(f"[PLOT ERROR] Gagal membuat anotasi, menyimpan gambar asli: {plot_error}")
        cv2.imwrite(filepath, frame)

    label_str = "no object detected"
    
    try:
        result = results[0]
        
        # --- KONDISI 1: JIKA MODEL ADALAH DETEKSI OBJEK ---
        if result.boxes and len(result.boxes) > 0:
            print("[INFO] Model terdeteksi sebagai 'Detection Model'. Memproses 'boxes'.")
            confidences = result.boxes.conf.tolist()
            class_ids = result.boxes.cls.tolist()
            
            best_idx = confidences.index(max(confidences))
            best_label = model.names[int(class_ids[best_idx])]
            best_conf = confidences[best_idx]
            
            label_str = f"{best_label} ({best_conf:.2f})"

        # --- KONDISI 2: JIKA MODEL ADALAH KLASIFIKASI GAMBAR ---
        elif result.probs is not None:
            print("[INFO] Model terdeteksi sebagai 'Classification Model'. Memproses 'probs'.")
            class_id = result.probs.top1
            confidence = result.probs.top1conf
            label = model.names[class_id]
            
            label_str = f"{label} ({float(confidence):.2f})"

    except Exception as e:
        print(f"[YOLO ERROR] Terjadi kesalahan saat memproses hasil: {e}")
        label_str = "no object detected"

    print(f"[CLASSIFICATION] Hasil Final: {label_str}")
    mqtt_client.publish(MQTT_TOPIC, label_str)
    print(f"[MQTT-MAIN] Hasil '{label_str}' dipublikasikan ke topik '{MQTT_TOPIC}'")


def camera_loop():
    """Loop utama untuk thread kamera yang berjalan di background."""
    global running, process_command
    
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 640)})
    picam2.configure(config)
    picam2.start()
    print("[CAMERA] Kamera siap.")

    while True:
        if running and process_command:
            print(f"[CAMERA LOOP] Menerima perintah: {process_command}")
            classify_and_publish(picam2, client)
            process_command = None
        time.sleep(0.5)

# --- Pengaturan MQTT ---
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT-MAIN] Terhubung ke broker dengan kode {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"[MQTT-MAIN] Berlangganan ke topik '{MQTT_TOPIC}'")

def on_message(client, userdata, msg):
    global running, process_command
    message = msg.payload.decode().strip().lower()
    print(f"[MQTT-MAIN] Pesan diterima: {message}")

    if message == "start":
        # Nyalakan LED di thread terpisah agar tidak memblokir
        led_thread = threading.Thread(target=control_led_timed)
        led_thread.start()
        
        running = True
        process_command = "start"
    
    elif message == "insert again" and running:
        # Nyalakan LED di thread terpisah agar tidak memblokir
        led_thread = threading.Thread(target=control_led_timed)
        led_thread.start()

        process_command = "insert again"
        
    elif message == "stop":
        running = False
        process_command = None

# --- Inisialisasi dan Loop Utama ---
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

camera_thread = threading.Thread(target=camera_loop)
camera_thread.daemon = True
camera_thread.start()

try:
    print("[MAIN] Menghubungkan ke MQTT Broker...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\n[EXIT] Program utama dihentikan oleh user.")
finally:
    print("[CLEANUP] Program utama selesai.")
    GPIO.cleanup() # <-- Membersihkan pin GPIO saat program keluar
