import time
import threading
import os
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from picamera2 import Picamera2
import cv2

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 8084 
MQTT_TOPIC = "waste/raw"

MODEL_PATH = "models/best.pt"
IMAGES_DIR = "/home/admin/caps/aiCameraDetection/images"

LABEL_TO_CATEGORY_MAP = {
    "recycle": ["plastic", "metal"],
    "organic": ["organic"],
    "paper": ["paper"],
    "other": ["mask", "battery"]
}

running = False
process_command = None

try:
    model = YOLO(MODEL_PATH)
    print("yolo successfully loaded.")
except Exception as e:
    print(f"error to load yolo: {e}")
    exit()

def get_category_from_label(label):
    label = label.lower()
    for category, labels_in_category in LABEL_TO_CATEGORY_MAP.items():
        if label in labels_in_category:
            return category
    return "other"

# clasify camera
def classify_and_publish(picam2, mqtt_client):
    print("prepare the camera")
    time.sleep(5)
    
    frame = picam2.capture_array()
    
    print("procesing the image")
    results = model(frame)

    timestamp = int(time.time())
    filepath = os.path.join(IMAGES_DIR, f"classified_{timestamp}.jpg")
    try:
        annotated_frame = results[0].plot()
        cv2.imwrite(filepath, annotated_frame)
        print(f"image saved at: {filepath}")
    except Exception as plot_error:
        print(f"failed to save the image, error: {plot_error}")
        cv2.imwrite(filepath, frame)

    final_category = "no object detected"
    
    try:
        result = results[0]
        detected_label = ""
        
        if result.boxes and len(result.boxes) > 0:
            confidences = result.boxes.conf.tolist()
            class_ids = result.boxes.cls.tolist()
            
            best_idx = confidences.index(max(confidences))
            detected_label = model.names[int(class_ids[best_idx])]

        elif result.probs is not None:
            class_id = result.probs.top1
            detected_label = model.names[class_id]
        
        if detected_label:
            final_category = get_category_from_label(detected_label)
            print(f"[GROUPING] Label terdeteksi: '{detected_label}', Dikelompokkan ke: '{final_category}'")
        
    except Exception as e:
        print(f"[YOLO ERROR] at configuring result: {e}")
        final_category = "no object detected"

    print(f"[CLASSIFICATION] Final: {final_category}")
    mqtt_client.publish(MQTT_TOPIC, final_category)

def camera_loop():
    global running, process_command
    
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 640)})
    picam2.configure(config)
    picam2.start()
    print("camera ready.")

    while True:
        if running and process_command:
            print(f"camera recive : {process_command}")
            classify_and_publish(picam2, client)
            process_command = None
        time.sleep(0.5)

def on_connect(client, userdata, flags, rc):
    #callback to mqtt
    if rc == 0:
        print(f"mqtt connected succsessfully")
        client.subscribe(MQTT_TOPIC)
        print(f"connected to: '{MQTT_TOPIC}'")
    else:
        print(f"connection failde, error: {rc}")

def on_message(client, userdata, msg):
    global running, process_command
    message = msg.payload.decode().strip().lower()
    print(f"recive message: {message}")

    if message == "start":
        print("program started")
        running = True
        process_command = "start"
    
    elif message == "insert again" and running:
        print("restart the program.")
        process_command = "insert again"
        
    elif message == "stop":
        print("program stop by user.")
        running = False
        process_command = None

client = mqtt.Client(transport="websockets") 

client.tls_set()

client.on_connect = on_connect
client.on_message = on_message

# run camera at background
camera_thread = threading.Thread(target=camera_loop)
camera_thread.daemon = True
camera_thread.start()

try:
    print(f"connect mqtt broker wss://{MQTT_BROKER}:{MQTT_PORT}...") 
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nprogram stoped.")
except Exception as e:
    print(f"\nerror: {e}")
finally:
    print("done")
