import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import time

# --- Pin & MQTT Configuration ---
SORTER_SERVO_PIN = 17
GATE_SERVO_PIN = 4

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 8084
MQTT_TOPIC = "waste/raw"

# --- Global Variables ---
pwm_sorter = None
pwm_gate = None
current_sorter_angle = 90

# --- Servo Functions ---
def setup_servos():
    global pwm_sorter, pwm_gate, current_sorter_angle
    
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SORTER_SERVO_PIN, GPIO.OUT)
    GPIO.setup(GATE_SERVO_PIN, GPIO.OUT)
    
    pwm_sorter = GPIO.PWM(SORTER_SERVO_PIN, 50)
    pwm_gate = GPIO.PWM(GATE_SERVO_PIN, 50)
    
    pwm_gate.start(0)
    
    print("Initializing servos...")
    
    print("Gate servo moving to standby position (100°).")
    move_servo(pwm_gate, 100)
    time.sleep(0.5)
    
    print("Sorter servo moving to default position (90°)...")
    default_duty_cycle = angle_to_duty_cycle(current_sorter_angle)
    pwm_sorter.start(default_duty_cycle)
    time.sleep(1)
    pwm_sorter.ChangeDutyCycle(0)
    
    print("\n--- System Ready ---")

def angle_to_duty_cycle(angle):
    return (angle / 18) + 2

def move_servo(pwm, angle):
    duty_cycle = angle_to_duty_cycle(angle)
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)

def smooth_move(pwm, start_angle, target_angle):
    if start_angle == target_angle:
        print(f"Sorter is already at {target_angle}°, no movement needed.")
        return target_angle

    print(f"Sorter moving from {start_angle}° to {target_angle}°...")
    
    step = 1 if target_angle > start_angle else -1
        
    for angle in range(start_angle, target_angle + step, step):
        duty_cycle = angle_to_duty_cycle(angle)
        pwm.ChangeDutyCycle(duty_cycle)
        time.sleep(0.02)
        
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)
    print(f"Sorter has reached {target_angle}°.")
    return target_angle

def operate_gate():
    print("Gate opening (moving to 0°)...")
    move_servo(pwm_gate, 0)
    
    time.sleep(1)
    
    print("Gate closing (returning to 100°)...")
    move_servo(pwm_gate, 100)

# --- MQTT Callback Functions ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Successfully connected to MQTT Broker!")
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"Failed to connect, status code: {rc}")

def on_message(client, userdata, msg):
    global current_sorter_angle
    
    payload = msg.payload.decode("utf-8").lower()
    print(f"\n>>> Message received: '{payload}'")
    
    angle_map = {
        "recycle": 70,
        "paper": 110,
        "organic": 30,
        "other": 160
    }
    
    target_angle = angle_map.get(payload, -1)

    if target_angle != -1:
        current_sorter_angle = smooth_move(pwm_sorter, current_sorter_angle, target_angle)
        
        print("Waiting 1 second before opening gate...")
        time.sleep(1)
        
        operate_gate()
        
        print("Checking if return movement is needed...")
        time.sleep(0.5)

        if payload == "other":
            print("Position 'other', returning to 'paper' (100°)...")
            target_return_angle = angle_map["paper"]
            current_sorter_angle = smooth_move(pwm_sorter, current_sorter_angle, target_return_angle)

        elif payload == "organic":
            print("Position 'organic', returning to 'recycle' (60°)...")
            target_return_angle = angle_map["recycle"]
            current_sorter_angle = smooth_move(pwm_sorter, current_sorter_angle, target_return_angle)
        
        else:
            print("Position 'paper' or 'recycle', staying put.")

        print("\n--- Cycle Complete, Waiting for Next Message ---")
    else:
        print("Invalid message. Waiting for the next message.")

# --- Main Function ---
def main():
    try:
        setup_servos()
        
        client = mqtt.Client(transport="websockets")
        client.tls_set()
        
        client.on_connect = on_connect
        client.on_message = on_message
        
        print(f"Connecting to broker wss://{MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if pwm_sorter:
            pwm_sorter.stop()
        if pwm_gate:
            pwm_gate.stop()
        GPIO.cleanup()
        print("GPIO cleaned up. Program finished.")

if __name__ == '__main__':
    main()
