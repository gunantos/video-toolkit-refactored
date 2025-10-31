"""
Subtitle processing: Whisper-based generator
"""

import time
from pathlib import Path
from typing import Optional, Tuple

import whisper

from core.utils.logging import get_logger

logger = get_logger(__name__)


def extract_audio_for_whisper(video_path: Path, audio_path: Path) -> bool:
    """Extract audio track optimized for Whisper (via ffmpeg)"""
    import subprocess
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    methods = [
        ["ffmpeg", "-y", "-i", str(video_path), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(audio_path)],
        ["ffmpeg", "-y", "-i", str(video_path), "-ar", "22050", "-ac", "1", "-c:a", "pcm_s16le", str(audio_path)],
        ["ffmpeg", "-y", "-i", str(video_path), "-q:a", "0", "-map", "a", str(audio_path)],
    ]
    for cmd in methods:
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            if audio_path.exists() and audio_path.stat().st_size > 1024:
                return True
        except Exception:
            continue
    return False


def generate_subtitle_whisper(audio_path: Path, output_folder: Path, src_lang: str = "zh", model: str = "base") -> Optional[Path]:
    """Generate subtitle SRT using Whisper"""
    try:
        start = time.time()
        model_obj = whisper.load_model(model)
        result = model_obj.transcribe(str(audio_path), language=src_lang, task="transcribe", verbose=False)
        srt_path = output_folder / "subtitle.srt"
        save_as_srt(result, srt_path)
        logger.info(f"Subtitle generated in {time.time()-start:.1f}s: {srt_path}")
        return srt_path
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return None


def save_as_srt(whisper_result, srt_path: Path):
    segments = whisper_result.get("segments", [])
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_time(seg.get('start', 0))} --> {format_time(seg.get('end', 0))}\n")
            f.write(seg.get("text", "").strip() + "\n\n")


def format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
