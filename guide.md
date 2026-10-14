# AWS Serverless Gun Detection — Complete Step-by-Step Guide

**Region: ap-south-1 (Mumbai) for everything**

## Prerequisites

- An AWS account with billing enabled (Rekognition Custom Labels is not free-tier)
- A free Kaggle account to download the dataset
- A modern web browser and a text editor
- Basic familiarity with the AWS console

## Overview

| Phase | What you do |
|---|---|
| 1 | Prepare the dataset locally |
| 2 | Create an S3 bucket and upload the dataset |
| 3 | Train a Rekognition Custom Labels model |
| 4 | Create an IAM role for Lambda |
| 5 | Deploy the Lambda function |
| 6 | Expose it through API Gateway |
| 7 | Host the frontend on S3 |
| 8 | Test, then shut down the model |

> 💰 **Cost warning:** Training costs ~$1. Running the model costs ~$4/hour. Follow Phase 8 and Cleanup to avoid surprise bills.

---

## Phase 1: Prepare Your Dataset (Local — No AWS Needed)

**Step 1: Download the Kaggle dataset**

1. Go to kaggle.com and search for "gun detection dataset YOLO"
2. Download and extract the zip file
3. Open the extracted folder — you will see .jpg/.png images and .txt label files

**Step 2: Organise images into two folders**

On your computer, create this exact structure:

```
dataset/
  gun/
  nogun/
```

1. Copy 50–100 clear gun images into `dataset/gun/`
2. Find 50–100 non-gun images (rooms, objects, people) and put them in `dataset/nogun/`
3. Keep numbers roughly equal — imbalance causes poor accuracy
4. Delete blurry, tiny, or duplicate images
5. Rename any files with spaces (e.g. `my gun.jpg` → `my_gun.jpg`)

> You only need image files (.jpg/.png). Ignore all .txt, .yaml, .cfg, and .xml files.

---

## Phase 2: S3 Bucket Setup

**Step 3: Create an S3 bucket**

1. Go to console.aws.amazon.com and log in
2. Confirm top-right region shows **ap-south-1 (Mumbai)**
3. Search for **S3** and open it
4. Click **Create bucket**
5. Bucket name: something unique like `gun-detection-yourname-2024` (lowercase, no spaces)
6. Region: confirm **ap-south-1**
7. Leave "Block all public access" checked for now
8. Leave everything else default and click **Create bucket**

**Step 4: Upload the dataset**

1. Click your bucket to open it
2. Click **Upload** → **Add folder**
3. Select your local `dataset/` folder (the one containing `gun/` and `nogun/` subfolders)
4. Confirm you see files listed under both `gun/` and `nogun/` prefixes
5. Click **Upload** and wait for it to finish
6. Verify in the console that `dataset/gun/` and `dataset/nogun/` folders exist in the bucket

---

## Phase 3: Rekognition Custom Labels

> ⚠️ Training costs ~$1 for a small dataset. Running the model costs ~$4/hour — stop it immediately after testing.

**Step 5: Create a Rekognition project**

1. Search for **Rekognition** in the AWS console and open it
2. In the left sidebar click **Custom Labels**
3. If you see a first-time setup screen, click **Get started** (AWS creates an internal S3 bucket — ignore it)
4. Click **Create project**
5. Project name: `gun-detector`
6. Click **Create project**

**Step 6: Create the training dataset**

1. Inside your project, click **Create dataset**
2. Dataset name: `gun-dataset`
3. Image location: select **Import images from Amazon S3 bucket**
4. S3 folder location: `s3://YOUR-BUCKET-NAME/dataset/`
5. Automatic labelling: select **Automatic labelling** (this reads folder names as class labels)
6. Click **Submit** and wait 1–2 minutes
7. You should see images listed with labels `gun` and `nogun`

**Step 7 (only if you got Access Denied): Fix S3 permissions for Rekognition**

