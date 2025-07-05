import RPi.GPIO as GPIO
import time
import threading


servo1_pin = 17  
servo2_pin = 27 

GPIO.setmode(GPIO.BCM)
GPIO.setup(servo1_pin, GPIO.OUT)
GPIO.setup(servo2_pin, GPIO.OUT)

servo1 = GPIO.PWM(servo1_pin, 50)
servo2 = GPIO.PWM(servo2_pin, 50)
servo1.start(0)
servo2.start(0)

servo1_default_angle = 0

def set_angle(pwm, angle):
    duty = 2 + (angle / 18)
    GPIO.output(pwm_pin(pwm), True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    GPIO.output(pwm_pin(pwm), False)
    pwm.ChangeDutyCycle(0)


def servo1_sequence():
    set_angle(servo1, 90)
    time.sleep(3)
    set_angle(servo1, servo1_default_angle)

def pwm_pin(pwm):
    return servo1_pin if pwm == servo1 else servo2_pin

category_map = {
    "organic": 1,
    "inorganic": 46,
    "plastic": 91,
    "others": 136
}

try:
    while True:
        category = input("Enter waste category (organic, inorganic, plastic, others): ").lower()
        if category in category_map:
            angle2 = category_map[category]
            print("Sorting...")

            t1 = threading.Thread(target=servo1_sequence)

            t2 = threading.Thread(target=set_angle, args=(servo2, angle2))

            t1.start()
            t2.start()

            t1.join()
            t2.join()

            print(f"Servo 1 moved to 90 degrees then returned to {servo1_default_angle} degrees, Servo 2 moved to {angle2} degrees.")
        else:
            print("Invalid category. Try again.")

except KeyboardInterrupt:
    print("Program stopped.")
    servo1.stop()
    servo2.stop()
    GPIO.cleanup()
