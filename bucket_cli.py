#!/usr/bin/env python
"""
bucket_cli.py

A simple CLI tool to upload, delete, restore, and view files in an S3 bucket,
with .bucketignore support, an invalidate command for CloudFront,
and automatic Content-Type detection via mimetypes.
"""

import os
import sys
import argparse
import time
import mimetypes
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
import fnmatch

def parse_arguments():
    """
    Parses command-line arguments and returns them.
    """
    parser = argparse.ArgumentParser(
        description="A CLI for interacting with an S3 bucket"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # 'upload' command
    upload_parser = subparsers.add_parser("upload", help="Upload or update a file in the bucket")
    upload_parser.add_argument("target", help="File name relative to the local bucket folder or '.' for all files in that folder")
    
    # 'delete' command
    delete_parser = subparsers.add_parser("delete", help="Delete a file in the bucket (does NOT delete locally)")
    delete_parser.add_argument("target", help="File name or '.' for all files in the bucket")
    
    # 'restore' command
    restore_parser = subparsers.add_parser("restore", help="Download a file from the bucket")
    restore_parser.add_argument("target", help="File name or '.' for all files in the bucket")
    
    # 'view' command
    subparsers.add_parser("view", help="View contents of the bucket")

    # 'invalidate' command (CloudFront)
    invalidate_parser = subparsers.add_parser("invalidate", help="Invalidate files in the CloudFront distribution")
    invalidate_parser.add_argument(
        "target",
        help="Path or '.' for all files, e.g. /images/*, /index.html, or . for everything"
    )

    return parser.parse_args()

def get_s3_client():
    """
    Creates and returns an S3 client using credentials from the .env file.
    """
    load_dotenv()  # Load environment variables from .env

    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION") or "us-east-1"

    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
    return s3

def invalidate_cloudfront(distribution_id, paths):
    """
    Creates a CloudFront invalidation for the given distribution_id and list of paths.
    'paths' should be a list of strings (e.g., ['/index.html', '/images/*']).
    """
    if not distribution_id:
        print("No CloudFront Distribution ID provided, skipping invalidation.")
        return

    cf_client = boto3.client("cloudfront")

    caller_reference = str(time.time())  # unique string for each invalidation

    try:
        print(f"Creating CloudFront invalidation for paths: {paths}")
        response = cf_client.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                "Paths": {
                    "Quantity": len(paths),
                    "Items": paths
                },
                "CallerReference": caller_reference
            }
        )
        inv_id = response["Invalidation"]["Id"]
        print(f"CloudFront Invalidation created: {inv_id}")
    except ClientError as e:
        print(f"Error creating CloudFront invalidation: {e}")

def get_local_bucket_path():
    """
    Returns the local folder path from which files should be uploaded and into which files should be restored.
    Defaults to 'bucket' if LOCAL_BUCKET_PATH is not defined.
    """
    local_path = os.getenv("LOCAL_BUCKET_PATH", "bucket")
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    return local_path

