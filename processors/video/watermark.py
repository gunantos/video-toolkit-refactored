"""
Video watermark utility using FFmpeg drawtext/overlay
"""

import subprocess
from pathlib import Path
from typing import Optional

from core.utils.logging import get_logger

logger = get_logger(__name__)


def embed_watermark(
    video_path: Path,
    output_path: Path,
    text: Optional[str] = None,
    logo_path: Optional[Path] = None,
    position: str = "bottom_right",
    opacity: float = 0.7,
):
    """Embed text or logo watermark to a video using FFmpeg.
    position: top_left, top_right, bottom_left, bottom_right, center
    """
    filters = []
    
    if logo_path and Path(logo_path).exists():
        # Prepare overlay position
        pos_map = {
            "top_left": ("10", "10"),
            "top_right": ("W-w-10", "10"),
            "bottom_left": ("10", "H-h-10"),
            "bottom_right": ("W-w-10", "H-h-10"),
            "center": ("(W-w)/2", "(H-h)/2"),
        }
        x, y = pos_map.get(position, ("W-w-10", "H-h-10"))
        filters.append(f"[1]format=rgba,colorchannelmixer=aa={opacity}[logo];[0][logo]overlay={x}:{y}")
    
    if text:
        # Simple drawtext overlay with shadow
        draw = (
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{text}':fontsize=24:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2:"
        )
        # Positioning
        if position == "top_left":
            draw += "x=10:y=10"
        elif position == "top_right":
            draw += "x=w-tw-10:y=10"
        elif position == "bottom_left":
            draw += "x=10:y=h-th-10"
        elif position == "center":
            draw += "x=(w-tw)/2:y=(h-th)/2"
        else:  # bottom_right default
            draw += "x=w-tw-10:y=h-th-10"
        filters.append(draw)
    
    vf = ",".join(filters) if filters else None
    cmd = ["ffmpeg", "-y", "-i", str(video_path)]
    if logo_path and Path(logo_path).exists():
        cmd.extend(["-i", str(logo_path)])
    if vf:
        cmd.extend(["-filter_complex", vf])
    cmd.extend(["-c:v", "libx264", "-c:a", "copy", str(output_path)])
    
    try:
        subprocess.run(cmd, check=True)
        return output_path.exists() and output_path.stat().st_size > 1024
    except Exception as e:
        logger.error(f"Watermark failed: {e}")
        return False
