import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import time

# --- PENGATURAN (Silakan ubah sesuai kebutuhan) ---

# Pengaturan Relay
RELAY_PIN = 21  # Pin GPIO yang terhubung ke pin IN relay

# Logika untuk menyalakan relay ACTIVE HIGH
# GPIO.HIGH = Menyalakan Relay
# GPIO.LOW  = Mematikan Relay
RELAY_ON_STATE = GPIO.HIGH
RELAY_OFF_STATE = GPIO.LOW

# --- Konfigurasi ---
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "waste/raw"

# --- AKHIR PENGATURAN ---


# Fungsi yang akan dipanggil saat berhasil terhubung ke broker MQTT
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("? Berhasil terhubung ke Broker MQTT!")
        client.subscribe(MQTT_TOPIC) # Langganan topik setelah terhubung
    else:
        print(f"? Gagal terhubung, kode error: {rc}")

# Fungsi yang akan dipanggil setiap kali ada pesan masuk
def on_message(client, userdata, msg):
    # Ambil payload (isi pesan) dan ubah dari byte menjadi string
    payload = msg.payload.decode("utf-8")
    print(f"?? Pesan diterima di topik '{msg.topic}': {payload}")

    # Cek apakah isi pesannya adalah "start" atau "insert again"
    if payload == "start" or payload == "insert again":
        try:
            print("Pemicu diterima. Delay 2 detik...")
            time.sleep(2)  # Delay selama 2 detik

            print("?? Menyalakan lampu selama 4 detik...")
            GPIO.output(RELAY_PIN, RELAY_ON_STATE) # Nyalakan lampu
            time.sleep(4)  # Biarkan lampu menyala selama 4 detik

        finally:
            print("? Mematikan lampu.")
            GPIO.output(RELAY_PIN, RELAY_OFF_STATE) # Pastikan lampu mati setelahnya

# Fungsi utama untuk setup
def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELAY_PIN, GPIO.OUT)
    # Pastikan relay dalam kondisi mati saat program dimulai
    GPIO.output(RELAY_PIN, RELAY_OFF_STATE)
    print("Setup GPIO selesai. Relay dalam kondisi OFF.")

# --- Program Utama ---
try:
    setup()

    # Inisialisasi client MQTT
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    # Hubungkan ke broker
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # loop_forever() adalah loop pemblokiran yang memproses lalu lintas jaringan,
    # mengirim dan menerima data, serta memanggil callback secara otomatis.
    print(f"?? Mendengarkan pesan di topik '{MQTT_TOPIC}'...")
    client.loop_forever()

except KeyboardInterrupt:
    print("\nProgram dihentikan oleh pengguna.")
finally:
    GPIO.cleanup() # Membersihkan pin GPIO
    print("GPIO cleanup selesai.")
