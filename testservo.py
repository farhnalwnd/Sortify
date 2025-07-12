# File: servo_listener.py
# Deskripsi: Skrip Python untuk Raspberry Pi yang mendengarkan perintah MQTT
#            dan menggerakkan servo dari 45 ke 135 derajat.

import paho.mqtt.client as mqtt
from gpiozero import Servo
from time import sleep

# --- KONFIGURASI ---
# Konfigurasi MQTT (samakan dengan pengirim/publisher)
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "waste/raw"

# Konfigurasi GPIO (gunakan nomor GPIO, bukan nomor pin fisik)
SERVO_PIN = 17
# --- AKHIR KONFIGURASI ---

# Fungsi untuk memetakan derajat ke nilai gpiozero (-1 sampai 1)
def angle_to_value(angle):
    """Mengubah sudut (0-180) menjadi nilai (-1.0 sampai 1.0)"""
    return (angle / 90.0) - 1.0

# Inisialisasi objek servo menggunakan gpiozero
try:
    servo = Servo(SERVO_PIN)
    print(f"Servo terhubung ke GPIO {SERVO_PIN}")
    
    # <<< DIUBAH: Atur posisi awal servo ke 45 derajat >>>
    initial_angle = 50
    servo.value = angle_to_value(initial_angle)
    print(f"Servo diatur ke posisi awal ({initial_angle} derajat).")
    sleep(1)
    servo.detach() # Lepaskan servo agar tidak "bergetar" saat idle
except Exception as e:
    print(f"Gagal menginisialisasi servo: {e}")
    print("Pastikan library gpiozero terinstall dan pin GPIO benar.")
    exit()

# <<< DIUBAH: Fungsi untuk menjalankan sekuens tes servo dari 45 ke 135 derajat >>>
def run_servo_test():
    """Menggerakkan servo ke 135 derajat lalu kembali ke 45 derajat."""
    print("Perintah 'test' diterima. Menggerakkan servo...")
    try:
        start_angle = 50
        end_angle = 150
        
        # Gerakkan ke posisi target (135 derajat)
        print(f"-> Bergerak ke {end_angle} derajat")
        servo.value = angle_to_value(end_angle)
        sleep(1.5) # Beri waktu servo untuk bergerak

        # Gerakkan kembali ke posisi awal (45 derajat)
        print(f"-> Kembali ke {start_angle} derajat")
        servo.value = angle_to_value(start_angle)
        sleep(1.5)

        # Lepaskan pin servo untuk mengurangi jitter/getaran dan konsumsi daya
        servo.detach()
        print("Tes servo selesai. Pin servo dilepaskan.")
    except Exception as e:
        print(f"Terjadi error saat menggerakkan servo: {e}")

# Callback yang dieksekusi saat berhasil terhubung ke broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Berhasil terhubung ke MQTT Broker di {MQTT_BROKER}")
        # Subscribe ke topik setelah berhasil terhubung
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribe ke topik: {MQTT_TOPIC}")
    else:
        print(f"Gagal terhubung, kode status: {rc}")

# Callback yang dieksekusi saat menerima pesan di topik yang disubscribe
def on_message(client, userdata, msg):
    # Decode pesan dari bytes ke string
    message = msg.payload.decode("utf-8")
    print(f"Pesan diterima di topik '{msg.topic}': {message}")
    
    # Periksa apakah pesannya adalah "test"
    if message == "test":
        run_servo_test()

# --- Program Utama ---
# Membuat instance client MQTT
client = mqtt.Client(client_id="RaspberryPiServoClient-123") # Client ID bisa dibuat unik

# Mengatur fungsi callback
client.on_connect = on_connect
client.on_message = on_message

# Mencoba terhubung ke broker
try:
    print(f"Menghubungkan ke broker {MQTT_BROKER}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
except Exception as e:
    print(f"Tidak dapat terhubung ke broker. Pastikan koneksi internet aktif. Error: {e}")
    exit()

# Memulai loop untuk mendengarkan pesan selamanya
# loop_forever() adalah blocking call, skrip akan berhenti di sini dan menunggu pesan
print("Menunggu perintah MQTT... (Tekan CTRL+C untuk keluar)")
client.loop_forever()
