# servo.py
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time

# --- Konfigurasi ---
# MQTT
MQTT_BROKER = "broker.emqx.io" #
MQTT_PORT = 1883 #
MQTT_TOPIC_SUB = "waste/raw"  # Berlangganan ke topik yang sama dengan main.py

# GPIO Pins
SERVO_PUSHER_PIN = 17   # PIN GPIO untuk servo pendorong (bisa diubah)
SERVO_SORTER_PIN = 12   # PIN GPIO untuk servo penyortir

# Frekuensi Servo
SERVO_FREQ = 50 #

# Posisi Sudut Servo Penyortir (Derajat)
SERVO_POSITIONS = { #
    "plastic": 20, #
    "paper": 95, #
    "organic": 150 #
}

# Posisi Sudut Servo Pendorong
PUSHER_HOME_POS = 0    # Posisi awal
PUSHER_PUSH_POS = 90   # Posisi saat mendorong

# --- Inisialisasi GPIO ---
GPIO.setmode(GPIO.BCM) #
GPIO.setup(SERVO_PUSHER_PIN, GPIO.OUT)
GPIO.setup(SERVO_SORTER_PIN, GPIO.OUT) #

pusher_pwm = GPIO.PWM(SERVO_PUSHER_PIN, SERVO_FREQ)
sorter_pwm = GPIO.PWM(SERVO_SORTER_PIN, SERVO_FREQ) #

pusher_pwm.start(0) #
sorter_pwm.start(0) #

# --- Fungsi Helper Servo ---
def angle_to_duty_cycle(angle):
    """Mengonversi sudut (0-180) ke duty cycle (2-12)."""
    return 2 + (angle / 180) * 10 #

def move_servo(pwm, angle):
    """Menggerakkan servo ke sudut tertentu."""
    duty = angle_to_duty_cycle(angle)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)

def get_sorter_position(label):
    """Mendapatkan posisi sudut untuk servo penyortir berdasarkan label."""
    label = label.split('(')[0].strip().lower() #
    if "plastic" in label or "plastik" in label: #
        return SERVO_POSITIONS["plastic"] #
    elif "paper" in label or "kertas" in label: #
        return SERVO_POSITIONS["paper"] #
    elif "organic" in label or "organik" in label: #
        return SERVO_POSITIONS["organic"] #
    return None #

# --- Logika Aksi Servo ---
def handle_classification(label):
    """Fungsi untuk menggerakkan kedua servo berdasarkan hasil klasifikasi."""
    print(f"[SERVO] Menerima klasifikasi: {label}")
    
    # 1. Gerakkan Servo Penyortir
    sorter_angle = get_sorter_position(label)
    if sorter_angle is not None:
        print(f"[SERVO-SORTER] Bergerak ke posisi '{label.split('(')[0].strip()}' di sudut {sorter_angle}°")
        move_servo(sorter_pwm, sorter_angle)
    else:
        print(f"[SERVO-SORTER] Tidak ada posisi yang cocok untuk label: {label}")
        return

    # 2. Tunggu 0.5 detik, lalu aktifkan Servo Pendorong
    time.sleep(0.5)
    print(f"[SERVO-PUSHER] Mendorong sampah (ke {PUSHER_PUSH_POS}°)")
    move_servo(pusher_pwm, PUSHER_PUSH_POS)
    time.sleep(1)
    print(f"[SERVO-PUSHER] Kembali ke posisi awal ({PUSHER_HOME_POS}°)")
    move_servo(pusher_pwm, PUSHER_HOME_POS)

# --- Pengaturan MQTT ---
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT-SERVO] Terhubung ke broker dengan kode {rc}")
    client.subscribe(MQTT_TOPIC_SUB) #
    print(f"[MQTT-SERVO] Berlangganan ke topik '{MQTT_TOPIC_SUB}'")

def on_message(client, userdata, msg):
    """Callback yang memfilter pesan masuk."""
    message = msg.payload.decode().strip()
    
    # Daftar perintah yang harus diabaikan oleh skrip servo
    commands_to_ignore = ["start", "stop", "insert again"]
    
    if message.lower() in commands_to_ignore:
        print(f"[SERVO] Mengabaikan pesan perintah: '{message}'")
        return
    
    # Jika bukan perintah, proses sebagai hasil klasifikasi
    handle_classification(message)

def cleanup():
    """Membersihkan resource GPIO saat program berhenti."""
    print("\n[CLEANUP] Membersihkan GPIO Servo...")
    pusher_pwm.stop()
    sorter_pwm.stop()
    GPIO.cleanup() #
    print("[CLEANUP] Selesai.")

# --- Loop Utama ---
client = mqtt.Client() #
client.on_connect = on_connect #
client.on_message = on_message #

try:
    print("[SERVO] Menghubungkan ke MQTT Broker...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60) #
    print("[SERVO] Mengatur posisi awal servo...")
    move_servo(pusher_pwm, PUSHER_HOME_POS)
    print("[SERVO] Skrip siap dan menunggu pesan klasifikasi.")
    client.loop_forever() #
except KeyboardInterrupt:
    print("\n[EXIT] Program servo dihentikan oleh user.")
finally:
    cleanup()