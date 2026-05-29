from __future__ import annotations

import asyncio
import io

import boto3
from botocore.exceptions import ClientError

from backend import config


_s3_client = None


def _get_client():
    global _s3_client
    if _s3_client is None:
        kwargs = dict(
            region_name=config.S3_REGION,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
        )
        if config.S3_ENDPOINT:
            kwargs["endpoint_url"] = config.S3_ENDPOINT
        _s3_client = boto3.client("s3", **kwargs)
    return _s3_client


def s3_public_url(key: str) -> str:
    return f"https://{config.S3_BUCKET_NAME}.s3.{config.S3_REGION}.amazonaws.com/{key}"


def _sync_upload(key: str, data: bytes, content_type: str) -> str:
    client = _get_client()
    client.put_object(
        Bucket=config.S3_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return s3_public_url(key)


def _sync_exists(key: str) -> bool:
    client = _get_client()
    try:
        client.head_object(Bucket=config.S3_BUCKET_NAME, Key=key)
        return True
    except ClientError:
        return False


def _sync_download(key: str) -> bytes:
    client = _get_client()
    resp = client.get_object(Bucket=config.S3_BUCKET_NAME, Key=key)
    return resp["Body"].read()


async def s3_upload(key: str, data: bytes, content_type: str) -> str:
    return await asyncio.to_thread(_sync_upload, key, data, content_type)


async def s3_exists(key: str) -> bool:
    return await asyncio.to_thread(_sync_exists, key)


async def s3_download(key: str) -> bytes:
    return await asyncio.to_thread(_sync_download, key)

