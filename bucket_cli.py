#!/usr/bin/env python
"""
bucket_cli.py

A simple CLI tool to upload, delete, restore, and view files in an S3 bucket,
using .bucketignore and a local folder set in .env (LOCAL_BUCKET_PATH).
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
    upload_parser.add_argument("target", help="File name relative to the local bucket folder or '.' for all files in that folder")
    
    # 'delete' command
    delete_parser = subparsers.add_parser("delete", help="Delete a file in the bucket (does NOT delete locally)")
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

def upload_files(s3_client, bucket_name, target):
    """
    Uploads a file (or all files) from the local 'bucket' folder to the specified S3 bucket,
    respecting .bucketignore patterns.
    """
    local_bucket_path = get_local_bucket_path()
    ignore_patterns = get_ignored_patterns()

    if target == ".":
        # Upload all files (recursively) from the local_bucket_path
        for root, dirs, files in os.walk(local_bucket_path):
            for file_name in files:
                local_path = os.path.join(root, file_name)
                # Derive the S3 key as the relative path from local_bucket_path
                s3_key = os.path.relpath(local_path, local_bucket_path)

                # Check against .bucketignore
                # We'll check only the filename and/or partial path
                # For best results, we can check the entire s3_key
                if should_ignore_file(s3_key, ignore_patterns):
                    print(f"Skipping {s3_key} (ignored by .bucketignore)")
                    continue

                try:
                    print(f"Uploading {s3_key}...")
                    s3_client.upload_file(local_path, bucket_name, s3_key)
                except ClientError as e:
                    print(f"Error uploading {s3_key}: {e}")
    else:
        # Upload a single file from the local bucket folder
        local_path = os.path.join(local_bucket_path, target)
        if not os.path.isfile(local_path):
            print(f"File '{local_path}' not found in local bucket folder.")
            return

        # Check against .bucketignore
        if should_ignore_file(target, ignore_patterns):
            print(f"Skipping {target} (ignored by .bucketignore)")
            return

        try:
            print(f"Uploading {target}...")
            s3_client.upload_file(local_path, bucket_name, target)
        except ClientError as e:
            print(f"Error uploading {target}: {e}")

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
                    key = obj["Key"]  # e.g., 'images/alexandria-logo.svg'
                    # Local path = local_bucket_path + relative subfolders
                    local_path = os.path.join(local_bucket_path, key)

                    # Ensure local subdirectories exist
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
        # Download a single file
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
