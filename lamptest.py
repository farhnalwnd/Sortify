
import RPi.GPIO as GPIO
import time

RELAY_PIN = 21 # Sesuaikan jika pin Anda berbeda

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.LOW) # Pastikan relay mati di awal (sinyal LOW)

try:
    print("Tes dimulai...")

    # 1. Menyalakan Relay
    print("Relay ON selama 5 detik.")
    GPIO.output(RELAY_PIN, GPIO.HIGH) # Kirim sinyal HIGH untuk menyalakan
    time.sleep(5)

    # 2. Mematikan Relay
    print("Relay OFF.")
    GPIO.output(RELAY_PIN, GPIO.LOW) # Kirim sinyal LOW untuk mematikan
    time.sleep(2) # Jeda singkat

    print("Tes selesai.")

finally:
    GPIO.cleanup()