Go to S3 → your bucket → **Permissions** tab → **Bucket policy** → **Edit** and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowRekognition",
      "Effect": "Allow",
      "Principal": { "Service": "rekognition.amazonaws.com" },
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::YOUR-BUCKET-NAME",
        "arn:aws:s3:::YOUR-BUCKET-NAME/*"
      ]
    }
  ]
}
```

Replace `YOUR-BUCKET-NAME` with your actual bucket name, then **Save changes** and retry Step 6.

**Step 8: Train the model**

1. Inside your project, click **Train model**
2. Training dataset: select `gun-dataset`
3. Leave test split as default (80/20 automatic)
4. Click **Train model**
5. Training takes 30–60 minutes. You can close the browser — AWS emails you when done
6. After training, check metrics: aim for Precision and Recall both above 70%

**Step 9: Copy the Model ARN**

1. Open your project → click on the trained model
2. Find the **Model ARN** — it looks like: `arn:aws:rekognition:ap-south-1:123456789:project/gun-detector/version/...`
3. Copy it and save it in a text file — you need it in the Lambda code

---

## Phase 4: IAM Role for Lambda

**Step 10: Create an IAM role**

1. Search for **IAM** in the AWS console and open it
2. Left sidebar → **Roles** → **Create role**
3. Trusted entity type: **AWS service**
4. Use case: **Lambda** → click **Next**
5. Search for and tick these three policies:
    - `AmazonRekognitionFullAccess`
    - `AmazonS3ReadOnlyAccess`
    - `AWSLambdaBasicExecutionRole`
6. Click **Next**, role name: `gun-lambda-role`
7. Click **Create role**

---

## Phase 5: Lambda Function

**Step 11: Create the Lambda function**

1. Search for **Lambda** and open it — confirm region is **ap-south-1**
2. Click **Create function** → **Author from scratch**
3. Function name: `gun-detector-function`
4. Runtime: **Python 3.12**
5. Architecture: **x86_64**
6. Expand **Change default execution role** → **Use an existing role** → select `gun-lambda-role`
7. Click **Create function**

**Step 12: Add the function code**

1. In the Code source section, click `lambda_function.py`
2. Delete all existing code and paste the following
3. Replace `YOUR_MODEL_ARN` with the ARN from Step 9
4. Replace `YOUR_BUCKET_NAME` with your bucket name
5. Click **Deploy**

```python
import json
import boto3
import base64
import uuid

MODEL_ARN = "YOUR_MODEL_ARN"
BUCKET_NAME = "YOUR_BUCKET_NAME"
REGION = "ap-south-1"

rekognition = boto3.client("rekognition", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)

def lambda_handler(event, context):
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST,OPTIONS"
    }

    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": headers, "body": ""}

    try:
        body = json.loads(event["body"])
        image_data = base64.b64decode(body["image"])

        key = f"uploads/{uuid.uuid4()}.jpg"
        s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=image_data)

        response = rekognition.detect_custom_labels(
            ProjectVersionArn=MODEL_ARN,
            Image={"S3Object": {"Bucket": BUCKET_NAME, "Name": key}},
            MinConfidence=50
        )

        s3.delete_object(Bucket=BUCKET_NAME, Key=key)

        labels = response.get("CustomLabels", [])
        if labels:
            top = max(labels, key=lambda x: x["Confidence"])
            result = {
                "detected": top["Name"],
                "confidence": round(top["Confidence"], 2),
                "all_labels": labels
            }
        else:
            result = {"detected": "none", "confidence": 0, "all_labels": []}

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(result)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": str(e)})
        }
