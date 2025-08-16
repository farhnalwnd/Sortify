import RPi.GPIO as GPIO
import time

# Ganti pin ini jika Anda menggunakan pin yang berbeda
SORTER_SERVO_PIN = 17

# Inisialisasi GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(SORTER_SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SORTER_SERVO_PIN, 50)
pwm.start(0)


def angle_to_duty_cycle(angle):
    return (angle / 18) + 2

def move_servo(angle):
    """Fungsi untuk menggerakkan servo ke sudut tertentu."""
    print(f"Menggerakkan servo ke {angle}°...")
    duty = angle_to_duty_cycle(angle)
    pwm.ChangeDutyCycle(duty)
    # Beri waktu servo untuk bergerak
    time.sleep(1)
    # Matikan sinyal untuk mencegah getaran
    pwm.ChangeDutyCycle(0)

print("Program Kalibrasi Servo. Tekan Ctrl+C untuk keluar.")

try:
    # Posisikan servo di tengah sebagai awal
    move_servo(90)
    while True:
        # Minta input sudut dari pengguna
        sudut_input = input("Masukkan sudut (0-180): ")
        try:
            sudut = int(sudut_input)
            if 0 <= sudut <= 180:
                move_servo(sudut)
            else:
                print("Sudut harus di antara 0 dan 180.")
        except ValueError:
            print("Input tidak valid! Harap masukkan angka.")

except KeyboardInterrupt:
    print("\nProgram dihentikan.")
finally:
    # Pastikan untuk membersihkan GPIO
    pwm.stop()
    GPIO.cleanup()
    print("GPIO dibersihkan.")
