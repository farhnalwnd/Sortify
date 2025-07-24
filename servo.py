import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import time

SORTER_SERVO_PIN = 18
GATE_SERVO_PIN = 23


MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "waste/raw"


pwm_sorter = None
pwm_gate = None
current_sorter_angle = 0

# --- Inisialisasi Servo ---
def setup_servos():
    global pwm_sorter, pwm_gate, current_sorter_angle
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SORTER_SERVO_PIN, GPIO.OUT)
    GPIO.setup(GATE_SERVO_PIN, GPIO.OUT)
    
    # Frekuensi PWM 50Hz
    pwm_sorter = GPIO.PWM(SORTER_SERVO_PIN, 50)
    pwm_gate = GPIO.PWM(GATE_SERVO_PIN, 50)
    
    pwm_sorter.start(0)
    pwm_gate.start(0)
    
    print("Kedua servo telah diinisialisasi.")
    
    # Atur posisi awal saat program dimulai
    # Servo penyortir di 0 derajat, servo penahan di posisi menutup (0 derajat)
    move_servo(pwm_gate, 0) # Pastikan gate tertutup
    time.sleep(0.5)
    current_sorter_angle = smooth_move(pwm_sorter, current_sorter_angle, 0) # Sorter di posisi awal
    print("Servo siap di posisi awal.")

def angle_to_duty_cycle(angle):
    """Mengonversi sudut (0-180) ke duty cycle (2-12)."""
    return (angle / 18) + 2

def move_servo(pwm, angle):
    """Menggerakkan servo secara langsung ke posisi target (untuk gate servo)."""
    duty_cycle = angle_to_duty_cycle(angle)
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5) # Waktu agar servo stabil
    pwm.ChangeDutyCycle(0) # Hentikan sinyal untuk mengurangi jitter

def smooth_move(pwm, start_angle, target_angle):
    """Menggerakkan servo secara perlahan dari posisi awal ke posisi target."""
    print(f"Servo penyortir bergerak dari {start_angle}° ke {target_angle}°...")
    
    step = 1 if target_angle > start_angle else -1
        
    for angle in range(start_angle, target_angle + step, step):
        duty_cycle = angle_to_duty_cycle(angle)
        pwm.ChangeDutyCycle(duty_cycle)
        time.sleep(0.015) # Delay kecil untuk pergerakan halus
        
    # Beri waktu agar servo stabil di posisi target
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0) 
    print("Pergerakan penyortir selesai.")
    return target_angle # Kembalikan posisi terakhir

def operate_gate():
    """Mengoperasikan servo penahan untuk membuka dan menutup."""
    print("Servo penahan membuka...")
    move_servo(pwm_gate, 90) # Buka penahan ke 90 derajat
    
    time.sleep(1) # Jeda 1 detik agar objek jatuh
    
    print("Servo penahan menutup...")
    move_servo(pwm_gate, 0) # Tutup kembali penahan ke 0 derajat

# --- Fungsi Callback MQTT ---
def on_connect(client, userdata, flags, rc):
    """Callback saat berhasil terhubung ke broker."""
    if rc == 0:
        print("Berhasil terhubung ke MQTT Broker!")
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribe ke topik: {MQTT_TOPIC}")
    else:
        print(f"Gagal terhubung, kode status: {rc}")

def on_message(client, userdata, msg):
    """Callback saat ada pesan masuk."""
    global current_sorter_angle
    
    payload = msg.payload.decode("utf-8").lower()
    print(f"\nPesan diterima: '{payload}'")
    
    target_angle = -1
    
    if payload == "plastic":
        target_angle = 45
    elif payload == "paper":
        target_angle = 90
    elif payload == "organic":
        target_angle = 135
    elif payload == "other":
        target_angle = 180
    else:
        print("Pesan tidak dikenali. Menunggu pesan berikutnya.")
        
    if target_angle != -1:
        # 1. Gerakkan servo penyortir
        current_sorter_angle = smooth_move(pwm_sorter, current_sorter_angle, target_angle)
        
        # 2. Tunggu 1 detik setelah penyortir sampai
        print("Menunggu 1 detik sebelum membuka penahan...")
        time.sleep(1)
        
        # 3. Operasikan servo penahan (buka lalu tutup)
        operate_gate()
        
        print("\nSiklus selesai. Siap menerima perintah berikutnya.")

# --- Fungsi Utama ---
def main():
    """Fungsi utama untuk menjalankan program."""
    try:
        setup_servos()
        
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        
        print(f"Menghubungkan ke broker {MQTT_BROKER}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("Program dihentikan.")
    except Exception as e:
        print(f"Terjadi error: {e}")
    finally:
        # Pastikan untuk membersihkan GPIO saat program selesai
        if pwm_sorter:
            pwm_sorter.stop()
        if pwm_gate:
            pwm_gate.stop()
        GPIO.cleanup()
        print("GPIO dibersihkan. Selesai.")

if __name__ == '__main__':
    main()
