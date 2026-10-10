# Jaltaranga — AWS Deployment Guide

This guide walks through deploying the complete Jaltaranga backend (SAM + Lambda + API Gateway + DynamoDB + S3) and frontend (Amplify or S3/CloudFront) to AWS.

---

## 1. Prerequisites

### A. Install AWS CLI & SAM CLI
If you don't have them installed on your machine:
* **AWS CLI**: Download from [aws.amazon.com/cli](https://aws.amazon.com/cli/) or run:
  ```powershell
  # Windows (via winget)
  winget install Amazon.AWSCLI
  ```
* **AWS SAM CLI**: Download from [docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) or run:
  ```powershell
  # Windows (via winget)
  winget install Amazon.ServerlessApplicationModelCLI
  ```

### B. Configure AWS Credentials
Ensure your AWS IAM user has permissions for CloudFormation, S3, Lambda, API Gateway, DynamoDB, SNS, and Bedrock.
```bash
aws configure
```
* **AWS Access Key ID**: `<your-access-key>`
* **AWS Secret Access Key**: `<your-secret-key>`
* **Default region name**: `ap-south-1` (Mumbai)
* **Default output format**: `json`

Verify authentication:
```bash
aws sts get-caller-identity
```

---

## 2. Deploy Backend Infrastructure (AWS SAM)

The AWS architecture is defined in `infra/template.yaml`.

### Step 2.1: Build the SAM template
From the project root:
```bash
sam build -t infra/template.yaml
```

### Step 2.2: Deploy via Guided SAM
Run the deployment wizard:
```bash
sam deploy --guided
```

You will be prompted with the following configuration:
* **Stack Name**: `jt-demo` (or `jt-dev`)
* **AWS Region**: `ap-south-1`
* **Parameter Env**: `demo` (or `dev`)
* **Parameter BedrockRegion**: `us-east-1` (or `ap-south-1` if your account has Nova access in Mumbai)
* **Parameter BedrockModelId**: `us.amazon.nova-micro-v1:0`
* **Parameter CorsOrigin**: `*` (or your frontend domain once deployed)
* **Parameter DispatchEmail**: `<your-team-email@example.com>` (receives test evacuation broadcast alerts)
* **Parameter BudgetEmail**: `<your-email@example.com>` (receives $10 budget threshold alerts)
* **Confirm changes before deploy**: `y`
* **Allow SAM CLI IAM role creation**: `y`
* **Save arguments to configuration file (samconfig.toml)**: `y`

### Step 2.3: Record Outputs
Once deployment completes, CloudFormation will print the following outputs:
* `ApiUrl`: e.g. `https://xyz123.execute-api.ap-south-1.amazonaws.com`
* `DataBucketName`: e.g. `jt-demo-data-123456789012`
* `DispatchTopicArn`: e.g. `arn:aws:sns:ap-south-1:...`

---

## 3. Seed the S3 Data Bucket

Upload the scenario replay data, corridor road network, and model assets to the deployed S3 bucket:

```bash
# Set your bucket name from Step 2.3
$BUCKET = "jt-demo-data-<your-account-id>"

# Upload static DEM & road graphs
aws s3 sync data/ "s3://$BUCKET/"

# Upload scenario data (July 2023 replay, forecasts, plans, roads)
aws s3 sync ml/out/ "s3://$BUCKET/"
aws s3 sync shared/fixtures/ "s3://$BUCKET/fixtures/"
```

*(Optional: If you have `make` installed, you can simply run: `make -C routing publish BUCKET=jt-demo-data-<accountid>`)*

---

## 4. Deploy Frontend (Web Console)

### Step 4.1: Configure Environment Variables
Create or edit `frontend/.env`:
```env
VITE_API_BASE=https://<your-api-id>.execute-api.ap-south-1.amazonaws.com
VITE_STATIC_BASE=https://<your-bucket-or-cloudfront-domain>
VITE_SCENARIO_ID=yamuna-2023-07
VITE_HERO_COLONY=DEL-YP-04
```

### Step 4.2: Build the Production Bundle
```bash
cd frontend
npm run build
```
This generates the optimized client assets in `frontend/dist/`.

### Step 4.3: Deploy to AWS Amplify (Option A - Recommended)
1. In the **AWS Console**, navigate to **AWS Amplify**.
2. Click **Deploy an app without Git provider** (Deploy static web app).
3. App name: `jt-demo-web`.
4. Environment name: `demo`.
5. Zip the contents of `frontend/dist/` and drag-and-drop the `.zip` file into Amplify.
6. Click **Save and deploy**. Your live URL (e.g., `https://main.xyz.amplifyapp.com`) will be active in seconds!

### Step 4.4: Deploy to S3 + CloudFront (Option B)
Alternatively, sync the build directly to an S3 website bucket:
```bash
aws s3 sync frontend/dist/ "s3://jt-demo-web-<account-id>/" --delete
```

---

## 5. Verify Deployed System

1. **API Gateway Health**:
   ```bash
   curl https://<your-api-id>.execute-api.ap-south-1.amazonaws.com/colonies
   ```
   Should return JSON list of monitored colonies.
2. **Frontend Live Console**:
   * Open your Amplify URL.
   * Verify the MapLibre basemap, Yamuna river corridor, and colony pins load.
   * Scrub the timeline slider across July 11–13, 2023.
   * Test switching to Hindi language (`हिंदी`).
   * Test dispatch generation and approving an evacuation alert.

---

## 6. Cost & Safety Guardrails
* **Serverless only**: No EC2 instances, No NAT Gateways, No SageMaker real-time endpoints.
* **DynamoDB**: Configured with `PAY_PER_REQUEST` (On-Demand) — $0 when idle.
* **Budget Alarm**: SAM deploys an automated CloudWatch budget alarm at **$10 USD** that emails your team if consumption exceeds the threshold.
