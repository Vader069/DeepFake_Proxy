import torch
import timm
print("Initializing model...")
model=timm.create_model("efficientnet_b0",pretrained=True)
save_path="model.pth"
torch.save(model.state_dict(),save_path)
print(f"Download complete. Model Saved to {save_path}")