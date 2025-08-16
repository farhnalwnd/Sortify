import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 8084 
CONTROL_TOPIC = "waste/raw" 

SENSORS = [
    {'trig': 5,  'echo': 6,  'topic': 'waste/sensor1'},
    {'trig': 13, 'echo': 19, 'topic': 'waste/sensor2'},
    {'trig': 26, 'echo': 12, 'topic': 'waste/sensor3'},
    {'trig': 16, 'echo': 20, 'topic': 'waste/sensor4'}
]

TINGGI_TONG_CM = 38
JARAK_SENSOR_DARI_BIBIR_CM = 1

is_running = False
stop_requested_time = None

def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    for sensor in SENSORS:
        GPIO.setup(sensor['trig'], GPIO.OUT)
        GPIO.setup(sensor['echo'], GPIO.IN)
        GPIO.output(sensor['trig'], False)
    time.sleep(2)

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
        if time.time() - pulse_start_time > 0.1:
            return -1
    pulse_end_time = time.time()

    pulse_duration = pulse_end_time - pulse_start_time

    distance = (pulse_duration * 34300) / 2
    return round(distance, 2)

def calculate_fullness_percentage(measured_distance_cm):
    if measured_distance_cm < 0:
        return -1 
    
    jarak_penuh = JARAK_SENSOR_DARI_BIBIR_CM
    jarak_kosong = jarak_penuh + TINGGI_TONG_CM

    if measured_distance_cm <= jarak_penuh:
        return 100
    if measured_distance_cm >= jarak_kosong:
        return 0
    
    tinggi_sampah = jarak_kosong - measured_distance_cm
    persentase = (tinggi_sampah / TINGGI_TONG_CM) * 100
    return int(round(persentase))

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"connected to broker wss://{MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(CONTROL_TOPIC)
        print(f"listening to topic '{CONTROL_TOPIC}'")
    else:
        print(f"failed, kode: {rc}")

def on_message(client, userdata, msg):
    global is_running, stop_requested_time
    command = msg.payload.decode('utf-8').lower()
    print(f"\nmessage recived: {command}")
    
    if command in ["start", "insert again"]:
        if not is_running:
            is_running = True
            stop_requested_time = None
            print("start.")
        else:
            stop_requested_time = None
            print("ℹ️ Pengukuran sudah berjalan (timer stop dibatalkan jika ada).")
            
    elif command == "stop":
        if is_running and stop_requested_time is None:
            stop_requested_time = time.time()
            print("stop order recived.")
        elif not is_running:
            print("stoped.")

if __name__ == "__main__":
    client = None
    try:
        setup_gpio()

        client = mqtt.Client(client_id="waste_sensor_suite", transport="websockets")
        client.tls_set()
        
        client.on_connect = on_connect
        client.on_message = on_message
        
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        print("\nwaiting for MQTT...")

        cycle_count = 0
        while True:
            if is_running and stop_requested_time is not None:
                if time.time() - stop_requested_time > 5:
                    is_running = False
                    stop_requested_time = None
                    cycle_count = 0
                    print("\nultrasonic stoped.")

            if is_running:
                cycle_count += 1
                print(f"\n--- counter #{cycle_count} ---")
                for sensor in SENSORS:
                    dist = measure_distance(sensor['trig'], sensor['echo'])
                    percent = calculate_fullness_percentage(dist)
                    
                    if percent != -1:
                        client.publish(sensor['topic'], str(percent))
                        print(f"{sensor['topic']} | distance: {dist} cm → avail: {percent}%")
                    else:
                        print(f"error, sensor not found: {sensor['topic']}")
                
                time.sleep(2) 
            else:
                print("waiting for start ordeer", end="\r")
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nended.")
    finally:
        GPIO.cleanup()
        if client:
            client.loop_stop()
            client.disconnect()
