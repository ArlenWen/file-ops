from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import jwt
import time
from datetime import datetime, timedelta
from typing import Optional
import aiofiles
import json
from pathlib import Path
from config import get_config

# 获取配置实例
config = get_config()

app = FastAPI(title=config.get('ui.title', 'OnlyOffice Document Server Integration'))

# CORS middleware - 使用配置文件中的设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get('security.cors_origins', ["*"]),
    allow_credentials=config.get('security.cors_credentials', True),
    allow_methods=config.get('security.cors_methods', ["*"]),
    allow_headers=config.get('security.cors_headers', ["*"]),
)

# File storage configuration - 使用配置文件
UPLOAD_DIR = Path(config.upload_directory)
UPLOAD_DIR.mkdir(exist_ok=True)

# Static files for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

def generate_jwt_token(payload: dict) -> str:
    """Generate JWT token for OnlyOffice Document Server"""
    return jwt.encode(payload, config.onlyoffice_secret, algorithm="HS256")

def verify_jwt_token(token: str) -> dict:
    """Verify JWT token from OnlyOffice Document Server"""
    try:
        return jwt.decode(token, config.onlyoffice_secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/config")
async def get_client_config():
    """获取客户端配置"""
    return {
        "server": {
            "url": config.server_url
        },
        "onlyoffice": {
            "api_js_url": config.onlyoffice_api_js_url
        },
        "ui": {
            "title": config.get('ui.title', 'OnlyOffice Document Editor'),
            "subtitle": config.get('ui.subtitle', '在线文档编辑和协作平台'),
            "language": config.get('ui.language', 'zh-CN')
        },
        "storage": {
            "allowed_extensions": config.allowed_extensions,
            "max_file_size": config.get('storage.max_file_size', 104857600)
        }
    }

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main page"""
    async with aiofiles.open("static/index.html", 'r', encoding='utf-8') as f:
        content = await f.read()
    return HTMLResponse(content=content)

@app.get("/editor", response_class=HTMLResponse)
async def editor():
    """Serve the editor page"""
    async with aiofiles.open("static/editor.html", 'r', encoding='utf-8') as f:
        content = await f.read()
    return HTMLResponse(content=content)

@app.get("/preview", response_class=HTMLResponse)
async def preview():
    """Serve the preview page"""
    async with aiofiles.open("static/preview.html", 'r', encoding='utf-8') as f:
        content = await f.read()
    return HTMLResponse(content=content)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    stored_filename = f"{file_id}{file_extension}"
    file_path = UPLOAD_DIR / stored_filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Save file metadata
    metadata = {
        "id": file_id,
        "original_name": file.filename,
        "stored_name": stored_filename,
        "upload_time": datetime.now().isoformat(),
        "size": len(content)
    }
    
    metadata_path = UPLOAD_DIR / f"{file_id}.json"
    async with aiofiles.open(metadata_path, 'w') as f:
        await f.write(json.dumps(metadata, indent=2))
    
    return {"message": "File uploaded successfully", "file_id": file_id}

@app.get("/files")
async def list_files():
    """List all uploaded files"""
    files = []
    for metadata_file in UPLOAD_DIR.glob("*.json"):
        async with aiofiles.open(metadata_file, 'r') as f:
            content = await f.read()
            metadata = json.loads(content)
            files.append({
                "id": metadata["id"],
                "name": metadata["original_name"],
                "upload_time": metadata["upload_time"],
                "size": metadata["size"]
            })
    
    return sorted(files, key=lambda x: x["upload_time"], reverse=True)

@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """Download a file"""
    metadata_path = UPLOAD_DIR / f"{file_id}.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    async with aiofiles.open(metadata_path, 'r') as f:
        content = await f.read()
        metadata = json.loads(content)
    
    file_path = UPLOAD_DIR / metadata["stored_name"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=metadata["original_name"],
        media_type='application/octet-stream'
    )

@app.delete("/delete/{file_id}")
async def delete_file(file_id: str):
    """Delete a file and its metadata"""
    metadata_path = UPLOAD_DIR / f"{file_id}.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Load metadata to get the stored filename
    async with aiofiles.open(metadata_path, 'r') as f:
        content = await f.read()
        metadata = json.loads(content)

    file_path = UPLOAD_DIR / metadata["stored_name"]

    # Delete the actual file if it exists
    if file_path.exists():
        file_path.unlink()

    # Delete the metadata file
    metadata_path.unlink()

    return {"message": "File deleted successfully", "file_id": file_id}

@app.get("/editor-config/{file_id}")
async def get_editor_config(file_id: str):
    """Get OnlyOffice editor configuration for a file"""
    metadata_path = UPLOAD_DIR / f"{file_id}.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    async with aiofiles.open(metadata_path, 'r') as f:
        content = await f.read()
        metadata = json.loads(content)

    # Determine document type based on file extension
    file_extension = Path(metadata["original_name"]).suffix.lower()
    document_type = "word"  # default
    if file_extension in ['.xlsx', '.xls']:
        document_type = "cell"
    elif file_extension in ['.pptx', '.ppt']:
        document_type = "slide"

    # Generate unique key for editor to avoid caching issues
    import time
    unique_key = f"edit_{file_id}_{int(time.time())}"

    # OnlyOffice editor configuration
    editor_config = {
        "document": {
            "fileType": file_extension[1:],  # remove the dot
            "key": unique_key,
            "title": metadata["original_name"],
            "url": f"{config.server_url}/download/{file_id}"
        },
        "documentType": document_type,
        "editorConfig": {
            "callbackUrl": f"{config.server_url}/callback/{file_id}",
            "lang": config.get('ui.language', 'zh-CN'),  # 设置编辑器语言
            "user": {
                "id": config.get('editor.default_user_id', 'user1'),
                "name": config.get('editor.default_user_name', 'User')
            }
        },
        "width": "100%",
        "height": "600px"
    }

    # Generate JWT token if secret is configured and JWT is enabled
    if config.onlyoffice_secret and config.get('onlyoffice.jwt_enabled', True):
        # OnlyOffice expects the entire config as the payload
        token = generate_jwt_token(editor_config)
        editor_config["token"] = token

        # Also add debug info to help troubleshoot
        print(f"Generated JWT token for file {file_id}")
        print(f"Using secret: {config.onlyoffice_secret[:10]}...")
    else:
        print(f"JWT token not generated - secret: {bool(config.onlyoffice_secret)}, jwt_enabled: {config.get('onlyoffice.jwt_enabled', True)}")

    return editor_config

@app.get("/preview-config/{file_id}")
async def get_preview_config(file_id: str):
    """Get OnlyOffice preview configuration for a file (read-only mode)"""
    metadata_path = UPLOAD_DIR / f"{file_id}.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    async with aiofiles.open(metadata_path, 'r') as f:
        content = await f.read()
        metadata = json.loads(content)

    # Determine document type based on file extension
    file_extension = Path(metadata["original_name"]).suffix.lower()
    document_type = "word"  # default
    if file_extension in ['.xlsx', '.xls']:
        document_type = "cell"
    elif file_extension in ['.pptx', '.ppt']:
        document_type = "slide"

    # Generate unique key for preview to avoid caching issues
    import time
    unique_key = f"preview_{file_id}_{int(time.time())}"

    # OnlyOffice preview configuration (read-only mode)
    preview_config = {
        "document": {
            "fileType": file_extension[1:],  # remove the dot
            "key": unique_key,  # Unique key for each preview session
            "title": metadata["original_name"],
            "url": f"{config.server_url}/download/{file_id}"
        },
        "documentType": document_type,
        "editorConfig": {
            "mode": "view",  # Set to view mode for preview
            "lang": config.get('ui.language', 'zh-CN'),
            "user": {
                "id": config.get('editor.default_user_id', 'user1'),
                "name": config.get('editor.default_user_name', 'User')
            },
            "customization": {
                "autosave": False,
                "comments": False,
                "compactToolbar": True,
                "help": False,
                "hideRightMenu": True,
                "hideRulers": True,
                "integrationMode": "embed",
                "toolbarNoTabs": True,
                "zoom": 100,
                "goback": False,
                "chat": False,
                "plugins": False,
                "macros": False
            },
            "embedded": {
                "saveUrl": "",
                "embedUrl": "",
                "shareUrl": "",
                "toolbarDocked": "top"
            }
        },
        "width": "100%",
        "height": "600px"
    }

    # Generate JWT token if secret is configured and JWT is enabled
    if config.onlyoffice_secret and config.get('onlyoffice.jwt_enabled', True):
        # OnlyOffice expects the entire config as the payload
        token = generate_jwt_token(preview_config)
        preview_config["token"] = token

        # Also add debug info to help troubleshoot
        print(f"Generated JWT token for preview {file_id}")
        print(f"Using secret: {config.onlyoffice_secret[:10]}...")
    else:
        print(f"JWT token not generated for preview - secret: {bool(config.onlyoffice_secret)}, jwt_enabled: {config.get('onlyoffice.jwt_enabled', True)}")

    return preview_config

@app.post("/callback/{file_id}")
async def onlyoffice_callback(file_id: str, request_data: dict):
    """Handle OnlyOffice Document Server callback"""
    try:
        print(f"Received callback for file {file_id}: {request_data}")

        # Verify JWT token if present and JWT is enabled
        if config.get('onlyoffice.jwt_enabled', True) and "token" in request_data:
            try:
                verify_jwt_token(request_data["token"])
                print("JWT token verified successfully")
            except Exception as token_error:
                print(f"JWT token verification failed: {token_error}")
                return {"error": 1, "message": "Invalid token"}

        status = request_data.get("status", 0)
        print(f"Document status: {status}")

        # Status 2 means document is ready for saving
        # Status 6 means document is being edited
        if status == 2:
            download_url = request_data.get("url")
            if download_url:
                print(f"Downloading updated document from: {download_url}")
                # Download the updated document
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(download_url)
                    if response.status_code == 200:
                        # Save the updated file
                        metadata_path = UPLOAD_DIR / f"{file_id}.json"
                        if metadata_path.exists():
                            async with aiofiles.open(metadata_path, 'r') as f:
                                content = await f.read()
                                metadata = json.loads(content)

                            file_path = UPLOAD_DIR / metadata["stored_name"]
                            async with aiofiles.open(file_path, 'wb') as f:
                                await f.write(response.content)

                            # Update metadata with last modified time
                            metadata["last_modified"] = datetime.now().isoformat()
                            async with aiofiles.open(metadata_path, 'w') as f:
                                await f.write(json.dumps(metadata, indent=2))

                            print(f"Document saved successfully: {file_path}")
                    else:
                        print(f"Failed to download document: {response.status_code}")

        return {"error": 0}

    except Exception as e:
        print(f"Callback error: {e}")
        return {"error": 1, "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.server_port)
