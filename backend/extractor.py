"""yt-dlp wrapper with extraction cache."""

import time
import uuid
import yt_dlp


class ExtractionCache:
    """In-memory cache for extraction results with TTL."""

    def __init__(self, ttl_seconds: int = 600):
        self._cache: dict[str, tuple[float, dict]] = {}
        self._ttl = ttl_seconds

    def store(self, extraction_id: str, data: dict) -> None:
        self._cache[extraction_id] = (time.time(), data)

    def get(self, extraction_id: str) -> dict | None:
        entry = self._cache.get(extraction_id)
        if entry is None:
            return None
        timestamp, data = entry
        if time.time() - timestamp > self._ttl:
            del self._cache[extraction_id]
            return None
        return data


# Global cache instance
cache = ExtractionCache(ttl_seconds=600)


def extract_video_info(url: str) -> dict:
    """Extract video info using yt-dlp. Returns dict with id, title, thumbnail, duration, formats."""
    extraction_id = uuid.uuid4().hex[:12]
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 60,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return {"id": extraction_id, "error": str(e)}

    formats = []
    for f in info.get("formats", []):
        # Only include formats with video
        if f.get("vcodec", "none") == "none":
            continue
        formats.append({
            "format_id": f.get("format_id", ""),
            "quality": f.get("format_note", f.get("height", "unknown")),
            "ext": f.get("ext", "mp4"),
            "filesize": f.get("filesize") or f.get("filesize_approx"),
            "height": f.get("height"),
            "url": f.get("url", ""),
        })

    # Sort by height descending
    formats.sort(key=lambda x: x.get("height") or 0, reverse=True)

    result = {
        "id": extraction_id,
        "title": info.get("title", "Untitled"),
        "thumbnail": info.get("thumbnail", ""),
        "duration": info.get("duration", 0),
        "formats": formats,
        "original_url": url,
    }
    cache.store(extraction_id, result)
    return result
