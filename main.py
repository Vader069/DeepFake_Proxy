from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import boto3
import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import datetime
import os

# Configs
REGION = "ap-south-2"
PROD_BUCKET = "deep-fake-proxy-production"
QUARANTINE_BUCKET = "deep-fake-proxy-quarantine"
SNS_TOPIC_ARN = "arn:aws:sns:ap-south-2:515964624887:DeepFakeAlerts"
DYNAMO_TABLE_NAME = "DeepFakeLogs"

app = FastAPI()

# Allow the frontend to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AWS Clients (Authenticated automatically via EC2 IAM Role)
s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
sns = boto3.client('sns', region_name=REGION)

# Load the ONNX Model
ort_session = ort.InferenceSession("model.onnx")

def process_image_for_model(image_bytes):
    """Format image for EfficientNet-B0 ONNX runtime with proper normalization"""
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    img = img.resize((224, 224))
    
    # 1. Scale pixels from 0-255 down to 0.0-1.0
    img_data = np.array(img).astype('float32') / 255.0 
    
    # 2. Apply Standard ImageNet Normalization (Required for PyTorch models)
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_data = (img_data - mean) / std
    
    # 3. Restructure matrix for ONNX (Channels-First, add Batch Dimension)
    img_data = np.transpose(img_data, (2, 0, 1)) 
    img_data = np.expand_dims(img_data, axis=0)  
    
    return img_data

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    # 1. Read Image
    image_bytes = await file.read()
    
    # 2. Run ONNX Inference
    input_tensor = process_image_for_model(image_bytes)
    input_name = ort_session.get_inputs()[0].name
    outputs = ort_session.run(None, {input_name: input_tensor})
    
    # Extract raw logit and apply Sigmoid to squash it between 0 and 1
    raw_logit = float(outputs[0][0][0])
    fake_probability = float(1 / (1 + np.exp(-raw_logit)))
    is_fake = fake_probability > 0.5

    # 3. AWS S3 Routing
    target_bucket = QUARANTINE_BUCKET if is_fake else PROD_BUCKET
    file.file.seek(0) # Reset file pointer before upload
    s3.upload_fileobj(file.file, target_bucket, file.filename)

    # 4. AWS DynamoDB Logging
    table = dynamodb.Table(DYNAMO_TABLE_NAME)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    table.put_item(
        Item={
            'FileName': file.filename,
            'Timestamp': timestamp,
            'IsFake': is_fake,
            'Confidence': str(round(fake_probability * 100, 2)) + "%"
        }
    )

    # 5. AWS SNS Alert Trigger
    if is_fake:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="SECURITY ALERT: Deepfake Detected",
            Message=f"A synthetic image ({file.filename}) was detected with {fake_probability*100:.2f}% confidence. It has been routed to the Quarantine Bucket."
        )

    # 6. Return Verdict to Frontend
    return {
        "filename": file.filename,
        "is_fake": is_fake,
        "confidence": fake_probability
    }