# --- Impor Pustaka ---
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time

# --- Konfigurasi MQTT dan Sensor ---
MQTT_BROKER = "broker.emqx.io"
MQTT_LISTENER_PORT = 1883        # Port MQTT biasa untuk menerima perintah
MQTT_PUBLISHER_PORT = 8083       # WebSocket port untuk kirim data ke web
WEBSOCKET_PATH = "/mqtt"         # Path WebSocket standar

CONTROL_TOPIC = "waste/raw"      # Topic untuk perintah (start, stop)
SENSORS = [
    {'trig': 5,  'echo': 6,  'topic': 'waste/sensor2'},
    {'trig': 13, 'echo': 19, 'topic': 'waste/sensor9'},
    {'trig': 26, 'echo': 16, 'topic': 'waste/sensor8'},
    {'trig': 20, 'echo': 21, 'topic': 'waste/sensor7'}
]

TINGGI_TONG_CM = 40
JARAK_SENSOR_DARI_BIBIR_CM = 10

# --- Variabel Global ---
is_running = False
stop_requested_time = None

# --- Setup GPIO ---
def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    for sensor in SENSORS:
        GPIO.setup(sensor['trig'], GPIO.OUT)
        GPIO.setup(sensor['echo'], GPIO.IN)
        GPIO.output(sensor['trig'], False)
    print("GPIO disiapkan.")
    time.sleep(2)

# --- Mengukur Jarak ---
def measure_distance(trig_pin, echo_pin):
    GPIO.output(trig_pin, True)
    time.sleep(0.00001)
    GPIO.output(trig_pin, False)

    timeout_start = time.time()
    while GPIO.input(echo_pin) == 0:
        if time.time() - timeout_start > 0.1:
            return -1
        pulse_start_time = time.time()

    while GPIO.input(echo_pin) == 1:
        if time.time() - timeout_start > 0.1:
            return -1
        pulse_end_time = time.time()

    pulse_duration = pulse_end_time - pulse_start_time
    distance = (pulse_duration * 34300) / 2
    return round(distance, 2)

# --- Hitung Persentase Sampah ---
def calculate_fullness_percentage(measured_distance_cm):
    if measured_distance_cm < 0:
        return -1
    full = JARAK_SENSOR_DARI_BIBIR_CM
    empty = full + TINGGI_TONG_CM
    if measured_distance_cm <= full:
        return 100
    if measured_distance_cm >= empty:
        return 0
    tinggi_sampah = empty - measured_distance_cm
    return int(round((tinggi_sampah / TINGGI_TONG_CM) * 100))

# --- Callback: Saat Konek ke Broker ---
def on_connect(client, userdata, flags, rc):
    client_id = client._client_id.decode('utf-8')
    if rc == 0:
        print(f"✅ Terkoneksi ke broker! (Client: {client_id})")
        if client_id == "waste_listener_client":
            client.subscribe(CONTROL_TOPIC)
            print(f"📡 Mendengarkan perintah di topic '{CONTROL_TOPIC}'")
    else:
        print(f"❌ Gagal konek (Client: {client_id}), kode: {rc}")

# --- Callback: Saat Terima Pesan ---
def on_message(client, userdata, msg):
    global is_running, stop_requested_time
    command = msg.payload.decode('utf-8').lower()
    print(f"📨 Perintah diterima: {command}")
    if command in ["start", "insert again"]:
        if not is_running:
            is_running = True
            stop_requested_time = None
            print("▶️ Memulai pengukuran.")
        else:
            stop_requested_time = None
            print("ℹ️ Pengukuran sudah berjalan.")
    elif command == "stop":
        if is_running and stop_requested_time is None:
            stop_requested_time = time.time()
            print("⏸️ Stop diminta, akan berhenti dalam 5 detik.")
        elif not is_running:
            print("ℹ️ Sudah dalam keadaan berhenti.")

# --- MAIN PROGRAM ---
if __name__ == "__main__":
    listener_client = None
    publisher_client = None
    try:
        setup_gpio()

        # --- Listener Client (port 1883) ---
        listener_client = mqtt.Client(client_id="waste_listener_client")
        listener_client.on_connect = on_connect
        listener_client.on_message = on_message
        listener_client.connect(MQTT_BROKER, MQTT_LISTENER_PORT, 60)
        listener_client.loop_start()

        # --- Publisher Client (via WebSocket) ---
        publisher_client = mqtt.Client(client_id="waste_publisher_client", transport="websockets")
        publisher_client.ws_set_options(path=WEBSOCKET_PATH)
        publisher_client.on_connect = on_connect
        publisher_client.connect(MQTT_BROKER, MQTT_PUBLISHER_PORT, 60)
        publisher_client.loop_start()

        print("\n🚀 Sistem siap. Menunggu perintah MQTT...")

        cycle_count = 0
        while True:
            if is_running and stop_requested_time is not None:
                if time.time() - stop_requested_time > 5:
                    is_running = False
                    stop_requested_time = None
                    cycle_count = 0
                    print("🛑 Pengukuran dihentikan total.")

            if is_running:
                cycle_count += 1
                print(f"\n--- Siklus #{cycle_count} ---")
                for sensor in SENSORS:
                    dist = measure_distance(sensor['trig'], sensor['echo'])
                    percent = calculate_fullness_percentage(dist)
                    if percent != -1:
                        publisher_client.publish(sensor['topic'], str(percent))
                        print(f"📤 {sensor['topic']} | {dist} cm → {percent}%")
            else:
                print("⌛ Mode siaga... menunggu perintah 'start'...", end="\r")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⛔ Program dihentikan oleh pengguna.")
    finally:
        GPIO.cleanup()
        if listener_client:
            listener_client.loop_stop()
            listener_client.disconnect()
        if publisher_client:
            publisher_client.loop_stop()
            publisher_client.disconnect()
        print("✅ GPIO dibersihkan. Semua koneksi ditutup.")
