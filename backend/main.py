"""Video Downloader API — FastAPI backend using Cobalt API."""

import os
import uuid

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from security import validate_url, verify_api_key

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

# Cobalt API instance URL
COBALT_URL = os.environ.get("COBALT_URL", "http://localhost:9000")

# In-memory cache for extraction results
_cache: dict[str, dict] = {}

QUALITY_OPTIONS = ["2160", "1440", "1080", "720", "480", "360"]


def require_auth(x_api_key: str = Header(None)):
    """Verify API key from request header."""
    if not x_api_key or not verify_api_key(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")


class ExtractRequest(BaseModel):
    url: str
    quality: str = "1080"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract(req: ExtractRequest, x_api_key: str = Header(None)):
    require_auth(x_api_key)
    if not validate_url(req.url):
        raise HTTPException(status_code=400, detail="URL not supported")

    extraction_id = uuid.uuid4().hex[:12]

    # Build format options for the user to choose from
    formats = []
    for q in QUALITY_OPTIONS:
        height = int(q)
        formats.append({
            "format_id": q,
            "quality": f"{q}p",
            "ext": "mp4",
            "filesize": None,
            "height": height,
        })

    result = {
        "id": extraction_id,
        "title": "Video",
        "thumbnail": "",
        "duration": 0,
        "formats": formats,
        "original_url": req.url,
    }
    _cache[extraction_id] = result
    return {
        "id": result["id"],
        "title": result["title"],
        "thumbnail": result["thumbnail"],
        "duration": result["duration"],
        "formats": formats,
    }


@app.get("/download/{extraction_id}")
async def download(extraction_id: str, format: str, x_api_key: str = Header(None)):
    require_auth(x_api_key)
    data = _cache.get(extraction_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Extraction expired or not found")

    # Call Cobalt API to get download URL
    cobalt_payload = {
        "url": data["original_url"],
        "videoQuality": format,
        "downloadMode": "auto",
        "filenameStyle": "classic",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                COBALT_URL,
                json=cobalt_payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Cobalt API unreachable: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Cobalt error: {resp.text}")

    result = resp.json()
    status = result.get("status")

    if status == "error":
        raise HTTPException(status_code=422, detail=result.get("error", "Unknown error"))

    # Get the download URL from cobalt response
    download_url = None
    if status in ("redirect", "tunnel"):
        download_url = result.get("url")
    elif status == "local-processing":
        download_url = result.get("tunnelUrl")
    elif status == "picker":
        # Multiple items available, take the first video
        items = result.get("items", [])
        if items:
            download_url = items[0].get("url")

    if not download_url:
        raise HTTPException(status_code=500, detail="No download URL from Cobalt")

    # Stream the video from cobalt/source to the iOS client
    async def stream():
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            async with client.stream("GET", download_url) as resp:
                async for chunk in resp.aiter_bytes(64 * 1024):
                    yield chunk

    return StreamingResponse(stream(), media_type="video/mp4")


if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    load_dotenv()
    uvicorn.run(app, host="0.0.0.0", port=8000)