```

**Step 13: Increase Lambda timeout**

1. Inside your Lambda function → **Configuration** tab → **General configuration** → **Edit**
2. Timeout: set to **30 seconds**
3. Memory: set to **256 MB**
4. Click **Save**

**Step 14: Allow Lambda to write to your S3 bucket**

Go to S3 → your bucket → **Permissions** → **Bucket policy** → **Edit**.

Add this as a second statement inside the existing `"Statement": [...]` array (add a comma after the first statement, then paste this):

```json
{
  "Sid": "AllowLambda",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::YOUR-ACCOUNT-ID:role/gun-lambda-role"
  },
  "Action": ["s3:PutObject", "s3:DeleteObject", "s3:GetObject"],
  "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/*"
}
```

Replace `YOUR-ACCOUNT-ID` (find your 12-digit account ID under your name in the top-right menu) and `YOUR-BUCKET-NAME`. Save the policy.

---

## Phase 6: API Gateway

**Step 15: Create an HTTP API**

1. Search for **API Gateway** and open it — confirm region is **ap-south-1**
2. Click **Create API** → choose **HTTP API** → click **Build**
3. Click **Add integration** → **Lambda** → select `gun-detector-function`
4. API name: `gun-detection-api`
5. Click **Next**

**Step 16: Configure the route**

1. Method: **POST**, Resource path: `/detect`, Integration: your Lambda function
2. Click **Next**
3. Stage name: `$default`, Auto-deploy: **enabled**
4. Click **Next** → **Create**

**Step 17: Enable CORS**

1. Open your new API → left sidebar → **CORS** → **Configure**
2. Access-Control-Allow-Origin: `*`
3. Access-Control-Allow-Headers: `content-type`
4. Access-Control-Allow-Methods: `POST, OPTIONS`
5. Click **Save**

**Step 18: Copy the Invoke URL**

1. Left sidebar → **Stages** → click `$default`
2. Copy the **Invoke URL** — it looks like `https://abc123.execute-api.ap-south-1.amazonaws.com`
3. Your full API endpoint will be: `https://abc123.execute-api.ap-south-1.amazonaws.com/detect`
4. Save this — you need it in the frontend

---

## Phase 7: Frontend

**Step 19: Create index.html**

