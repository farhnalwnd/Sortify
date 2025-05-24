import torch
from torchvision import transforms
from PIL import Image
import os

# === PATH MODEL ===
MODEL_PATH = "/home/admin/caps/aiCameraDetection/models/best.pt"

# === TRANSFORMASI SESUAI MODEL ===
transform = transforms.Compose([
    transforms.Resize((512, 384)),       # Ganti jika model input-nya beda
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

# === LOAD MODEL SEKALI ===
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = torch.load(MODEL_PATH, map_location=device, weights_only=False)
model.eval()

# === LABEL (EDIT SESUAI KELAS MODEL) ===
CLASS_NAMES = ['organic', 'plastic', 'paper']  # Contoh label, ganti sesuai modelmu

# === FUNGSI KLASIFIKASI GAMBAR ===
def classify_image(image_path):
    image = Image.open(image_path).convert('RGB')
    image_tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(image_tensor)
        _, predicted = torch.max(output, 1)
        label = CLASS_NAMES[predicted.item()]

    return label
