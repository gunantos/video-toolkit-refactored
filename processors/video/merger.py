"""
Video merger and splitter (FFmpeg wrappers)
"""

import subprocess
from pathlib import Path
from typing import List

from core.utils.logging import get_logger

logger = get_logger(__name__)


def concat_videos_from_folder(folder: Path, output_file: Path) -> bool:
    files = sorted(folder.glob("*.mp4"))
    if not files:
        return False
    list_file = output_file.with_suffix(".txt")
    list_file.write_text("\n".join([f"file '{f.as_posix()}'" for f in files]), encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output_file)]
    try:
        subprocess.run(cmd, check=True)
        return output_file.exists() and output_file.stat().st_size > 1024
    finally:
        try:
            list_file.unlink()
        except:
            pass


def split_video_by_duration(video_path: Path, output_folder: Path, duration: int):
    output_folder.mkdir(parents=True, exist_ok=True)
    pattern = str(output_folder / f"{video_path.stem}_part_%03d.mp4")
    cmd = [
        "ffmpeg","-y","-hide_banner","-loglevel","error",
        "-i", str(video_path),
        "-c","copy","-map","0",
        "-segment_time", str(duration), "-f","segment", "-reset_timestamps","1",
        pattern
    ]
    subprocess.run(cmd, check=True)
