# AWS Serverless Gun Detection

A fully serverless, cloud-based image classification system that detects firearms in uploaded images. Built on AWS with Amazon Rekognition Custom Labels, Lambda, API Gateway, and S3, with a lightweight web frontend.

**Region:** ap-south-1 (Mumbai)

---

## What It Does

Users upload an image through a web page. The system analyses it with a custom-trained computer vision model and returns a verdict — **Gun Detected** or **No Gun Found** — along with a confidence score. No servers are provisioned or managed.

## Architecture

```
Browser (S3-hosted static page)
        │  POST /detect  (base64 image)
        ▼
API Gateway (HTTP API)
        ▼
AWS Lambda (Python 3.12)
   ├─ stores image temporarily in S3
   ├─ calls Rekognition Custom Labels
   └─ deletes image, returns result as JSON
        ▼
Amazon Rekognition Custom Labels (trained model)
```

| Component | Role |
|---|---|
| **Amazon S3** | Stores the training dataset, temporary uploads, and hosts the static frontend |
| **Rekognition Custom Labels** | Trains and serves the gun / no-gun classification model |
| **AWS Lambda** | Backend logic: receives the image, invokes the model, returns the result |
| **API Gateway (HTTP API)** | Public HTTPS endpoint connecting the frontend to Lambda |
| **IAM** | Least-purpose role granting Lambda access to S3, Rekognition, and logging |
| **CloudWatch** | Lambda logs for debugging |

## How It Works

### 1. Dataset preparation
A gun-detection dataset from Kaggle is curated into two balanced classes, `gun` and `nogun`, with roughly 50–100 clean images each. Blurry, tiny, and duplicate images are removed.

### 2. Storage
The dataset is uploaded to an S3 bucket, with folder names serving as class labels.

### 3. Model training
Rekognition Custom Labels imports the dataset from S3 and automatically labels images from their folder names. It trains a model with an automatic 80/20 train/test split. Quality is checked via precision and recall, targeting above 70%.

### 4. Backend inference
A Lambda function receives a base64-encoded image, saves it temporarily to S3, sends it to the trained model, and deletes it right after. The top prediction and confidence are returned. Predictions below 50% confidence are ignored.

### 5. API layer
API Gateway exposes a `POST /detect` route with CORS enabled so the browser can call it.

### 6. Frontend
A single-page HTML app, hosted on S3 static website hosting, lets users select an image, preview it, and view the result with colour-coded feedback.

### 7. Run on demand
The Rekognition model is started only for testing and stopped immediately afterwards to control cost.

## Cost Notes

- Training: ~$1 for a small dataset
- Running the model: ~$4/hour while in RUNNING state
- Always stop the model when not in use

## Known Limitations

- Small dataset, so accuracy depends heavily on image quality and class balance
- Image-level classification only; no bounding boxes or video support
- The public frontend has no authentication; add API keys or auth before any real-world use
- Intended for learning and demonstration, not production security screening

## Getting Started

See [guide.md](guide.md) for the full step-by-step setup, troubleshooting, and cleanup instructions.

---

Made by K:)
