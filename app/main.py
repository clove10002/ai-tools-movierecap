import os
import oci
import shutil
import requests

from fastapi import FastAPI, Query
from utils import download_and_convert
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

class DeletePayload(BaseModel):
    bucket_name: str
    object_name: str
    namespace: str = None  # Optional: Will auto-detect if not provided

if os.path.isdir("/tmp"):
    app.mount("/videos", StaticFiles(directory="/tmp"), name="videos")

def get_tmp_directory_size():
    total_size = 0
    for dirpath, dirnames, filenames in os.walk("/tmp"):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
    return total_size


@app.get("/download")
def download_video(torrent_url: str = Query(..., description="Magnet or .torrent link")):
    output_path = download_and_convert(torrent_url)
    return {"status": "success", "saved_path": output_path}

#upload to oracle bucket
@app.post("/upload-mp4")
def upload_to_oracle(payload: dict):
    """
    JSON Body Example:
    {
        "file_name": "1f16ddfc-1df0-40e1-8bc3-078bad7cafc8/movie.mp4",
        "par_url": "https://objectstorage.ap-singapore-1.oraclecloud.com/p/<token>/n/<namespace>/b/<bucket>/o/.../movie.mp4"
    }
    """    
    file_name = payload.get("file_name")
    par_url = payload.get("par_url")

    if not file_name or not par_url:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "detail": "file_name and par_url are required in the request body"}
        )

    # Build the absolute file path safely (supports nested folders)
    file_path = os.path.join("/tmp", *file_name.split("/"))

    if not os.path.isfile(file_path):
        return JSONResponse(
            status_code=404,
            content={"status": "error", "detail": f"{file_name} not found in /tmp"}
        )

    try:
        # Stream upload to avoid high memory usage
        with open(file_path, "rb") as f:
            headers = {"Content-Type": "video/mp4"}
            response = requests.put(par_url, data=f, headers=headers, stream=True)
            response.raise_for_status()

        return {"status": "success", "oracle_url": par_url}

    except requests.HTTPError as e:
        return JSONResponse(
            status_code=response.status_code,
            content={"status": "error", "detail": str(e), "response_text": response.text}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)}
        )
        
@app.post("/upload-srt")
def upload_to_oracle(payload: dict):
    """
    JSON Body Example:
    {
        "file_name": "1f16ddfc-1df0-40e1-8bc3-078bad7cafc8/movie.srt",
        "par_url": "https://objectstorage.ap-singapore-1.oraclecloud.com/p/<token>/n/<namespace>/b/<bucket>/o/.../movie.srt"
    }
    """     
    file_name = payload.get("file_name")
    par_url = payload.get("par_url")

    if not file_name or not par_url:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "detail": "file_name and par_url are required in the request body"}
        )

    # Build the absolute file path safely (supports nested folders)
    file_path = os.path.join("/tmp", *file_name.split("/"))

    if not os.path.isfile(file_path):
        return JSONResponse(
            status_code=404,
            content={"status": "error", "detail": f"{file_name} not found in /tmp"}
        )

    try:
        # Stream upload to avoid high memory usage
        with open(file_path, "rb") as f:
            headers = {"Content-Type": "text/plain"}
            response = requests.put(par_url, data=f, headers=headers, stream=True)
            response.raise_for_status()

        return {"status": "success", "oracle_url": par_url}

    except requests.HTTPError as e:
        return JSONResponse(
            status_code=response.status_code,
            content={"status": "error", "detail": str(e), "response_text": response.text}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)}
        )        

@app.post("/delete-file")
def delete_from_oracle(payload: DeletePayload):
    try:
        # Load OCI config from ~/.oci/config
        config = oci.config.from_file(os.path.expanduser("~/.oci/config"))

        object_storage = oci.object_storage.ObjectStorageClient(config)

        # Get namespace if not provided
        namespace = payload.namespace
        if not namespace:
            namespace = object_storage.get_namespace().data

        # Perform delete
        object_storage.delete_object(
            namespace_name=namespace,
            bucket_name=payload.bucket_name,
            object_name=payload.object_name
        )

        return {"status": "success", "message": f"{payload.object_name} deleted from {payload.bucket_name}"}

    except oci.exceptions.ServiceError as e:
        return JSONResponse(
            status_code=e.status,
            content={"status": "error", "detail": "Failed to delete file", "response_text": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)}
        )


@app.delete("/flash")
def delete_tmp_files():
    tmp_path = "/tmp"
    deleted = []

    try:
        for filename in os.listdir(tmp_path):
            file_path = os.path.join(tmp_path, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
                deleted.append(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                deleted.append(file_path)
        return {"status": "success", "deleted": deleted}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/list")
def list_videos():
    mp4_files = []

    for root, _, files in os.walk("/tmp"):
        for file in files:
            if file.endswith(".mp4"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, "/tmp")
                mp4_files.append(rel_path)
    return JSONResponse(content={"videos": mp4_files})


@app.get("/tmp-size")
def tmp_size():
    size_bytes = get_tmp_directory_size()
    size_mb = size_bytes / (1024 * 1024)
    return {"size_bytes": size_bytes, "size_mb": round(size_mb, 2)}

