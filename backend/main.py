"""Video Downloader API — FastAPI backend with yt-dlp."""

import asyncio
import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from security import validate_url, verify_api_key
from extractor import extract_video_info, cache

app = FastAPI(title="Video Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY environment variable is required")


def require_auth(x_api_key: str = Header(None)):
    """Verify API key from request header."""
    if not x_api_key or not verify_api_key(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")


class ExtractRequest(BaseModel):
    url: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract(req: ExtractRequest, x_api_key: str = Header(None)):
    require_auth(x_api_key)
    if not validate_url(req.url):
        raise HTTPException(status_code=400, detail="URL not supported")

    # Run blocking yt-dlp in thread to avoid blocking event loop
    result = await asyncio.to_thread(extract_video_info, req.url)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    # Remove direct URLs from response (keep server-side only)
    safe_formats = []
    for f in result.get("formats", []):
        safe_formats.append({
            "format_id": f["format_id"],
            "quality": f["quality"],
            "ext": f["ext"],
            "filesize": f.get("filesize"),
            "height": f.get("height"),
        })
    return {
        "id": result["id"],
        "title": result["title"],
        "thumbnail": result["thumbnail"],
        "duration": result["duration"],
        "formats": safe_formats,
    }


@app.get("/download/{extraction_id}")
async def download(extraction_id: str, format: str, x_api_key: str = Header(None)):
    require_auth(x_api_key)
    data = cache.get(extraction_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Extraction expired or not found")

    # Find the requested format
    target = None
    for f in data.get("formats", []):
        if f["format_id"] == format or str(f.get("quality")) == format:
            target = f
            break
    if target is None:
        raise HTTPException(status_code=400, detail="Format not found")

    video_url = target.get("url")
    if not video_url:
        raise HTTPException(status_code=500, detail="No download URL available")

    # Stream via yt-dlp subprocess (async, non-blocking)
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", "-f", target["format_id"], "-o", "-", data["original_url"],
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    async def stream():
        while True:
            chunk = await proc.stdout.read(64 * 1024)
            if not chunk:
                break
            yield chunk
        await proc.wait()

    headers = {"Content-Type": "video/mp4"}
    if target.get("filesize"):
        headers["Content-Length"] = str(target["filesize"])

    return StreamingResponse(stream(), headers=headers, media_type="video/mp4")


if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    load_dotenv()
    uvicorn.run(app, host="0.0.0.0", port=8000)
