import time
import threading
import os
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from picamera2 import Picamera2
import cv2

# --- Konfigurasi ---
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "waste/raw"

MODEL_PATH = "models/best.pt"
IMAGES_DIR = "/home/admin/caps/aiCameraDetection/images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# --- PEMETAAN KATEGORI ---
# Kamus untuk memetakan label dari model ke kategori utama
LABEL_TO_CATEGORY_MAP = {
    "recycle": ["plastic", "metal"],
    "organic": ["organic"],
    "paper": ["paper"],
    "other": ["mask", "battery"]
}

# Variabel Global untuk Kontrol Thread
running = False
process_command = None

# --- Inisialisasi Model ---
try:
    model = YOLO(MODEL_PATH)
except Exception as e:
    print(f"[ERROR] Gagal memuat model YOLO: {e}")
    exit()

# --- FUNGSI BARU UNTUK MENGELOMPOKKAN ---
def get_category_from_label(label):
    """Mencari kategori utama berdasarkan label yang terdeteksi."""
    label = label.lower() # Pastikan label dalam huruf kecil
    for category, labels_in_category in LABEL_TO_CATEGORY_MAP.items():
        if label in labels_in_category:
            return category
    # Jika label tidak ditemukan di kategori manapun, kembalikan 'others' sebagai default
    return "others"

# --- Fungsi Utama (Dimodifikasi) ---
def classify_and_publish(picam2, mqtt_client):
    """
    Fungsi hybrid yang bisa menangani model deteksi (boxes) dan klasifikasi (probs).
    Sekarang mengirimkan KATEGORI, bukan label mentah.
    """
    print("[CAMERA] Persiapan mengambil gambar...")
    time.sleep(5)  # Waktu tunggu agar kamera stabil
    frame = picam2.capture_array()
    
    print("[YOLO] Memproses gambar...")
    results = model(frame)

    timestamp = int(time.time())
    filepath = os.path.join(IMAGES_DIR, f"classified_{timestamp}.jpg")
    try:
        # Coba simpan gambar dengan anotasi (bounding box)
        annotated_frame = results[0].plot()
        cv2.imwrite(filepath, annotated_frame)
        print(f"[CAMERA] Gambar anotasi disimpan di: {filepath}")
    except Exception as plot_error:
        print(f"[PLOT ERROR] Gagal membuat anotasi, menyimpan gambar asli: {plot_error}")
        cv2.imwrite(filepath, frame)

    # Variabel untuk menampung hasil akhir (kategori)
    final_category = "no object detected"
    
    try:
        result = results[0]
        detected_label = ""
        
        # --- KONDISI 1: JIKA MODEL ADALAH DETEKSI OBJEK ---
        if result.boxes and len(result.boxes) > 0:
            print("[INFO] Model terdeteksi sebagai 'Detection Model'.")
            confidences = result.boxes.conf.tolist()
            class_ids = result.boxes.cls.tolist()
            
            # Ambil label dari deteksi dengan confidence tertinggi
            best_idx = confidences.index(max(confidences))
            detected_label = model.names[int(class_ids[best_idx])]

        # --- KONDISI 2: JIKA MODEL ADALAH KLASIFIKASI GAMBAR ---
        elif result.probs is not None:
            print("[INFO] Model terdeteksi sebagai 'Classification Model'.")
            class_id = result.probs.top1
            detected_label = model.names[class_id]
        
        # --- PROSES PENGELOMPOKAN ---
        if detected_label:
            final_category = get_category_from_label(detected_label)
            print(f"[GROUPING] Label terdeteksi: '{detected_label}', Dikelompokkan ke: '{final_category}'")
        
    except Exception as e:
        print(f"[YOLO ERROR] Terjadi kesalahan saat memproses hasil: {e}")
        final_category = "no object detected"

    print(f"[CLASSIFICATION] Hasil Final: {final_category}")
    mqtt_client.publish(MQTT_TOPIC, final_category)
    print(f"[MQTT-MAIN] Kategori '{final_category}' dipublikasikan ke topik '{MQTT_TOPIC}'")


def camera_loop():
    # ... (Fungsi ini tidak berubah)
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
            process_command = None  # Reset perintah setelah diproses
        time.sleep(0.5)

# --- Pengaturan MQTT ---
def on_connect(client, userdata, flags, rc):
    # ... (Fungsi ini tidak berubah)
    print(f"[MQTT-MAIN] Terhubung ke broker dengan kode {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"[MQTT-MAIN] Berlangganan ke topik '{MQTT_TOPIC}'")

def on_message(client, userdata, msg):
    # ... (Fungsi ini tidak berubah)
    global running, process_command
    message = msg.payload.decode().strip().lower()
    print(f"[MQTT-MAIN] Pesan diterima: {message}")

    if message == "start":
        print("[CONTROL] Perintah 'start' diterima. Memulai proses.")
        running = True
        process_command = "start"
    
    elif message == "insert again" and running:
        print("[CONTROL] Perintah 'insert again' diterima. Memulai proses.")
        process_command = "insert again"
        
    elif message == "stop":
        print("[CONTROL] Perintah 'stop' diterima. Menghentikan proses.")
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
