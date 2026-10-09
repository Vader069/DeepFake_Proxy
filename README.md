# DEEPFAKE PROXY: AI-Powered Image Authentication System

## 1. Mission Overview

The Deepfake Proxy is a full-stack, cloud-native application designed to ingest image payloads, analyze them using a convolutional neural network for synthetic manipulation, and autonomously route the data based on the AI's verdict. The system is built for high availability, utilizing Dockerized microservices, secure HTTPS tunneling, and automated AWS cloud infrastructure.

## 2. System Architecture & Workflow

The application operates on a globally distributed architecture, bridging client-side processing with a secure cloud backend:

1. **The Command Center (Frontend):** A static HTML/CSS/Vanilla JS interface hosted on AWS Amplify. It captures the user's image and transmits it securely over HTTPS.
2. **The Ingress Node (Nginx Reverse Proxy):** Hosted on an AWS EC2 instance. It intercepts the incoming payload, decrypts the SSL transmission (via Certbot/Let's Encrypt), and bypasses default size restrictions to funnel the image into the internal Docker network.
3. **The Engine (FastAPI & ONNX):** A Dockerized Python backend that receives the image, applies mathematical normalization (ImageNet standards), and feeds it into an EfficientNet-B0 ONNX model.
4. **The Cloud Ecosystem (AWS Integrations):** Based on the AI's Softmax probability output, the backend interacts with three AWS services:
* **AWS S3:** Routes authentic images to a Production bucket and synthetic images to a Quarantine bucket.
* **AWS DynamoDB:** Logs a permanent cryptographic record of the scan, including the filename, UTC timestamp, classification, and exact confidence percentage.
* **AWS SNS:** Triggers an automated email/SMS security alert to administrators if a deepfake is detected.



## 3. Technology Stack

* **Frontend:** HTML5, CSS3, Vanilla JavaScript
* **Backend API:** Python 3.10, FastAPI, Uvicorn
* **Machine Learning:** PyTorch (Training), ONNX Runtime (Inference), EfficientNet-B0
* **Containerization:** Docker
* **Web Server / Proxy:** Nginx, Certbot (SSL/HTTPS)
* **Cloud Infrastructure (AWS):** EC2, S3, DynamoDB, SNS, Amplify, Route 53 (DNS)
* **Domain Routing:** DuckDNS / Custom Domain

## 4. The Machine Learning Pipeline

The core intelligence of this system is based on an **EfficientNet-B0** convolutional neural network.

* **Model Optimization (ONNX):** The model was originally trained using PyTorch (`.pth`). However, deploying a full PyTorch environment to a lightweight cloud server consumes massive amounts of memory. To bypass this, the model was compiled into the **ONNX (Open Neural Network Exchange)** format. Using `onnxruntime`, the API executes matrix math at highly optimized speeds on standard CPU hardware without requiring a heavy PyTorch dependency.
* **Image Calibration (Preprocessing):** Neural networks cannot process raw JPEG/PNG files. When an image hits the API, `numpy` and `PIL` are used to execute a strict preprocessing pipeline:
1. **Resizing:** Forced to `224x224` pixels.
2. **Scaling:** Pixel arrays (0-255) are mathematically squashed to a `0.0` to `1.0` scale.
3. **ImageNet Normalization:** A specific statistical color filter is applied (Mean: `[0.485, 0.456, 0.406]`, Std: `[0.229, 0.224, 0.225]`) to match the exact conditions the model was originally trained under. Without this, the AI suffers from sensory overload and flags authentic images as fake.
4. **Tensor Formatting:** Transposed into a "Channels-First" layout `(1, 3, 224, 224)` required by ONNX.


* **Mathematical Verdict (Softmax):** The ONNX model outputs raw, unnormalized scores called *logits* (e.g., `[ 1.37, -8.92]`). The API applies a **Softmax function** to these logits, forcing them into a clean probability distribution that equals 100%. The system extracts Index 1 (the "Fake" probability) to make its final S3 routing decision.

## 5. Backend API Architecture (FastAPI & Boto3)

The backend operates continuously as a Uvicorn-driven **FastAPI** web server. It listens on Port 8000 for incoming POST requests from the frontend.

* **Zero-Trust AWS Authentication:** The Python script uses the `boto3` library to communicate with AWS S3, DynamoDB, and SNS. Crucially, there are **no hardcoded AWS credentials** in the source code. The EC2 instance running this code was assigned a cryptographic **IAM Role**. The `boto3` library automatically detects this role and inherits its permissions, ensuring maximum security.
* **CORS Configuration:** Cross-Origin Resource Sharing (CORS) middleware is enabled in FastAPI, allowing the externally hosted AWS Amplify frontend to successfully transmit payloads to the EC2 backend without browser security rejections.

### Local Development Commands

To test the backend locally before orbital deployment, the following commands are utilized in the terminal:

1. **Install Dependencies:**
```bash
pip install -r requirements.txt

```


*Why:* Installs `fastapi`, `uvicorn`, `python-multipart` (for image file parsing), `onnxruntime`, and `boto3` in the local environment.
2. **Ignite the Local Server:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000

```


*Why:* `uvicorn` acts as the Asynchronous Server Gateway Interface (ASGI). `main:app` targets the `app` instance inside `main.py`. `--host 0.0.0.0` binds the server to all network interfaces, allowing local network testing.

## 6. Cloud Infrastructure & EC2 Deployment

The backend engine operates on an AWS EC2 instance running Ubuntu. To ensure absolute consistency between local testing and cloud production, the FastAPI application is wrapped in a Docker container.

### Server Ignition Sequence

Once the AWS EC2 instance is provisioned and Port 8000 is opened in the AWS Security Group, the local payload (code, model, and dependencies) is beamed to the server using Secure Copy Protocol (SCP):

```bash
scp -i deepfake-key.pem main.py Dockerfile requirements.txt model.onnx ubuntu@<EC2_IP>:~/.

```

The server is then breached via SSH to install the native Docker engine, compile the image, and ignite the container:

```bash
ssh -i deepfake-key.pem ubuntu@<EC2_IP>
sudo apt update && sudo apt install docker.io -y
sudo docker build -t deepfake-api .
sudo docker run -d -p 8000:8000 deepfake-api

```

*(The `-d` flag runs the container in detached mode, while `-p 8000:8000` binds the container's internal API port to the EC2 instance's exposed port).*

## 7. Nginx Reverse Proxy & SSL Security

By default, the EC2 instance serves API traffic over unencrypted HTTP. However, modern web browsers employ strict security protocols that instantly block API calls from a secure HTTPS frontend to an insecure HTTP backend (the "Mixed Content" blockade).

To bypass this and harden the perimeter, **Nginx** is deployed as a reverse proxy, and **Let's Encrypt (Certbot)** is used to forge a production-grade SSL certificate.

### The Reverse Proxy Configuration

Nginx intercepts public web traffic and quietly funnels it into the internal Docker network on Port 8000. The configuration file (`/etc/nginx/sites-available/deepfake-api`) is architected as follows:

```nginx
server {
    server_name deepfakeproxy.duckdns.org;
    client_max_body_size 50M; # Critical: Bypasses Nginx's default 1MB file size limit

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

```

**Operational Nuance:** By default, Nginx will instantly terminate any incoming file upload larger than 1 Megabyte. Injecting `client_max_body_size 50M;` forces the proxy to accept heavy, high-resolution image payloads without crashing the connection.

### Encrypting the Tunnel

```bash
sudo certbot --nginx -d deepfakeproxy.duckdns.org

```

This single command automatically negotiates the cryptographic handshake, validates domain ownership, and rewrites the Nginx configuration to force all traffic through Port 443 (HTTPS).

## 8. AWS Amplify & Global Routing

The frontend Command Center (HTML, CSS, JS) is physically decoupled from the backend and deployed via **AWS Amplify**.

1. **Static Cloud Hosting:** The UI files are compressed into a `.zip` archive and manually deployed to the Amplify Console. Because the UI is entirely client-side, it runs natively within the user's browser, eliminating the need for a dedicated frontend web server.
2. **DNS & Edge Routing:** The Amplify environment is bound to a custom vanity URL. Amplify autonomously handles the heavy lifting of provisioning SSL certificates via AWS Certificate Manager (ACM) and distributes the UI globally across Amazon's Content Delivery Network (CDN).
3. **The Secure Uplink:** The frontend `script.js` uses asynchronous JavaScript to `fetch()` data directly from the Nginx-secured EC2 domain (`[https://deepfakeproxy.duckdns.org/analyze](https://deepfakeproxy.duckdns.org/analyze)`), seamlessly bridging the separate frontend and backend cloud architectures into one unified application.

---
