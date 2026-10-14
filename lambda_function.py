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