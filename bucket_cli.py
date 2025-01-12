#!/usr/bin/env python
"""
bucket_cli.py

A simple CLI tool to upload, delete, restore, and view files in an S3 bucket,
with support for a .bucketignore file (to skip uploading certain files).
"""

import os
import sys
import argparse
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
    upload_parser.add_argument("target", help="File name or '.' for all files in the current directory")
    
    # 'delete' command
    delete_parser = subparsers.add_parser("delete", help="Delete a file in the bucket")
    delete_parser.add_argument("target", help="File name or '.' for all files in the bucket")
    
    # 'restore' command
    restore_parser = subparsers.add_parser("restore", help="Download a file from the bucket")
    restore_parser.add_argument("target", help="File name or '.' for all files in the bucket")
    
    # 'view' command
    subparsers.add_parser("view", help="View contents of the bucket")

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

def upload_files(s3_client, bucket_name, target):
    """
    Uploads a file (or all files in the current directory if target='.')
    to the specified S3 bucket, skipping those matched in .bucketignore.
    """
    ignore_patterns = get_ignored_patterns()

    if target == ".":
        # Upload all files in the current directory
        for file_name in os.listdir("."):
            if os.path.isfile(file_name):
                # Skip if file matches any pattern in .bucketignore
                if should_ignore_file(file_name, ignore_patterns):
                    print(f"Skipping {file_name} (ignored by .bucketignore)")
                    continue
                # Proceed with upload
                try:
                    print(f"Uploading {file_name}...")
                    s3_client.upload_file(file_name, bucket_name, file_name)
                except ClientError as e:
                    print(f"Error uploading {file_name}: {e}")
    else:
        # Upload single file
        if not os.path.isfile(target):
            print(f"File '{target}' not found on local machine.")
            return
        if should_ignore_file(target, ignore_patterns):
            print(f"Skipping {target} (ignored by .bucketignore)")
            return
        try:
            print(f"Uploading {target}...")
            s3_client.upload_file(target, bucket_name, target)
        except ClientError as e:
            print(f"Error uploading {target}: {e}")

def delete_files(s3_client, bucket_name, target):
    """
    Deletes a file (or all files if target='.') from the specified S3 bucket.
    """
    if target == ".":
        # Delete all files in the bucket
        try:
            objects_to_delete = s3_client.list_objects_v2(Bucket=bucket_name)
            if "Contents" in objects_to_delete:
                for obj in objects_to_delete["Contents"]:
                    key = obj["Key"]
                    print(f"Deleting {key}...")
                    s3_client.delete_object(Bucket=bucket_name, Key=key)
            else:
                print("Bucket is already empty.")
        except ClientError as e:
            print(f"Error listing/deleting files: {e}")
    else:
        # Delete a single file
        try:
            print(f"Deleting {target}...")
            s3_client.delete_object(Bucket=bucket_name, Key=target)
        except ClientError as e:
            print(f"Error deleting {target}: {e}")

def restore_files(s3_client, bucket_name, target):
    """
    Downloads a file (or all files in the bucket if target='.') to the local machine.
    """
    if target == ".":
        # Download all files from the bucket
        try:
            objects_to_download = s3_client.list_objects_v2(Bucket=bucket_name)
            if "Contents" in objects_to_download:
                for obj in objects_to_download["Contents"]:
                    key = obj["Key"]
                    print(f"Downloading {key}...")
                    s3_client.download_file(bucket_name, key, key)
            else:
                print("Bucket is empty. Nothing to download.")
        except ClientError as e:
            print(f"Error listing/downloading files: {e}")
    else:
        # Download a single file
        try:
            print(f"Downloading {target}...")
            s3_client.download_file(bucket_name, target, target)
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
    if not bucket_name:
        print("Error: Please set S3_BUCKET_NAME in your .env file.")
        sys.exit(1)

    command = args.command

    if command == "upload":
        upload_files(s3_client, bucket_name, args.target)
    elif command == "delete":
        delete_files(s3_client, bucket_name, args.target)
    elif command == "restore":
        restore_files(s3_client, bucket_name, args.target)
    elif command == "view":
        view_bucket(s3_client, bucket_name)
    else:
        print("No valid command was provided. Use '--help' for usage information.")

if __name__ == "__main__":
    main()