Create a file named `index.html` on your computer with the following code. Replace `YOUR_API_URL` with your full API endpoint from Step 18 (include `/detect` at the end).

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gun Detection</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: sans-serif; background: #f4f4f4; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
    .card { background: white; border-radius: 12px; padding: 32px; max-width: 480px; width: 100%; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
    h1 { font-size: 22px; margin-bottom: 6px; }
    p.sub { font-size: 14px; color: #666; margin-bottom: 24px; }
    .upload-area { border: 2px dashed #ccc; border-radius: 8px; padding: 24px; text-align: center; cursor: pointer; margin-bottom: 16px; }
    .upload-area:hover { border-color: #185FA5; background: #f0f6ff; }
    #file-input { display: none; }
    #preview { max-width: 100%; border-radius: 8px; margin-bottom: 16px; display: none; }
    button { width: 100%; padding: 12px; background: #185FA5; color: white; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; }
    button:hover { background: #0C447C; }
    button:disabled { background: #999; cursor: not-allowed; }
    .result { margin-top: 20px; padding: 16px; border-radius: 8px; text-align: center; display: none; }
    .result.gun { background: #FCEBEB; border: 1px solid #F7C1C1; }
    .result.nogun { background: #EAF3DE; border: 1px solid #C0DD97; }
    .result .label { font-size: 22px; font-weight: 600; }
    .result .conf { font-size: 14px; color: #555; margin-top: 4px; }
    #spinner { display: none; text-align: center; margin-top: 16px; color: #555; font-size: 14px; }
  </style>
</head>
<body>
<div class="card">
  <h1>Gun Detection</h1>
  <p class="sub">Upload an image to check for weapons</p>
  <div class="upload-area" onclick="document.getElementById('file-input').click()">
    <p>Click to upload an image</p>
    <p style="font-size:12px;color:#999;margin-top:4px">JPG or PNG</p>
  </div>
  <input type="file" id="file-input" accept="image/*" onchange="handleFile(event)">
  <img id="preview">
  <button id="detect-btn" onclick="detect()" disabled>Detect</button>
  <div id="spinner">Analysing image...</div>
  <div class="result" id="result">
    <div class="label" id="result-label"></div>
    <div class="conf" id="result-conf"></div>
  </div>
</div>
<script>
  const API_URL = "YOUR_API_URL";
  let selectedFile = null;

  function handleFile(e) {
    selectedFile = e.target.files[0];
    if (!selectedFile) return;
    const reader = new FileReader();
    reader.onload = ev => {
      const p = document.getElementById('preview');
      p.src = ev.target.result;
      p.style.display = 'block';
    };
    reader.readAsDataURL(selectedFile);
    document.getElementById('detect-btn').disabled = false;
    document.getElementById('result').style.display = 'none';
  }

  async function detect() {
    if (!selectedFile) return;
    document.getElementById('detect-btn').disabled = true;
    document.getElementById('spinner').style.display = 'block';
    document.getElementById('result').style.display = 'none';
    const reader = new FileReader();
    reader.onload = async ev => {
      const base64 = ev.target.result.split(',')[1];
      try {
        const resp = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: base64 })
        });
        const data = await resp.json();
        const isGun = data.detected === 'gun';
        const result = document.getElementById('result');
        result.className = 'result ' + (isGun ? 'gun' : 'nogun');
        document.getElementById('result-label').textContent = isGun ? 'Gun Detected' : 'No Gun Found';
        document.getElementById('result-conf').textContent = 'Confidence: ' + data.confidence + '%';
        result.style.display = 'block';
      } catch (err) {
        alert('Error: ' + err.message);
      } finally {
        document.getElementById('spinner').style.display = 'none';
        document.getElementById('detect-btn').disabled = false;
      }
    };
    reader.readAsDataURL(selectedFile);
  }
</script>
</body>
</html>
```

**Step 20: Enable S3 static website hosting**

1. S3 → your bucket → **Properties** tab
2. Scroll to **Static website hosting** → **Edit**
3. Enable it, Index document: `index.html` → **Save changes**
4. Go to **Permissions** tab → **Block public access** → **Edit**
5. Uncheck **Block all public access**, confirm the warning, **Save changes**
6. Go to **Bucket policy** → **Edit**, add this statement to your existing policy:

```json
{
  "Sid": "PublicReadWebsite",
  "Effect": "Allow",
  "Principal": "*",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/index.html"
}
```

7. Upload `index.html` to the **root** of the S3 bucket (not inside any subfolder)
8. Go to Properties → Static website hosting → copy the **Bucket website endpoint**
9. Open that URL in your browser — your app should load

---

## Phase 8: Test and Shut Down

**Step 21: Start the Rekognition model**

1. Rekognition → Custom Labels → `gun-detector` project → your model
2. Click **Start model**, Inference units: **1**
3. Click **Start** and wait 2–5 minutes for status to show **RUNNING**

**Step 22: Test the app**

1. Open your S3 website URL
2. Upload a gun image → click Detect → should return "Gun Detected"
3. Upload a non-gun image → should return "No Gun Found"
4. If you get a CORS error → re-check API Gateway CORS settings (Step 17)
5. If you get an error in the result → go to Lambda → **Monitor** → **View logs in CloudWatch** to see what went wrong

**Step 23: Stop the model immediately after testing**

1. Rekognition → Custom Labels → your project → your model
2. Click **Stop model** → confirm
3. Wait for status to show **STOPPED**

> 🚨 Never leave the model in RUNNING state when not testing. It costs ~$4/hour.

---

## Cleanup (When Project Is Done)

Delete in this order to avoid dependency errors:

1. **Rekognition**: stop model → delete model → delete project
2. **API Gateway**: select API → Actions → Delete
3. **Lambda**: select function → Actions → Delete
4. **S3**: empty bucket → delete bucket
5. **IAM**: Roles → find `gun-lambda-role` → Delete
6. **CloudWatch**: Log groups → `/aws/lambda/gun-detector-function` → Delete

---

## Common Errors Quick Reference

|Error|Likely cause|Fix|
|---|---|---|
|Access Denied on dataset import|S3 bucket policy missing|Do Step 7|
|CORS error in browser|API Gateway CORS not set|Re-do Step 17|
|Lambda timeout|Timeout too short|Increase to 30s (Step 13)|
|Model not found|Wrong ARN or model not RUNNING|Check ARN, start model|
|Empty result / 0 confidence|Model not started|Start model (Step 21)|
|500 error from Lambda|Permission or code issue|Check CloudWatch logs|

---

Made by K:)