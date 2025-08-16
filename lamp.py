import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import time

RELAY_PIN = 21

RELAY_ON_STATE = GPIO.LOW
RELAY_OFF_STATE = GPIO.HIGH

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 8084
MQTT_TOPIC = "waste/raw"

# connect to mqtt
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("mqtt connected succsessfully")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"conection to mqtt failed: {rc}")

# listening to broker
def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    print(f"recived message '{msg.topic}': {payload}")

    if payload == "start" or payload == "insert again":
        try:
            time.sleep(2)

            GPIO.output(RELAY_PIN, RELAY_ON_STATE)
            time.sleep(4)

        finally:
            GPIO.output(RELAY_PIN, RELAY_OFF_STATE)

# setup relay
def setup():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELAY_PIN, GPIO.OUT)
    GPIO.output(RELAY_PIN, RELAY_OFF_STATE)

try:
    setup()

    client = mqtt.Client(transport="websockets")
    
    # activation encription tls for wss
    client.tls_set()

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"connected to wss://{MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    print(f"watch the topic '{MQTT_TOPIC}'...")
    client.loop_forever()

except KeyboardInterrupt:
    print("\nprogram stoped.")
except Exception as e:
    print(f"\nerror: {e}")
finally:
    GPIO.cleanup()