def get_ignored_patterns():
    """
    Reads patterns from a .bucketignore file in the current directory, if it exists,
    and returns them as a list of strings. Lines starting with '#' are considered comments.
    """
    ignore_file = ".bucketignore"
    patterns = []
    
    if os.path.isfile(ignore_file):
        with open(ignore_file, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
    return patterns

def should_ignore_file(filename, ignore_patterns):
    """
    Checks whether `filename` matches any pattern in `ignore_patterns`.
    If yes, returns True (meaning we should ignore the file).
    """
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False

def guess_content_type(file_path):
    """
    Uses the 'mimetypes' library to guess the content type of a file.
    Returns 'application/octet-stream' if it cannot determine the type.
    """
    content_type, _ = mimetypes.guess_type(file_path)
    return content_type or "application/octet-stream"

def to_s3_key(local_path, local_bucket_path):
    """
    Derive the S3 key as the relative path from local_bucket_path,
    then replace backslashes with forward slashes to ensure
    proper directory structure in S3.
    """
    # e.g., relative path might be "images\logo.png" on Windows
    rel_path = os.path.relpath(local_path, local_bucket_path)

    # Convert backslashes to forward slashes
    s3_key = rel_path.replace("\\", "/")
    return s3_key


def upload_single_file(s3_client, local_path, bucket_name, s3_key):
    """
    Upload a single file with Content-Type guessed via mimetypes.
    """
    content_type = guess_content_type(local_path)
    try:
        s3_client.upload_file(
            Filename=local_path,
            Bucket=bucket_name,
            Key=s3_key,
            ExtraArgs={"ContentType": content_type}
        )
        print(f"Uploaded {s3_key} (Content-Type: {content_type})")
    except ClientError as e:
        print(f"Error uploading {s3_key}: {e}")

def upload_files(s3_client, bucket_name, target):
    """
    Uploads a file (or all files) from the local 'bucket' folder to the specified S3 bucket,
    respecting .bucketignore patterns and using guessed Content-Type.
    """
    local_bucket_path = get_local_bucket_path()
    ignore_patterns = get_ignored_patterns()

    if target == ".":
        # Upload all files (recursively) from the local_bucket_path
        for root, dirs, files in os.walk(local_bucket_path):
            for file_name in files:
                local_path = os.path.join(root, file_name)
                # Derive the S3 key as the relative path from local_bucket_path
                s3_key = to_s3_key(local_path, local_bucket_path)

                if should_ignore_file(s3_key, ignore_patterns):
                    print(f"Skipping {s3_key} (ignored by .bucketignore)")
                    continue

                upload_single_file(s3_client, local_path, bucket_name, s3_key)
    else:
        # Upload a single file from the local bucket folder
        local_path = os.path.join(local_bucket_path, target)
        if not os.path.isfile(local_path):
            print(f"File '{local_path}' not found in local bucket folder.")
            return

        if should_ignore_file(target, ignore_patterns):
            print(f"Skipping {target} (ignored by .bucketignore)")
            return
        
        s3_key = to_s3_key(local_path, local_bucket_path)

        upload_single_file(s3_client, local_path, bucket_name, s3_key)

def delete_files(s3_client, bucket_name, target):
    """
    Deletes a file (or all files if target='.') from the specified S3 bucket.
    This does NOT remove files locally.
    """
    if target == ".":
        # Delete all files in the bucket
        try:
            objects_to_delete = s3_client.list_objects_v2(Bucket=bucket_name)
            if "Contents" in objects_to_delete:
                for obj in objects_to_delete["Contents"]:
                    key = obj["Key"]
                    print(f"Deleting {key} in bucket...")
                    s3_client.delete_object(Bucket=bucket_name, Key=key)
            else:
                print("Bucket is already empty.")
        except ClientError as e:
            print(f"Error listing/deleting files: {e}")
    else:
        # Delete a single file
        try:
            print(f"Deleting {target} in bucket...")
            s3_client.delete_object(Bucket=bucket_name, Key=target)
        except ClientError as e:
            print(f"Error deleting {target}: {e}")

def restore_files(s3_client, bucket_name, target):
    """
    Downloads a file (or all files) from the bucket into the local 'bucket' folder,
    creating subdirectories as necessary.
    """
    local_bucket_path = get_local_bucket_path()

    if target == ".":
        # Download all files from the bucket
        try:
            objects_to_download = s3_client.list_objects_v2(Bucket=bucket_name)
            if "Contents" in objects_to_download:
                for obj in objects_to_download["Contents"]:
                    key = obj["Key"]
                    local_path = os.path.join(local_bucket_path, key)
                    local_dir = os.path.dirname(local_path)
                    if local_dir and not os.path.exists(local_dir):
                        os.makedirs(local_dir)

                    print(f"Downloading {key} to {local_path}...")
                    s3_client.download_file(bucket_name, key, local_path)
            else:
                print("Bucket is empty. Nothing to download.")
        except ClientError as e:
            print(f"Error listing/downloading files: {e}")
    else:
        key = target
        local_path = os.path.join(local_bucket_path, key)
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir)

        try:
            print(f"Downloading {key} to {local_path}...")
            s3_client.download_file(bucket_name, key, local_path)
        except ClientError as e:
            print(f"Error downloading {target}: {e}")

def view_bucket(s3_client, bucket_name):
    """
    Prints the list of objects in the specified S3 bucket.
    """
    try:
        objects = s3_client.list_objects_v2(Bucket=bucket_name)
        if "Contents" in objects:
            print(f"Files in bucket '{bucket_name}':")
            for obj in objects["Contents"]:
                print(obj["Key"])
        else:
            print(f"Bucket '{bucket_name}' is empty.")
    except ClientError as e:
        print(f"Error viewing bucket: {e}")

def main():
    args = parse_arguments()
    s3_client = get_s3_client()
    
    # Retrieve your bucket name from the .env
    bucket_name = os.getenv("S3_BUCKET_NAME")
    command = args.command

    if command == "upload":
        if not bucket_name:
            print("Error: Please set S3_BUCKET_NAME in your .env file.")
            sys.exit(1)
        upload_files(s3_client, bucket_name, args.target)

    elif command == "delete":
        if not bucket_name:
            print("Error: Please set S3_BUCKET_NAME in your .env file.")
            sys.exit(1)
        delete_files(s3_client, bucket_name, args.target)

    elif command == "restore":
        if not bucket_name:
            print("Error: Please set S3_BUCKET_NAME in your .env file.")
            sys.exit(1)
        restore_files(s3_client, bucket_name, args.target)

    elif command == "view":
        if not bucket_name:
            print("Error: Please set S3_BUCKET_NAME in your .env file.")
            sys.exit(1)
        view_bucket(s3_client, bucket_name)

    elif command == "invalidate":
        # Invalidate command doesn't need S3 bucket name
        distribution_id = os.getenv("CLOUDFRONT_DISTRIBUTION_ID")
        target = args.target
        if target == ".":
            # Invalidate everything
            invalidate_cloudfront(distribution_id, ["/*"])
        else:
            # Ensure path starts with "/"
            if not target.startswith("/"):
                target = "/" + target
            invalidate_cloudfront(distribution_id, [target])

    else:
        print("No valid command was provided. Use '--help' for usage information.")

if __name__ == "__main__":
    main()
