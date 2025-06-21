import boto3
import os
from dotenv import load_dotenv
from uuid import uuid4
load_dotenv()
BUCKET_NAME=os.getenv("S3_BUCKET_NAME")

if BUCKET_NAME is None:
    print("S3 Bucket name is not set in environment variables")

s3=boto3.client("s3")

def upload_file_to_s3(file_obj,content_type:str,chat_id:str)->str:
    file_extension=file_obj.filename.split(".")[-1]
    unique_filename = f"media/{chat_id}/{uuid4()}.{file_extension}"
    s3.upload_fileobj(
        Fileobj=file_obj.file,
        Bucket=BUCKET_NAME,
        Key=unique_filename,
        ExtraArgs={"ContentType": content_type}
    )
    file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"
    return file_url
