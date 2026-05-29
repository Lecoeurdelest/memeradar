import sys, json
sys.path.insert(0, ".")
from backend.storage import _get_client
from backend import config

client = _get_client()

client.put_public_access_block(
    Bucket=config.S3_BUCKET_NAME,
    PublicAccessBlockConfiguration={
        "BlockPublicAcls": False,
        "IgnorePublicAcls": False,
        "BlockPublicPolicy": False,
        "RestrictPublicBuckets": False,
    }
)
print("block public access disabled")

policy = json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "PublicRead",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": [
            f"arn:aws:s3:::{config.S3_BUCKET_NAME}/memes/*",
            f"arn:aws:s3:::{config.S3_BUCKET_NAME}/uploads/*",
        ]
    }]
})
client.put_bucket_policy(Bucket=config.S3_BUCKET_NAME, Policy=policy)
print("public-read policy applied")
