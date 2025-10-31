"""
Subtitle translation utilities
"""

from pathlib import Path
from typing import Optional

from deep_translator import GoogleTranslator

from core.utils.logging import get_logger

logger = get_logger(__name__)


def translate_subtitle_robust(srt_path: Path, output_folder: Path, target_lang: str = "id") -> Optional[Path]:
    try:
        lines = srt_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        out_lines = []
        buffer = []
        for line in lines:
            if line.strip().isdigit() or "-->" in line or not line.strip():
                # flush buffer
                if buffer:
                    text = " ".join(buffer)
                    translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
                    # naive split back (keep as single line)
                    out_lines.append(translated)
                    buffer = []
                out_lines.append(line)
            else:
                buffer.append(line)
        # last flush
        if buffer:
            text = " ".join(buffer)
            translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
            out_lines.append(translated)
        out_path = output_folder / f"{srt_path.stem}.translated.srt"
        out_path.write_text("\n".join(out_lines), encoding="utf-8")
        return out_path
    except Exception as e:
        logger.error(f"Subtitle translation failed: {e}")
        return None
