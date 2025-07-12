import time
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

# Konfigurasi MQTT Broker
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883

# ==============================================================================
# --- KONFIGURASI SENSOR (SESUAIKAN PIN & TOPIK DI SINI) ---
# ==============================================================================
SENSORS_CONFIG = [
    {
        "name": "Tong Sampah 1 (Plastic)",
        "trig_pin": 18,  # Pin Trig sensor 1 (Tetap sesuai permintaan)
        "echo_pin": 24,  # Pin Echo sensor 1 (Tetap sesuai permintaan)
        "topic": "waste/bin_status/plastic"
    },
    {
        "name": "Tong Sampah 2 (Paper)",
        "trig_pin": 23,  # Ganti dengan pin Trig sensor 2
        "echo_pin": 25,  # Ganti dengan pin Echo sensor 2
        "topic": "waste/bin_status/paper"
    },
    {
        "name": "Tong Sampah 3 (Organic)",
        "trig_pin": 5,   # Ganti dengan pin Trig sensor 3
        "echo_pin": 6,   # Ganti dengan pin Echo sensor 3
        "topic": "waste/bin_status/organic"
    },
    {
        "name": "Tong Sampah 4 (Others)",
        "trig_pin": 12,  # Ganti dengan pin Trig sensor 4
        "echo_pin": 13,  # Ganti dengan pin Echo sensor 4
        "topic": "waste/bin_status/others"
    }
]
# ==============================================================================

# Inisialisasi GPIO
GPIO.setmode(GPIO.BCM)
for sensor in SENSORS_CONFIG:
    GPIO.setup(sensor["trig_pin"], GPIO.OUT)
    GPIO.setup(sensor["echo_pin"], GPIO.IN)

# Inisialisasi MQTT Client
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)

def read_distance(trig_pin, echo_pin):
    """Membaca jarak dari satu sensor ultrasonik."""
    # Kirim sinyal trigger
    GPIO.output(trig_pin, False)
    time.sleep(0.05)
    
    GPIO.output(trig_pin, True)
    time.sleep(0.00001)
    GPIO.output(trig_pin, False)

    pulse_start = time.time()
    pulse_end = time.time()

    # Tunggu sinyal echo kembali
    while GPIO.input(echo_pin) == 0:
        pulse_start = time.time()

    while GPIO.input(echo_pin) == 1:
        pulse_end = time.time()

    # Hitung jarak
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150  # Konversi ke cm
    return round(distance, 2)

def calculate_bin_capacity(distance_cm):
    """Menghitung persentase kapasitas tong sampah berdasarkan jarak."""
    max_distance = 50.0  # Tinggi tong sampah (cm), sesuaikan jika perlu
    # Pastikan jarak tidak lebih dari max_distance untuk perhitungan yang akurat
    # dan tidak kurang dari 0
    clamped_distance = max(0, min(distance_cm, max_distance))
    
    filled_percent = (1 - (clamped_distance / max_distance)) * 100
    return round(max(0, min(100, filled_percent)), 2)

try:
    print("[ULTRASONIC] Skrip dimulai. Membaca 4 sensor...")
    while True:
        # Loop melalui setiap sensor dalam konfigurasi
        for sensor in SENSORS_CONFIG:
            distance = read_distance(sensor["trig_pin"], sensor["echo_pin"])
            capacity = calculate_bin_capacity(distance)
            
            print(f"[{sensor['name']}] Jarak: {distance} cm, Kapasitas: {capacity}% -> Topik: {sensor['topic']}")
            
            # Publikasikan ke topik MQTT yang sesuai
            client.publish(sensor["topic"], f"{capacity}%")
            
            # Beri jeda singkat antar pembacaan sensor untuk stabilitas
            time.sleep(1)
        
        print("--- Siklus pembacaan selesai. Menunggu 10 detik. ---")
        # Tunggu sebelum memulai siklus pembacaan berikutnya
        time.sleep(10)

except KeyboardInterrupt:
    print("\n[EXIT] Program dihentikan oleh user.")
finally:
    print("[CLEANUP] Membersihkan GPIO...")
    GPIO.cleanup()
    print("[CLEANUP] Selesai.")
