"""
Telegram-friendly compress: scale/bitrate to fit ~48MB
"""

import subprocess
from pathlib import Path

from core.utils.logging import get_logger

logger = get_logger(__name__)


def compress_for_telegram(input_video: Path, output_video: Path, target_size_mb: int = 48) -> bool:
    """Compress video to approximately target size using two-pass CRF/bitrate heuristics.
    Heuristic: assume duration to estimate bitrate; fall back to CRF if unknown.
    """
    try:
        # Get duration via ffprobe (seconds)
        cmd_dur = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            str(input_video)
        ]
        out = subprocess.check_output(cmd_dur, text=True).strip()
        duration = float(out) if out else 0.0
    except Exception:
        duration = 0.0

    output_video.parent.mkdir(parents=True, exist_ok=True)

    if duration > 0:
        # bitrate (bits/s) = target_size(bytes) * 8 / duration
        target_bits = target_size_mb * 1024 * 1024 * 8
        v_bitrate = int(max(200_000, target_bits * 0.85 / duration))  # 85% video bitrate
        a_bitrate = int(max(64_000, target_bits * 0.15 / duration))   # 15% audio bitrate
        v_bitrate_k = max(200, v_bitrate // 1000)
        a_bitrate_k = max(64, a_bitrate // 1000)
        cmd = [
            "ffmpeg", "-y", "-i", str(input_video),
            "-vf", "scale='min(960,iw)':-2",  # limit width to 960, keep aspect
            "-c:v", "libx264", "-preset", "medium", "-b:v", f"{v_bitrate_k}k",
            "-c:a", "aac", "-b:a", f"{a_bitrate_k}k",
            str(output_video)
        ]
    else:
        # fallback CRF
        cmd = [
            "ffmpeg", "-y", "-i", str(input_video),
            "-vf", "scale='min(960,iw)':-2",
            "-c:v", "libx264", "-preset", "medium", "-crf", "26",
            "-c:a", "aac", "-b:a", "96k",
            str(output_video)
        ]
    try:
        subprocess.run(cmd, check=True)
        # quick size check
        if output_video.exists() and output_video.stat().st_size <= target_size_mb * 1024 * 1024:
            logger.info(f"Compressed within target: {output_video.stat().st_size/1024/1024:.1f} MB")
        return output_video.exists()
    except Exception as e:
        logger.error(f"Compress failed: {e}")
        return False
