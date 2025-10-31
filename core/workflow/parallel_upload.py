"""
Parallel upload with concurrency control and result logging
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List
import json

from core.utils.logging import get_logger
from core.workflow.caption import render_platform_caption
from uploaders.platforms.tiktok import TikTokUploader
from uploaders.platforms.tiktok_success import wait_tiktok_success
from uploaders.manager import UploadManager

logger = get_logger(__name__)


async def upload_to_platform(platform: str, video: Path, metadata: Dict[str, Any], profile: str | None) -> Dict[str, Any]:
    try:
        cap = render_platform_caption(platform, metadata)
        if platform == "tiktok":
            u = TikTokUploader(profile_name=profile or "default")
            ok = u.upload(video, caption=cap.get("caption", ""), tags=cap.get("tags", []))
            ok2 = wait_tiktok_success(u.driver) if u.driver else False
            return {"platform": platform, "success": bool(ok and ok2)}
        elif platform == "telegram":
            res = UploadManager().upload("telegram", video, {"caption": cap.get("caption", video.stem)})
            return {"platform": platform, "success": bool(res)}
        else:
            # Placeholder for other platforms
            return {"platform": platform, "success": False, "error": "not_implemented"}
    except Exception as e:
        logger.error(f"Upload error on {platform}: {e}")
        return {"platform": platform, "success": False, "error": str(e)}


async def parallel_upload(platforms: List[str], video: Path, metadata: Dict[str, Any], profile: str | None, limit: int = 2) -> List[Dict[str, Any]]:
    sem = asyncio.Semaphore(limit)

    async def _wrapped(p: str):
        async with sem:
            return await upload_to_platform(p, video, metadata, profile)

    tasks = [_wrapped(p) for p in platforms]
    return await asyncio.gather(*tasks)


def save_upload_results(working_dir: Path, results: List[Dict[str, Any]]):
    out = working_dir / "upload_results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
