import onnxruntime as ort
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk

TARGET_IMAGE = "image1.png"

def calculate_softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()

print("Waking up the neural brain...")
session = ort.InferenceSession("model.onnx")

print(f"Analyzing target: {TARGET_IMAGE}...")
img = Image.open(TARGET_IMAGE).convert('RGB')
model_img = img.resize((224, 224))


img_np = (np.array(model_img, dtype=np.float32) / 255.0 - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
input_data = np.transpose(img_np, (2, 0, 1))[np.newaxis, ...].astype(np.float32)


logits = session.run(None, {session.get_inputs()[0].name: input_data})[0][0]


probabilities = calculate_softmax(logits)
real_conf = probabilities[0] * 100
fake_conf = probabilities[1] * 100

is_fake = fake_conf > 50.0
verdict = "WARNING: DEEPFAKE DETECTED" if is_fake else "CLEAR: HUMAN CONFIRMED"
color = "red" if is_fake else "green"
details = f"Real Match: {real_conf:.2f}%   |   Deepfake Match: {fake_conf:.2f}%"


print("Deploying visual interface...")
root = tk.Tk()
root.title("Deepfake Proxy Analysis")
root.geometry("420x480")


display_img = ImageTk.PhotoImage(img.resize((300, 300)))
tk.Label(root, image=display_img).pack(pady=15)

tk.Label(root, text=verdict, fg=color, font=("Arial", 14, "bold")).pack()
tk.Label(root, text=details, font=("Arial", 12)).pack(pady=10)


root.mainloop()