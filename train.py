import json
import os
import warnings
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import timm

# CONFIGURATION
JSON_FILE = 'export.json'
IMAGE_DIR = './'

class DeepfakeDataset(Dataset):
    def __init__(self, json_data, transform=None):
        self.data = json_data
        self.transform = transform
        self.valid_data = []
        
        local_files = {}
        for root, dirs, files in os.walk(IMAGE_DIR):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    local_files[f.lower()] = os.path.join(root, f)

        print(f"System Check: Located {len(local_files)} image files on disk.")

        # parser
        for item in self.data:
            # Label studio label extractor
            label_raw = item.get('choice', item.get('label', item.get('image_labels', None)))
            
            if not label_raw and 'annotations' in item:
                try:
                    res = item['annotations'][0]['result'][0]['value']
                    label_raw = res.get('choices', res.get('labels', [None]))[0]
                except (IndexError, KeyError):
                    label_raw = None

            if isinstance(label_raw, list) and len(label_raw) > 0:
                label_raw = label_raw[0]

            if not label_raw:
                continue

            label_str = str(label_raw).strip().lower()
            
            # Map string representation to 0 (Real) or 1 (Deepfake)
            if 'real' in label_str:
                label = 0
            elif 'fake' in label_str or 'deepfake' in label_str:
                label = 1
            else:
                continue

            # Extract filename from manifest
            raw_path = item.get('image', item.get('file_upload', item.get('file', '')))
            raw_filename = os.path.basename(str(raw_path)).lower()
            
            # Match disk file 
            matched_path = None
            if raw_filename in local_files:
                matched_path = local_files[raw_filename]
            else:
                for local_name, full_path in local_files.items():
                    if local_name in raw_filename or raw_filename.endswith(local_name):
                        matched_path = full_path
                        break

            if matched_path:
                self.valid_data.append((matched_path, label))

        print(f"System Check: Successfully matched {len(self.valid_data)} records from manifest to disk files.")
        
        if len(self.valid_data) == 0:
            print("\n--- DEBUG DIAGNOSTICS ---")
            if self.data:
                print("Sample manifest item:", json.dumps(self.data[0], indent=2))
            print("Sample disk files found:", list(local_files.keys())[:5])
            raise ValueError("CRITICAL FAILURE: No images matched. Check debug output above.")

    def __len__(self):
        return len(self.valid_data)

    def __getitem__(self, idx):
        img_path, label = self.valid_data[idx]
        image = Image.open(img_path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        return image, torch.tensor(label, dtype=torch.long)

# Data loader
print("Parsing Label Studio manifest...")
with open(JSON_FILE, 'r') as f:
    data = json.load(f)

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

dataset = DeepfakeDataset(data, transform=transform)
dataloader = DataLoader(dataset, batch_size=4, shuffle=True)

# Foundation
print("Initializing EfficientNet-B0...")
model = timm.create_model('efficientnet_b0', pretrained=True, num_classes=2)
model.train()

# TRAINING LOOP
optimizer = optim.Adam(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()

print("Initiating fine-tuning (20 Epochs)...")
for epoch in range(20):
    total_loss = 0
    for images, labels in dataloader:
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    print(f"Epoch {epoch+1}/20 | Loss: {total_loss/len(dataloader):.4f}")

# EXPORT TO ONNX
print("Training complete. Converting model to ONNX format...")
model.eval()
dummy_input = torch.randn(1, 3, 224, 224)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    torch.onnx.export(
        model, 
        dummy_input, 
        "model.onnx", 
        export_params=True, 
        opset_version=11, 
        input_names=['input'], 
        output_names=['output'], 
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
    )

print("Mission Accomplished: model.onnx is successfully created and saved.")