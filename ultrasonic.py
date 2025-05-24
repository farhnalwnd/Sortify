import RPi.GPIO as GPIO
import time

# Konfigurasi GPIO
TRIG = 23
ECHO = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():
    GPIO.output(TRIG, False)
    time.sleep(0.1)

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()

    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start

    distance = pulse_duration * 17150  # cm
    distance = round(distance, 2)

    return distance

def get_fullness(distance):
    if distance > 45:
        distance = 45
    elif distance < 5:
        distance = 5

    fullness = ((45 - distance) / 40.0) * 100
    return round(fullness, 2)

try:
    while True:
        jarak = get_distance()
        persen = get_fullness(jarak)

        print(f"Jarak: {jarak} cm | Kepenuhan: {persen} %")
        time.sleep(1)

except KeyboardInterrupt:
    print("\nProgram dihentikan")
    GPIO.cleanup()
