# servo.py (Versi Modifikasi dengan kategori 'others')
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time

# --- Konfigurasi ---
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC_SUB = "waste/raw"

# GPIO Pins
SERVO_PUSHER_PIN = 27
SERVO_SORTER_PIN = 17

# Frekuensi Servo
SERVO_FREQ = 50

# ===================================================================
# --- SESUAIKAN SUDUT SERVO ANDA DI SINI ---
# ===================================================================
SERVO_POSITIONS = {
    "plastic": 20,   # <-- Ganti sudut untuk plastik
    "paper": 95,     # <-- Ganti sudut untuk kertas
    "organic": 150,  # <-- Ganti sudut untuk organik
    "others": 60     # <-- Ganti sudut untuk kategori 'lainnya'
}
# ===================================================================

# Posisi Sudut Servo Pendorong
PUSHER_HOME_POS = 0
PUSHER_PUSH_POS = 90

# --- Inisialisasi GPIO ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PUSHER_PIN, GPIO.OUT)
GPIO.setup(SERVO_SORTER_PIN, GPIO.OUT)

pusher_pwm = GPIO.PWM(SERVO_PUSHER_PIN, SERVO_FREQ)
sorter_pwm = GPIO.PWM(SERVO_SORTER_PIN, SERVO_FREQ)

pusher_pwm.start(0)
sorter_pwm.start(0)

# --- Fungsi Helper Servo ---
def angle_to_duty_cycle(angle):
    return 2 + (angle / 180) * 10

def move_servo(pwm, angle):
    """Menggerakkan servo ke sudut tertentu dan menahan posisinya."""
    duty = angle_to_duty_cycle(angle)
    pwm.ChangeDutyCycle(duty)
    time.sleep(1) # Beri waktu agar servo fisik sempat mencapai posisi target.

def get_sorter_position(label):
    """Mencari posisi sudut servo berdasarkan label klasifikasi."""
    # Membersihkan label dari confidence score, cth: "plastic (0.92)" -> "plastic"
    cleaned_label = label.split('(')[0].strip().lower()
    
    # Mencocokkan label yang sudah bersih dengan kamus SERVO_POSITIONS
    if "plastic" in cleaned_label or "plastik" in cleaned_label:
        return SERVO_POSITIONS["plastic"]
    elif "paper" in cleaned_label or "kertas" in cleaned_label:
        return SERVO_POSITIONS["paper"]
    elif "organic" in cleaned_label or "organik" in cleaned_label:
        return SERVO_POSITIONS["organic"]
    elif "others" in cleaned_label or "lainnya" in cleaned_label:
        return SERVO_POSITIONS["others"]
    
    # Jika label tidak ada dalam kamus, kembalikan None
    return None

# ===================================================================
# --- FUNGSI LOGIKA UTAMA DENGAN PENANDA TAHAPAN YANG JELAS ---
# ===================================================================
def handle_classification(label):
    print(f"\n[INFO] Siklus baru dimulai untuk klasifikasi: {label}")
    
    # --- TAHAP 1: GERAKKAN SERVO PENYORTIR (PIN 17) ---
    print("--- TAHAP 1: Menggerakkan Servo Penyortir ---")
    sorter_angle = get_sorter_position(label)
    
    if sorter_angle is None:
        print(f"[GAGAL] Label '{label}' tidak dikenali. Siklus dibatalkan.")
        # Pertimbangkan untuk memindahkan servo ke posisi default/netral jika label tidak dikenali
        # move_servo(sorter_pwm, 90) 
        return

    print(f"  -> Mengarahkan penyortir ke sudut {sorter_angle}°.")
    move_servo(sorter_pwm, sorter_angle)
    print("  -> Servo Penyortir sekarang diam menahan posisi.")

    # --- TAHAP 2: GERAKKAN SERVO PENDORONG (PIN 27) ---
    print("\n--- TAHAP 2: Menggerakkan Servo Pendorong ---")
    print(f"  -> Pendorong bergerak maju ke {PUSHER_PUSH_POS}°.")
    move_servo(pusher_pwm, PUSHER_PUSH_POS)
    
    time.sleep(0.5) # Jeda singkat saat pendorong di depan
    
    print(f"  -> Pendorong kembali ke posisi awal {PUSHER_HOME_POS}°.")
    move_servo(pusher_pwm, PUSHER_HOME_POS)
    
    print("\n[INFO] Siklus pembuangan selesai.")
# ===================================================================

# --- Pengaturan MQTT ---
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT-SERVO] Terhubung ke broker dengan kode {rc}")
    client.subscribe(MQTT_TOPIC_SUB)
    print(f"[MQTT-SERVO] Berlangganan ke topik '{MQTT_TOPIC_SUB}'")

def on_message(client, userdata, msg):
    message = msg.payload.decode().strip()
    commands_to_ignore = ["start", "stop", "insert again"]
    if message.lower() in commands_to_ignore:
        return
    handle_classification(message)

def cleanup():
    print("\n[CLEANUP] Mengembalikan servo ke posisi awal...")
    move_servo(pusher_pwm, PUSHER_HOME_POS)
    move_servo(sorter_pwm, 90) # Kembalikan sorter ke posisi netral (90 derajat)
    pusher_pwm.stop()
    sorter_pwm.stop()
    GPIO.cleanup()
    print("[CLEANUP] Selesai.")

# --- Loop Utama ---
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    print("[SERVO] Skrip dimulai. Menghubungkan ke MQTT Broker...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    print("[SERVO] Mengatur posisi awal servo...")
    move_servo(pusher_pwm, PUSHER_HOME_POS)
    move_servo(sorter_pwm, 90) # Atur sorter ke posisi netral di awal
    print("[SERVO] Skrip siap menunggu hasil klasifikasi.")
    client.loop_forever()
except KeyboardInterrupt:
    print("\n[EXIT] Program servo dihentikan oleh user.")
finally:
    cleanup()
