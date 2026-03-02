"""
Storage Service - S3-compatible File Storage Platform
Supports file upload, download, CDN integration, and image processing
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import boto3
from botocore.config import Config
import os
import hashlib
import redis
import json
from PIL import Image
import io

# S3 Client
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv('S3_ENDPOINT_URL', 'http://minio:9000'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin'),
    config=Config(
        signature_version='s3v4',
        retries={'max_attempts': 3}
    )
)

# Redis for caching
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=3,
    decode_responses=True
)

app = FastAPI(
    title="Rizz Storage Service",
    description="S3-compatible File Storage Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'rizz-storage')


# ===== Models =====

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int
    content_type: str
    url: str
    cdn_url: Optional[str] = None
    uploaded_at: str


class FileMetadata(BaseModel):
    file_id: str
    filename: str
    size: int
    content_type: str
    owner: str
    uploaded_at: str
    downloads: int
    is_public: bool


class GeneratePresignedUrlResponse(BaseModel):
    url: str
    expires_at: str
    file_id: str


# ===== Helper Functions =====

def generate_file_id(file_content: bytes) -> str:
    """Generate unique file ID based on content hash"""
    return hashlib.sha256(file_content).hexdigest()[:32]


def get_file_path(file_id: str) -> str:
    """Generate S3 path from file ID"""
    return f"files/{file_id[:2]}/{file_id[2:4]}/{file_id}"


# ===== API Endpoints =====

@app.get('/health')
async def health_check():
    """Health check"""
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        return {
            'status': 'healthy',
            'service': 'storage',
            's3': 'connected',
            'bucket': BUCKET_NAME,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            'status': 'degraded',
            'service': 'storage',
            's3': 'disconnected',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@app.post('/api/storage/upload', response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    is_public: bool = Query(default=False),
    x_owner: Optional[str] = Header(None)
):
    """Upload a file"""
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size (max 100MB)
        if file_size > 100 * 1024 * 1024:
            raise HTTPException(status_code=400, detail='File too large (max 100MB)')
        
        # Generate file ID
        file_id = generate_file_id(content)
        file_path = get_file_path(file_id)
        
        # Set ACL
        acl = 'public-read' if is_public else 'private'
        
        # Upload to S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=file_path,
            Body=content,
            ContentType=file.content_type,
            ACL=acl,
            Metadata={
                'original_filename': file.filename,
                'owner': x_owner or 'anonymous',
                'uploaded_at': datetime.utcnow().isoformat()
            }
        )
        
        # Generate URLs
        file_url = f"/api/storage/download/{file_id}"
        cdn_url = None
        if is_public:
            cdn_url = f"{os.getenv('CDN_URL', '')}/{file_path}"
        
        # Cache metadata in Redis
        metadata = {
            'file_id': file_id,
            'filename': file.filename,
            'size': file_size,
            'content_type': file.content_type,
            'owner': x_owner or 'anonymous',
            'uploaded_at': datetime.utcnow().isoformat(),
            'downloads': 0,
            'is_public': is_public
        }
        redis_client.setex(f'file:{file_id}', 86400 * 7, json.dumps(metadata))
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            size=file_size,
            content_type=file.content_type,
            url=file_url,
            cdn_url=cdn_url,
            uploaded_at=datetime.utcnow().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/storage/download/{file_id}')
async def download_file(file_id: str):
    """Download a file"""
    try:
        # Get metadata from cache
        metadata_json = redis_client.get(f'file:{file_id}')
        if metadata_json:
            metadata = json.loads(metadata_json)
            # Increment download count
            metadata['downloads'] = metadata.get('downloads', 0) + 1
            redis_client.setex(f'file:{file_id}', 86400 * 7, json.dumps(metadata))
        
        # Get file from S3
        file_path = get_file_path(file_id)
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=file_path)
        
        return StreamingResponse(
            response['Body'],
            media_type=response['ContentType'],
            headers={
                'Content-Disposition': f'attachment; filename="{metadata.get("filename", file_id)}"'
            } if metadata else {}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail='File not found')


@app.get('/api/storage/file/{file_id}')
async def get_file_info(file_id: str):
    """Get file metadata"""
    try:
        # Try cache first
        metadata_json = redis_client.get(f'file:{file_id}')
        if metadata_json:
            return json.loads(metadata_json)
        
        # Get from S3
        file_path = get_file_path(file_id)
        response = s3_client.head_object(Bucket=BUCKET_NAME, Key=file_path)
        
        metadata = {
            'file_id': file_id,
            'filename': response['Metadata'].get('original_filename', 'unknown'),
            'size': response['ContentLength'],
            'content_type': response['ContentType'],
            'owner': response['Metadata'].get('owner', 'unknown'),
            'uploaded_at': response['Metadata'].get('uploaded_at'),
            'downloads': 0,
            'is_public': response.get('ACL', {}).get('Grantees', []) != []
        }
        
        # Cache for 7 days
        redis_client.setex(f'file:{file_id}', 86400 * 7, json.dumps(metadata))
        
        return metadata
    except Exception as e:
        raise HTTPException(status_code=404, detail='File not found')


@app.delete('/api/storage/file/{file_id}')
async def delete_file(file_id: str, x_owner: Optional[str] = Header(None)):
    """Delete a file"""
    try:
        # Get metadata to check ownership
        metadata_json = redis_client.get(f'file:{file_id}')
        if metadata_json:
            metadata = json.loads(metadata_json)
            if x_owner and metadata.get('owner') != x_owner:
                raise HTTPException(status_code=403, detail='Not authorized')
        
        # Delete from S3
        file_path = get_file_path(file_id)
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=file_path)
        
        # Remove from cache
        redis_client.delete(f'file:{file_id}')
        
        return {'status': 'deleted', 'file_id': file_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/storage/presigned-url', response_model=GeneratePresignedUrlResponse)
async def generate_presigned_url(
    file_id: str,
    expiration: int = Query(default=3600, ge=60, le=604800)
):
    """Generate presigned URL for temporary access"""
    try:
        file_path = get_file_path(file_id)
        
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': file_path},
            ExpiresIn=expiration
        )
        
        return GeneratePresignedUrlResponse(
            url=url,
            expires_at=datetime.utcnow() + timedelta(seconds=expiration),
            file_id=file_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/storage/image/{file_id}/resize')
async def resize_image(
    file_id: str,
    width: int = Query(..., ge=1, le=4096),
    height: int = Query(..., ge=1, le=4096),
    quality: int = Query(default=85, ge=1, le=100)
):
    """Resize an image and return new file"""
    try:
        # Get original file
        file_path = get_file_path(file_id)
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=file_path)
        
        # Open and resize image
        image = Image.open(io.BytesIO(response['Body'].read()))
        image = image.resize((width, height), Image.Resampling.LANCZOS)
        
        # Save to buffer
        output = io.BytesIO()
        image.save(output, format=image.format, quality=quality)
        output.seek(0)
        
        # Generate new file ID
        content = output.getvalue()
        new_file_id = generate_file_id(content)
        new_file_path = get_file_path(new_file_id)
        
        # Upload resized image
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=new_file_path,
            Body=content,
            ContentType=response['ContentType'],
            ACL='private',
            Metadata={
                'original_file_id': file_id,
                'resized': 'true',
                'dimensions': f'{width}x{height}',
                'uploaded_at': datetime.utcnow().isoformat()
            }
        )
        
        return {
            'file_id': new_file_id,
            'original_file_id': file_id,
            'dimensions': f'{width}x{height}',
            'size': len(content),
            'url': f'/api/storage/download/{new_file_id}'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/storage/stats')
async def get_storage_stats():
    """Get storage statistics"""
    try:
        # Get bucket stats
        paginator = s3_client.get_paginator('list_objects_v2')
        
        total_size = 0
        total_files = 0
        
        for page in paginator.paginate(Bucket=BUCKET_NAME):
            if 'Contents' in page:
                total_files += len(page['Contents'])
                total_size += sum(obj['Size'] for obj in page['Contents'])
        
        return {
            'statistics': {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_gb': round(total_size / (1024**3), 2),
                'bucket': BUCKET_NAME
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/storage/files')
async def list_files(
    prefix: str = Query(default=''),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """List files with optional prefix filter"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix,
            MaxKeys=limit
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
        
        return {
            'files': files,
            'count': len(files),
            'prefix': prefix
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8004)
