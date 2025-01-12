# S3 Bucket CLI

A simple Python CLI tool to upload, delete, restore, and view files in an S3 bucket.

## 1. Prerequisites

1. **Python** (3.8+ recommended)
2. **pip** (for installing Python packages)
3. **AWS Account** with permissions to access the S3 bucket (see [AWS documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html) for setting up IAM users, access keys, etc.)
4. **(Optional)** [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) - not strictly required, but helpful for verification.

## 2. AWS Setup

- Log in to your AWS Console.
- Go to [IAM (Identity and Access Management)](https://console.aws.amazon.com/iam/home?region=us-east-1#/home).
- Create (or use) a user with the **`AmazonS3FullAccess`** policy (or a custom policy that at least allows reading/writing to the S3 bucket in question).
- Generate **Access Key ID** and **Secret Access Key** for this user.

## 3. Create an S3 Bucket

- In the AWS console, navigate to **S3**.
- Click "Create bucket" and follow the prompts to set the name, region, etc.
- Copy the bucket name for use in the `.env` file.

## 4. Local Environment Setup

1. **Clone** or **download** this repository.
2. **Create** a `.env` file in the project root with the following format:

    ```text
    AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
    AWS_REGION=us-east-1
    S3_BUCKET_NAME=your-bucket-name
    ```

   Replace with your actual credentials and bucket name. Keep the `.env` file **secret**.

3. **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

## 5. Usage

From the command line in the same directory as `bucket_cli.py`, you can run:

- **Upload a single file**:
  ```bash
  python bucket_cli.py upload index.html
